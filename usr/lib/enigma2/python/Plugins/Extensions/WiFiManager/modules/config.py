# -*- coding: utf-8 -*-

import subprocess
from re import search

from Screens.MessageBox import MessageBox
from Screens.Screen import Screen
from Components.ActionMap import ActionMap
from Components.ConfigList import ConfigListScreen
from Components.Pixmap import Pixmap
from Components.Label import Label
from Components.config import ConfigIP, ConfigSubsection, ConfigText, ConfigYesNo, ConfigPassword, ConfigSelection, getConfigListEntry, ConfigEnableDisable

from . import _

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


WEP_LIST = ["ASCII", "HEX"]
MODE_LIST = [
    "WPA/WPA2",
    "WPA2",
    "WPA",
    "WEP",
    "Unencrypted"
]
NETWORK_CONFIGS = [
    ("dhcp", _("Automatic (DHCP)")),
    ("static", _("Manual (Static IP)"))
]


class WiFiConfigScreen(Screen, ConfigListScreen):
    skin = """
    <screen position="center,center" size="800,700" title="Configurazione WiFi">
        <widget name="config" position="10,10" size="780,514" scrollbarMode="showOnDemand" />
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

    def __init__(self, session, iface='wlan0', network_info=None):
        Screen.__init__(self, session)

        self.session = session
        self.iface = iface

        self.network_info = network_info if network_info is not None else {}

        self.list = []
        self.onChangedEntry = []
        self.helpList = []
        self.advanced_mode = False

        ConfigListScreen.__init__(
            self,
            self.list,
            session=session,
            on_change=self.onSelectionChanged)
        self.network_config = ConfigSubsection()
        self.wifi_config = ConfigSubsection()
        self.wifi_config.essid = ConfigText(
            default=self.network_info.get(
                'essid', ''), fixed_size=False)
        self.wifi_config.hiddenessid = ConfigYesNo(default=False)
        self.wifi_config.encryption = ConfigSelection(
            MODE_LIST, default=self.network_info.get(
                'encryption', 'WPA/WPA2'))
        self.wifi_config.wepkeytype = ConfigSelection(
            WEP_LIST, default="ASCII")
        self.wifi_config.psk = ConfigPassword(
            default=self.network_info.get(
                'password', ''), fixed_size=False)

        self.wifi_config.connection_type = ConfigSelection(
            NETWORK_CONFIGS, default="dhcp")
        self.wifi_config.ip = ConfigIP(default=[192, 168, 1, 100])
        self.wifi_config.netmask = ConfigIP(default=[255, 255, 255, 0])
        self.wifi_config.gateway = ConfigIP(default=[192, 168, 1, 1])
        self.wifi_config.dns1 = ConfigIP(default=[8, 8, 8, 8])
        self.wifi_config.dns2 = ConfigIP(default=[8, 8, 4, 4])

        # ADVANCED SETTINGS (dalla classe WiFiConfig originale)
        self.wifi_config.interface = ConfigSelection(
            choices=self.get_interfaces(), default=iface)
        self.wifi_config.mode = ConfigSelection(choices=[
            ("managed", "Managed (Client)"),
            ("ad-hoc", "Ad-Hoc"),
            ("master", "Master (AP)"),
            ("monitor", "Monitor"),
            ("auto", "Auto")
        ], default="managed")

        # Channel Selection
        channels = [("auto", "Auto")]
        channels.extend([(str(i), f"Channel {i}") for i in range(1, 14)])
        self.wifi_config.channel = ConfigSelection(
            choices=channels, default="auto")

        # TX Power
        self.wifi_config.txpower = ConfigSelection(choices=[
            ("auto", "Auto"),
            ("1", "1 dBm (Min)"),
            ("5", "5 dBm"),
            ("10", "10 dBm"),
            ("15", "15 dBm"),
            ("20", "20 dBm (Max)")
        ], default="auto")

        # RTS Threshold
        self.wifi_config.rts = ConfigSelection(choices=[
            ("auto", "Auto"),
            ("off", "Disabled"),
            ("2347", "2347 (Default)"),
            ("1000", "1000 bytes"),
            ("500", "500 bytes"),
            ("250", "250 bytes")
        ], default="auto")

        # Fragmentation Threshold
        self.wifi_config.frag = ConfigSelection(choices=[
            ("auto", "Auto"),
            ("off", "Disabled"),
            ("2346", "2346 (Default)"),
            ("1000", "1000 bytes"),
            ("500", "500 bytes")
        ], default="auto")

        # Country Code
        self.wifi_config.country = ConfigSelection(choices=[
            ("auto", "Auto"),
            ("US", "United States (US)"),
            ("EU", "Europe (EU)"),
            ("GB", "United Kingdom (GB)"),
            ("DE", "Germany (DE)"),
            ("IT", "Italy (IT)"),
            ("FR", "France (FR)"),
            ("JP", "Japan (JP)")
        ], default="auto")

        # Data Rate
        self.wifi_config.rate = ConfigSelection(choices=[
            ("auto", "Auto"),
            ("1", "1 Mbps"),
            ("2", "2 Mbps"),
            ("5.5", "5.5 Mbps"),
            ("11", "11 Mbps"),
            ("6", "6 Mbps"),
            ("9", "9 Mbps"),
            ("12", "12 Mbps"),
            ("18", "18 Mbps"),
            ("24", "24 Mbps"),
            ("36", "36 Mbps"),
            ("48", "48 Mbps"),
            ("54", "54 Mbps")
        ], default="auto")

        self["HelpWindow"] = Pixmap()
        self["HelpWindow"].hide()
        self["key_red"] = Label(_("Cancel"))
        self["key_green"] = Label(_("Save & Connect"))
        self["key_yellow"] = Label(_("Advanced"))
        self["key_blue"] = Label(_("Defaults"))

        self["actions"] = ActionMap(["ColorActions", "OkCancelActions"], {
            "red": self.cancel,
            "green": self.save_and_connect,
            "yellow": self.toggle_advanced,
            "blue": self.set_defaults,
            "cancel": self.cancel,
            "ok": self.keyOK,
        })
        self.wifi_config.connection_type.addNotifier(
            self.configChanged, initial_call=False)
        self.buildConfigList()
        self.setTitle(
            _("Configure {}").format(
                self.network_info.get(
                    'essid',
                    'WiFi Network')))

        if not network_info:
            self.load_current_settings()

    def configChanged(self, configElement=None):
        """Handle configuration changes"""
        self.buildConfigList()

    def changedEntry(self):
        self.item = self["config"].getCurrent()
        for x in self.onChangedEntry:
            x()

    def onSelectionChanged(self):
        try:
            if not self["config"] or not self["config"].list:
                return

            ConfigListScreen.selectionChanged(self)

            for x in self.onChangedEntry:
                x()

            current = self["config"].getCurrent()
            if current and len(current) > 1 and current[1] is not None:
                if isinstance(
                    current[1],
                    (ConfigEnableDisable,
                     ConfigYesNo,
                     ConfigSelection)):
                    self['key_green'].setText(
                        _('Save & Connect') if self['config'].isChanged() else '- - - -')

        except Exception as e:
            print(f"[WiFiConfig] Selection changed error: {e}")

    def get_interfaces(self):
        """Get available WiFi interfaces using system commands"""
        interfaces = []
        try:
            # Method 1: Check /proc/net/wireless
            with open('/proc/net/wireless', 'r') as f:
                lines = f.readlines()
            for line in lines[2:]:  # Skip header lines
                if ':' in line:
                    ifname = line.split(':')[0].strip()
                    if ifname and ifname not in interfaces:
                        interfaces.append((ifname, ifname))

            # Method 2: Check ip link for common WiFi interfaces
            if not interfaces:
                for iface in ['wlan0', 'wlan1', 'wlan2', 'wlp2s0', 'wlp3s0']:
                    try:
                        result = subprocess.run(['ip', 'link', 'show', iface],
                                                capture_output=True, text=True)
                        if result.returncode == 0:
                            interfaces.append((iface, iface))
                    except Exception as e:
                        print(e)
                        continue

            # Method 3: Use iwconfig to find wireless interfaces
            if not interfaces:
                try:
                    result = subprocess.run(
                        ['iwconfig'], capture_output=True, text=True)
                    if result.returncode == 0:
                        for line in result.stdout.split('\n'):
                            if 'IEEE 802.11' in line and 'no wireless extensions' not in line:
                                ifname = line.split()[0]
                                if ifname and ifname not in interfaces:
                                    interfaces.append((ifname, ifname))
                except Exception as e:
                    print(e)
                    pass

        except Exception as e:
            print(f"[WiFiConfig] Error getting interfaces: {e}")

        if not interfaces:
            interfaces = [("wlan0", "wlan0")]

        return interfaces

    def load_current_settings(self):
        """Load current WiFi settings using system commands"""
        try:
            ifname = self.wifi_config.interface.value

            # Get current settings using iwconfig
            result = subprocess.run(
                ['iwconfig', ifname], capture_output=True, text=True)
            if result.returncode != 0:
                print(f"[WiFiConfig] Cannot get settings for {ifname}")
                return

            output = result.stdout

            # Load current mode
            mode_match = search(r'Mode:(\w+)', output)
            if mode_match:
                current_mode = mode_match.group(1).lower()
                if current_mode in [choice[0]
                                    for choice in self.wifi_config.mode.choices]:
                    self.wifi_config.mode.value = current_mode

            # Load current channel
            channel_match = search(r'Channel[=:](\d+)', output)
            if channel_match:
                current_channel = channel_match.group(1)
                if current_channel in [choice[0]
                                       for choice in self.wifi_config.channel.choices]:
                    self.wifi_config.channel.value = current_channel

            # Load TX power
            power_match = search(r'Tx-Power[=:](\d+)', output)
            if power_match:
                current_power = power_match.group(1)
                if current_power in [choice[0]
                                     for choice in self.wifi_config.txpower.choices]:
                    self.wifi_config.txpower.value = current_power

            # Load rate
            rate_match = search(r'Rate[=:](\d+\.?\d*)', output)
            if rate_match:
                current_rate = rate_match.group(1)
                # Remove decimal for matching
                current_rate_clean = current_rate.split('.')[0]
                if current_rate_clean in [choice[0]
                                          for choice in self.wifi_config.rate.choices]:
                    self.wifi_config.rate.value = current_rate_clean

            # Load RTS threshold
            rts_match = search(r'RTS thr[=:](\w+)', output)
            if rts_match:
                rts_val = rts_match.group(1)
                if rts_val == "off":
                    self.wifi_config.rts.value = "off"
                elif rts_val.isdigit() and rts_val in [choice[0] for choice in self.wifi_config.rts.choices]:
                    self.wifi_config.rts.value = rts_val

            # Load fragmentation threshold
            frag_match = search(r'Fragment thr[=:](\w+)', output)
            if frag_match:
                frag_val = frag_match.group(1)
                if frag_val == "off":
                    self.wifi_config.frag.value = "off"
                elif frag_val.isdigit() and frag_val in [choice[0] for choice in self.wifi_config.frag.choices]:
                    self.wifi_config.frag.value = frag_val

            print(f"[WiFiConfig] Loaded settings for {ifname}")

        except Exception as e:
            print(f"[WiFiConfig] Error loading settings: {e}")

    def apply_advanced_settings(self):
        try:
            ifname = self.wifi_config.interface.value
            commands = []

            if self.wifi_config.mode.value != "auto":
                commands.append(
                    "iwconfig {} mode {}".format(
                        ifname, self.wifi_config.mode.value))

            if self.wifi_config.channel.value != "auto":
                commands.append(
                    "iwconfig {} channel {}".format(
                        ifname, self.wifi_config.channel.value))

            if self.wifi_config.txpower.value != "auto":
                commands.append(
                    "iwconfig {} txpower {}".format(
                        ifname, self.wifi_config.txpower.value))

            if self.wifi_config.rts.value != "auto":
                rts_val = "off" if self.wifi_config.rts.value == "off" else self.wifi_config.rts.value
                commands.append("iwconfig {} rts {}".format(ifname, rts_val))

            if self.wifi_config.frag.value != "auto":
                frag_val = "off" if self.wifi_config.frag.value == "off" else self.wifi_config.frag.value
                commands.append("iwconfig {} frag {}".format(ifname, frag_val))

            if self.wifi_config.country.value != "auto":
                commands.append(
                    "iw reg set {}".format(
                        self.wifi_config.country.value))

            if self.wifi_config.rate.value != "auto":
                commands.append(
                    "iwconfig {} rate {}M".format(
                        ifname, self.wifi_config.rate.value))

            success_count = 0
            failed_commands = []

            for cmd in commands:
                try:
                    result = subprocess.run(
                        cmd, shell=True, capture_output=True, text=True, timeout=10)
                    if result.returncode == 0:
                        success_count += 1
                        print(
                            "[WiFiConfig] Command successful: {}".format(cmd))
                    else:
                        failed_commands.append(
                            "{}: {}".format(
                                cmd, result.stderr.strip()))
                        print(
                            "[WiFiConfig] Command failed: {} - {}".format(cmd, result.stderr))
                except subprocess.TimeoutExpired:
                    failed_commands.append("{}: Timeout".format(cmd))
                    print("[WiFiConfig] Command timeout: {}".format(cmd))
                except Exception as e:
                    failed_commands.append("{}: {}".format(cmd, str(e)))
                    print("[WiFiConfig] Error executing {}: {}".format(cmd, e))

            # Mostra il risultato all'utente
            if success_count > 0 or failed_commands:
                if success_count > 0:
                    message = _("WiFi settings applied successfully\n\n")
                    message += _("Applied: {} commands\n").format(success_count)
                    if failed_commands:
                        message += _("Failed: {} commands").format(len(failed_commands))
                    self.session.open(
                        MessageBox, message, MessageBox.TYPE_INFO)
                else:
                    message = _(
                        "No settings were applied\n\nFailed commands:\n")
                    message += "\n".join(failed_commands[:3])
                    self.session.open(
                        MessageBox, message, MessageBox.TYPE_WARNING)

            return success_count, failed_commands

        except Exception as e:
            print("[WiFiConfig] Error in apply_advanced_settings: {}".format(e))
            self.session.open(
                MessageBox,
                _("Error applying advanced settings: {}").format(
                    str(e)),
                MessageBox.TYPE_ERROR)
            return 0, [str(e)]

    def buildConfigList(self):
        """Build configuration list with basic/advanced/network sections"""
        self.list = []

        # BASIC SECTION (always shown)
        section = '--------------------------( BASIC SETTINGS )-----------------------'
        self.list.append(getConfigListEntry(section))
        self.list.append(
            getConfigListEntry(
                _("Interface"),
                self.wifi_config.interface))

        self.list.append(
            getConfigListEntry(
                _("Network Name (SSID)"),
                self.wifi_config.essid))
        self.list.append(
            getConfigListEntry(
                _("Hidden Network"),
                self.wifi_config.hiddenessid))
        self.list.append(
            getConfigListEntry(
                _("Encryption"),
                self.wifi_config.encryption))

        # Show password field only for encrypted networks
        if self.wifi_config.encryption.value != "Unencrypted":
            self.list.append(
                getConfigListEntry(
                    _("Password"),
                    self.wifi_config.psk))

            # Show WEP key type for WEP encryption
            if self.wifi_config.encryption.value == "WEP":
                self.list.append(
                    getConfigListEntry(
                        _("WEP Key Type"),
                        self.wifi_config.wepkeytype))

        # NETWORK SECTION (sempre visibile)
        section = '--------------------------( NETWORK SETTINGS )-----------------------'
        self.list.append(getConfigListEntry(section))
        self.list.append(
            getConfigListEntry(
                _("IP Configuration"),
                self.wifi_config.connection_type))

        # Mostra configurazione IP solo se manuale
        if self.wifi_config.connection_type.value == "static":
            self.list.append(
                getConfigListEntry(
                    _("IP Address"),
                    self.wifi_config.ip))
            self.list.append(
                getConfigListEntry(
                    _("Netmask"),
                    self.wifi_config.netmask))
            self.list.append(
                getConfigListEntry(
                    _("Gateway"),
                    self.wifi_config.gateway))
            self.list.append(
                getConfigListEntry(
                    _("DNS Server 1"),
                    self.wifi_config.dns1))
            self.list.append(
                getConfigListEntry(
                    _("DNS Server 2"),
                    self.wifi_config.dns2))

        # ADVANCED SECTION (conditional)
        if self.advanced_mode:
            section = '--------------------------( ADVANCED SETTINGS )-----------------------'
            self.list.append(getConfigListEntry(section))
            self.list.append(
                getConfigListEntry(
                    _("Operation Mode"),
                    self.wifi_config.mode))
            self.list.append(
                getConfigListEntry(
                    _("Channel"),
                    self.wifi_config.channel))
            self.list.append(
                getConfigListEntry(
                    _("TX Power"),
                    self.wifi_config.txpower))
            self.list.append(
                getConfigListEntry(
                    _("RTS Threshold"),
                    self.wifi_config.rts))
            self.list.append(
                getConfigListEntry(
                    _("Fragmentation"),
                    self.wifi_config.frag))
            self.list.append(
                getConfigListEntry(
                    _("Country Code"),
                    self.wifi_config.country))
            self.list.append(
                getConfigListEntry(
                    _("Data Rate"),
                    self.wifi_config.rate))

        self["config"].list = self.list
        self["config"].l.setList(self.list)

    def toggle_advanced(self):
        """Toggle advanced settings visibility"""
        self.advanced_mode = not self.advanced_mode
        self["key_yellow"].setText(
            _("Basic") if self.advanced_mode else _("Advanced"))
        self.buildConfigList()

    def keyOK(self):
        """Handle OK button in config list"""
        pass

    def cancel(self):
        """Cancel configuration"""
        self.close(None)

    def save_and_connect(self):
        """Save configuration and connect"""
        try:
            # Validate input
            if not self.wifi_config.essid.value:
                self.session.open(
                    MessageBox,
                    _("Please enter a network name"),
                    MessageBox.TYPE_ERROR)
                return

            if self.wifi_config.encryption.value != "Unencrypted" and not self.wifi_config.psk.value:
                self.session.open(
                    MessageBox,
                    _("Please enter a password"),
                    MessageBox.TYPE_ERROR)
                return

            # Write wpa_supplicant configuration
            self.write_wpa_supplicant_config()

            # Write network configuration
            self.write_network_config()

            # Apply advanced settings if in advanced mode
            if self.advanced_mode:
                self.apply_advanced_settings()

            # Return success
            self.close(True)

        except Exception as e:
            print("Error saving configuration: " + str(e))

    def write_network_config(self):
        """Scrive configurazione network autonoma per Enigma2"""
        try:
            config_file = "/etc/enigma2/network.conf"

            config_lines = [
                "# Network configuration for {}".format(
                    self.wifi_config.essid.value), "[network]", "connection_type={}".format(
                    self.wifi_config.connection_type.value), ]

            if self.wifi_config.connection_type.value == "static":
                config_lines.extend([
                    "ip={}".format(".".join(str(x) for x in self.wifi_config.ip.value)),
                    "netmask={}".format(".".join(str(x) for x in self.wifi_config.netmask.value)),
                    "gateway={}".format(".".join(str(x) for x in self.wifi_config.gateway.value)),
                    "dns1={}".format(".".join(str(x) for x in self.wifi_config.dns1.value)),
                    "dns2={}".format(".".join(str(x) for x in self.wifi_config.dns2.value))
                ])

            with open(config_file, "w") as f:
                f.write("\n".join(config_lines))

            print(f"[WiFiConfig] Network configuration saved to {config_file}")
            return True

        except Exception as e:
            print(f"[WiFiConfig] Error writing network config: {e}")
            return False

    def write_wpa_supplicant_config(self):
        """Write wpa_supplicant configuration like Enigma2"""
        config_file = f"/etc/wpa_supplicant.{self.iface}.conf"

        lines = [
            "# WiFi configuration for {}".format(self.wifi_config.essid.value),
            "ctrl_interface=/var/run/wpa_supplicant",
            "update_config=1",
            "",
            "network={",
            '\tssid="{}"'.format(self.wifi_config.essid.value),
        ]

        if self.wifi_config.hiddenessid.value:
            lines.append('\tscan_ssid=1')
        else:
            lines.append('\tscan_ssid=0')

        encryption = self.wifi_config.encryption.value
        if encryption in ("WPA", "WPA2", "WPA/WPA2"):
            lines.append('\tkey_mgmt=WPA-PSK')
            if encryption == "WPA":
                lines.append('\tproto=WPA')
                lines.append('\tpairwise=TKIP')
                lines.append('\tgroup=TKIP')
            elif encryption == "WPA2":
                lines.append('\tproto=RSN')
                lines.append('\tpairwise=CCMP')
                lines.append('\tgroup=CCMP')
            else:  # WPA/WPA2
                lines.append('\tproto=WPA RSN')
                lines.append('\tpairwise=CCMP TKIP')
                lines.append('\tgroup=CCMP TKIP')
            lines.append('\tpsk="{}"'.format(self.wifi_config.psk.value))

        elif encryption == "WEP":
            lines.append('\tkey_mgmt=NONE')
            if self.wifi_config.wepkeytype.value == "ASCII":
                lines.append(
                    '\twep_key0="{}"'.format(
                        self.wifi_config.psk.value))
            else:
                lines.append(
                    '\twep_key0={}'.format(
                        self.wifi_config.psk.value))
        else:  # Unencrypted
            lines.append('\tkey_mgmt=NONE')

        lines.append("}")

        # Write the file
        with open(config_file, 'w') as f:
            f.write('\n'.join(lines))

        print(f"[WiFiConfig] Configuration saved to {config_file}")

    def set_defaults(self):
        """Reset all settings to defaults"""
        self.wifi_config.hiddenessid.value = False
        self.wifi_config.encryption.value = "WPA/WPA2"
        self.wifi_config.wepkeytype.value = "ASCII"
        self.wifi_config.psk.value = ""

        # Network defaults
        self.wifi_config.connection_type.value = "dhcp"
        self.wifi_config.ip.value = [192, 168, 1, 100]
        self.wifi_config.netmask.value = [255, 255, 255, 0]
        self.wifi_config.gateway.value = [192, 168, 1, 1]
        self.wifi_config.dns1.value = [8, 8, 8, 8]
        self.wifi_config.dns2.value = [8, 8, 4, 4]

        # Advanced defaults
        self.wifi_config.mode.value = "managed"
        self.wifi_config.channel.value = "auto"
        self.wifi_config.txpower.value = "auto"
        self.wifi_config.rts.value = "auto"
        self.wifi_config.frag.value = "auto"
        self.wifi_config.country.value = "auto"
        self.wifi_config.rate.value = "auto"

        self.buildConfigList()

        self.session.open(MessageBox,
                          _("All settings reset to defaults"),
                          MessageBox.TYPE_INFO)


WiFiConfig = WiFiConfigScreen
