![](https://komarev.com/ghpvc/?username=Belfagor2005)
[![Python package](https://github.com/Belfagor2005/WiFi-Manager/actions/workflows/pylint.yml/badge.svg)](https://github.com/Belfagor2005/WiFi-Manager/actions/workflows/pylint.yml)
[![Ruff Status](https://github.com/Belfagor2005/WiFi-Manager/actions/workflows/ruff.yml/badge.svg)](https://github.com/Belfagor2005/WiFi-Manager/actions/workflows/ruff.yml)
[![Version](https://img.shields.io/badge/Version-1.1-blue.svg)](https://github.com/Belfagor2005/WiFi-Manager)
[![Enigma2](https://img.shields.io/badge/Enigma2-Plugin-ff6600.svg)](https://www.enigma2.net)
[![Python](https://img.shields.io/badge/Python-2.7%2B-blue.svg)](https://www.python.org)
[![License: GPL v3](https://img.shields.io/badge/License-GPLv3-blue.svg)](https://www.gnu.org/licenses/gpl-3.0)
[![GitHub stars](https://img.shields.io/github/stars/Belfagor2005/WiFi-Manager?style=social)](https://github.com/Belfagor2005/WiFi-Manager/stargazers)

---

# 📶 WiFi-Manager

**WiFi-Manager** is a comprehensive tool for **Enigma2 devices** to manage, monitor, and optimize WiFi connections.

It provides both **basic and advanced functionalities**, suitable for **home** and **professional** use.

---

## 📺 Screenshot

<p align="center">
  <img src="https://raw.githubusercontent.com/Belfagor2005/WiFi-Manager/main/screen/main.png" height="220">
</p>

---

## 1. Main Menu

- ✅ **Scanner** - Basic network scan  
- ✅ **Monitor** - Real-time signal quality monitoring  
- ✅ **Config** - Advanced configuration options  
- ✅ **Connects** - Connection management  
- ✅ **Diagnostics** - Network tests and diagnostics  
- ✅ **Detailed Info** - Connection info in `iwconfig` style  
- ✅ **Advanced Tools** - Access to all `iwlist` tools  
- ✅ **Config Setup** - Manage all WiFi configuration files  
- ✅ **Speedtest** - Run detailed speed tests  

---

## 2. Connection Management

- ✅ Scan available WiFi networks  
- ✅ Connect to a specific network  
- ✅ Disconnect from a network (sets ESSID blank)  
- ✅ Edit or add WiFi configurations  
- ✅ Auto-connect in automatic mode  
- ✅ Monitor connection quality and signal strength  

---

## 3. Advanced Configuration

- 📶 Fixed or automatic bitrate settings  
- 📡 Select a specific WiFi channel  
- 🔐 Encryption management (WEP/WPA)  
- ⚡ TX Power control  
- 🔋 Power management options  

---

## 4. Structure

```text
/usr/lib/enigma2/python/Plugins/Extensions/WiFiManager/
├── plugin.py # Main descriptor
├── WiFiManager.py # Main screen with 3x2 grid
├── modules/
│ ├── init.py # Import all modules
│ ├── scanner.py # Basic network scanner
│ ├── monitor.py # Signal quality monitor
│ ├── config.py # WiFi configuration
│ ├── diagnostics.py # Diagnostic tests
│ ├── detailed_info.py # Detailed info (iwconfig style)
│ ├── iwlist_tools.py # Advanced tools (iwlist)
│ ├── flags.py # Wireless constants
│ ├── iwlibs.py # Base WiFi functions
│ ├── iwconfig.py # iwconfig equivalent
│ ├── iwlist.py # iwlist equivalent
│ └── tools.py # Utilities
└── icons/
├── plugin.png # Main icon (64x64)
├── wifi-scan.png # Scanner
├── wifi-monitor.png # Monitor
├── wifi-config.png # Configuration
├── wifi-diagnostic.png# Diagnostics
├── wifi-info.png # Detailed info
└── wifi-tools.png # Advanced tools
```
---

## 5. Support

For troubleshooting, guidance, or community support, visit:  
- [LinuxSat Support](https://www.linuxsat-support.com)  
- [CorvoBoys Forum](https://www.corvoboys.org)  

---

