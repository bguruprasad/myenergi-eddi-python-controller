# Changelog

## 2026-06-06

### Initial Release

- **API Research** - Investigated myenergi unofficial REST API; documented authentication (HTTP Digest Auth), director-based server discovery, and all available endpoints for Zappi, Eddi, Libbi, and Harvi devices. Saved findings to `API_RESEARCH.md`.

- **Project Setup** - Created Python project with `myenergi_client.py` (API client) and `eddi_control.py` (CLI tool). Added `requirements.txt` (requests, python-dotenv), `.env.example` for credentials, and `.gitignore`.

- **Eddi CLI Tool** - Built CLI with the following commands:
  - `status` - Show Eddi status (mode, temps, power, grid, generation)
  - `start` - Set Eddi to normal (active) mode
  - `stop` - Set Eddi to stopped mode
  - `boost` - Boost a heater for a given duration (heater 1 or 2, configurable minutes)
  - `devices` - List all connected Eddi devices
  - Auto-detects Eddi serial when only one device is present

- **Bug Fix: Director hostname** - The director API returns the full hostname (e.g. `s18.myenergi.net`) rather than just the server prefix (`s18`). Fixed `_discover_server()` and `_get_base_url()` to handle both formats, preventing the doubled hostname error (`s18.myenergi.net.myenergi.net`).

- **Fix: LibreSSL warning** - Suppressed `NotOpenSSLWarning` from urllib3 caused by macOS system Python using LibreSSL 2.8.3 instead of OpenSSL 1.1.1+. Added early `warnings.filterwarnings()` call before imports.

- **Cron Automation** - Set up cron jobs to automatically stop Eddi at 10:00 AM IST and start at 8:00 PM IST daily. Output logged to `eddi_cron.log`.
