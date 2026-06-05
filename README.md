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

## Automation Examples

```bash
# Cron: Start Eddi at 1am, stop at 5am (off-peak heating)
# 0 1 * * * cd /path/to/myenergi && python3 eddi_control.py start
# 0 5 * * * cd /path/to/myenergi && python3 eddi_control.py stop
```
