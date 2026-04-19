# -*- coding: utf-8 -*-

import time
import traceback
import subprocess

from json import dump
from os.path import exists
from re import IGNORECASE, search, escape, sub, DOTALL
from twisted.internet import reactor, threads

from Screens.MessageBox import MessageBox
from Screens.Screen import Screen
from Screens.ChoiceBox import ChoiceBox
from Screens.InputBox import InputBox

from Components.ActionMap import ActionMap
from Components.Label import Label
from Components.MenuList import MenuList
from Components.config import ConfigPassword, ConfigSubsection, ConfigYesNo

from . import _
from .tools import (
    # ensure_interface_up,
    format_signal_quality,
    get_current_connected_essid,
    get_interface_info,
    get_ip_address,
    get_wifi_interfaces,
    load_saved_networks,
    # parse_iwlist_detailed,
    scan_networks as tools_scan,
    # scan_networks_simple,
    verify_connection,
)
from .config import WiFiConfigScreen

"""
#########################################################
#                                                       #
#  WiFi Manager Plugin                                  #
#  Version: 1.0                                         #
#  Created by Lululla (https://github.com/Belfagor2005) #
#  License: Gnu Gpl v2                                  #
#  https://creativecommons.org/licenses/by-nc-sa/4.0    #
#  Last Modified: "00:00 - 20251110"                    #
#                                                       #
#  Credits:                                             #
#  - Original concept by Lululla                        #
#  Usage of this code without proper attribution        #
#  is strictly prohibited.                              #
#  For modifications and redistribution,                #
#  please maintain this credit header.                  #
#########################################################
"""


CONFIG_FILE = "/etc/wifi_saved_networks.json"
MODE_LIST = ["WPA/WPA2", "WPA2", "WPA", "WEP", "Unencrypted"]
WEP_LIST = ["ASCII", "HEX"]


class WiFiConnectZ(Screen):
    skin = """
    <screen position="center,center" size="800,700" title="WiFi Connection Manager">
        <widget name="network_list" position="10,5" size="776,350" scrollbarMode="showOnDemand" />
        <widget name="status" position="10,368" size="776,250" font="Regular;20" />
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
        self.list = []
        Screen.__init__(self, session)

        self.session = session
        self.networks = []
        self.current_network = None
        self.interface = None
        self.is_scanning = False
        self.is_connecting = False
        self.helpList = []

        self.connect_config = ConfigSubsection()
        self.connect_config.password = ConfigPassword(
            default="", fixed_size=False)
        self.connect_config.remember = ConfigYesNo(default=True)

        self["network_list"] = MenuList([])
        self["status"] = Label(_("Initializing WiFi..."))
        self["key_red"] = Label(_("Exit"))
        self["key_green"] = Label()
        self["key_yellow"] = Label()
        self["key_blue"] = Label(_("Scan"))

        self.normal_actions = ActionMap(
            ["ColorActions", "OkCancelActions", "DirectionActions"],
            {
                "red": self.keyExit,
                "green": self.do_nothing,
                "yellow": self.do_nothing,
                "blue": self.scan_networks,
                "cancel": self.keyExit,
                "ok": self.show_network_options,
                "up": self.keyUp,
                "down": self.keyDown,
                "left": self.keyLeft,
                "right": self.keyRight
            },
            -1
        )
        self.setTitle(_("WiFi Connection Manager"))

        self.interfaces = get_wifi_interfaces()
        self.find_wifi_interface()

        self.saved_networks = load_saved_networks(CONFIG_FILE, self.interface)

        self.check_current_connection()
        reactor.callLater(1, self.force_initial_scan)
        self["actions"] = self.normal_actions

    def do_nothing(self):
        print("[DEBUG] Button in pause")

    def force_initial_scan(self):
        """Force initial scan with fallback"""
        print("[DEBUG] Force initial scan")
        if not self.interface:
            print("[DEBUG] No interface available for initial scan")
            self["status"].setText(_("No WiFi interface available"))
            return

        print(f"[DEBUG] Starting initial scan on interface: {self.interface}")
        self["status"].setText(_("Performing initial scan..."))
        self.scan_networks()

    def find_wifi_interface(self):
        """Find available WiFi interface using the improved function from tools.py"""
        print("[WiFiConnectZ] Finding WiFi interface...")

        interfaces = self.interfaces

        if interfaces:
            self.interface = interfaces[0]
            print(f"[WiFiConnectZ] Using interface: {self.interface}")
            self["status"].setText(
                _("Interface found: {}").format(
                    self.interface))
        else:
            self.interface = None
            self["status"].setText(_("No WiFi interface found"))
            self.show_message(
                _("No WiFi interface detected. Please check your hardware."))
            print("[WiFiConnectZ] No WiFi interfaces found")

    def select_network_simple(self):
        """Automatically select when browsing"""
        print("[DEBUG] select_network_simple CALLED")
        index = self["network_list"].getSelectionIndex()
        print("[DEBUG] Current index: " + str(index))
        print("[DEBUG] Total networks: " + str(len(self.networks)))

        if index is not None and index < len(self.networks):
            self.current_network = self.networks[index]
            essid = self.current_network.get('essid')
            print("[DEBUG] SELECTED NETWORK: " + str(essid))
            self.update_status_based_on_network()
        else:
            print(f"[DEBUG] NO NETWORK SELECTED - index: {index}")

    def scan_networks(self):
        """Scan for available WiFi networks - NON-BLOCKING"""
        if self.is_scanning:
            return

        if not self.interface:
            self["status"].setText(_("No WiFi interface available"))
            return

        self.is_scanning = True
        self["key_blue"].setText(_("Scanning..."))
        self["status"].setText(_("Scanning for networks..."))

        def do_scan():
            try:
                return tools_scan(self.interface, detailed=True)
            except Exception as e:
                print(f"[DEBUG] Scan failed: {e}")
                return []

        def scan_completed(networks):
            self.is_scanning = False
            self["key_blue"].setText(_("Scan"))
            self.networks = networks
            self.update_display_after_scan()

        def scan_failed(failure):
            self.is_scanning = False
            self["key_blue"].setText(_("Scan"))
            self["status"].setText(_("Scan failed"))
            print(f"[DEBUG] Scan error: {failure}")

        deferred = threads.deferToThread(do_scan)
        deferred.addCallback(scan_completed)
        deferred.addErrback(scan_failed)

    def update_network_list(self):
        """Update the network list display with connection indicators"""
        network_list = []
        current_essid = get_current_connected_essid(self.interface)

        print(f"[DEBUG] Current connected ESSID: {current_essid}")

        # Save the current selection
        current_index = self["network_list"].getSelectionIndex()

        for net in self.networks:
            essid = net.get('essid', _('Unknown'))
            signal = net.get('signal', 0)
            is_encrypted = net.get('encryption', False)

            # CONNECTION INDICATOR - mark if this is the currently connected
            # network
            if essid == current_essid:
                connection_indicator = "-> "
            else:
                connection_indicator = "   "

            # Security icon
            if is_encrypted:
                icon = _("[LOCK]")
                security = _("Secured")
            else:
                icon = _("[OPEN]")
                security = _("Open")

            # Saved password indicator
            if self.get_saved_password(essid):
                saved_indicator = _("[SAVED] ")
            else:
                saved_indicator = ""

            network_list.append(
                _("{connection}{saved}{icon} {essid} | {security} | {signal} dBm").format(
                    connection=connection_indicator,
                    saved=saved_indicator,
                    icon=icon,
                    essid=essid,
                    security=security,
                    signal=signal))

        print(f"[DEBUG] update_network_list - {len(network_list)} items")

        # Update the list
        self["network_list"].setList(network_list)

        # Restore the previous selection if possible
        if current_index is not None and current_index < len(network_list):
            self["network_list"].moveToIndex(current_index)
        elif network_list:
            self["network_list"].moveToIndex(0)

    def update_status(self, message):
        """Update status label"""
        self["status"].setText(message)

    def update_status_selection(self):
        """Update status based on current selection"""
        if not self.current_network:
            self.show_current_connection_status()
            return

        essid = self.current_network.get('essid')
        current_essid = get_current_connected_essid(self.interface)

        print(
            f"[DEBUG] update_status_selection - Selected: {essid}, Connected: {current_essid}")

        if current_essid == essid:
            # Already connected to this network
            self.update_status(
                _("CONNECTED to: {} - Press OK for options").format(essid))
        elif self.current_network.get('encryption'):
            # Protected network
            if self.get_saved_password(essid):
                self.update_status(
                    _("{} - Password saved - Press OK for options").format(essid))
            else:
                self.update_status(
                    _("{} - Password required - Press OK for options").format(essid))
        else:
            # Open network
            self.update_status(
                _("{} - Open network - Press OK for options").format(essid))

    def update_button_labels(self):
        """Update button labels based on selection"""
        if not self.current_network:
            return
        return  # hide buttons

    def update_status_based_on_network(self):
        """Update status with network info"""
        if not self.current_network:
            self.show_current_connection_status()
            return

        essid = self.current_network.get('essid')
        current_essid = get_current_connected_essid(self.interface)
        is_encrypted = self.current_network.get('encryption', False)
        has_saved_password = self.get_saved_password(essid)
        signal_strength = self.current_network.get('signal', 0)

        signal_quality = format_signal_quality(signal_strength)

        # IF CONNECTED TO THIS NETWORK
        if current_essid == essid:
            interface = get_wifi_interfaces()
            ip = _("No IP")
            if interface:
                ip = get_ip_address(interface)

            # Check if static IP is configured
            network_type = _("DHCP")
            try:
                if exists("/etc/enigma2/network.conf"):
                    with open("/etc/enigma2/network.conf", 'r') as f:
                        for line in f:
                            if line.startswith('connection_type='):
                                network_type = _(
                                    "Static") if "static" in line else _("DHCP")
                                break
            except Exception as e:
                print(e)
                pass

            status_msg = _("CONNECTED to: {essid}\nIP: {ip} | Network: {network_type}\nSignal: {quality} ({strength} dBm)\nPress OK for options").format(
                essid=essid, ip=ip or _("No IP"), network_type=network_type, quality=signal_quality, strength=signal_strength)

        # PROTECTED NETWORK WITH SAVED PASSWORD
        elif is_encrypted and has_saved_password:
            status_msg = _("{essid} - Password saved\nSignal: {quality} ({strength} dBm)\nPress OK to connect or edit").format(
                essid=essid, quality=signal_quality, strength=signal_strength)

        # PROTECTED NETWORK WITHOUT PASSWORD
        elif is_encrypted:
            status_msg = _("{essid} - Password required\nSignal: {quality} ({strength} dBm)\nPress OK to enter password").format(
                essid=essid, quality=signal_quality, strength=signal_strength)

        # OPEN NETWORK
        else:
            status_msg = _("{essid} - Open network\nSignal: {quality} ({strength} dBm)\nPress OK to connect").format(
                essid=essid, quality=signal_quality, strength=signal_strength)

        self["status"].setText(status_msg)

    def update_wpa_supplicant(self, essid, password, encryption):
        """Update wpa_supplicant configuration"""
        try:
            wpa_file = "/etc/wpa_supplicant.%s.conf" % self.interface

            # Read existing content
            content = ""
            if exists(wpa_file):
                with open(wpa_file, 'r') as f:
                    content = f.read()

            # Remove existing network block for this ESSID
            content = sub(
                r'network=\{([^}]*ssid="%s"[^}]*)\}' %
                escape(essid), '', content, flags=DOTALL)

            # Add new network block
            network_block = """
                network={
                    ssid="%s"
                    scan_ssid=0
                    key_mgmt=WPA-PSK
                    proto=WPA RSN
                    pairwise=CCMP TKIP
                    group=CCMP TKIP
                    psk="%s"
                }
                """ % (essid, password)

            # Append new network block
            content = content.rstrip() + network_block

            # Write back to file
            with open(wpa_file, 'w') as f:
                f.write(content)

            print("[DEBUG] Updated wpa_supplicant for: " + essid)

        except Exception as e:
            print("[DEBUG] Error updating wpa_supplicant: " + str(e))

    def update_display_after_scan(self):
        """Update display after scanning completes"""
        print("[DEBUG] ENTERED update_display_after_scan")

        try:
            if self.networks:
                print(f"[DEBUG] Networks found: {len(self.networks)}")

                # UPDATE THE VISIBLE LIST
                self.update_network_list()
                print("[DEBUG] After update_network_list")

                self["network_list"].moveToIndex(0)
                print("[DEBUG] Before select_network_simple")
                self.select_network_simple()
                print("[DEBUG] After select_network_simple")
            else:
                print("[DEBUG] No networks found")
                self["status"].setText(
                    _("No networks found - Press BLUE to rescan"))
                self["network_list"].setList([_("No networks found")])

            print("[DEBUG] update_display_after_scan COMPLETED")

        except Exception as e:
            print(f"[DEBUG] ERROR in update_display_after_scan: {e}")
            traceback.print_exc()

    def refresh_after_configuration(self):
        """Refresh after configuration"""
        print("[DEBUG] Refresh after configuration")
        # Reload saved networks
        self.saved_networks = load_saved_networks(CONFIG_FILE, self.interface)
        # Update the network list in the UI
        self.update_network_list()
        # Update status based on the currently selected network
        self.update_status_based_on_network()

    def refresh_after_connection(self):
        """Simple but effective refresh"""
        print("[DEBUG] Refreshing GUI after connection change")

        # 1. Update current connection status
        self.check_current_connection()

        # 2. Refresh the network list (rebuild the entire list)
        self.update_network_list()

        # 3. Update the buttons
        self.update_button_labels()

        # 4. Update the status display
        self.update_status_selection()

        print("[DEBUG] GUI refresh completed")

    def save_network_password(self, essid, password, encryption="WPA/WPA2"):
        """Save network password to BOTH JSON and wpa_supplicant"""
        try:
            print("[DEBUG] Saving network to both systems: " + essid)

            # Save to JSON
            self.saved_networks[essid] = {
                'password': password,
                'encryption': encryption,
                'timestamp': time.time(),
                'interface': self.interface
            }
            with open(CONFIG_FILE, 'w') as f:
                dump(self.saved_networks, f, indent=2)

            # Also update wpa_supplicant
            self.update_wpa_supplicant(essid, password, encryption)

            print("[DEBUG] Network saved successfully")

        except Exception as e:
            print("[DEBUG] Error saving network: " + str(e))

    def get_saved_password(self, essid):
        """Get saved password for network"""
        saved = self.saved_networks.get(essid, {})
        password = saved.get('password', "")
        print("[DEBUG] get_saved_password for '%s': '%s'" % (
            essid, "***" if password else "EMPTY"))
        return password

    def get_current_connected_essid(self):
        """Semplificato - usa tools.py"""
        return get_current_connected_essid(self.interface)

    def verify_connectionp(self, essid):
        """Semplificato - usa tools.py"""
        return verify_connection(self.interface, essid)

    def handle_connect_after_password(self, answer, callback):
        """Handle connection after password entry"""
        if answer:
            self.execute_connection_with_callback(None)

    def handle_connect_after_config(self, answer, callback):
        """Handle connection after configuration"""
        if answer:
            self.execute_connection_with_callback(None)

    def connect_to_open_network_thread(self):
        try:
            essid = self.current_network.get('essid')

            # Disconnect first
            subprocess.run(
                "iwconfig {} essid off".format(self.interface),
                shell=True,
                capture_output=True,
                timeout=5
            )
            time.sleep(1)

            # Connect to open network
            cmd = 'iwconfig {} essid "{}"'.format(self.interface, essid)
            result = subprocess.run(
                cmd,
                shell=True,
                capture_output=True,
                text=True,
                timeout=30
            )

            if result.returncode == 0:
                dhcp_success = False

                for dhcp_client in ['dhcpcd', 'udhcpc', 'dhclient']:
                    try:
                        if dhcp_client == 'dhcpcd':
                            result = subprocess.run(
                                ['dhcpcd', self.interface],
                                capture_output=True,
                                text=True,
                                timeout=15
                            )
                        elif dhcp_client == 'udhcpc':
                            result = subprocess.run(
                                ['udhcpc', '-i', self.interface, '-t', '5', '-n'],
                                capture_output=True,
                                text=True,
                                timeout=15
                            )
                        elif dhcp_client == 'dhclient':
                            result = subprocess.run(
                                ['dhclient', self.interface, '-v'],
                                capture_output=True,
                                text=True,
                                timeout=15
                            )

                        if result.returncode == 0:
                            dhcp_success = True
                            break
                    except Exception as e:
                        print(e)
                        continue

                time.sleep(3)
                return self.verify_connectionp(essid) and dhcp_success
            else:
                return False

        except Exception as e:
            print("[DEBUG] Open network connection error: {}".format(e))
            return False

    def connect_with_saved_config_thread(self, essid, password=None):
        """Connect using saved configuration - IN THREAD"""
        try:
            # Stop any existing connections
            subprocess.run(['killall', 'wpa_supplicant'],
                           capture_output=True, timeout=5)
            subprocess.run(['killall', 'dhclient'],
                           capture_output=True, timeout=5)
            subprocess.run(['killall', 'dhcpcd'],
                           capture_output=True, timeout=5)
            time.sleep(2)

            # Start wpa_supplicant with saved config
            config_file = f"/etc/wpa_supplicant.{self.interface}.conf"
            if not exists(config_file):
                return False

            cmd = [
                'wpa_supplicant',
                '-B',
                '-i',
                self.interface,
                '-c',
                config_file]
            result = subprocess.run(
                cmd, capture_output=True, text=True, timeout=10)

            if result.returncode != 0:
                return False

            # Wait for association
            time.sleep(3)

            # Try multiple DHCP clients
            dhcp_success = False
            for dhcp_client in ['dhcpcd', 'udhcpc', 'dhclient']:
                try:
                    print("[DEBUG] Trying DHCP client: " + dhcp_client)
                    if dhcp_client == 'dhcpcd':
                        result = subprocess.run(
                            ['dhcpcd', self.interface], capture_output=True, text=True, timeout=15)
                    elif dhcp_client == 'udhcpc':
                        result = subprocess.run(['udhcpc',
                                                 '-i',
                                                 self.interface,
                                                 '-t',
                                                 '5',
                                                 '-n'],
                                                capture_output=True,
                                                text=True,
                                                timeout=15)
                    elif dhcp_client == 'dhclient':
                        result = subprocess.run(
                            ['dhclient', self.interface, '-v'], capture_output=True, text=True, timeout=15)

                    if result.returncode == 0:
                        dhcp_success = True
                        break
                except Exception as e:
                    print(e)
                    continue

            # Verify connection
            time.sleep(2)
            return self.verify_connectionp(essid) and dhcp_success

        except Exception as e:
            print(f"[DEBUG] Connection error: {e}")
            return False

    def execute_connection(self):
        """Make connection in separate thread to avoid GUI freeze"""
        if self.is_connecting:
            return

        self.is_connecting = True
        essid = self.current_network.get('essid')
        self["status"].setText(_("Connecting to %s...") % essid)

        def connect_thread():
            try:
                if self.current_network.get('encryption'):
                    saved_password = self.get_saved_password(essid)
                    return self.connect_with_saved_config_thread(
                        essid, saved_password)
                else:
                    return self.connect_to_open_network_thread()
            except Exception as e:
                print(f"[DEBUG] Connection error in thread: {e}")
                return False
            finally:
                self.is_connecting = False

        def connect_callback(success):
            if success:
                self["status"].setText(_("Connected to %s") % essid)
                self.refresh_after_connection()
            else:
                self["status"].setText(_("Failed to connect to %s") % essid)
            self.update_button_labels()

        threads.deferToThread(connect_thread).addCallback(connect_callback)

    def execute_connection_with_callback(self, callback):
        """Execute connection with network configuration"""
        def connection_finished(success):
            if success:
                # Apply network configuration ONLY after successful WiFi
                # connection
                self.apply_network_configuration()
                self.show_message(_("Connected successfully!"))
            else:
                self.show_message(_("Connection failed!"))
            self.refresh_after_connection()

        if self.current_network.get('encryption'):
            saved_password = self.get_saved_password(
                self.current_network.get('essid'))
            success = self.connect_with_saved_config_thread(
                self.current_network.get('essid'), saved_password)
        else:
            # ALWAYS USE THE THREADED VERSION
            success = self.connect_to_open_network_thread()

        # Wait for the thread to finish before applying network config
        reactor.callLater(5, lambda: connection_finished(success))

    def open_configuration_with_callback(self, callback):
        """Open configuration and return to callback - FIXED"""
        print("[DEBUG] OPEN CONFIGURATION CALLED")

        try:
            if not self.current_network:
                print("[DEBUG] No current network")
                if callback:
                    callback()
                return

            essid = self.current_network.get('essid')
            if not essid:
                print("[DEBUG] No ESSID")
                if callback:
                    callback()
                return

            saved_config = self.saved_networks.get(essid, {})
            print("[DEBUG] Saved config:", saved_config)

            network_info = {
                'essid': essid,
                'encryption': saved_config.get('encryption', 'WPA/WPA2'),
                'password': saved_config.get('password', '')
            }

            def config_callback(result):
                print("[DEBUG] Configuration callback, result:", result)
                self.refresh_after_configuration()

                if result:
                    self.session.openWithCallback(
                        lambda answer: self.handle_connect_after_config(
                            answer,
                            callback),
                        MessageBox,
                        _("WiFi and network configuration saved for %s\n\nConnect now?") %
                        essid,
                        MessageBox.TYPE_YESNO)
                else:
                    if callback:
                        callback()

            print("[DEBUG] Opening WiFiConfigScreen...")
            self.session.openWithCallback(
                config_callback,
                WiFiConfigScreen,
                self.interface,
                network_info
            )

        except Exception as e:
            print("[DEBUG] Error opening config:", str(e))
            traceback.print_exc()
            if callback:
                callback()

    def open_password_dialog_with_callback(self, callback):
        """Open password dialog and return to callback - FIXED"""
        def password_entered(password):
            if password:
                essid = self.current_network.get('essid')
                self.save_network_password(essid, password)

                self.session.openWithCallback(
                    lambda answer: self.handle_connect_after_password(
                        answer, callback), MessageBox, _("Password saved for %s\n\nConnect now?") %
                    essid, MessageBox.TYPE_YESNO)
            else:
                if callback:
                    callback()

        self.session.openWithCallback(
            password_entered,
            InputBox,
            title=_("Enter password for: %s") %
            self.current_network.get('essid'),
            windowTitle=_("WiFi Password"))

    def apply_network_configuration(self):
        """Applica configurazione network da /etc/enigma2/network.conf"""
        try:
            config_file = "/etc/enigma2/network.conf"
            if not exists(config_file):
                print("[DEBUG] No network configuration found")
                return

            # Leggi configurazione
            config_data = {}
            with open(config_file, 'r') as f:
                for line in f:
                    line = line.strip()
                    if line and not line.startswith('#') and '=' in line:
                        key, value = line.split('=', 1)
                        config_data[key] = value

            # Applica configurazione
            if config_data.get('connection_type') == 'static':
                ip = config_data.get('ip', '')
                netmask = config_data.get('netmask', '')
                gateway = config_data.get('gateway', '')

                if ip and netmask:
                    cmd = f"ifconfig {self.interface} {ip} netmask {netmask}"
                    subprocess.run(cmd, shell=True, timeout=10)

                if gateway:
                    cmd = f"route add default gw {gateway} {self.interface}"
                    subprocess.run(cmd, shell=True, timeout=10)

                # Applica DNS
                dns1 = config_data.get('dns1', '')
                dns2 = config_data.get('dns2', '')
                if dns1 or dns2:
                    dns_content = ""
                    if dns1:
                        dns_content += f"nameserver {dns1}\n"
                    if dns2:
                        dns_content += f"nameserver {dns2}\n"

                    with open("/etc/resolv.conf", "w") as f:
                        f.write(dns_content)

                print("[DEBUG] Static network configuration applied")
            else:
                # DHCP - ottieni IP automaticamente
                subprocess.run(
                    "dhclient {}".format(self.interface),
                    shell=True,
                    timeout=15
                )
                print("[DEBUG] DHCP configuration applied")

        except Exception as e:
            print(f"[DEBUG] Error applying network configuration: {e}")

    def disconnect_from_network(self):
        """Disconnect from current network - IN THREAD"""
        def disconnect_thread():
            try:
                subprocess.run(
                    "killall wpa_supplicant 2>/dev/null",
                    shell=True,
                    timeout=5
                )

                subprocess.run(
                    "killall dhclient 2>/dev/null",
                    shell=True,
                    timeout=5
                )

                subprocess.run(
                    "iwconfig {} essid off".format(self.interface),
                    shell=True,
                    timeout=5
                )

                # Reset interface
                subprocess.run(
                    "ip link set {} down".format(self.interface),
                    shell=True,
                    timeout=5
                )

                subprocess.run(
                    "ip link set {} up".format(self.interface),
                    shell=True,
                    timeout=5
                )

                return True

            except Exception as e:
                print("[DEBUG] Disconnect error: {}".format(e))
                return False

        def disconnect_callback(success):
            if success:
                self["status"].setText(_("Disconnected"))
                self.refresh_after_connection()
            else:
                self["status"].setText(_("Error disconnecting"))

        threads.deferToThread(disconnect_thread).addCallback(
            disconnect_callback)

    def forget_network_with_callback(self, callback):
        """Forget network and return to callback - FIXED"""

        def forget_finished():
            self.session.openWithCallback(
                lambda result: callback() if callback else None,
                MessageBox,
                _("Network forgotten!"),
                MessageBox.TYPE_INFO,
                timeout=3
            )

        self.forget_network()
        reactor.callLater(0.5, forget_finished)

    def forget_network(self):
        """Forget saved network - removes ALL fields"""
        if not self.current_network:
            return

        essid = self.current_network.get('essid')
        if essid in self.saved_networks:
            del self.saved_networks[essid]  # Remove entire entry
            try:
                with open(CONFIG_FILE, 'w') as f:
                    dump(self.saved_networks, f, indent=2)
                self.show_message(_("Forgotten network: {}").format(essid))
                self.update_network_list()
            except Exception as e:
                self.show_message(_("Error: {}").format(str(e)))

    def show_current_connection_status(self):
        """Show current connection status"""
        try:
            result = subprocess.run(
                "iwconfig {}".format(self.interface),
                shell=True,
                capture_output=True,
                text=True
            )

            if 'ESSID:' in result.stdout:
                essid_match = search(r'ESSID:"([^"]*)"', result.stdout)

                if essid_match and essid_match.group(1):
                    essid = essid_match.group(1)

                    signal_match = search(
                        r'Signal level=(-?\d+)', result.stdout)
                    signal = signal_match.group(1) if signal_match else "?"

                    # Get IP address
                    ip_result = subprocess.run(
                        "ip addr show {}".format(self.interface),
                        shell=True,
                        capture_output=True,
                        text=True
                    )

                    ip_match = search(
                        r'inet (\d+\.\d+\.\d+\.\d+)', ip_result.stdout)
                    ip_addr = ip_match.group(1) if ip_match else _("No IP")

                    self["status"].setText(
                        _("Connected: {} | Signal: {} dBm | IP: {}").format(
                            essid,
                            signal,
                            ip_addr
                        )
                    )
                    return

            self["status"].setText(_("Not connected to any network"))

        except Exception as e:
            self["status"].setText(_("Status check failed: {}".format(e)))

    def show_connection_details_with_callback(self, callback):
        """Show connection details in vertical format"""
        try:
            result = subprocess.run(
                f"iwconfig {
                    self.interface}",
                shell=True,
                capture_output=True,
                text=True)
            if result.returncode == 0:
                details = []

                # Parse and organize connection details
                lines = result.stdout.split('\n')
                for line in lines:
                    line = line.strip()
                    if not line:
                        continue

                    # Organize key information in readable format
                    if 'ESSID:' in line:
                        essid_match = search(r'ESSID:"([^"]*)"', line)
                        if essid_match:
                            details.append(
                                _("Network: {essid}").format(
                                    essid=essid_match.group(1)))

                    elif 'Frequency:' in line:
                        freq_match = search(r'Frequency:([0-9.]+ GHz)', line)
                        if freq_match:
                            details.append(
                                _("Frequency: {frequency}").format(
                                    frequency=freq_match.group(1)))

                    elif 'Access Point:' in line:
                        ap_match = search(
                            r'Access Point: ([0-9A-Fa-f:]+)', line)
                        if ap_match:
                            details.append(
                                _("Access Point: {ap}").format(
                                    ap=ap_match.group(1)))

                    elif 'Bit Rate=' in line:
                        rate_match = search(
                            r'Bit Rate=([0-9.]+ [GM]b/s)', line)
                        if rate_match:
                            details.append(
                                _("Bit Rate: {rate}").format(
                                    rate=rate_match.group(1)))

                    elif 'Signal level=' in line:
                        signal_match = search(
                            r'Signal level=(-?\d+) dBm', line)
                        if signal_match:
                            details.append(
                                _("Signal Level: {signal} dBm").format(
                                    signal=signal_match.group(1)))

                    elif 'Link Quality=' in line:
                        quality_match = search(r'Link Quality=([0-9/]+)', line)
                        if quality_match:
                            details.append(
                                _("Link Quality: {quality}").format(
                                    quality=quality_match.group(1)))

                    elif 'Mode:' in line:
                        mode_match = search(r'Mode:([A-Za-z]+)', line)
                        if mode_match:
                            details.append(
                                _("Mode: {mode}").format(
                                    mode=mode_match.group(1)))

                # Add IP address information
                try:
                    ip_result = subprocess.run(
                        "ip addr show {}".format(self.interface),
                        shell=True,
                        capture_output=True,
                        text=True
                    )

                    ip_match = search(
                        r'inet (\d+\.\d+\.\d+\.\d+)',
                        ip_result.stdout
                    )

                    if ip_match:
                        details.append(
                            _("IP Address: {ip}").format(
                                ip=ip_match.group(1)
                            )
                        )

                    # Add MAC address
                    mac_match = search(
                        r'link/ether ([0-9a-f:]+)',
                        ip_result.stdout,
                        IGNORECASE
                    )

                    if mac_match:
                        details.append(
                            _("MAC Address: {mac}").format(
                                mac=mac_match.group(1)
                            )
                        )

                except Exception as e:
                    print(e)
                    pass

                if details:
                    # Create formatted details text
                    details_text = "\n".join(details)
                    formatted_text = _("Connection Details:\n\n{details}").format(
                        details=details_text)

                    self.session.openWithCallback(
                        lambda result: callback() if callback else None,
                        MessageBox,
                        formatted_text,
                        MessageBox.TYPE_INFO
                    )
                    return

            # Fallback if no details found
            self.session.openWithCallback(
                lambda result: callback() if callback else None,
                MessageBox,
                _("No connection details available"),
                MessageBox.TYPE_INFO
            )

        except Exception as e:
            self.session.openWithCallback(
                lambda result: callback() if callback else None,
                MessageBox,
                _("Error getting connection details: {error}").format(
                    error=str(e)),
                MessageBox.TYPE_ERROR)

    def show_message(self, message, callback=None, timeout=None):
        """Show message with proper callback handling"""
        print(f"[DEBUG] show_message: '{message}'")

        try:
            if callback:
                self.session.openWithCallback(
                    lambda result: callback() if callback else None,
                    MessageBox,
                    message,
                    MessageBox.TYPE_INFO,
                    timeout=timeout or 3
                )
            else:
                def show_msg():
                    try:
                        self.session.open(
                            MessageBox,
                            message,
                            MessageBox.TYPE_INFO,
                            timeout=timeout or 3)
                    except Exception as e:
                        print(f"[DEBUG] Error showing message: {e}")
                        # Fallback: update status instead
                        self["status"].setText(message)

                reactor.callLater(0.1, show_msg)
        except Exception as e:
            print(f"[DEBUG] Error in show_message: {e}")
            # Fallback: update status instead
            self["status"].setText(message)

    def show_network_options(self):
        """ChoiceBox with all possible options"""
        print("[DEBUG] OK PRESSED - Network options")

        # GET CURRENT SELECTION FROM LIST
        current_index = self["network_list"].getSelectionIndex()
        print("[DEBUG] Current index from list: " + str(current_index))

        if current_index is not None and current_index < len(self.networks):
            self.current_network = self.networks[current_index]
            essid = self.current_network.get('essid')
            current_essid = get_current_connected_essid(self.interface)

            print("[DEBUG] Network for options: " + str(essid))
            print("[DEBUG] Current connected: " + str(current_essid))

            options = []

            # IF CONNECTED TO THIS NETWORK
            if current_essid == essid:
                print("[DEBUG] Already connected to this network")
                options = [
                    (_("Disconnect"), "disconnect"),
                    (_("Connection Info"), "info"),
                    (_("Edit Configuration"), "edit_config"),
                    (_("Back"), "back")
                ]
                title = _("Connected to: %s") % essid

            # IF NOT CONNECTED
            else:
                print("[DEBUG] Not connected to this network")
                options = [(_("Connect"), "connect")]

                if self.current_network.get('encryption'):
                    if self.get_saved_password(essid):
                        options.append((_("Edit Password"), "enter_password"))
                    else:
                        options.append((_("Enter Password"), "enter_password"))

                options.append((_("Edit Configuration"), "edit_config"))
                options.append((_("Forget Network"), "forget"))
                options.append((_("Connection Info"), "info"))
                options.append((_("Back"), "back"))

                title = _("Network: %s") % essid

            print("[DEBUG] Final options: " + str([opt[0] for opt in options]))

            def choice_callback(choice):
                print(f"[DEBUG] choice_callback called with: {choice}")
                if choice is None:
                    print("[DEBUG] User cancelled ChoiceBox")
                    return

                action = choice[1]
                print(f"[DEBUG] Action selected: {action}")

                if action == "back":
                    print("[DEBUG] Back selected")
                    return

                elif action == "connect":
                    print("[DEBUG] Connect selected")
                    # SEMPLICE: esegui connessione e aggiorna status
                    self.execute_connection()
                    self["status"].setText(_("Connecting to %s...") % essid)

                elif action == "disconnect":
                    print("[DEBUG] Disconnect selected")
                    # SEMPLICE: esegui disconnessione e aggiorna status
                    self.disconnect_from_network()
                    self["status"].setText(_("Disconnecting..."))

                elif action == "enter_password":
                    print("[DEBUG] Enter password selected")
                    self.open_password_dialog_with_callback(lambda: None)

                elif action == "edit_config":
                    print("[DEBUG] Edit config selected")
                    self.open_configuration_with_callback(lambda: None)

                elif action == "forget":
                    print("[DEBUG] Forget selected")
                    self.forget_network_with_callback(lambda: None)

                elif action == "info":
                    print("[DEBUG] Info selected")
                    self.show_connection_details_with_callback(lambda: None)

            # Open ChoiceBox with callback
            self.session.openWithCallback(
                choice_callback, ChoiceBox, title, options)

        else:
            print("[DEBUG] No valid network selected")
            self["status"].setText(_("No network selected"))

    def check_current_connection(self):
        """Check current connection status using tools.py"""
        if not self.interface:
            return

        info = get_interface_info(self.interface)

        if 'error' in info:
            self["status"].setText(_("Not connected to any network"))
            return

        if info.get('essid') and info['essid'] != _("Not connected"):
            essid = info['essid']
            quality = info.get('quality', _('?'))
            interface = get_wifi_interfaces()
            ip_addr = _("No interface")
            if interface:
                ip_addr = get_ip_address(interface)

            self["status"].setText(
                _("Connected to: {essid}\nSignal: {quality} | IP: {ip}").format(
                    essid=essid, quality=quality, ip=ip_addr))
        else:
            self["status"].setText(_("Not connected to any network"))

    def keyUp(self):
        """Handle UP key - navigate and auto-select"""
        print("[DEBUG] UP pressed")
        self["network_list"].up()
        current_index = self["network_list"].getSelectionIndex()
        print("[DEBUG] After UP - index: " + str(current_index))
        if current_index is not None and current_index < len(self.networks):
            self.current_network = self.networks[current_index]
            print("[DEBUG] Selected after UP: " +
                  str(self.current_network.get('essid')))
            self.update_status_based_on_network()

    def keyDown(self):
        """Handle DOWN key - navigate and auto-select"""
        print("[DEBUG] DOWN pressed")
        self["network_list"].down()
        current_index = self["network_list"].getSelectionIndex()
        print("[DEBUG] After DOWN - index: " + str(current_index))
        if current_index is not None and current_index < len(self.networks):
            self.current_network = self.networks[current_index]
            print("[DEBUG] Selected after DOWN: " +
                  str(self.current_network.get('essid')))
            self.update_status_based_on_network()

    def keyLeft(self):
        """Handle LEFT key - navigate and auto-select"""
        print("[DEBUG] LEFT pressed")
        self["network_list"].pageUp()
        current_index = self["network_list"].getSelectionIndex()
        print("[DEBUG] After LEFT - index: " + str(current_index))
        if current_index is not None and current_index < len(self.networks):
            self.current_network = self.networks[current_index]
            self.update_status_based_on_network()

    def keyRight(self):
        """Handle RIGHT key - navigate and auto-select"""
        print("[DEBUG] RIGHT pressed")
        self["network_list"].pageDown()
        current_index = self["network_list"].getSelectionIndex()
        print("[DEBUG] After RIGHT - index: " + str(current_index))
        if current_index is not None and current_index < len(self.networks):
            self.current_network = self.networks[current_index]
            self.update_status_based_on_network()

    def keyExit(self):
        """Handle exit"""
        self.close()
