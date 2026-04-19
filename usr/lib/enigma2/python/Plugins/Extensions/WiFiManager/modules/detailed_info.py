# -*- coding: utf-8 -*-

import subprocess
import traceback
from datetime import datetime
from os.path import basename, realpath, isdir
from Screens.Screen import Screen
from Components.ActionMap import ActionMap
from Components.Button import Button
from Components.ScrollLabel import ScrollLabel

from . import _
from .tools import (
    get_interface_info,
    is_interface_up,
    scan_networks,
    format_signal_quality,
    get_wifi_interfaces
)

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


class WiFiDetailedInfo(Screen):
    skin = """
    <screen position="center,center" size="800,700" title="WiFi Detailed Info">
        <widget name="info_output" position="10,10" size="780,600" font="Regular;18" />
        <widget name="key_red" position="10,635" size="180,40" zPosition="1" font="Regular;20" halign="center" valign="center" backgroundColor="red" transparent="1" />
        <widget name="key_green" position="210,635" size="180,40" zPosition="1" font="Regular;20" halign="center" valign="center" backgroundColor="green" transparent="1" />
        <eLabel name="" position="9,677" size="180,8" zPosition="3" backgroundColor="#fe0000" />
        <eLabel name="" position="209,677" size="180,8" zPosition="3" backgroundColor="#fe00" />
    </screen>
    """

    def __init__(self, session, ifname):
        Screen.__init__(self, session)
        self.session = session
        self.ifname = ifname
        self.debug_file = '/tmp/WifiManager_detailed_info_debug.txt'
        self["info_output"] = ScrollLabel()
        self["key_red"] = Button(_("Refresh"))
        self["key_green"] = Button(_("Close"))
        self["actions"] = ActionMap(
            ["ColorActions", "OkCancelActions", "DirectionActions"],
            {
                "red": self.refresh_info,
                "green": self.close,
                "cancel": self.close,
                "pageUp": self.pageUp,
                "pageDown": self.pageDown,
                "up": self.pageUp,
                "down": self.pageDown,
                "left": self.pageUp,
                "right": self.pageDown,
            }
        )
        self.setTitle(_("Detailed Info - {}").format(ifname))
        # Write initialization to the debug file
        self._write_debug(
            f"🚀 WiFiDetailedInfo INITIALIZED for interface: {ifname}")
        self.refresh_info()

    def _write_debug(self, message, error=False):
        """Write debug messages to file"""
        try:
            timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            log_level = "❌ ERROR" if error else "📝 DEBUG"
            full_message = f"[{timestamp}] {log_level}: {message}\n"

            with open(self.debug_file, "a", encoding="utf-8") as f:
                f.write(full_message)

            # Also print to console for dual debugging
            print(full_message.strip())
        except Exception as e:
            print(f"CRITICAL: Cannot write to debug file: {e}")

    def pageUp(self):
        self["info_output"].pageUp()

    def pageDown(self):
        self["info_output"].pageDown()

    def refresh_info(self):
        self._write_debug("🔄 STARTING REFRESH for {}".format(self.ifname))
        print("[WiFiDetailedInfo] Starting refresh for {}".format(self.ifname))

        wifi_ifaces = get_wifi_interfaces()

        if self.ifname not in wifi_ifaces:
            error_msg = _("❌ Interface {} not found or not a WiFi interface\n").format(
                self.ifname)
            error_msg += _("Available interfaces: {}").format(
                ', '.join(wifi_ifaces) if wifi_ifaces else _('None')
            )

            self._write_debug(
                "Interface not found: {}".format(
                    self.ifname), error=True)
            self["info_output"].setText(error_msg)
            return

        try:
            info_text = _(
                "📡 DETAILED WIFI INFORMATION - {}\n").format(self.ifname.upper())
            info_text += "=" * 60 + "\n\n"

            # 1. BASIC INTERFACE INFORMATION
            self._write_debug("Getting basic interface info...")
            print("[WiFiDetailedInfo] Getting basic interface info...")
            info_text += _("🔧 BASIC INTERFACE INFO\n")
            info_text += "-" * 40 + "\n"
            basic_info = self.get_basic_interface_info()
            info_text += basic_info
            info_text += "\n"

            # 2. WIRELESS INFORMATION
            self._write_debug("Getting wireless info...")
            print("[WiFiDetailedInfo] Getting wireless info...")
            info_text += _("📶 WIRELESS INFORMATION\n")
            info_text += "-" * 40 + "\n"
            wireless_info = self.get_wireless_info()
            info_text += wireless_info
            info_text += "\n"

            # 3. DRIVER AND HARDWARE INFO
            self._write_debug("Getting driver info...")
            print("[WiFiDetailedInfo] Getting driver info...")
            info_text += _("🔌 DRIVER & HARDWARE\n")
            info_text += "-" * 40 + "\n"
            driver_info = self.get_driver_info()
            info_text += driver_info
            info_text += "\n"

            # 4. NETWORK STATISTICS
            self._write_debug("Getting network statistics...")
            print("[WiFiDetailedInfo] Getting network statistics...")
            info_text += _("📊 NETWORK STATISTICS\n")
            info_text += "-" * 40 + "\n"
            stats_info = self.get_network_statistics()
            info_text += stats_info
            info_text += "\n"

            # 5. AVAILABLE NETWORKS (scan results)
            self._write_debug("Scanning for available networks...")
            print("[WiFiDetailedInfo] Scanning for available networks...")
            info_text += _("🌐 AVAILABLE NETWORKS\n")
            info_text += "-" * 40 + "\n"
            networks_info = self.get_available_networks()
            info_text += networks_info

            # Also save complete information to the debug file
            self._write_debug(
                f"REFRESH COMPLETED SUCCESSFULLY - Interface: {self.ifname}")
            self._write_debug(
                f"FINAL OUTPUT LENGTH: {
                    len(info_text)} characters")

            # Save the full output to the debug file
            try:
                with open(self.debug_file, "a", encoding="utf-8") as f:
                    f.write(
                        "\n" +
                        "=" *
                        50 +
                        " FULL OUTPUT " +
                        "=" *
                        50 +
                        "\n")
                    f.write(info_text)
                    f.write("\n" + "=" * 120 + "\n")
            except Exception as e:
                self._write_debug(
                    f"Error saving full output to debug file: {e}", error=True)

            print("[WiFiDetailedInfo] Refresh completed successfully")
            self["info_output"].setText(info_text)

        except Exception as e:
            error_msg = _(
                "❌ Error getting detailed info:\n{}\n\n").format(str(e))
            stack_trace = traceback.format_exc()
            self._write_debug(
                f"CRITICAL ERROR during refresh: {error_msg}",
                error=True)
            self._write_debug(f"STACK TRACE: {stack_trace}", error=True)
            print(f"[WiFiDetailedInfo] ERROR: {e}")
            print(f"Stack trace: {stack_trace}")
            self["info_output"].setText(error_msg)

    def get_wireless_info(self):
        """Get wireless-specific information using tools.py"""
        self._write_debug(
            f"Getting wireless info for {
                self.ifname} using tools.py")
        print(f"[WiFiDetailedInfo] Getting wireless info for {self.ifname}")
        info = ""

        try:
            interface_info = get_interface_info(self.ifname)

            if 'error' in interface_info:
                info += _("❌ Error: {}\n").format(interface_info['error'])
                self._write_debug(
                    f"Error getting wireless info: {
                        interface_info['error']}", error=True)
                return info

            info += _("📡 Interface Type: WIRELESS\n")
            self._write_debug("Interface is WIRELESS")

            # ESSID
            essid = interface_info.get('essid', _('Not connected'))
            info += _("📡 ESSID: {}\n").format(essid)
            self._write_debug(f"ESSID: {essid}")

            # Mode
            mode = interface_info.get('mode', _('Unknown'))
            info += _("🔧 Mode: {}\n").format(mode)
            self._write_debug(f"Mode: {mode}")

            # Frequency/Channel
            frequency = interface_info.get('frequency', _('Unknown'))
            info += _("📶 Frequency: {}\n").format(frequency)
            self._write_debug(f"Frequency: {frequency}")

            # Quality and Signal
            quality = interface_info.get('quality', _('Unknown'))
            info += _("📊 Quality: {}\n").format(quality)
            self._write_debug(f"Quality: {quality}")

            # Bit Rate
            bitrate = interface_info.get('bitrate', _('Unknown'))
            info += _("🚀 Bit Rate: {}\n").format(bitrate)
            self._write_debug(f"Bit Rate: {bitrate}")

            # TX Power
            txpower = interface_info.get('txpower', _('Unknown'))
            info += _("⚡ TX Power: {}\n").format(txpower)
            self._write_debug(f"TX Power: {txpower}")

            # Protocol/Driver
            protocol = interface_info.get('protocol', _('Unknown'))
            info += _("💾 Protocol: {}\n").format(protocol)
            self._write_debug(f"Protocol: {protocol}")

        except Exception as e:
            error_msg = _("Wireless info error: {}").format(str(e))
            info += _("❌ {}\n").format(error_msg)
            self._write_debug(error_msg, error=True)
            print(f"[WiFiDetailedInfo] {error_msg}")

        self._write_debug(f"Wireless info completed, length: {len(info)}")
        return info

    def get_basic_interface_info(self):
        """Get basic interface information using tools.py"""
        self._write_debug(
            f"Getting basic info for {
                self.ifname} using tools.py")
        print(f"[WiFiDetailedInfo] Getting basic info for {self.ifname}")
        info = ""

        try:
            interface_info = get_interface_info(self.ifname)
            if 'error' in interface_info:
                info += _("❌ Error: {}\n").format(interface_info['error'])
                self._write_debug(
                    f"Error getting interface info: {
                        interface_info['error']}", error=True)
                return info

            # Status
            status = _("UP and active") if is_interface_up(
                self.ifname) else _("DOWN")
            icon = "✅" if is_interface_up(self.ifname) else "🔌"
            info += _("{} Status: {}\n").format(icon, status)
            self._write_debug(f"Status: {status}")

            # Interface name
            info += _("🔧 Interface: {}\n").format(interface_info.get('name', self.ifname))

            # MAC Address
            if 'ap_addr' in interface_info and interface_info['ap_addr'] != _(
                    "Unknown"):
                info += _("📟 MAC: {}\n").format(interface_info['ap_addr'])
                self._write_debug(f"MAC: {interface_info['ap_addr']}")

            # Type
            interface_type = _(
                "Wireless") if self.ifname in get_wifi_interfaces() else _("Wired")
            icon = "📡" if interface_type == _("Wireless") else "🔌"
            info += _("{} Type: {} interface\n").format(icon, interface_type)
            self._write_debug(f"Type: {interface_type}")

        except Exception as e:
            error_msg = _("Basic info error: {}").format(str(e))
            info += _("❌ {}\n").format(error_msg)
            self._write_debug(error_msg, error=True)
            print(f"[WiFiDetailedInfo] {error_msg}")

        self._write_debug(f"Basic info completed, length: {len(info)}")
        return info

    def get_driver_info(self):
        """Get driver and hardware information"""
        self._write_debug("Getting driver info")
        info = ""

        try:
            driver_path = f"/sys/class/net/{self.ifname}/device/driver"
            self._write_debug(f"Checking driver path: {driver_path}")

            # Driver information
            if isdir(driver_path):
                driver_link = realpath(driver_path)  # Resolve symlink
                driver_name = basename(driver_link)  # Get actual driver name
                info += _("💾 Driver: {}\n").format(driver_name)
                self._write_debug(f"Driver found: {driver_name}")
            else:
                info += _("💾 Driver: Unknown\n")
                self._write_debug("Driver: Unknown")

            # Additional interface information
            interface_info = get_interface_info(self.ifname)
            protocol = interface_info.get('protocol')
            if protocol not in (None, "", _("Unknown")):
                info += _("🔧 Module: {}\n").format(protocol)
                self._write_debug(f"Module: {protocol}")

            # Interface type
            if self.ifname in get_wifi_interfaces():
                info += _("📡 Type: Wireless interface\n")
                self._write_debug("Type: Wireless")
            else:
                info += _("🔌 Type: Wired interface\n")
                self._write_debug("Type: Wired")

        except Exception as e:
            error_msg = _("Driver info error: {}").format(str(e))
            info += _("❌ {}\n").format(error_msg)
            self._write_debug(error_msg, error=True)

        self._write_debug(f"Driver info completed, length: {len(info)}")
        return info

    def get_network_statistics(self):
        """Get network statistics"""
        self._write_debug("Getting network statistics")
        info = ""
        try:
            # Interface statistics
            rx_path = f'/sys/class/net/{self.ifname}/statistics/rx_bytes'
            tx_path = f'/sys/class/net/{self.ifname}/statistics/tx_bytes'

            self._write_debug(f"Reading RX bytes from: {rx_path}")
            result = subprocess.run(['cat', rx_path],
                                    capture_output=True, text=True, timeout=5)
            if result.returncode == 0:
                rx_bytes = int(result.stdout.strip())
                formatted_rx = self.format_bytes(rx_bytes)
                info += _("⬇️  Received: {}\n").format(formatted_rx)
                self._write_debug(f"RX bytes: {rx_bytes} ({formatted_rx})")
            else:
                self._write_debug(f"Failed to read RX bytes: {result.stderr}")

            self._write_debug(f"Reading TX bytes from: {tx_path}")
            result = subprocess.run(['cat', tx_path],
                                    capture_output=True, text=True, timeout=5)
            if result.returncode == 0:
                tx_bytes = int(result.stdout.strip())
                formatted_tx = self.format_bytes(tx_bytes)
                info += _("⬆️  Transmitted: {}\n").format(formatted_tx)
                self._write_debug(f"TX bytes: {tx_bytes} ({formatted_tx})")
            else:
                self._write_debug(f"Failed to read TX bytes: {result.stderr}")

        except Exception as e:
            error_msg = _("Statistics error: {}").format(str(e))
            info += _("❌ {}\n").format(error_msg)
            self._write_debug(error_msg, error=True)

        self._write_debug(f"Network statistics completed, length: {len(info)}")
        return info

    def get_available_networks(self):
        """Get available networks via scan using tools.py"""
        self._write_debug("Starting network scan using tools.py")
        info = ""

        try:
            self._write_debug(f"Running scan_networks for {self.ifname}")

            networks = scan_networks(self.ifname, detailed=True)

            self._write_debug(
                f"Scan completed, found {
                    len(networks)} networks")

            if networks:
                info += _("Found {} networks:\n").format(len(networks))
                self._write_debug(f"Found {len(networks)} networks")

                for i, net in enumerate(networks[:8]):
                    essid = net.get('essid', _('Unknown'))
                    signal = net.get('signal', _('N/A'))
                    quality_percent = net.get('quality_percent', 0)
                    channel = net.get('channel', '?')
                    encrypted = "🔒" if net.get('encryption') else "🔓"

                    signal_quality = format_signal_quality(quality_percent)

                    info += _("  {:2d}. {} {:20} | Signal: {:4} dBm ({}) | Channel: {}\n").format(
                        i + 1, encrypted, essid, signal, signal_quality, channel)

                if len(networks) > 8:
                    info += _("  ... and {} more networks\n").format(len(networks) - 8)
            else:
                info += _("No networks found or scan not supported\n")
                self._write_debug("No networks found in scan")

        except Exception as e:
            error_msg = _("Scan error: {}").format(str(e))
            info += _("{}\n").format(error_msg)
            self._write_debug(error_msg, error=True)

        self._write_debug(f"Network scan completed, length: {len(info)}")
        return info

    def format_bytes(self, bytes):
        """Format bytes to human readable format"""
        for unit in ['B', 'KB', 'MB', 'GB']:
            if bytes < 1024.0:
                return f"{bytes:.1f} {unit}"
            bytes /= 1024.0
        return f"{bytes:.1f} TB"
