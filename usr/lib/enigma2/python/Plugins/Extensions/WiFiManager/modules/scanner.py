# -*- coding: utf-8 -*-

import subprocess
from re import search
from enigma import eTimer

from Screens.Screen import Screen
from Components.ActionMap import ActionMap
from Components.Button import Button
from Components.ScrollLabel import ScrollLabel

from . import _
# from .iwlibs import getWNICnames, Wireless
from .tools import (
    get_wifi_interfaces,
    is_interface_up,
    ensure_interface_up,
    parse_iwlist_detailed,
    format_signal_quality,
    get_interface_info
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


# Attempt to import pythonwifi with fallback
try:
    from wifi.scan import Cell
    PYTHONWIFI_AVAILABLE = True
    print("[WiFiScanner] pythonwifi module available")
except ImportError as e:
    PYTHONWIFI_AVAILABLE = False
    print(f"[WiFiScanner] pythonwifi not available: {e}")
    # Define fallback for Cell

    class Cell:
        @staticmethod
        def all(interface, timeout=5):
            return []

IW_ENCODE_DISABLED = 0x8000  # Encoding disabled
IW_ENCODE_ENABLED = 0x0000  # Encoding enabled


class WiFiScanner(Screen):
    skin = """
    <screen position="center,center" size="800,700" title="WiFi Scanner">
        <widget name="scan_output" position="10,10" size="782,608" font="Regular;18" />
        <widget name="key_red" position="10,635" size="180,40" zPosition="1" font="Regular;20" halign="center" valign="center" backgroundColor="red" transparent="1" />
        <widget name="key_green" position="210,635" size="180,40" zPosition="1" font="Regular;20" halign="center" valign="center" backgroundColor="green" transparent="1" />
        <widget name="key_yellow" position="410,635" size="180,40" zPosition="1" font="Regular;20" halign="center" valign="center" backgroundColor="yellow" transparent="1" />
        <widget name="key_blue" position="600,635" size="180,40" zPosition="1" font="Regular;20" halign="center" valign="center" backgroundColor="blue" transparent="1" />
        <eLabel name="" position="9,677" size="180,8" zPosition="3" backgroundColor="#fe0000" />
        <eLabel name="" position="209,677" size="180,8" zPosition="3" backgroundColor="#fe00" />
        <eLabel name="" position="409,677" size="180,8" zPosition="3" backgroundColor="#cccc40" />
        <eLabel name="" position="599,677" size="180,8" zPosition="3" backgroundColor="#1a27408b" />
    </screen>
    """

    def __init__(self, session):
        Screen.__init__(self, session)
        self.session = session
        self.scan_timer = eTimer()
        self.scan_timer.callback.append(self.perform_scan)

        self["scan_output"] = ScrollLabel()
        self["key_red"] = Button(_("Scan"))
        self["key_green"] = Button(_("Refresh"))
        self["key_yellow"] = Button(_("Details"))
        self["key_blue"] = Button(_("Exit"))

        self["actions"] = ActionMap(
            ["ColorActions", "OkCancelActions", "DirectionActions"],
            {
                "red": self.start_scan,
                "green": self.refresh_scan,
                "yellow": self.toggle_details,
                "blue": self.close,
                "cancel": self.close,
                "pageUp": self.pageUp,
                "pageDown": self.pageDown,
                "up": self.pageUp,
                "down": self.pageDown,
                "left": self.pageUp,
                "right": self.pageDown,
                "ok": self.refresh_scan,
            }
        )

        self.detailed_view = False
        self.last_scan_results = []
        self.setTitle(_("WiFi Scanner"))
        self.start_scan()

    def pageUp(self):
        self["scan_output"].pageUp()

    def pageDown(self):
        self["scan_output"].pageDown()

    def start_scan(self):
        self["scan_output"].setText(_("Scanning for WiFi networks..."))
        self.scan_timer.start(1000, True)

    def refresh_scan(self):
        if self.last_scan_results:
            self.display_networks(self.last_scan_results)
        else:
            self.start_scan()

    def perform_scan(self):
        try:
            networks = []
            print("[WiFiScanner] Starting scan process...")

            wifi_ifaces = get_wifi_interfaces()
            if not wifi_ifaces:
                networks.append(_("No WiFi interfaces found\n"))
                networks.extend(self.get_detailed_network_status())
                self.last_scan_results = networks
                self.display_networks(networks)
                return

            # FIRST ATTEMPT: use pythonwifi if available
            if PYTHONWIFI_AVAILABLE:
                networks.extend(self.scan_with_pythonwifi(wifi_ifaces))
            else:
                networks.append(
                    _("\n[INFO] pythonwifi not available, using iwlist\n"))

            # SECOND ATTEMPT: use iwlist as fallback
            if not networks or len(networks) <= 2:
                networks.extend(self.scan_with_iwlist(wifi_ifaces))

            # THIRD ATTEMPT: if everything fails, show diagnostics

            # If no scan worked, show diagnostic info
            if len(networks) <= 3:  # Only headers and few results
                print("[WiFiScanner] Scan failed, showing diagnostics")
                networks.extend(self.get_detailed_network_status())

            self.last_scan_results = networks
            self.display_networks(networks)

        except Exception as e:
            error_msg = _("Scan error: {}\n").format(str(e))
            print(f"[WiFiScanner] {error_msg}")
            self["scan_output"].setText(_("Scan error: ") + str(e))

    def scan_with_iwlist(self, wifi_ifaces):
        """Scan using iwlist as fallback"""
        print("[WiFiScanner] Starting iwlist fallback scan")

        networks = []
        networks.append(_("\n=== SCAN WITH IWLIST ===\n"))

        for iface in wifi_ifaces:
            try:
                print("[WiFiScanner] iwlist scan on {}".format(iface))

                result = subprocess.check_output(
                    ['iwlist', iface, 'scan'],
                    stderr=subprocess.STDOUT,
                    text=True,
                    timeout=15
                )

                parsed_networks = parse_iwlist_detailed(result)

                if parsed_networks:
                    for i, net in enumerate(parsed_networks):
                        essid = net.get('essid', _('Unknown'))
                        signal = net.get('signal', 0)
                        quality_percent = net.get('quality_percent', 0)
                        channel = net.get('channel', '?')
                        encrypted = _("Yes") if net.get(
                            'encryption') else _("No")

                        signal_quality = format_signal_quality(quality_percent)

                        networks.append(
                            _("{index:2d}. {essid:20} | Quality: {quality:3}% ({signal_quality}) | Signal: {signal:4} dBm | Channel: {channel} | Encrypted: {encrypted}\n").format(
                                index=i +
                                1,
                                essid=essid,
                                quality=quality_percent,
                                signal_quality=signal_quality,
                                signal=signal,
                                channel=channel,
                                encrypted=encrypted))

                    print("[WiFiScanner] iwlist found {} networks".format(
                        len(parsed_networks)
                    ))
                    break

            except subprocess.TimeoutExpired:
                networks.append(_("   iwlist timeout on {}\n").format(iface))

            except subprocess.CalledProcessError as e:
                networks.append(
                    _("   iwlist error on {interface}: {error}\n").format(
                        interface=iface,
                        error=e
                    )
                )

            except Exception as e:
                networks.append(
                    _("   iwlist exception on {interface}: {error}\n").format(
                        interface=iface,
                        error=e
                    )
                )

        if len(networks) <= 2:
            networks.append(_("   No networks found with iwlist\n"))

        return networks

    def scan_with_pythonwifi(self, wifi_ifaces):
        """Scan using pythonwifi and Cell.all()"""
        networks = []
        networks.append(_("\n=== SCAN WITH PYTHONWIFI ===\n"))

        for iface in wifi_ifaces:
            try:
                print(
                    "[WiFiScanner] Scanning with pythonwifi on {}".format(iface))

                # Ensure interface is up
                if not is_interface_up(iface):
                    print(
                        "[WiFiScanner] Activating interface {}".format(iface))
                    ensure_interface_up(iface)

                # Perform scan with Cell.all()
                scan_results = list(Cell.all(iface, timeout=10))

                print("[WiFiScanner] Found {} networks on {}".format(
                    len(scan_results),
                    iface
                ))

                if scan_results:
                    for i, cell in enumerate(scan_results):
                        network_info = self.parse_cell(cell, i)
                        if network_info:
                            networks.append(network_info)

                    break  # Use first working interface

                else:
                    networks.append(
                        _("   No networks found on {}\n").format(iface))

            except Exception as e:
                error_msg = _("   Error on {interface}: {error}\n").format(
                    interface=iface,
                    error=str(e)
                )

                networks.append(error_msg)
                print("[WiFiScanner] pythonwifi error: {}".format(error_msg))
                continue

        return networks

    def parse_cell(self, cell, index):
        """Parse a pythonwifi Cell object"""
        try:
            # ESSID
            essid = cell.ssid if cell.ssid else _("Hidden")

            # Quality
            quality = self.parse_quality(cell.quality)

            # Signal
            signal = self.extract_signal_from_cell(cell)

            # Channel and Frequency
            channel = getattr(cell, 'channel', 0)
            frequency = getattr(cell, 'frequency', 0)
            print("[WiFiScanner] frequency cell: {}".format(frequency))

            # Encryption
            encrypted = _("Yes") if cell.encrypted else _("No")

            # Format signal quality
            signal_quality = format_signal_quality(quality)

            return _(
                "{index:2d}. {essid:20} | Quality: {quality:3}% ({signal_quality}) | Signal: {signal:4} dBm | Channel: {channel:2} | Encrypted: {encrypted}\n"
            ).format(
                index=index + 1,
                essid=essid,
                quality=quality,
                signal_quality=signal_quality,
                signal=signal,
                channel=channel,
                encrypted=encrypted
            )

        except Exception as e:
            print("[WiFiScanner] Error parsing cell: {}".format(e))
            return None

    def parse_quality(self, quality_str):
        """Parse quality string (e.g., '39/70')"""
        try:
            if isinstance(quality_str, str) and '/' in quality_str:
                parts = quality_str.split('/')
                if len(parts) == 2:
                    current = int(parts[0])
                    max_val = int(parts[1])
                    if max_val > 0:
                        return int((current / max_val) * 100)
            return 0
        except (ValueError, ZeroDivisionError):
            return 0

    def extract_signal_from_cell(self, cell, debug=False):
        """Extract signal strength from a Cell object"""
        signal = 0

        # Method 1: direct signal attribute
        if hasattr(cell, 'signal') and cell.signal is not None:
            if isinstance(cell.signal, (int, float)):
                return int(cell.signal)
            elif isinstance(cell.signal, str):
                match = search(r'(-?\d+)\s*dBm?', cell.signal)
                if match:
                    return int(match.group(1))

        # Method 2: estimate from quality
        quality = self.parse_quality(getattr(cell, 'quality', '0/100'))
        if quality > 0:
            # Rough estimation: -30dBm (excellent) to -90dBm (poor)
            return int(-90 + (quality * 0.6))

        return signal

    def parse_iwlist_output(self, output):
        """Parse iwlist output with debug"""
        print("[WiFiScanner] Parsing iwlist output...")

        networks = []

        if "Cell" not in output:
            print("[WiFiScanner] No 'Cell' found in iwlist output")
            return [_("iwlist: No networks found or interface busy\n")]

        lines = output.split('\n')
        current_net = {}
        cell_count = 0

        for line in lines:
            line = line.strip()
            print("[WiFiScanner] iwlist line: {}".format(line))

            # New cell
            if 'Cell' in line and 'Address' in line:
                cell_count += 1

                if current_net:
                    formatted = self.format_network(current_net)
                    networks.append(formatted)
                    print(
                        "[WiFiScanner] Added network: {}".format(
                            formatted.strip()))

                parts = line.split('Address: ')
                current_net = {'bssid': parts[1] if len(parts) > 1 else ''}
                print("[WiFiScanner] New cell #{}".format(cell_count))

            # ESSID
            elif 'ESSID:' in line:
                essid = line.split('ESSID:"')[1].rstrip(
                    '"') if 'ESSID:"' in line else _('Hidden')
                current_net['essid'] = essid
                print("[WiFiScanner] Found ESSID: {}".format(essid))

            # Quality
            elif 'Quality=' in line:
                match = search(r'Quality=(\d+)/(\d+)', line)

                if match:
                    try:
                        current_qual = int(match.group(1))
                        max_qual = int(match.group(2))

                        if max_qual > 0:
                            quality = (current_qual / max_qual) * 100
                            current_net['quality'] = int(quality)
                            print("[WiFiScanner] Quality: {}/{} = {}%".format(
                                current_qual, max_qual, quality
                            ))
                        else:
                            current_net['quality'] = 0
                            print("[WiFiScanner] Quality: {}/{} = 0% (max is 0)".format(
                                current_qual, max_qual
                            ))

                    except (ValueError, ZeroDivisionError) as e:
                        current_net['quality'] = 0
                        print(
                            "[WiFiScanner] Error parsing quality: {}".format(e))

                signal_match = search(r'Signal level=(-?\d+)', line)

                if signal_match:
                    current_net['signal'] = int(signal_match.group(1))
                    print(
                        "[WiFiScanner] Signal: {} dBm".format(
                            signal_match.group(1)))

                else:
                    alt_signal_match = search(
                        r'signal[=:](-?\d+)', line, search.IGNORECASE)

                    if alt_signal_match:
                        current_net['signal'] = int(alt_signal_match.group(1))
                        print("[WiFiScanner] Signal (alt): {} dBm".format(
                            alt_signal_match.group(1)
                        ))

            # Signal level (separate line)
            elif 'Signal level=' in line and 'quality' not in line.lower():
                match = search(r'Signal level=(-?\d+)', line)

                if match:
                    current_net['signal'] = int(match.group(1))
                    print(
                        "[WiFiScanner] Signal level: {} dBm".format(
                            match.group(1)))

        if current_net:
            formatted = self.format_network(current_net)
            networks.append(formatted)
            print("[WiFiScanner] Final network: {}".format(formatted.strip()))

        print("[WiFiScanner] Total networks parsed: {}".format(len(networks)))

        return networks if networks else [_("iwlist: No networks found\n")]

    def fallback_iwlist_scan(self):
        """Fallback scan with iwlist using tools.py"""
        print("[WiFiScanner] Starting fallback iwlist scan")
        networks = []
        networks.append(_("\n=== FALLBACK SCAN with iwlist ===\n"))

        try:
            wifi_ifaces = get_wifi_interfaces()

            for iface in wifi_ifaces:
                try:
                    print(f"[WiFiScanner] iwlist scan on {iface}")
                    result = subprocess.check_output(['iwlist', iface, 'scan'],
                                                     stderr=subprocess.STDOUT,
                                                     text=True,
                                                     timeout=15)
                    print(f"[WiFiScanner] iwlist output length: {len(result)}")

                    # DEBUG: Show sample of iwlist output for signal parsing
                    lines = result.split('\n')
                    signal_lines = [
                        line for line in lines if 'Signal level' in line or 'Quality' in line]
                    for i, line in enumerate(signal_lines[:3]):
                        print(
                            f"[SIGNAL] iwlist signal line {i}: {
                                line.strip()}")

                    # Use parse_iwlist_detailed da tools.py
                    parsed_networks = parse_iwlist_detailed(result)
                    if parsed_networks:
                        for i, net in enumerate(parsed_networks):
                            essid = net.get('essid', _('Unknown'))
                            signal = net.get('signal', 0)
                            quality_percent = net.get('quality_percent', 0)
                            channel = net.get('channel', '?')
                            encrypted = _("Yes") if net.get(
                                'encryption') else _("No")

                            # Use format_signal_quality
                            signal_quality = format_signal_quality(
                                quality_percent)

                            networks.append(
                                _("{index:2d}. {essid:20} | Quality: {quality:3}% ({signal_quality}) | Signal: {signal:4} dBm | Channel: {channel} | Encrypted: {encrypted}\n").format(
                                    index=i +
                                    1,
                                    essid=essid,
                                    quality=quality_percent,
                                    signal_quality=signal_quality,
                                    signal=signal,
                                    channel=channel,
                                    encrypted=encrypted))
                        print("[WiFiScanner] iwlist found {} networks".format(
                            len(parsed_networks)
                        ))
                        break
                    else:
                        print("[WiFiScanner] No networks parsed from iwlist output")
                except Exception as e:
                    print(
                        "[WiFiScanner] iwlist error on {}: {}".format(
                            iface, e))
                    continue

            if len(networks) <= 2:  # Only header
                networks.append(_("   No results with iwlist\n"))
                print("[WiFiScanner] iwlist found no networks")

        except Exception as e:
            error_msg = _("   iwlist error: {}\n").format(e)
            networks.append(error_msg)
            print("[WiFiScanner] {}".format(error_msg))

        return networks

    def process_pythonwifi_scan(self, scan_results):
        """Process pythonwifi results"""
        networks = []
        if not scan_results:
            return [_("pythonwifi: No networks found\n")]

        for i, network in enumerate(scan_results):
            essid = network.essid or _("Hidden")
            quality = network.quality.quality if network.quality else 0
            signal = network.quality.siglevel if network.quality else 0

            networks.append(
                _("{index}. {essid:20} | Quality: {quality:3}% | Signal: {signal:4} dBm\n").format(
                    index=i + 1, essid=essid, quality=quality, signal=signal))

        return networks

    def format_network(self, net):
        """Format a network for display"""
        essid = net.get('essid', _('Unknown'))
        quality = net.get('quality', 0)
        signal = net.get('signal', 0)
        bssid = net.get('bssid', '')[:8]
        return _("{essid:20} | Quality: {quality:3}% | Signal: {signal:4} dBm | {bssid}...\n").format(
            essid=essid, quality=quality, signal=signal, bssid=bssid)

    def format_network_info(self, net):
        """Format network info for display"""
        essid = net.get('essid', _('Unknown'))
        bssid = net.get('bssid', _('Unknown'))
        quality = net.get('quality', 0)
        signal = net.get('signal', 0)

        return _("{essid:20} | Quality: {quality:3}% | Signal: {signal:4} dBm | {bssid}\n").format(
            essid=essid, quality=quality, signal=signal, bssid=bssid)

    def get_basic_network_info(self, network, index):
        essid = network.essid or _("Hidden")
        quality = network.quality.quality if network.quality else 0
        signal = network.quality.siglevel if network.quality else 0

        return _("{index:2d}. {essid:20} | Quality: {quality:3}% | Signal: {signal:4} dBm\n").format(
            index=index, essid=essid, quality=quality, signal=signal)

    def get_detailed_network_status(self):
        """Detailed network diagnostics"""
        info = []
        info.append("\n" + "=" * 50)
        info.append(_("\nDETAILED DIAGNOSTICS"))
        info.append("\n" + "=" * 50 + "\n")

        try:
            # WiFi Interfaces
            info.append(_("\nWIFI INTERFACES:\n"))
            wifi_ifaces = get_wifi_interfaces()
            if wifi_ifaces:
                info.append(_("   Found: {}\n").format(', '.join(wifi_ifaces)))
            else:
                info.append(_("   No WiFi interfaces found\n"))

            # Interface status
            info.append(_("\nINTERFACE STATUS:\n"))
            for iface in wifi_ifaces:
                status = _("ACTIVE") if is_interface_up(
                    iface) else _("INACTIVE")
                icon = "V" if is_interface_up(iface) else "X"
                info.append(
                    _("   {icon} {interface}: {status}\n").format(
                        icon=icon, interface=iface, status=status))

            # Active connections
            info.append(_("\nACTIVE CONNECTIONS:\n"))
            for iface in wifi_ifaces:
                interface_info = get_interface_info(iface)
                if 'essid' in interface_info and interface_info['essid'] != _(
                        "Not connected"):
                    essid = interface_info['essid']
                    quality = interface_info.get('quality', '?')
                    info.append(
                        _("   {interface}: Connected to {essid} ({quality})\n").format(
                            interface=iface, essid=essid, quality=quality))
                else:
                    info.append(
                        _("   {interface}: Not connected\n").format(
                            interface=iface))

            # Solutions
            info.append(_("\nPOSSIBLE SOLUTIONS:\n"))
            info.append(_("   1. Disconnect from current WiFi network\n"))
            info.append(_("   2. Restart WiFi adapter\n"))
            info.append(_("   3. Check if WiFi driver is installed\n"))
            info.append(_("   4. Try with different USB WiFi adapter\n"))
            info.append(_("   5. Check root permissions\n"))

        except Exception as e:
            info.append(_("Diagnostic error: {}\n").format(e))

        return info

    def display_networks(self, networks):
        if isinstance(networks, list):
            self["scan_output"].setText("".join(networks))
        else:
            self["scan_output"].setText(networks)

    def toggle_details(self):
        self.detailed_view = not self.detailed_view
        if self.detailed_view:
            self["scan_output"].setText(
                _("Detailed view enabled - rescan to see details"))
        else:
            self["scan_output"].setText(
                _("Basic view enabled - rescan to see basic info"))
