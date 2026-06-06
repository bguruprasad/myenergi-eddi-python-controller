# myenergi Eddi Controller

Automate start/stop and boost control for your myenergi Eddi via the unofficial API.

## Setup

```bash
python3 -m pip install -r requirements.txt
cp .env.example .env
# Edit .env with your hub serial and API key
```

### Getting your credentials
1. Open the **myenergi app**
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
```

## Automation (Cron)

Cron jobs are set up to stop Eddi at 10 AM and start at 8 PM IST daily. Logs go to `eddi_cron.log`.

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
# Stop at 9am, start at 9pm daily
0 9  * * * cd /path/to/myenergi && /usr/bin/python3 eddi_control.py stop >> /path/to/myenergi/eddi_cron.log 2>&1
0 21 * * * cd /path/to/myenergi && /usr/bin/python3 eddi_control.py start >> /path/to/myenergi/eddi_cron.log 2>&1

# Weekdays only - stop at 10am, start at 8pm
0 10 * * 1-5 cd /path/to/myenergi && /usr/bin/python3 eddi_control.py stop >> /path/to/myenergi/eddi_cron.log 2>&1
0 20 * * 1-5 cd /path/to/myenergi && /usr/bin/python3 eddi_control.py start >> /path/to/myenergi/eddi_cron.log 2>&1
```

### Check logs

```bash
cat eddi_cron.log
```
