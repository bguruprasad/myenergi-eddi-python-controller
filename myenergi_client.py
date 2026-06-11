"""myenergi API client for Eddi control."""

from __future__ import annotations

import logging
import time
import warnings
import urllib3

import requests
from requests.auth import HTTPDigestAuth

warnings.filterwarnings("ignore", category=urllib3.exceptions.NotOpenSSLWarning)

logger = logging.getLogger(__name__)

DIRECTOR_URL = "https://director.myenergi.net"

# Eddi `sta` value when the device is stopped. Anything else means running
# (Paused / Diverting / Boosting / Max Temp Reached).
STATUS_STOPPED = 6

# Defaults for verified mode changes: poll status after each command to
# confirm the device actually obeyed, retrying a few times before giving up.
VERIFY_ATTEMPTS = 3
VERIFY_WAIT_SECONDS = 60

# Within each attempt, poll the status this many times (with a short pause
# between polls) to account for cloud API lag where the device has already
# changed state but the server hasn't caught up yet.
VERIFY_POLLS = 3
VERIFY_POLL_INTERVAL = 15  # seconds between status polls within one attempt


class MyenergiClient:
    """Client for the myenergi API using HTTP Digest Authentication."""

    def __init__(self, hub_serial: str, api_key: str, server: str = None):
        self.hub_serial = hub_serial
        self.api_key = api_key
        self.auth = HTTPDigestAuth(hub_serial, api_key)
        self.base_url = f"https://{server}.myenergi.net" if server else None

    def _discover_server(self) -> str:
        """Query the director to find which server this hub is on."""
        logger.info("Discovering server from director...")
        resp = requests.get(
            f"{DIRECTOR_URL}/cgi-jstatus-*",
            auth=self.auth,
            timeout=15,
        )
        resp.raise_for_status()
        asn = resp.headers.get("X_MYENERGI-asn") or resp.headers.get("x_myenergi-asn")
        if not asn:
            raise RuntimeError(
                "Could not determine server from director response. "
                f"Headers: {dict(resp.headers)}"
            )
        asn = asn.strip()
        # Director may return just "s18" or full "s18.myenergi.net"
        if ".myenergi.net" in asn:
            return asn
        return asn

    def _get_base_url(self) -> str:
        """Return the base URL, discovering the server if needed."""
        if not self.base_url:
            server = self._discover_server()
            if ".myenergi.net" in server:
                self.base_url = f"https://{server}"
            else:
                self.base_url = f"https://{server}.myenergi.net"
            logger.info("Discovered server: %s", self.base_url)
        return self.base_url

    def _get(self, path: str) -> dict:
        """Make an authenticated GET request to the API."""
        url = f"{self._get_base_url()}{path}"
        logger.info("API call: GET %s", url)
        resp = requests.get(url, auth=self.auth, timeout=15)
        resp.raise_for_status()
        data = resp.json()
        logger.info("API response [%s]: %s", resp.status_code, data)
        return data

    # -- Device discovery ------------------------------------------------

    def get_all_status(self) -> dict:
        """Get status of all connected devices."""
        return self._get("/cgi-jstatus-*")

    def get_eddi_status(self) -> list[dict]:
        """Get status of all Eddi devices."""
        data = self._get("/cgi-jstatus-E")
        return data.get("eddi", [])

    def get_eddi_by_serial(self, serial: str) -> dict:
        """Get status of a specific Eddi by serial number."""
        data = self._get(f"/cgi-jstatus-E{serial}")
        eddis = data.get("eddi", [])
        if not eddis:
            raise ValueError(f"Eddi {serial} not found")
        return eddis[0]

    # -- Eddi control ----------------------------------------------------

    def eddi_start(self, serial: str) -> dict:
        """Set Eddi to normal (active) mode."""
        logger.info("Starting Eddi %s (normal mode)", serial)
        return self._get(f"/cgi-eddi-mode-E{serial}-1")

    def eddi_stop(self, serial: str) -> dict:
        """Set Eddi to stopped mode."""
        logger.info("Stopping Eddi %s", serial)
        return self._get(f"/cgi-eddi-mode-E{serial}-0")

    def eddi_boost(self, serial: str, heater: int = 1, minutes: int = 30) -> dict:
        """
        Boost an Eddi heater for a given duration.

        Args:
            serial: Eddi serial number
            heater: 1 or 2 (which heater to boost)
            minutes: Duration in minutes (0 to cancel)
        """
        if heater not in (1, 2):
            raise ValueError("Heater must be 1 or 2")
        heater_code = heater * 10  # 10 for heater 1, 20 for heater 2
        logger.info(
            "Boosting Eddi %s heater %d for %d minutes",
            serial, heater, minutes,
        )
        return self._get(f"/cgi-eddi-boost-E{serial}-{heater_code}-{minutes}")

    def eddi_cancel_boost(self, serial: str, heater: int = 1) -> dict:
        """Cancel an active boost on the specified heater."""
        logger.info("Cancelling boost on Eddi %s heater %d", serial, heater)
        return self.eddi_boost(serial, heater=heater, minutes=0)

    # -- Verified mode changes -------------------------------------------

    def _set_mode_verified(  # pylint: disable=too-many-arguments
        self,
        serial: str,
        *,
        command,
        is_target,
        label: str,
        attempts: int = VERIFY_ATTEMPTS,
        wait_seconds: int = VERIFY_WAIT_SECONDS,
    ) -> tuple[bool, int]:
        """Issue a mode command, then poll status to confirm it took effect.

        Sometimes the API accepts a command (HTTP 200) but the Eddi does not
        actually change state. This re-issues the command up to `attempts`
        times, waiting `wait_seconds` between each command and its check.

        Args:
            serial: Eddi serial number.
            command: Zero-arg callable that issues the mode command.
            is_target: Predicate on the `sta` status code; True when the
                desired state has been reached.
            label: Human-readable action name for logging (e.g. "stop").
            attempts: Max number of command+verify cycles.
            wait_seconds: Seconds to wait after a command before checking.

        Returns:
            (success, last_status) where last_status is the most recent `sta`.
        """
        last_status = -1
        for attempt in range(1, attempts + 1):
            logger.info(
                "Eddi %s: %s attempt %d/%d", serial, label, attempt, attempts
            )
            try:
                cmd_result = command()
                logger.info(
                    "Eddi %s: %s command result (attempt %d/%d): %s",
                    serial, label, attempt, attempts, cmd_result,
                )
            except Exception:  # pylint: disable=broad-except
                logger.exception(
                    "Eddi %s: %s command raised an error (attempt %d/%d)",
                    serial, label, attempt, attempts,
                )

            logger.info(
                "Waiting %ds before verifying %s...", wait_seconds, label
            )
            time.sleep(wait_seconds)

            # Poll status multiple times within this attempt to ride out
            # cloud API lag (the device may have obeyed but the server
            # hasn't reflected the new state yet).
            verified = False
            for poll in range(1, VERIFY_POLLS + 1):
                logger.info(
                    "Eddi %s: verifying %s (attempt %d/%d, poll %d/%d)...",
                    serial, label, attempt, attempts, poll, VERIFY_POLLS,
                )
                try:
                    eddi = self.get_eddi_by_serial(serial)
                    last_status = eddi.get("sta", -1)
                except Exception:  # pylint: disable=broad-except
                    logger.exception(
                        "Eddi %s: status check failed "
                        "(attempt %d/%d, poll %d/%d)",
                        serial, attempt, attempts, poll, VERIFY_POLLS,
                    )
                    # Status unknown; sleep and retry the poll.
                    if poll < VERIFY_POLLS:
                        time.sleep(VERIFY_POLL_INTERVAL)
                    continue

                if is_target(last_status):
                    logger.info(
                        "Eddi %s: %s verified on attempt %d, poll %d "
                        "(sta=%s)",
                        serial, label, attempt, poll, last_status,
                    )
                    verified = True
                    break

                logger.info(
                    "Eddi %s: %s not yet confirmed "
                    "(attempt %d/%d, poll %d/%d, sta=%s)",
                    serial, label, attempt, attempts,
                    poll, VERIFY_POLLS, last_status,
                )
                if poll < VERIFY_POLLS:
                    time.sleep(VERIFY_POLL_INTERVAL)

            if verified:
                return True, last_status

            logger.warning(
                "Eddi %s: %s not confirmed after attempt %d (sta=%s)",
                serial, label, attempt, last_status,
            )

        logger.error(
            "Eddi %s: %s FAILED after %d attempts (sta=%s)",
            serial, label, attempts, last_status,
        )
        return False, last_status

    def eddi_stop_verified(
        self,
        serial: str,
        attempts: int = VERIFY_ATTEMPTS,
        wait_seconds: int = VERIFY_WAIT_SECONDS,
    ) -> tuple[bool, int]:
        """Stop the Eddi and confirm it actually stopped, retrying if not."""
        return self._set_mode_verified(
            serial,
            command=lambda: self.eddi_stop(serial),
            is_target=lambda sta: sta == STATUS_STOPPED,
            label="stop",
            attempts=attempts,
            wait_seconds=wait_seconds,
        )

    def eddi_start_verified(
        self,
        serial: str,
        attempts: int = VERIFY_ATTEMPTS,
        wait_seconds: int = VERIFY_WAIT_SECONDS,
    ) -> tuple[bool, int]:
        """Start the Eddi and confirm it left the stopped state, retrying."""
        return self._set_mode_verified(
            serial,
            command=lambda: self.eddi_start(serial),
            is_target=lambda sta: sta != STATUS_STOPPED,
            label="start",
            attempts=attempts,
            wait_seconds=wait_seconds,
        )

    # -- Eddi history ----------------------------------------------------

    def eddi_day_data(self, serial: str, year: int, month: int, day: int) -> dict:
        """Get minute-by-minute energy data for a specific day."""
        return self._get(f"/cgi-jday-E{serial}-{year}-{month}-{day}")
