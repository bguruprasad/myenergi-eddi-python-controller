# myenergi Eddi Controller

Automate start/stop and boost control for your myenergi Eddi via the unofficial API. Includes optional WhatsApp notifications via Callmebot.

## Features

- Start, stop, and boost your Eddi water heater from the command line
- View real-time status (power, temperatures, mode)
- Schedule automation via cron
- WhatsApp notifications on every action (optional)
- Structured logging with timestamps and duration tracking
- Verbose mode (`-v`) for debugging API calls

## Setup

```bash
python3 -m pip install -r requirements.txt
cp .env.example .env
# Edit .env with your hub serial and API key
```

### Getting your credentials
1. Open the **myenergi app** on your phone (iOS/Android)
2. Go to **My Account** > **Advanced**
3. Note your **Hub Serial Number**
4. Generate an **API Key**

## Environment Variables

Copy `.env.example` to `.env` and set the following:

| Variable | Required | Description |
|----------|----------|-------------|
| `MYENERGI_HUB_SERIAL` | Yes | Your hub serial number (found in the app under Hub, or printed on the device) |
| `MYENERGI_API_KEY` | Yes | API key generated from the myenergi mobile app (My Account > Advanced) |
| `MYENERGI_SERVER` | No | Server hostname, e.g. `s18` (auto-discovered from the director if not set) |
| `CALLMEBOT_PHONE` | No | Your phone number with country code for WhatsApp notifications (e.g. `+353861234567`) |
| `CALLMEBOT_API_KEY` | No | API key from Callmebot for WhatsApp notifications |

## Usage

```bash
# Check Eddi status
python3 eddi_control.py status

# Start Eddi (normal mode)
python3 eddi_control.py start

# Stop Eddi
python3 eddi_control.py stop

# Boost heater 1 for 30 minutes
python3 eddi_control.py boost --heater 1 --minutes 30

# Boost heater 2 for 60 minutes
python3 eddi_control.py boost --heater 2 --minutes 60

# Cancel active boost
python3 eddi_control.py boost --cancel

# List all Eddi devices
python3 eddi_control.py devices

# Enable debug logging
python3 eddi_control.py -v status
```

## Logging

All commands produce timestamped logs with duration tracking:

```
2026-06-06 10:23:38 [INFO] eddi_control - Fetching Eddi status...
2026-06-06 10:23:38 [INFO] myenergi_client - Discovered server: https://s18.myenergi.net
2026-06-06 10:23:39 [INFO] eddi_control -   Status:         Stopped
2026-06-06 10:23:39 [INFO] eddi_control -   Grid:           76 W
2026-06-06 10:23:39 [INFO] eddi_control - Completed in 0.63s
```

Use `-v` for verbose/debug output including HTTP request details.

## Automation (Cron)

Schedule Eddi start/stop using cron. Logs go to `eddi_cron.log`.

### Managing cron jobs

```bash
# List current cron jobs
crontab -l

# Edit cron jobs (opens in text editor)
crontab -e

# Remove all cron jobs (careful!)
crontab -r
```

### Cron time format

```
MIN  HOUR  DAY  MONTH  WEEKDAY  command
 0    10    *     *       *      # every day at 10:00
 0    20    *     *      1-5     # weekdays only at 20:00
*/30  *     *     *       *      # every 30 minutes
```

### Examples

```bash
# Stop at 10am, start at 8pm daily
0 10 * * * cd /path/to/myenergi && /usr/bin/python3 eddi_control.py stop >> /path/to/myenergi/eddi_cron.log 2>&1
0 20 * * * cd /path/to/myenergi && /usr/bin/python3 eddi_control.py start >> /path/to/myenergi/eddi_cron.log 2>&1

# Weekdays only - stop at 10am, start at 8pm
0 10 * * 1-5 cd /path/to/myenergi && /usr/bin/python3 eddi_control.py stop >> /path/to/myenergi/eddi_cron.log 2>&1
0 20 * * 1-5 cd /path/to/myenergi && /usr/bin/python3 eddi_control.py start >> /path/to/myenergi/eddi_cron.log 2>&1
```

### Check logs

```bash
cat eddi_cron.log
```

## WhatsApp Notifications (Optional)

Get a WhatsApp message every time the Eddi is started, stopped, boosted, or when you check status. Powered by [Callmebot](https://www.callmebot.com/).

### Setup

1. Add **+34 611 04 87 48** to your WhatsApp contacts
2. Send **`I allow callmebot to send me messages`** to that number on WhatsApp
3. You'll receive an **API key** in the reply
4. Add to your `.env`:
   ```
   CALLMEBOT_PHONE=+353861234567
   CALLMEBOT_API_KEY=your_api_key
   ```

### Notification messages

| Command | WhatsApp Message |
|---------|-----------------|
| `start` | 🟢 Your Eddi water heater has been started. |
| `stop` | 🔴 Your Eddi water heater has been stopped. |
| `boost` | ⚡ Your Eddi water heater is boosting heater 1 for 30 min. |
| `boost --cancel` | ⏹ Your Eddi water heater boost has been cancelled. |
| `status` | 📊 Eddi Status: Stopped \| Grid: -1.2 kW. |

Notifications are optional. If the env vars are not set, the tool works normally without them. There may be a 5-15 second delay on messages due to the free Callmebot service.

## License

MIT
