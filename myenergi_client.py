"""myenergi API client for Eddi control."""

import requests
from requests.auth import HTTPDigestAuth


DIRECTOR_URL = "https://director.myenergi.net"


class MyenergiClient:
    """Client for the myenergi API using HTTP Digest Authentication."""

    def __init__(self, hub_serial: str, api_key: str, server: str = None):
        self.hub_serial = hub_serial
        self.api_key = api_key
        self.auth = HTTPDigestAuth(hub_serial, api_key)
        self.base_url = f"https://{server}.myenergi.net" if server else None

    def _discover_server(self) -> str:
        """Query the director to find which server this hub is on."""
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
        return asn.strip()

    def _get_base_url(self) -> str:
        if not self.base_url:
            server = self._discover_server()
            self.base_url = f"https://{server}.myenergi.net"
            print(f"Discovered server: {server}")
        return self.base_url

    def _get(self, path: str) -> dict:
        """Make an authenticated GET request to the API."""
        url = f"{self._get_base_url()}{path}"
        resp = requests.get(url, auth=self.auth, timeout=15)
        resp.raise_for_status()
        return resp.json()

    # ── Device discovery ──────────────────────────────────────────────

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

    # ── Eddi control ──────────────────────────────────────────────────

    def eddi_start(self, serial: str) -> dict:
        """Set Eddi to normal (active) mode."""
        return self._get(f"/cgi-eddi-mode-E{serial}-1")

    def eddi_stop(self, serial: str) -> dict:
        """Set Eddi to stopped mode."""
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
        return self._get(f"/cgi-eddi-boost-E{serial}-{heater_code}-{minutes}")

    def eddi_cancel_boost(self, serial: str, heater: int = 1) -> dict:
        """Cancel an active boost on the specified heater."""
        return self.eddi_boost(serial, heater=heater, minutes=0)

    # ── Eddi history ──────────────────────────────────────────────────

    def eddi_day_data(self, serial: str, year: int, month: int, day: int) -> dict:
        """Get minute-by-minute energy data for a specific day."""
        return self._get(f"/cgi-jday-E{serial}-{year}-{month}-{day}")
