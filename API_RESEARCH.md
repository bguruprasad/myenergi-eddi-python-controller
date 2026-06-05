# myenergi API Research

## Overview

myenergi does **not** provide an official public API program, but there is a well-documented **unofficial REST API** that the myenergi app itself uses. The community has reverse-engineered it extensively, and myenergi has tacitly allowed its use.

---

## 1. Authentication

### Credentials Needed
- **Hub Serial Number** - Found on your myenergi hub (e.g., `10XXXXXX`) or in the app under "Hub"
- **API Key** - Generated from the **myenergi app**:
  1. Open the myenergi app
  2. Go to **My Account** > **Advanced**
  3. Generate an **API Key**

### Auth Method
- **HTTP Digest Authentication** (not Basic Auth)
- Username: Hub serial number
- Password: API key

---

## 2. API Base URLs (Director System)

myenergi uses a "director" system to route you to the correct server for your hub.

### Step 1: Find your server
```
GET https://director.myenergi.net/cgi-jstatus-*
```
The response header `X_MYENERGI-asn` tells you which server your hub is on.

### Server URLs
| ASN Value | Base URL |
|-----------|----------|
| s1        | `https://s1.myenergi.net` |
| s2        | `https://s2.myenergi.net` |
| s3        | `https://s3.myenergi.net` |
| s5        | `https://s5.myenergi.net` |
| s6        | `https://s6.myenergi.net` |
| s7        | `https://s7.myenergi.net` |
| s8        | `https://s8.myenergi.net` |
| s11       | `https://s11.myenergi.net` |
| s12       | `https://s12.myenergi.net` |
| s18       | `https://s18.myenergi.net` |

---

## 3. Available Endpoints

### Status Endpoints

| Endpoint | Description |
|----------|-------------|
| `GET /cgi-jstatus-*` | Status of all devices |
| `GET /cgi-jstatus-Z` | Status of all **Zappi** chargers |
| `GET /cgi-jstatus-E` | Status of all **Eddi** diverters |
| `GET /cgi-jstatus-H` | Status of all **Harvi** sensors |
| `GET /cgi-jstatus-L` | Status of all **Libbi** batteries |
| `GET /cgi-jstatus-Z{serial}` | Status of specific Zappi |
| `GET /cgi-jstatus-E{serial}` | Status of specific Eddi |

### Zappi Control Endpoints

| Endpoint | Description |
|----------|-------------|
| `GET /cgi-zappi-mode-Z{serial}-{mode}-{boost_kwh}-0-0000` | Set Zappi mode |

#### Zappi Modes
| Mode | Value |
|------|-------|
| Fast | `1` |
| Eco | `2` |
| Eco+ | `3` |
| Stop | `4` |

#### Zappi Boost
```
# Start manual boost (e.g., 10 kWh)
GET /cgi-zappi-mode-Z{serial}-{mode}-10-0-0000

# Start smart boost (complete by time, e.g., 10 kWh by 08:00)
GET /cgi-zappi-mode-Z{serial}-{mode}-10-0-0800

# Stop boost
GET /cgi-zappi-mode-Z{serial}-{mode}-0-0-0000
```

#### Zappi Minimum Green Level
```
GET /cgi-set-min-green-Z{serial}-{percent}
```
`percent` = 50-100 (percentage of green energy required)

### Eddi Control Endpoints

| Endpoint | Description |
|----------|-------------|
| `GET /cgi-eddi-mode-E{serial}-{mode}` | Set Eddi mode |
| `GET /cgi-eddi-boost-E{serial}-{heater}-{time}` | Boost Eddi |

#### Eddi Modes
| Mode | Value |
|------|-------|
| Normal | `1` |
| Stop | `0` |

#### Eddi Boost
```
# Boost heater 1 for 30 minutes
GET /cgi-eddi-boost-E{serial}-10-30

# Boost heater 2 for 60 minutes
GET /cgi-eddi-boost-E{serial}-20-60

# Cancel boost
GET /cgi-eddi-boost-E{serial}-10-0
```

### Libbi Control Endpoints

| Endpoint | Description |
|----------|-------------|
| `GET /cgi-libbi-mode-L{serial}-{mode}` | Set Libbi mode |

#### Libbi Modes
| Mode | Value |
|------|-------|
| Stopped | `0` |
| Normal | `1` |
| Export | `5` |

### History / Data Endpoints

| Endpoint | Description |
|----------|-------------|
| `GET /cgi-jday-Z{serial}-{YYYY}-{MM}-{DD}` | Zappi daily energy data (minute-by-minute) |
| `GET /cgi-jday-E{serial}-{YYYY}-{MM}-{DD}` | Eddi daily energy data |
| `GET /cgi-jday-H{serial}-{YYYY}-{MM}-{DD}` | Harvi daily energy data |
| `GET /cgi-jdayhour-Z{serial}-{YYYY}-{MM}-{DD}` | Zappi hourly summary |

---

## 4. Key Status Response Fields

### Zappi Status Fields
| Field | Description |
|-------|-------------|
| `sno` | Serial number |
| `dat` | Date |
| `tim` | Time |
| `ectp1` | CT1 power (watts) - typically grid |
| `ectp2` | CT2 power (watts) - typically generation |
| `ectt1` | CT1 type (e.g., "Internal Load") |
| `ectt2` | CT2 type |
| `grd` | Grid power (watts) |
| `gen` | Generated power (watts) |
| `div` | Diverted power (watts) |
| `sta` | Status: 1=Paused, 3=Diverting, 5=Complete |
| `zmo` | Zappi mode: 1=Fast, 2=Eco, 3=Eco+, 4=Stop |
| `pst` | Plug status: A=EV disconnected, B1=EV connected, B2=Waiting, C1=Charging, C2=... |
| `vol` | Voltage (x10) |
| `frq` | Frequency (x100) |
| `bsm` | Boost mode: 0=Off, 1=Manual, 2=Smart |
| `mgl` | Minimum green level |
| `che` | Charge added this session (kWh) |

---

## 5. Example: cURL Request

```bash
# Step 1: Find your server
curl --digest -u 'HUB_SERIAL:API_KEY' \
  https://director.myenergi.net/cgi-jstatus-*

# Note the X_MYENERGI-asn header in the response (e.g., s18)

# Step 2: Get Zappi status
curl --digest -u 'HUB_SERIAL:API_KEY' \
  https://s18.myenergi.net/cgi-jstatus-Z

# Step 3: Set Zappi to Eco mode
curl --digest -u 'HUB_SERIAL:API_KEY' \
  https://s18.myenergi.net/cgi-zappi-mode-ZSERIAL-2-0-0-0000

# Step 4: Get yesterday's energy data
curl --digest -u 'HUB_SERIAL:API_KEY' \
  https://s18.myenergi.net/cgi-jday-ZSERIAL-2026-6-4
```

---

## 6. Popular Open-Source Libraries

| Library | Language | GitHub |
|---------|----------|--------|
| **pymyenergi** | Python | `CJNE/pymyenergi` |
| **myenergi-api** | Node.js | `bisand/myenergi-api` |
| **go-myenergi** | Go | `DanielVandworpsern/go-myenergi` |
| **MyEnergi-App-Api** | Docs | `twonk/MyEnergi-App-Api` (comprehensive API docs) |

### pymyenergi (Most Popular - Python)
```bash
pip install pymyenergi
```
```python
import asyncio
from pymyenergi.connection import Connection
from pymyenergi.client import MyenergiClient

async def main():
    conn = Connection('HUB_SERIAL', 'API_KEY')
    client = MyenergiClient(conn)

    # Get all devices
    devices = await client.get_devices()

    # Get Zappi status
    zappis = await client.get_zappis()
    for zappi in zappis:
        print(f"Zappi {zappi.serial}: mode={zappi.mode}, status={zappi.status}")
        print(f"  Charge rate: {zappi.charge_rate}W")
        print(f"  Energy added: {zappi.charge_added}kWh")

    # Set mode
    await zappis[0].set_mode("Eco")

    # Start boost
    await zappis[0].start_boost(10)  # 10 kWh

    await conn.close()

asyncio.run(main())
```

---

## 7. Home Assistant Integration

myenergi has an official **Home Assistant** integration:
- HACS integration: `CJNE/ha-myenergi`
- Provides entities for all devices
- Supports mode changes, boost control, and energy monitoring

---

## 8. Rate Limits & Best Practices

- **No official rate limit documented**, but community recommends:
  - Max **1 request per 10 seconds** for polling
  - Avoid rapid repeated requests (risk of temporary IP ban)
- Data from the API can lag by ~5-10 seconds behind real-time
- The hub must be online and connected for API access
- All API calls go through myenergi's cloud servers (no direct local API)

---

## 9. Important Notes

- This is an **unofficial API** - myenergi could change it at any time
- The API uses **HTTPS with Digest Authentication** (not Basic)
- All times in responses are in **UTC**
- Power values are in **Watts**, energy in **Joules** (for minute data) or **kWh**
- The API is **read-heavy** - control commands are simple GETs
- There is **no webhook/push notification** support - you must poll

---

## 10. Quick Start Checklist

- [ ] Get Hub serial number from the app or device label
- [ ] Generate API key in myenergi app (My Account > Advanced)
- [ ] Query the director to find your server
- [ ] Start making API calls!

---

## References
- Community API docs: `https://github.com/twonk/MyEnergi-App-Api`
- pymyenergi library: `https://github.com/CJNE/pymyenergi`
- Home Assistant integration: `https://github.com/CJNE/ha-myenergi`
