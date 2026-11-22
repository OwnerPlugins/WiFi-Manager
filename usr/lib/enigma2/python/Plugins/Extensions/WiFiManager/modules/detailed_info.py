# -*- coding: utf-8 -*-

from twisted.internet import threads
import traceback
from datetime import datetime
from os.path import basename, realpath, isdir
from Screens.Screen import Screen
from Components.ActionMap import ActionMap
from Components.Button import Button
from Components.ScrollLabel import ScrollLabel

from . import _
from .skin_scale import scale_skin
from .signal_indicator import WiFiSignalIndicator, skin_compact
from .tools import (
    get_interface_info,
    is_interface_up,
    scan_networks,
    format_signal_quality,
    get_wifi_interfaces,
    get_ip_address,
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
    skin = scale_skin("""
    <screen position="center,center" size="800,700" title="WiFi Detailed Info">
        <widget name="info_output" position="10,58" size="780,560" font="Regular;18" />
        <widget name="key_red" position="10,635" size="180,40" zPosition="1" font="Regular;20" halign="center" valign="center" backgroundColor="red" transparent="1" />
        <widget name="key_green" position="210,635" size="180,40" zPosition="1" font="Regular;20" halign="center" valign="center" backgroundColor="green" transparent="1" />
        <eLabel name="" position="9,677" size="180,8" zPosition="3" backgroundColor="#fe0000" />
        <eLabel name="" position="209,677" size="180,8" zPosition="3" backgroundColor="#fe00" />
    """ + skin_compact(540, 2) + """
    </screen>
    """)

    def __init__(self, session, ifname):
        Screen.__init__(self, session)
        self.signal_indicator = WiFiSignalIndicator(self)
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
        self.closed = False
        self.running = False
        self._iface_info = {}
        self._wifi_ifaces = []
        self.onClose.append(self._on_close)
        self.onLayoutFinish.append(self.refresh_info)

    def _on_close(self):
        self.closed = True

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
        """Collect the information in a thread (it used to freeze the GUI)"""
        if self.running:
            return
        self.running = True
        self["info_output"].setText(_("Reading interface information..."))

        def done(text):
            self.running = False
            if not self.closed:
                self["info_output"].setText(text)

        def failed(failure):
            self.running = False
            if not self.closed:
                self["info_output"].setText(str(failure.value))

        d = threads.deferToThread(self._collect)
        d.addCallback(done)
        d.addErrback(failed)

    def _collect(self):
        """Worker thread: returns the text to show"""
        # new log for every refresh (the file used to grow forever)
        try:
            open(self.debug_file, "w").close()
        except Exception:
            pass
        self._write_debug("🔄 STARTING REFRESH for {}".format(self.ifname))
        print("[WiFiDetailedInfo] Starting refresh for {}".format(self.ifname))

        wifi_ifaces = get_wifi_interfaces()
        self._wifi_ifaces = wifi_ifaces
        # read once, used by all the sections below
        self._iface_info = get_interface_info(self.ifname)

        if self.ifname not in wifi_ifaces:
            error_msg = _("❌ Interface {} not found or not a WiFi interface\n").format(
                self.ifname)
            error_msg += _("Available interfaces: {}").format(
                ', '.join(wifi_ifaces) if wifi_ifaces else _('None')
            )

            self._write_debug(
                "Interface not found: {}".format(
                    self.ifname), error=True)
            return error_msg
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
                "REFRESH COMPLETED SUCCESSFULLY - Interface: {}".format(self.ifname)
            )

            self._write_debug(
                "FINAL OUTPUT LENGTH: {} characters".format(len(info_text))
            )

            # Save the full output to the debug file
            try:
                with open(self.debug_file, "a", encoding="utf-8") as f:
                    f.write(
                        "\n"
                        + "=" * 50
                        + " FULL OUTPUT "
                        + "=" * 50
                        + "\n"
                    )
                    f.write(info_text)
                    f.write("\n" + "=" * 120 + "\n")

            except Exception as e:
                self._write_debug(
                    "Error saving full output to debug file: {}".format(e),
                    error=True
                )

            print("[WiFiDetailedInfo] Refresh completed successfully")
            return info_text

        except Exception as e:
            error_msg = _(
                "❌ Error getting detailed info:\n{}\n\n").format(str(e))
            stack_trace = traceback.format_exc()

            self._write_debug(
                "CRITICAL ERROR during refresh: {}".format(error_msg),
                error=True
            )

            self._write_debug(
                "STACK TRACE: {}".format(stack_trace),
                error=True
            )

            print("[WiFiDetailedInfo] ERROR: {}".format(e))
            print("Stack trace: {}".format(stack_trace))
            return error_msg

    def get_wireless_info(self):
        """Get wireless-specific information using tools.py"""
        self._write_debug(
            "Getting wireless info for {} using tools.py".format(self.ifname)
        )
        print(
            "[WiFiDetailedInfo] Getting wireless info for {}".format(
                self.ifname))
        info = ""

        try:
            interface_info = self._iface_info
            if 'error' in interface_info:
                info += _("❌ Error: {}\n").format(interface_info['error'])

                self._write_debug(
                    "Error getting wireless info: {}".format(
                        interface_info['error']), error=True)

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
            "Getting basic info for {} using tools.py".format(self.ifname)
        )
        print("[WiFiDetailedInfo] Getting basic info for {}".format(self.ifname))
        info = ""

        try:
            interface_info = self._iface_info
            if 'error' in interface_info:
                info += _("❌ Error: {}\n").format(interface_info['error'])

                self._write_debug(
                    "Error getting interface info: {}".format(
                        interface_info['error']
                    ),
                    error=True
                )

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
            mac = self._read_sys("address")
            if mac:
                info += _("📟 MAC: {}\n").format(mac.upper())
            if 'ap_addr' in interface_info and interface_info['ap_addr'] not in (
                    _("Unknown"), "Not-Associated"):
                info += _("📡 Access Point: {}\n").format(
                    interface_info['ap_addr'])
            ip = get_ip_address(self.ifname)
            info += _("🌐 IP: {}\n").format(ip or _("No IP address"))
            gateway, dns = self._gateway_dns()
            if gateway:
                info += _("🚪 Gateway: {}\n").format(gateway)
            if dns:
                info += _("📖 DNS: {}\n").format(", ".join(dns))

            # Type
            interface_type = _(
                "Wireless") if self.ifname in self._wifi_ifaces else _("Wired")
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
            interface_info = self._iface_info
            protocol = interface_info.get('protocol')
            if protocol not in (None, "", _("Unknown")):
                info += _("🔧 Module: {}\n").format(protocol)
                self._write_debug(f"Module: {protocol}")

            # Interface type
            if self.ifname in self._wifi_ifaces:
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

    def _read_sys(self, name):
        try:
            with open("/sys/class/net/%s/%s" % (self.ifname, name)) as f:
                return f.read().strip()
        except Exception:
            return None

    def _gateway_dns(self):
        gateway, dns = None, []
        try:
            with open("/proc/net/route") as f:
                for line in f.readlines()[1:]:
                    parts = line.split()
                    if len(parts) > 2 and parts[1] == "00000000":
                        g = int(parts[2], 16)
                        gateway = "%d.%d.%d.%d" % (g & 255, (g >> 8) & 255,
                                                   (g >> 16) & 255, g >> 24)
                        break
        except Exception:
            pass
        try:
            with open("/etc/resolv.conf") as f:
                for line in f:
                    if line.startswith("nameserver"):
                        dns.append(line.split()[1])
        except Exception:
            pass
        return gateway, dns

    def get_network_statistics(self):
        """Traffic counters from sysfs"""
        info = ""
        try:
            rx = self._read_sys("statistics/rx_bytes")
            tx = self._read_sys("statistics/tx_bytes")
            if rx is not None:
                info += _("⬇️  Received: {}\n").format(self.format_bytes(int(rx)))
            if tx is not None:
                info += _("⬆️  Transmitted: {}\n").format(self.format_bytes(int(tx)))
            errors = [self._read_sys("statistics/" + n) or "0" for n in
                      ("rx_errors", "tx_errors", "rx_dropped", "tx_dropped")]
            info += _("⚠️  Errors RX/TX: {}/{}  Dropped RX/TX: {}/{}\n").format(*errors)
        except Exception as e:
            info += _("❌ {}\n").format(_("Statistics error: {}").format(str(e)))
        return info

    def get_available_networks(self):
        """Get available networks via scan using tools.py"""
        self._write_debug("Starting network scan using tools.py")
        info = ""

        try:
            self._write_debug(
                "Running scan_networks for {}".format(
                    self.ifname))

            networks = scan_networks(self.ifname, detailed=True)

            self._write_debug(
                "Scan completed, found {} networks".format(len(networks))
            )

            if networks:
                info += _("Found {} networks:\n").format(len(networks))
                self._write_debug("Found {} networks".format(len(networks)))

                networks = sorted(
                    networks, key=lambda n: n.get(
                        'quality_percent', 0), reverse=True)
                for i, net in enumerate(networks[:8]):
                    essid = net.get('essid', _('Unknown'))
                    signal = net.get('signal')
                    if signal is None:
                        signal = _('N/A')
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

        self._write_debug(
            "Network scan completed, length: {}".format(len(info))
        )

        return info

    def format_bytes(self, bytes):
        """Format bytes to human readable format"""
        for unit in ['B', 'KB', 'MB', 'GB']:
            if bytes < 1024.0:
                return f"{bytes:.1f} {unit}"
            bytes /= 1024.0
        return f"{bytes:.1f} TB"
