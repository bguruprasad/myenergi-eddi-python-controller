#!/usr/bin/env python3
"""CLI tool to control myenergi Eddi - start, stop, boost."""

import argparse
import os
import sys
import warnings

warnings.filterwarnings("ignore", message=".*urllib3.*OpenSSL.*")

from dotenv import load_dotenv  # pylint: disable=wrong-import-position

from myenergi_client import MyenergiClient  # pylint: disable=wrong-import-position

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


def get_client() -> MyenergiClient:
    """Load credentials from .env and return an authenticated API client."""
    load_dotenv()
    hub_serial = os.getenv("MYENERGI_HUB_SERIAL")
    api_key = os.getenv("MYENERGI_API_KEY")
    server = os.getenv("MYENERGI_SERVER")

    if not hub_serial or not api_key or hub_serial == "your_hub_serial_here":
        print("Error: Set MYENERGI_HUB_SERIAL and MYENERGI_API_KEY in .env")
        print("  cp .env.example .env && edit .env")
        sys.exit(1)

    return MyenergiClient(hub_serial, api_key, server=server or None)


def pick_eddi(client: MyenergiClient, serial: str = None) -> str:
    """Return the Eddi serial to use. Auto-selects if only one exists."""
    if serial:
        return serial

    eddis = client.get_eddi_status()
    if not eddis:
        print("Error: No Eddi devices found on your hub.")
        sys.exit(1)

    if len(eddis) == 1:
        return str(eddis[0]["sno"])

    print("Multiple Eddi devices found. Use --serial to pick one:")
    for e in eddis:
        print(f"  Serial: {e['sno']}")
    sys.exit(1)


def format_power(watts: int) -> str:
    """Format a power value in watts to a human-readable string."""
    if abs(watts) >= 1000:
        return f"{watts / 1000:.1f} kW"
    return f"{watts} W"


def cmd_status(args):
    """Display current Eddi status including temps and power."""
    client = get_client()
    serial = pick_eddi(client, args.serial)
    eddi = client.get_eddi_by_serial(serial)

    status_code = eddi.get("sta", 0)
    status_text = EDDI_STATUS.get(status_code, f"Unknown ({status_code})")
    heater_num = eddi.get("hno", 0)
    active_heater = EDDI_HEATER_STATUS.get(heater_num, f"Unknown ({heater_num})")
    diverted = eddi.get("div", 0)
    grid = eddi.get("grd", 0)
    generated = eddi.get("gen", 0)
    temp_1 = eddi.get("tp1", None)
    temp_2 = eddi.get("tp2", None)
    date = eddi.get("dat", "")
    time = eddi.get("tim", "")

    print(f"{'='*45}")
    print(f" Eddi Status  -  Serial: {serial}")
    print(f"{'='*45}")
    print(f"  Status:         {status_text}")
    print(f"  Active heater:  {active_heater}")
    print(f"  Diverted:       {format_power(diverted)}")
    print(f"  Grid:           {format_power(grid)}")
    print(f"  Generated:      {format_power(generated)}")
    if temp_1 is not None:
        print(f"  Temp (tank 1):  {temp_1 / 10:.1f} C")
    if temp_2 is not None:
        print(f"  Temp (tank 2):  {temp_2 / 10:.1f} C")
    print(f"  Last updated:   {date} {time} UTC")
    print(f"{'='*45}")


def cmd_start(args):
    """Start the Eddi in normal (diverting) mode."""
    client = get_client()
    serial = pick_eddi(client, args.serial)
    result = client.eddi_start(serial)
    print(f"Eddi {serial}: Started (normal mode)")
    return result


def cmd_stop(args):
    """Stop the Eddi."""
    client = get_client()
    serial = pick_eddi(client, args.serial)
    result = client.eddi_stop(serial)
    print(f"Eddi {serial}: Stopped")
    return result


def cmd_boost(args):
    """Boost a heater for a given duration, or cancel an active boost."""
    client = get_client()
    serial = pick_eddi(client, args.serial)

    if args.cancel:
        result = client.eddi_cancel_boost(serial, heater=args.heater)
        print(f"Eddi {serial}: Boost cancelled for heater {args.heater}")
    else:
        result = client.eddi_boost(
            serial, heater=args.heater, minutes=args.minutes
        )
        print(
            f"Eddi {serial}: Boosting heater {args.heater} "
            f"for {args.minutes} min"
        )
    return result


def cmd_devices(_args):
    """List all Eddi devices connected to the hub."""
    client = get_client()
    eddis = client.get_eddi_status()
    if not eddis:
        print("No Eddi devices found.")
        return
    print(f"Found {len(eddis)} Eddi device(s):")
    for e in eddis:
        status = EDDI_STATUS.get(e.get("sta", 0), "Unknown")
        print(f"  Serial: {e['sno']}  Status: {status}")


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
  %(prog)s boost --cancel           Cancel active boost
""",
    )
    parser.add_argument(
        "--serial", "-s",
        help="Eddi serial number (auto-detected if only one)",
    )
    sub = parser.add_subparsers(dest="command", required=True)

    sub.add_parser("status", help="Show Eddi status")
    sub.add_parser("start", help="Start Eddi (normal mode)")
    sub.add_parser("stop", help="Stop Eddi")
    sub.add_parser("devices", help="List all Eddi devices")

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
