#!/usr/bin/env python3
"""CLI tool to control myenergi Eddi - start, stop, boost."""

import argparse
import logging
import logging.handlers
import os
import sys
import time
import warnings

warnings.filterwarnings("ignore", message=".*urllib3.*OpenSSL.*")

from dotenv import load_dotenv  # pylint: disable=wrong-import-position

from myenergi_client import MyenergiClient  # pylint: disable=wrong-import-position
from notifier import send_telegram_multi  # pylint: disable=wrong-import-position

logger = logging.getLogger("eddi_control")

# Eddi status codes
EDDI_STATUS = {
    1: "Paused",
    3: "Diverting",
    4: "Boosting",
    5: "Max Temp Reached",
    6: "Stopped",
}

EDDI_HEATER_STATUS = {
    0: "None",
    1: "Heater 1",
    2: "Heater 2",
}

LOG_FORMAT = "%(asctime)s [%(levelname)s] %(name)s - %(message)s"
LOG_DATE_FORMAT = "%Y-%m-%d %H:%M:%S"

LOG_FILE = os.path.join(os.path.dirname(os.path.abspath(__file__)), "eddi_cron.log")
LOG_MAX_BYTES = 10 * 1024 * 1024  # 10 MB
LOG_BACKUP_COUNT = 1  # keep 1 rotated copy


def setup_logging(verbose: bool = False):
    """Configure logging with timestamps to both console and rotating file."""
    level = logging.DEBUG if verbose else logging.INFO

    console = logging.StreamHandler(sys.stdout)
    console.setFormatter(logging.Formatter(LOG_FORMAT, datefmt=LOG_DATE_FORMAT))

    file_handler = logging.handlers.RotatingFileHandler(
        LOG_FILE,
        maxBytes=LOG_MAX_BYTES,
        backupCount=LOG_BACKUP_COUNT,
    )
    file_handler.setFormatter(
        logging.Formatter(LOG_FORMAT, datefmt=LOG_DATE_FORMAT)
    )

    logging.basicConfig(
        level=level,
        handlers=[console, file_handler],
    )


def get_client() -> MyenergiClient:
    """Load credentials from .env and return an authenticated API client."""
    load_dotenv()
    hub_serial = os.getenv("MYENERGI_HUB_SERIAL")
    api_key = os.getenv("MYENERGI_API_KEY")
    server = os.getenv("MYENERGI_SERVER")

    if not hub_serial or not api_key or hub_serial == "your_hub_serial_here":
        logger.error(
            "Set MYENERGI_HUB_SERIAL and MYENERGI_API_KEY in .env"
        )
        logger.error("  cp .env.example .env && edit .env")
        sys.exit(1)

    return MyenergiClient(hub_serial, api_key, server=server or None)


def notify(message: str):
    """Send a Telegram notification if bot credentials are configured."""
    token = os.getenv("TELEGRAM_BOT_TOKEN")
    chat_ids = os.getenv("TELEGRAM_CHAT_ID")

    if not token or not chat_ids:
        logger.debug("Telegram notifications not configured, skipping")
        return

    send_telegram_multi(token, chat_ids, message)


def pick_eddi(client: MyenergiClient, serial: str = None) -> str:
    """Return the Eddi serial to use. Auto-selects if only one exists."""
    if serial:
        return serial

    eddis = client.get_eddi_status()
    if not eddis:
        logger.error("No Eddi devices found on your hub.")
        sys.exit(1)

    if len(eddis) == 1:
        return str(eddis[0]["sno"])

    logger.error("Multiple Eddi devices found. Use --serial to pick one:")
    for eddi in eddis:
        logger.error("  Serial: %s", eddi['sno'])
    sys.exit(1)


def format_power(watts: int) -> str:
    """Format a power value in watts to a human-readable string."""
    if abs(watts) >= 1000:
        return f"{watts / 1000:.1f} kW"
    return f"{watts} W"


def cmd_status(args):  # pylint: disable=too-many-locals
    """Display current Eddi status including temps and power."""
    start_time = time.time()
    logger.info("Fetching Eddi status...")

    client = get_client()
    serial = pick_eddi(client, args.serial)
    eddi = client.get_eddi_by_serial(serial)

    status_code = eddi.get("sta", 0)
    status_text = EDDI_STATUS.get(status_code, f"Unknown ({status_code})")
    heater_num = eddi.get("hno", 0)
    active_heater = EDDI_HEATER_STATUS.get(
        heater_num, f"Unknown ({heater_num})"
    )
    diverted = eddi.get("div", 0)
    grid = eddi.get("grd", 0)
    generated = eddi.get("gen", 0)
    temp_1 = eddi.get("tp1", None)
    temp_2 = eddi.get("tp2", None)
    date = eddi.get("dat", "")
    eddi_time = eddi.get("tim", "")

    logger.info("=" * 45)
    logger.info(" Eddi Status  -  Serial: %s", serial)
    logger.info("=" * 45)
    logger.info("  Status:         %s", status_text)
    logger.info("  Active heater:  %s", active_heater)
    logger.info("  Diverted:       %s", format_power(diverted))
    logger.info("  Grid:           %s", format_power(grid))
    logger.info("  Generated:      %s", format_power(generated))
    if temp_1 is not None:
        logger.info("  Temp (tank 1):  %.1f C", temp_1 / 10)
    if temp_2 is not None:
        logger.info("  Temp (tank 2):  %.1f C", temp_2 / 10)
    logger.info("  Last updated:   %s %s UTC", date, eddi_time)
    logger.info("=" * 45)

    elapsed = time.time() - start_time
    logger.info("Completed in %.2fs", elapsed)

    # Build compact status message for Telegram
    msg = f"📊 Eddi Status: {status_text} | Grid: {format_power(grid)}."
    notify(msg)


def status_text_for(status_code: int) -> str:
    """Return a human-readable name for an Eddi `sta` status code."""
    return EDDI_STATUS.get(status_code, f"Unknown ({status_code})")


def cmd_start(args):
    """Start the Eddi in normal (diverting) mode."""
    start_time = time.time()
    logger.info("Starting Eddi...")

    client = get_client()
    serial = pick_eddi(client, args.serial)

    if args.no_verify:
        client.eddi_start(serial)
        elapsed = time.time() - start_time
        logger.info("Eddi %s: Started (normal mode) [%.2fs]", serial, elapsed)
        notify("🟢 Your Eddi water heater has been started.")
        return

    success, last_status = client.eddi_start_verified(serial)
    elapsed = time.time() - start_time

    if success:
        logger.info("Eddi %s: Started & verified [%.2fs]", serial, elapsed)
        notify("🟢 Your Eddi water heater has been started (verified).")
        return

    logger.error("Eddi %s: start FAILED [%.2fs]", serial, elapsed)
    notify(
        f"⚠️ FAILED to start your Eddi water heater. "
        f"Current state: {status_text_for(last_status)}. "
        f"Please check manually."
    )
    sys.exit(1)


def cmd_stop(args):
    """Stop the Eddi."""
    start_time = time.time()
    logger.info("Stopping Eddi...")

    client = get_client()
    serial = pick_eddi(client, args.serial)

    if args.no_verify:
        client.eddi_stop(serial)
        elapsed = time.time() - start_time
        logger.info("Eddi %s: Stopped [%.2fs]", serial, elapsed)
        notify("🔴 Your Eddi water heater has been stopped.")
        return

    success, last_status = client.eddi_stop_verified(serial)
    elapsed = time.time() - start_time

    if success:
        logger.info("Eddi %s: Stopped & verified [%.2fs]", serial, elapsed)
        notify("🔴 Your Eddi water heater has been stopped (verified).")
        return

    logger.error("Eddi %s: stop FAILED [%.2fs]", serial, elapsed)
    notify(
        f"⚠️ FAILED to stop your Eddi water heater. "
        f"Current state: {status_text_for(last_status)}. "
        f"Please check manually."
    )
    sys.exit(1)


def cmd_boost(args):
    """Boost a heater for a given duration, or cancel an active boost."""
    start_time = time.time()
    client = get_client()
    serial = pick_eddi(client, args.serial)

    if args.cancel:
        logger.info("Cancelling boost on Eddi %s heater %d...",
                     serial, args.heater)
        client.eddi_cancel_boost(serial, heater=args.heater)
        elapsed = time.time() - start_time
        msg = (
            f"Eddi {serial}: Boost cancelled for "
            f"heater {args.heater} [{elapsed:.2f}s]"
        )
        logger.info(msg)
        notify(
            "⏹ Your Eddi water heater boost has been cancelled."
        )
    else:
        logger.info("Boosting Eddi %s heater %d for %d min...",
                     serial, args.heater, args.minutes)
        client.eddi_boost(
            serial, heater=args.heater, minutes=args.minutes
        )
        elapsed = time.time() - start_time
        msg = (
            f"Eddi {serial}: Boosting heater {args.heater} "
            f"for {args.minutes} min [{elapsed:.2f}s]"
        )
        logger.info(msg)
        notify(
            f"⚡ Your Eddi water heater is boosting "
            f"heater {args.heater} for {args.minutes} min."
        )


def cmd_devices(_args):
    """List all Eddi devices connected to the hub."""
    start_time = time.time()
    logger.info("Discovering Eddi devices...")

    client = get_client()
    eddis = client.get_eddi_status()

    if not eddis:
        logger.warning("No Eddi devices found.")
        return

    logger.info("Found %d Eddi device(s):", len(eddis))
    for eddi in eddis:
        status = EDDI_STATUS.get(eddi.get("sta", 0), "Unknown")
        logger.info("  Serial: %s  Status: %s", eddi['sno'], status)

    elapsed = time.time() - start_time
    logger.info("Completed in %.2fs", elapsed)


def main():
    """Parse CLI arguments and dispatch to the appropriate command."""
    parser = argparse.ArgumentParser(
        description="Control myenergi Eddi - start, stop, and boost",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""\
examples:
  %(prog)s status                  Show Eddi status
  %(prog)s start                   Start Eddi (normal mode)
  %(prog)s stop                    Stop Eddi
  %(prog)s boost --minutes 30      Boost heater 1 for 30 min
  %(prog)s boost --heater 2 -m 60  Boost heater 2 for 60 min
  %(prog)s boost --cancel          Cancel active boost
""",
    )
    parser.add_argument(
        "--serial", "-s",
        help="Eddi serial number (auto-detected if only one)",
    )
    parser.add_argument(
        "--verbose", "-v", action="store_true",
        help="Enable debug logging",
    )
    sub = parser.add_subparsers(dest="command", required=True)

    sub.add_parser("status", help="Show Eddi status")
    sub.add_parser("devices", help="List all Eddi devices")

    start_p = sub.add_parser("start", help="Start Eddi (normal mode)")
    start_p.add_argument(
        "--no-verify", action="store_true",
        help="Skip status verification (faster, no 60s wait)",
    )

    stop_p = sub.add_parser("stop", help="Stop Eddi")
    stop_p.add_argument(
        "--no-verify", action="store_true",
        help="Skip status verification (faster, no 60s wait)",
    )

    boost_p = sub.add_parser("boost", help="Boost a heater")
    boost_p.add_argument(
        "--heater", type=int, default=1, choices=[1, 2],
        help="Heater number (default: 1)",
    )
    boost_p.add_argument(
        "--minutes", "-m", type=int, default=30,
        help="Boost duration in minutes (default: 30)",
    )
    boost_p.add_argument(
        "--cancel", action="store_true",
        help="Cancel active boost",
    )

    args = parser.parse_args()
    setup_logging(verbose=args.verbose)

    commands = {
        "status": cmd_status,
        "start": cmd_start,
        "stop": cmd_stop,
        "boost": cmd_boost,
        "devices": cmd_devices,
    }
    commands[args.command](args)


if __name__ == "__main__":
    main()
