# -*- coding: utf-8 -*-

import time
import subprocess
from json import load, dump
from re import search, findall, DOTALL
from os.path import exists

from .. import _

"""
#########################################################
#                                                       #
#  WiFi Manager Plugin                                  #
#  Version: 1.0                                         #
#  Created by Lululla (https://github.com/Belfagor2005) #
#  License: Gnu Gpl v2                                  #
#  https://creativecommons.org/licenses/by-nc-sa/4.0    #
#  Last Modified: "00:00 - 20250101"                    #
#                                                       #
#  Credits:                                             #
#  - Original concept by Lululla                        #
#  Usage of this code without proper attribution        #
#  is strictly prohibited.                              #
#  For modifications and redistribution,                #
#  please maintain this credit header.                  #
#########################################################
"""


def open_virtual_keyboard(session, callback, title, text=""):
    """Open the Enigma2 virtual keyboard (falls back to InputBox).

    callback receives the typed text, or None if the user cancelled.
    """
    try:
        from Screens.VirtualKeyBoard import VirtualKeyBoard
        session.openWithCallback(
            callback, VirtualKeyBoard, title=title, text=text or "")
    except Exception as e:
        print("[WiFiManager] VirtualKeyBoard not available: %s" % e)
        from Screens.InputBox import InputBox
        session.openWithCallback(
            callback, InputBox, title=title, text=text or "",
            windowTitle=title)


def verify_connection(interface, essid):
    """Verify connection to network"""
    try:
        result = subprocess.run(
            ['iwconfig', interface],
            capture_output=True,
            text=True)
        if f'ESSID:"{essid}"' in result.stdout:
            ip_result = subprocess.run(
                ['ip', 'addr', 'show', interface],
                capture_output=True,
                text=True)
            return 'inet ' in ip_result.stdout
        return False
    except Exception as e:
        print(e)
        return False


def is_interface_up(interface):
    """Check if interface is up"""
    try:
        result = subprocess.run(
            ['ip', 'link', 'show', interface], capture_output=True, text=True)
        return 'state UP' in result.stdout
    except Exception as e:
        print(e)
        return False


def ensure_interface_up(interface):
    """Ensure WiFi interface is up - with better error handling"""
    if not interface:
        return False

    try:
        # Check if interface exists
        result = subprocess.run(
            ['ip', 'link', 'show', interface], capture_output=True, text=True)
        if result.returncode != 0:
            print(f"[DEBUG] Interface {interface} not found")
            return False

        # Try to bring interface up
        result = subprocess.run(
            ['ip', 'link', 'set', interface, 'up'],
            capture_output=True,
            text=True,
            timeout=10)

        if result.returncode == 0:
            print(f"[DEBUG] Interface {interface} brought up successfully")
            time.sleep(1)  # Wait for interface to initialize
            return True
        else:
            print(f"[DEBUG] Failed to bring interface up: {result.stderr}")
            # Try alternative command
            result2 = subprocess.run(
                ['ifconfig', interface, 'up'],
                capture_output=True,
                text=True,
                timeout=10)
            return result2.returncode == 0

    except Exception as e:
        print(f"[DEBUG] Error ensuring interface up: {e}")
        return False


_IFACE_CACHE = {'time': 0, 'value': []}


def _fast_wifi_interfaces():
    """sysfs + /proc/net/wireless: instant, no external command"""
    found = []
    try:
        import os
        if os.path.exists('/sys/class/net'):
            for ifname in sorted(os.listdir('/sys/class/net')):
                if os.path.exists('/sys/class/net/%s/wireless' % ifname) or \
                        os.path.exists('/sys/class/net/%s/phy80211' % ifname):
                    found.append(ifname)
    except Exception as e:
        print("[get_wifi_interfaces] sysfs error: %s" % e)
    try:
        with open('/proc/net/wireless', 'r') as f:
            for line in f.readlines()[2:]:
                ifname = line.split(':')[0].strip()
                if ifname and ifname not in found:
                    found.append(ifname)
    except Exception:
        pass
    return found


def get_wifi_interfaces(use_cache=True):
    """Returns the WiFi interfaces.

    Fast path (sysfs, /proc) first; the slow methods (iwconfig, ip, iw)
    only if nothing was found. Result cached for 5 seconds because many
    screens call this often.
    """
    now = time.time()
    if use_cache and now - _IFACE_CACHE['time'] < 5:
        return list(_IFACE_CACHE['value'])
    wifi_interfaces = _fast_wifi_interfaces()
    if not wifi_interfaces:
        wifi_interfaces = _slow_wifi_interfaces()
    _IFACE_CACHE['time'] = now
    _IFACE_CACHE['value'] = list(wifi_interfaces)
    return wifi_interfaces


def _slow_wifi_interfaces():
    """Detection with external commands (fallback)"""
    wifi_interfaces = []

    try:
        # METHOD 1: Check /proc/net/wireless (most reliable)
        try:
            with open('/proc/net/wireless', 'r') as f:
                lines = f.readlines()
            for line in lines[2:]:  # Skip header lines
                parts = line.split(':')
                if len(parts) > 0:
                    ifname = parts[0].strip()
                    if ifname and ifname not in wifi_interfaces:
                        wifi_interfaces.append(ifname)
        except Exception as e:
            print(
                f"[get_wifi_interfaces] Error reading /proc/net/wireless: {e}")

        # METHOD 2: Check iwconfig output
        try:
            result = subprocess.run(
                ['iwconfig'],
                capture_output=True,
                text=True,
                timeout=10)
            if result.returncode == 0:
                for line in result.stdout.split('\n'):
                    if 'IEEE 802.11' in line or 'ESSID:' in line:
                        if 'no wireless extensions' not in line:
                            ifname_match = search(r'^(\w+)\s+', line)
                            if ifname_match:
                                ifname = ifname_match.group(1)
                                if ifname and ifname not in wifi_interfaces:
                                    wifi_interfaces.append(ifname)
        except Exception as e:
            print(f"[get_wifi_interfaces] Error with iwconfig: {e}")

        # METHOD 3: Check ip link show with iw verification
        try:
            result = subprocess.run(
                ['ip', 'link', 'show'], capture_output=True, text=True, timeout=10)
            if result.returncode == 0:
                for line in result.stdout.split('\n'):
                    if any(
                        name in line for name in [
                            'wlan',
                            'wlp',
                            'wifi',
                            'ath',
                            'ra']):
                        ifname_match = search(r'^\d+:\s+(\w+):', line)
                        if ifname_match:
                            ifname = ifname_match.group(1)
                            if ifname and ifname not in wifi_interfaces:
                                # Verify it's actually a WiFi interface
                                try:
                                    iw_result = subprocess.run(['iw', 'dev', ifname, 'info'],
                                                               capture_output=True, text=True, timeout=5)
                                    if iw_result.returncode == 0:
                                        wifi_interfaces.append(ifname)
                                except Exception as e:
                                    print(e)
                                    pass
        except Exception as e:
            print(f"[get_wifi_interfaces] Error with ip link: {e}")

        # METHOD 4: Check common interface names with verification
        common_names = [
            'wlan0',
            'wlan1',
            'wlan2',
            'wlp2s0',
            'wlp3s0',
            'wifi0',
            'ath0',
            'ra0']
        for ifname in common_names:
            try:
                result = subprocess.run(['ip', 'link', 'show', ifname],
                                        capture_output=True, text=True, timeout=5)
                if result.returncode == 0:
                    # Verify it's a WiFi interface
                    iw_result = subprocess.run(['iw', 'dev', ifname, 'info'],
                                               capture_output=True, text=True, timeout=5)
                    if iw_result.returncode == 0 and ifname not in wifi_interfaces:
                        wifi_interfaces.append(ifname)
            except Exception as e:
                print(e)
                pass

        # METHOD 5: Check sysfs for wireless devices
        try:
            import os
            if os.path.exists('/sys/class/net'):
                for ifname in os.listdir('/sys/class/net'):
                    wireless_path = f'/sys/class/net/{ifname}/wireless'
                    if os.path.exists(
                            wireless_path) and ifname not in wifi_interfaces:
                        wifi_interfaces.append(ifname)
        except Exception as e:
            print(f"[get_wifi_interfaces] Error checking sysfs: {e}")

    except Exception as e:
        print(f"[get_wifi_interfaces] General error: {e}")

    return wifi_interfaces


def get_current_connected_essid(interface):
    """Get currently connected ESSID"""
    try:
        result = subprocess.run(
            ['iwconfig', interface],
            capture_output=True,
            text=True)
        if result.returncode == 0:
            essid_match = search(r'ESSID:"([^"]*)"', result.stdout)
            if essid_match and essid_match.group(1):
                return essid_match.group(1)
    except Exception as e:
        print(e)
        pass
    return None


def get_ip_address(interface):
    """Get assigned IPv4 address (ioctl first: no external command)"""
    try:
        import socket
        import fcntl
        import struct
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        try:
            res = fcntl.ioctl(s.fileno(), 0x8915,  # SIOCGIFADDR
                              struct.pack('256s', interface.encode()[:15]))
            return socket.inet_ntoa(res[20:24])
        finally:
            s.close()
    except Exception:
        pass
    try:
        result = subprocess.run(
            ['ip', 'addr', 'show', interface],
            capture_output=True,
            text=True)
        ip_match = search(r'inet (\d+\.\d+\.\d+\.\d+)', result.stdout)
        return ip_match.group(1) if ip_match else None
    except Exception as e:
        print(e)
        return None


def get_interface_info(ifname):
    """Returns detailed information about an interface using system commands"""
    try:
        info = {'name': ifname}

        # Get basic interface info using iwconfig
        result = subprocess.run(['iwconfig', ifname],
                                capture_output=True, text=True)

        if result.returncode != 0:
            info['error'] = _("Interface {} not available").format(ifname)
            return info

        output = result.stdout
        print("[DEBUG] iwconfig output for {}:\n{}".format(ifname, output))

        # Extract ESSID
        essid_match = search(r'ESSID:"([^"]*)"', output)
        info['essid'] = essid_match.group(
            1) if essid_match else _("Not connected")

        # Extract AP MAC address
        ap_match = search(r'Access Point: ([0-9A-Fa-f:]{17})', output)
        info['ap_addr'] = ap_match.group(1) if ap_match else _("Unknown")

        # Extract Mode
        mode_match = search(r'Mode:(\w+)', output)
        info['mode'] = mode_match.group(1) if mode_match else _("Unknown")

        # Extract Frequency/Channel
        freq_match = search(r'Frequency:([0-9.]+) GHz', output)
        channel_match = search(r'Channel[=:](\d+)', output)

        if freq_match:
            info['frequency'] = _("{} GHz").format(freq_match.group(1))
        elif channel_match:
            info['frequency'] = _("Channel {}").format(channel_match.group(1))
        else:
            info['frequency'] = _("Unknown")

        # Extract Bitrate
        rate_match = search(r'Bit Rate[=:]([0-9.]+) Mb/s', output)
        info['bitrate'] = _("{} Mb/s").format(rate_match.group(1)
                                              ) if rate_match else _("Unknown")

        # Extract Signal Quality
        quality_match = search(r'Link Quality=(\d+)/(\d+)', output)
        signal_match = search(r'Signal level=(-?\d+) dBm', output)

        # Alternative match for signal
        if not signal_match:
            signal_match = search(r'Signal[=\s:]*(-?\d+)', output)

        # If still not found, try iw
        if not signal_match:
            try:
                iw_result = subprocess.run(
                    ['iw', 'dev', ifname, 'link'],
                    capture_output=True,
                    text=True,
                    timeout=5
                )

                if iw_result.returncode == 0:
                    iw_signal_match = search(
                        r'signal: (-?\d+)', iw_result.stdout)

                    if iw_signal_match:
                        info['signal_dbm'] = int(iw_signal_match.group(1))

            except Exception as e:
                print(e)
                pass

        if quality_match:
            quality = int(quality_match.group(1))
            max_quality = int(quality_match.group(2))

            if max_quality > 0:
                percentage = (quality / max_quality) * 100
                info['quality'] = _("{:.1f}%").format(percentage)
            else:
                info['quality'] = _("0%")

        elif signal_match:
            signal_dbm = int(signal_match.group(1))
            info['quality'] = _("{} dBm").format(signal_dbm)
            info['signal_dbm'] = signal_dbm

        else:
            info['quality'] = _("Unknown")

        # If we have dBm, also store it as generic signal
        if 'signal_dbm' in info:
            info['signal'] = info['signal_dbm']

        # Extract TX Power
        power_match = search(r'Tx-Power[=:](-?\d+) dBm', output)
        info['txpower'] = _("{} dBm").format(
            power_match.group(1)) if power_match else _("Unknown")

        # Get protocol (driver) information using ethtool
        try:
            ethtool_result = subprocess.run(
                ['ethtool', '-i', ifname],
                capture_output=True,
                text=True,
                timeout=5
            )

            if ethtool_result.returncode == 0:
                ethtool_output = ethtool_result.stdout
                print(
                    "[DEBUG] ethtool output for {}:\n{}".format(
                        ifname, ethtool_output))

                driver_match = search(r'driver:\s*(\S+)', ethtool_output)

                if driver_match:
                    info['protocol'] = driver_match.group(1)
                    print("[DEBUG] Found driver: {}".format(info['protocol']))
                else:
                    info['protocol'] = _("Unknown")
                    print("[DEBUG] Driver not found in ethtool output")

                # Try fallback to version
                if info['protocol'] == _("Unknown"):
                    version_match = search(r'version:\s*(\S+)', ethtool_output)
                    if version_match:
                        info['protocol'] = version_match.group(1)

            else:
                info['protocol'] = _("Unknown")
                print("[DEBUG] ethtool failed with returncode: {}".format(
                    ethtool_result.returncode
                ))

        except subprocess.TimeoutExpired:
            info['protocol'] = _("Timeout")
            print("[DEBUG] ethtool timeout")

        except FileNotFoundError:
            info['protocol'] = _("ethtool not found")
            print("[DEBUG] ethtool command not found")

        except Exception as e:
            info['protocol'] = _("Error")
            print("[DEBUG] ethtool exception: {}".format(e))

        print("[DEBUG] Final interface info: {}".format(info))
        return info

    except Exception as e:
        print("[DEBUG] Error in get_interface_info: {}".format(e))
        return {'name': ifname, 'error': str(e)}


def parse_wpa_supplicant(wpa_file, interface):
    """Parse wpa_supplicant config file"""
    networks = {}
    try:
        with open(wpa_file, 'r') as f:
            content = f.read()

        network_blocks = findall(r'network=\{([^}]+)\}', content, DOTALL)

        for block in network_blocks:
            ssid_match = search(r'ssid="([^"]+)"', block)
            psk_match = search(r'psk="([^"]+)"', block)

            if ssid_match and psk_match:
                essid = ssid_match.group(1)
                password = psk_match.group(1)
                networks[essid] = {
                    'password': password,
                    'encryption': 'WPA/WPA2',
                    'timestamp': time.time(),
                    'interface': interface
                }
    except Exception as e:
        print(f"Error parsing wpa_supplicant: {e}")

    return networks


def parse_iw_scan(scan_output):
    """Parse iw scan output"""
    networks = []
    current_bss = {}

    for line in scan_output.split('\n'):
        line = line.strip()

        if line.startswith('BSS'):
            if current_bss:
                networks.append(current_bss)
            current_bss = {}
            bss_match = search(r'BSS ([0-9a-f:]{17})', line)
            if bss_match:
                current_bss['bssid'] = bss_match.group(1).lower()

        elif 'SSID:' in line:
            ssid_match = search(r'SSID: (.+)', line)
            if ssid_match:
                current_bss['essid'] = ssid_match.group(1).strip()

        elif 'signal:' in line:
            signal_match = search(r'signal: (-?\d+\.\d+) dBm', line)
            if signal_match:
                current_bss['signal'] = float(signal_match.group(1))

        elif 'freq:' in line:
            freq_match = search(r'freq: (\d+)', line)
            if freq_match:
                current_bss['frequency'] = int(freq_match.group(1))

    if current_bss:
        networks.append(current_bss)

    return networks


def parse_iwlist_scan(scan_output):
    """Parse iwlist scan output into network list"""
    networks = []
    current_network = {}

    for line in scan_output.split('\n'):
        line = line.strip()

        # New cell block
        if 'Cell' in line and 'Address' in line:
            if current_network:
                networks.append(current_network)
            current_network = {}
            mac_match = search(r'Address: ([0-9A-Fa-f:]{17})', line)
            if mac_match:
                current_network['bssid'] = mac_match.group(1)

        # ESSID
        elif 'ESSID:' in line:
            essid_match = search(r'ESSID:"([^"]*)"', line)
            if essid_match:
                current_network['essid'] = essid_match.group(1)

        # Signal Quality
        elif 'Quality=' in line:
            quality_match = search(r'Quality=(\d+)/(\d+)', line)
            signal_match = search(r'Signal level=(-?\d+) dBm', line)

            if quality_match:
                quality = int(quality_match.group(1))
                max_quality = int(quality_match.group(2))
                if max_quality > 0:
                    percentage = (quality / max_quality) * 100
                    current_network['quality'] = percentage
                else:
                    current_network['quality'] = 0
            if signal_match:
                current_network['signal'] = int(signal_match.group(1))

        # Channel/Frequency
        elif 'Channel:' in line or 'Frequency:' in line:
            channel_match = search(r'Channel:(\d+)', line)
            freq_match = search(r'Frequency:([0-9.]+) GHz', line)

            if channel_match:
                current_network['channel'] = int(channel_match.group(1))
            if freq_match:
                current_network['frequency'] = float(freq_match.group(1))

        # Encryption
        elif 'Encryption key:' in line:
            encrypt_match = search(r'Encryption key:(\w+)', line)
            if encrypt_match:
                current_network['encryption'] = encrypt_match.group(1) == 'on'

        # Mode
        elif 'Mode:' in line:
            mode_match = search(r'Mode:(\w+)', line)
            if mode_match:
                current_network['mode'] = mode_match.group(1)

    # Add the last network
    if current_network:
        networks.append(current_network)

    return networks


def dbm_to_percent(dbm):
    """-100 dBm -> 0%, -50 dBm or better -> 100%"""
    try:
        dbm = int(dbm)
    except (TypeError, ValueError):
        return 0
    if dbm >= 0:
        return 0
    return max(0, min(100, 2 * (dbm + 100)))


def parse_iwlist_detailed(scan_output):
    """Parse 'iwlist <if> scan' output.

    Every network: bssid, essid ('' = hidden), signal (dBm or None),
    quality_percent, channel, frequency (GHz), encryption (bool),
    security ('WPA2', 'WPA', 'WPA/WPA2', 'WEP', 'Open'), mode
    """
    networks = []
    current_net = {}

    def close_net():
        if current_net and 'bssid' in current_net:
            if current_net['encryption'] and current_net['security'] == 'Open':
                current_net['security'] = 'WEP'
            if 'quality_percent' not in current_net:
                current_net['quality_percent'] = dbm_to_percent(
                    current_net.get('signal'))
            networks.append(current_net)

    for line in scan_output.split('\n'):
        line = line.strip()

        if 'Cell' in line and 'Address' in line:
            close_net()
            current_net = {'encryption': False, 'security': 'Open',
                           'essid': '', 'signal': None}
            mac_match = search(r'Address: ([0-9A-Fa-f:]{17})', line)
            if mac_match:
                current_net['bssid'] = mac_match.group(1).upper()
            continue

        if not current_net:
            continue

        if 'ESSID:' in line:
            essid_match = search(r'ESSID:\s*"(.*)"', line)
            if essid_match:
                current_net['essid'] = essid_match.group(
                    1).strip().strip('\x00')

        if 'Encryption key:' in line:
            value = line.split('Encryption key:', 1)[1].strip().lower()
            current_net['encryption'] = value.startswith('on')

        # "Quality=54/70  Signal level=-56 dBm" (same line!)
        quality_match = search(r'Quality[=:](\d+)/(\d+)', line)
        if quality_match:
            q, qmax = int(quality_match.group(1)), int(quality_match.group(2))
            current_net['quality_percent'] = int(
                q * 100 / qmax) if qmax > 0 else 0

        signal_match = search(r'Signal level[=:]\s*(-?\d+)\s*dBm', line)
        if signal_match:
            current_net['signal'] = int(signal_match.group(1))
        elif 'Signal level' in line:
            rel = search(r'Signal level[=:]\s*(\d+)/(\d+)', line)
            if rel and 'quality_percent' not in current_net:
                current_net['quality_percent'] = int(
                    int(rel.group(1)) * 100 / max(1, int(rel.group(2))))

        channel_match = search(r'Channel[:\s](\d+)', line)
        if channel_match and 'channel' not in current_net:
            current_net['channel'] = int(channel_match.group(1))

        freq_match = search(r'Frequency[:=]([0-9.]+) GHz', line)
        if freq_match:
            current_net['frequency'] = float(freq_match.group(1))

        mode_match = search(r'Mode:(\w+)', line)
        if mode_match:
            current_net['mode'] = mode_match.group(1)

        if 'IE:' in line:
            if 'WPA2' in line or '802.11i' in line:
                sec = current_net['security']
                current_net['security'] = 'WPA/WPA2' if sec == 'WPA' else 'WPA2'
            elif 'WPA Version' in line:
                sec = current_net['security']
                current_net['security'] = 'WPA/WPA2' if sec == 'WPA2' else 'WPA'

    close_net()
    return networks


def group_networks(networks, include_hidden=False):
    """One entry per network name (strongest access point), sorted by
    signal: what the user wants to see in a list"""
    best = {}
    for net in networks:
        essid = net.get('essid', '')
        if not essid and not include_hidden:
            continue
        key = essid or net.get('bssid', '')
        net['aps'] = 1
        old = best.get(key)
        if old is None:
            best[key] = net
        else:
            if net.get('quality_percent', 0) > old.get('quality_percent', 0):
                net['aps'] = old.get('aps', 1) + 1
                best[key] = net
            else:
                old['aps'] = old.get('aps', 1) + 1
    return sorted(best.values(),
                  key=lambda n: (n.get('quality_percent', 0),
                                 n.get('signal') or -999), reverse=True)


def scan_networks_simple(ifname):
    """Simple network scan using iw dev scan"""
    try:
        result = subprocess.run(['iw', 'dev', ifname, 'scan'],
                                capture_output=True, text=True, timeout=20)

        if result.returncode != 0:
            raise Exception(f"iw scan failed: {result.stderr.strip()}")

        return parse_iw_scan(result.stdout)

    except subprocess.TimeoutExpired:
        raise Exception(f"Scan timeout on {ifname}")
    except Exception as e:
        raise Exception(f"Scan failed on {ifname}: {str(e)}")


def scan_networks(ifname, detailed=False):
    """Scan available networks using iwlist - VERSIONE SICURA"""
    try:
        result = subprocess.run(
            ['iwlist', ifname, 'scan'],
            capture_output=True,
            text=True,
            timeout=30)

        if result.returncode != 0:
            raise Exception(f"Scan failed: {result.stderr.strip()}")

        networks = parse_iwlist_detailed(result.stdout)
        for net in networks:
            # backward compatibility for the callers
            net['quality'] = net.get('quality_percent', 0)
        return networks

    except subprocess.TimeoutExpired:
        raise Exception(f"Scan timeout on {ifname}")
    except Exception as e:
        raise Exception(f"Scan failed on {ifname}: {str(e)}")


def format_signal_quality(quality_data):
    """Format the signal quality into readable text"""
    if quality_data is None or quality_data == "":
        return _("No data")

    # Handle both percentage and dBm
    if isinstance(quality_data, (int, float)):
        quality = quality_data
    elif isinstance(quality_data, dict) and hasattr(quality_data, 'quality'):
        quality = quality_data.quality
    else:
        return _("Unknown")

    levels = [
        (90, _("Excellent")),
        (70, _("Good")),
        (50, _("Fair")),
        (30, _("Poor")),
        (0, _("Very Poor"))
    ]

    for threshold, description in levels:
        if quality >= threshold:
            return _("{} ({:.0f}%)").format(description, quality)

    return _("{} ({:.0f}%)").format(_('Very Poor'), quality)


def load_saved_networks(config_file=None, interface=None):
    """Load saved networks from file"""
    try:
        # If config_file is not specified, use the default one
        if config_file is None:
            config_file = "/etc/wifi_saved_networks.json"

        if exists(config_file):
            with open(config_file, 'r') as f:
                networks = load(f)
                if networks:
                    return networks

        # Fallback to wpa_supplicant if interface is provided
        if interface:
            wpa_file = f"/etc/wpa_supplicant.{interface}.conf"
            if exists(wpa_file):
                networks = parse_wpa_supplicant(wpa_file, interface)
                if networks:
                    with open(config_file, 'w') as f:
                        dump(networks, f, indent=2)
                    return networks
    except Exception as e:
        print(f"Error loading saved networks: {e}")
    return {}


def test_ping(host="8.8.8.8", count=3, timeout=5, debug=False):
    """
    Test ping latency for Enigma2 devices.
    Returns the average ping in ms or an error string.
    """
    try:
        ping_commands = [
            ["ping", "-c", str(count), "-W", str(timeout), host],
            ["ping6", "-c", str(count), "-W", str(timeout), host],
            ["ping", "-c", str(count), host],
            ["busybox", "ping", "-c", str(count), host],
            ["ping", "-4", "-c", str(count), host]
        ]

        ping_result = None
        last_error = None
        used_command = None

        for cmd in ping_commands:
            try:
                if debug:
                    print("[PING] Trying command: {}".format(' '.join(cmd)))

                ping_result = subprocess.run(
                    cmd,
                    capture_output=True,
                    text=True,
                    timeout=timeout + 5
                )

                if ping_result.returncode == 0:
                    used_command = ' '.join(cmd)
                    break
                else:
                    last_error = ping_result.stderr
                    if debug:
                        print("[PING] Command failed (code {}): {}".format(
                            ping_result.returncode,
                            last_error
                        ))

            except (subprocess.TimeoutExpired, FileNotFoundError, Exception) as e:
                last_error = str(e)
                if debug:
                    print("[PING] Command error: {}".format(e))
                continue

        if ping_result is None or ping_result.returncode != 0:
            error_msg = _("Ping not available")
            if last_error and "Name or service not known" in last_error:
                error_msg = _("Host not found")
            elif last_error and "Network is unreachable" in last_error:
                error_msg = _("Network unreachable")
            return error_msg

        if debug:
            print("[PING] Success with: {}".format(used_command))
            print("[PING] Output:\n{}".format(ping_result.stdout))
            if ping_result.stderr:
                print("[PING] Error:\n{}".format(ping_result.stderr))

        output = ping_result.stdout

        time_lines = []
        for line in output.split('\n'):
            if 'time=' in line or 'ms' in line:
                time_lines.append(line)
                if debug:
                    print("[PING] Time line: {}".format(line))

        times = []
        time_patterns = [
            r'time=([\d.]+)\s*ms',
            r'time=([\d.]+)ms',
            r'([\d.]+)\s*ms',
            r'icmp_seq=\d+.+?([\d.]+)\s*ms'
        ]

        for line in time_lines:
            for pattern in time_patterns:
                time_matches = findall(pattern, line)

                for match in time_matches:
                    try:
                        times.append(float(match))
                        if debug:
                            print("[PING] Found time: {} ms".format(match))
                        break
                    except ValueError:
                        continue

        if debug:
            print("[PING] Found individual times: {}".format(times))

        if times:
            avg_time = sum(times) / len(times)
            if debug:
                print("[PING] Calculated average: {:.1f} ms".format(avg_time))
            return _("{:.1f} ms").format(avg_time)

        stats_lines = [
            line for line in output.split('\n')
            if 'min/avg/max' in line.lower() or 'rtt' in line.lower()
        ]

        if stats_lines:
            stats_line = stats_lines[-1]

            if debug:
                print("[PING] Stats line: {}".format(stats_line))

            stats_patterns = [
                r'([\d.]+)/([\d.]+)/([\d.]+)',
                r'=\s*([\d.]+)/([\d.]+)/([\d.]+)',
                r'avg\s*[=:]\s*([\d.]+)'
            ]

            for pattern in stats_patterns:
                match = search(pattern, stats_line)

                if match:
                    try:
                        if len(match.groups()) >= 3:
                            avg_ping = float(match.group(2))
                        else:
                            avg_ping = float(match.group(1))

                        if debug:
                            print(
                                "[PING] Found average from stats: {:.1f} ms".format(avg_ping))

                        return _("{:.1f} ms").format(avg_ping)

                    except (ValueError, IndexError):
                        continue

        if "bytes from" in output or "icmp_seq" in output:
            return _("Connected but no timing data")

        return _("No ping data")

    except subprocess.TimeoutExpired:
        return _("Timeout")

    except Exception as e:
        if debug:
            print("[PING] Exception: {}".format(e))
        return _("Error: {}".format(str(e)))


# ---------------------------------------------------------------------------
# wpa_supplicant configuration (shared by connect.py and config.py)
# ---------------------------------------------------------------------------

def _wpa_quote_ok(text):
    """True if text can be written between quotes in wpa_supplicant.conf"""
    return all(
        32 <= ord(c) < 127 for c in text) and '"' not in text and '\\' not in text


def _hex(text):
    import binascii
    return binascii.hexlify(text.encode('utf-8')).decode('ascii')


def wpa_psk(essid, password):
    """Pre-shared key like 'wpa_passphrase' does: 64 hex digits.

    Written without quotes, so any character in the password is safe.
    """
    import hashlib
    import binascii
    if len(password) == 64 and all(
            c in '0123456789abcdefABCDEF' for c in password):
        return password.lower()           # already a raw key
    key = hashlib.pbkdf2_hmac('sha1', password.encode('utf-8'),
                              essid.encode('utf-8'), 4096, 32)
    return binascii.hexlify(key).decode('ascii')


def wpa_network_block(essid, password="", security="WPA/WPA2", hidden=False,
                      wep_ascii=True):
    """network={...} block for wpa_supplicant.conf.

    security: 'WPA/WPA2', 'WPA2', 'WPA', 'WEP', 'Open'/'Unencrypted'
    """
    lines = ["network={"]
    lines.append('\tssid="%s"' % essid if _wpa_quote_ok(essid)
                 else '\tssid=%s' % _hex(essid))
    lines.append('\tscan_ssid=%d' % (1 if hidden else 0))
    if security in ("WPA", "WPA2", "WPA/WPA2"):
        lines.append('\tkey_mgmt=WPA-PSK')
        if security == "WPA":
            lines += ['\tproto=WPA', '\tpairwise=TKIP', '\tgroup=TKIP']
        elif security == "WPA2":
            lines += ['\tproto=RSN', '\tpairwise=CCMP', '\tgroup=CCMP']
        else:
            lines += ['\tproto=WPA RSN', '\tpairwise=CCMP TKIP',
                      '\tgroup=CCMP TKIP']
        if 8 <= len(password) <= 63 or len(password) == 64:
            lines.append('\tpsk=%s' % wpa_psk(essid, password))
        else:
            # invalid length for WPA: write it anyway, wpa_supplicant
            # will report the error
            lines.append('\tpsk="%s"' % password.replace('"', ''))
    elif security == "WEP":
        lines.append('\tkey_mgmt=NONE')
        if wep_ascii and _wpa_quote_ok(password):
            lines.append('\twep_key0="%s"' % password)
        else:
            lines.append('\twep_key0=%s' % (password if not wep_ascii
                                            else _hex(password)))
        lines.append('\twep_tx_keyidx=0')
    else:
        lines.append('\tkey_mgmt=NONE')
    lines.append("}")
    return "\n".join(lines) + "\n"


def write_wpa_supplicant(interface, block):
    """Write /etc/wpa_supplicant.<if>.conf with only this network (the
    same format Enigma2 uses), so wpa_supplicant joins exactly it"""
    path = "/etc/wpa_supplicant.%s.conf" % interface
    header = ("ctrl_interface=/var/run/wpa_supplicant\n"
              "eapol_version=1\n"
              "fast_reauth=1\n"
              "ap_scan=1\n")
    with open(path, "w") as f:
        f.write(header + block)
    try:
        import os
        os.chmod(path, 0o600)         # contains the WiFi key
    except Exception:
        pass
    return path
