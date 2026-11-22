<h1 align="center">📶 WiFi-Manager</h1>

<p align="center">
  <a href="https://github.com/Belfagor2005/WiFi-Manager">
    <img src="https://img.shields.io/badge/Version-1.5-blue.svg" alt="Version">
  </a>

  <a href="https://www.enigma2.net">
    <img src="https://img.shields.io/badge/Enigma2-Plugin-ff6600.svg" alt="Enigma2">
  </a>

  <a href="https://www.python.org">
    <img src="https://img.shields.io/badge/Python-3-blue.svg" alt="Python">
  </a>

  <a href="https://www.gnu.org/licenses/gpl-3.0.html">
    <img src="https://img.shields.io/badge/License-GPLv3-blue.svg" alt="GPLv3">
  </a>

  <a href="https://github.com/Belfagor2005/WiFi-Manager/actions/workflows/pylint.yml">
    <img src="https://github.com/Belfagor2005/WiFi-Manager/actions/workflows/pylint.yml/badge.svg" alt="Pylint">
  </a>

  <a href="https://github.com/Belfagor2005/WiFi-Manager/actions/workflows/flake8.yml">
    <img src="https://github.com/Belfagor2005/WiFi-Manager/actions/workflows/flake8.yml/badge.svg" alt="PEP8">
  </a>
</p>

<p align="center">
  <a href="https://github.com/Belfagor2005">
    <img src="https://komarev.com/ghpvc/?username=Belfagor2005&label=Repository%20Views&color=blueviolet" alt="Visitors">
  </a>
</p>

<p align="center">
  <a href="https://ko-fi.com/lululla">
    <img src="https://img.shields.io/badge/_-Donate-red.svg?logo=githubsponsors&labelColor=555555&style=for-the-badge" alt="Ko-fi">
  </a>

  <a href="https://paypal.me/belfagor2005">
    <img src="https://img.shields.io/badge/_-Donate-green.svg?logo=githubsponsors&labelColor=555555&style=for-the-badge" alt="PayPal">
  </a>
</p>

---

**WiFi-Manager** is a complete tool for **Enigma2 receivers** to scan, connect,
monitor, diagnose and speed-test WiFi connections.

---

## 📺 Screenshot

<p align="center">
  <img src="https://raw.githubusercontent.com/Belfagor2005/WiFi-Manager/main/screen/main.png" height="220">
</p>
<p align="center">
  <img src="https://raw.githubusercontent.com/Belfagor2005/WiFi-Manager/main/screen/speedtest.png" height="220">
</p>

---

## ⬇️ Installation

From the receiver console (telnet / SSH):

```sh
wget -q --no-check-certificate "https://raw.githubusercontent.com/Belfagor2005/WiFi-Manager/main/installer.sh" -O - | /bin/sh
```

Then restart the GUI. Requires a Python 3 image (OpenATV, OpenPLi, OpenBH, ...).

### 🔄 Automatic updates

When the plugin opens it checks (in the background, once per Enigma2 session)
the version published in `installer.sh` on GitHub. If a newer release exists it
shows the changelog and asks whether to update; the installer then runs in the
Enigma2 console and the GUI can be restarted from the same dialog.
A manual check is available in **About → GREEN "Check for updates"**.

---

## 1. Main Menu

| Icon | Function |
|------|----------|
| **Scanner** | Networks grouped by name and sorted by signal, connected network marked, band (2.4/5 GHz), channel, security (WPA2/WPA/WEP/Open), details with BSSID |
| **Monitor** | Real-time quality and signal with large live signal icon |
| **Connect** | Scan, connect, disconnect, saved passwords, virtual keyboard |
| **Diagnostics** | Drivers, kernel modules, interface state, link parameters, scan test |
| **Details Info** | `iwconfig`-style information, MAC, access point, IP, gateway, DNS, traffic counters |
| **Tools** | `iwlist` tools, restart interface, reload WiFi driver, WiFi system logs |
| **Config** | WiFi and network configuration (DHCP / static), advanced radio settings |
| **Speedtest** | Graphical speed test (see below) |
| **Info** | About, support and donation QR codes (also with the **INFO** key) |

### 📶 Live signal indicator

All main screens show an animated WiFi icon with the current signal
(dBm / %) and the network name: the arcs light up from red (weak) to green
(excellent), move bar by bar when the signal changes, turn blue while searching
and grey when no WiFi is available. Data is read from `/proc/net/wireless`,
without external commands.

---

## 2. ⚡ Speed Test

- Live **download / upload gauges**, **ping** and **jitter**
- **Automatic choice of the closest server** among public
  [LibreSpeed](https://github.com/librespeed/speedtest) backends
  (GARR Roma / Bologna / Bari, Clouvider, Hetzner, CESNET) plus OVH, Tele2,
  Cloudflare; YELLOW button to choose the server manually
- IP address and provider, last result remembered
- **Verdict for IPTV**: SD / HD / Full HD / 4K
- BLUE button: classic text tests (quick, full with all servers, detailed)

How it measures (same method as LibreSpeed / speedtest.net): parallel
connections, timed test with the warm-up excluded, real bytes counted,
upload confirmed by the server, IPv4 tried first.

> On WiFi the result is limited by the receiver's WiFi link: the **Full test**
> shows the link rate (real throughput is usually 50-70 % of it).

---

## 3. Connection Management

- Scan available networks and connect with one key
- Password requested with the **virtual keyboard** (TXT key also works)
- Saved passwords, edit or forget a network
- `wpa_supplicant` configuration written safely: the key is stored as a
  pre-computed PSK (like `wpa_passphrase`), so any character is accepted
- DHCP or static IP

---

## 4. Advanced Configuration

- 📶 Fixed or automatic bitrate
- 📡 Channel and regulatory domain
- 🔐 Encryption WPA / WPA2 / WEP / open
- ⚡ TX power, RTS and fragmentation thresholds
- 🔋 Power management

---

## 5. Structure

```text
/usr/lib/enigma2/python/Plugins/Extensions/WiFiManager/
├── plugin.py               # Plugin descriptor
├── WiFiManager.py          # Main menu (3x3 grid), Tools menu, About
├── modules/
│   ├── scanner.py          # Network scanner
│   ├── monitor.py          # Signal monitor
│   ├── connect.py          # Connection manager
│   ├── config.py           # WiFi / network configuration
│   ├── diagnostics.py      # Diagnostics
│   ├── detailed_info.py    # Detailed info (iwconfig style)
│   ├── iwlist_tools.py     # Advanced tools
│   ├── speed_gauge.py      # Graphical speed test
│   ├── speed_engine.py     # Speed measurement engine
│   ├── speedtest*.py       # Classic text speed tests
│   ├── signal_indicator.py # Live WiFi signal icon
│   ├── updater.py          # Automatic update check
│   ├── tools.py            # Shared utilities
│   └── iwlibs.py, iwconfig.py, iwlist.py, flags.py  # pythonwifi port
├── icons/                  # Menu icons, signal/ and gauge/ images, QR codes
└── locale/                 # Translations
```

---

## 6. Support

For troubleshooting, guidance, or community support, visit:
- [LinuxSat Support](https://www.linuxsat-support.com)
- [CorvoBoys Forum](https://www.corvoboys.org)

If you like the plugin, you can offer a coffee ☕ via
[Ko-fi](https://ko-fi.com/lululla) or [PayPal](https://paypal.me/belfagor2005)
(QR codes in the plugin **About** screen).
