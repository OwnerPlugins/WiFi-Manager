# -*- coding: utf-8 -*-

import subprocess
from re import search
from enigma import eTimer

from Screens.Screen import Screen
from Screens.MessageBox import MessageBox
from Components.ActionMap import ActionMap
from Components.Label import Label
from Components.ScrollLabel import ScrollLabel
from Components.Button import Button
# , ConfigText, getConfigListEntry
from Components.config import ConfigSubsection, ConfigSelection
from Components.ConfigList import ConfigListScreen

from .tools import get_wifi_interfaces, scan_networks
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


class IWListTools(Screen):
    skin = """
    <screen position="center,center" size="800,700" title="WiFi Advanced Tools">
        <widget name="info_label" position="19,529" size="760,80" font="Regular;20" />
        <widget name="key_red" position="10,635" size="200,40" zPosition="1" font="Regular;20" halign="center" valign="center" backgroundColor="red" transparent="1" />
        <widget name="key_green" position="210,635" size="200,40" zPosition="1" font="Regular;20" halign="center" valign="center" backgroundColor="green" transparent="1" />
        <widget name="key_yellow" position="410,635" size="200,40" zPosition="1" font="Regular;20" halign="center" valign="center" backgroundColor="yellow" transparent="1" />
        <eLabel name="" position="645,630" size="150,20" backgroundColor="#49bbff" halign="center" valign="center" transparent="0" cornerRadius="9" font="Regular; 16" zPosition="1" text="OK - SELECT" />
        <eLabel name="" position="645,657" size="150,20" backgroundColor="#49bbff" halign="center" valign="center" transparent="0" cornerRadius="9" font="Regular; 16" zPosition="1" text="TXT - KEYBOARD" />
        <eLabel name="" position="9,677" size="200,8" zPosition="3" backgroundColor="#fe0000" />
        <eLabel name="" position="209,677" size="200,8" zPosition="3" backgroundColor="#fe00" />
        <eLabel name="" position="409,677" size="200,8" zPosition="3" backgroundColor="#cccc40" />
    </screen>
    """

    def __init__(self, session, tool_name=None):
        Screen.__init__(self, session)
        self.session = session
        self.tool_name = tool_name

        interfaces = get_wifi_interfaces()
        self.interface = interfaces[0] if interfaces else None

        self["info_label"] = Label(_("Executing tool..."))
        self["key_red"] = Button(_("Close"))
        self["key_green"] = Button("")
        self["key_yellow"] = Button("Help")

        self.menu_entries = [
            (_("Advanced Scan"), "scanning", _("Detailed network scanning")),
            (_("Channel Info"), "channel", _("Available frequencies/channels")),
            (_("Bitrate Info"), "bitrate", _("Supported bit rates")),
            (_("Encryption Info"), "encryption", _("Encryption keys and security")),
            (_("Power Management"), "power", _("Power management settings")),
            (_("Retry Limits"), "retry", _("Retry limits and lifetime")),
            (_("Access Points"), "ap", _("List of access points/peers")),
            (_("Advanced Config"), "advanced_config", _("Advanced WiFi Configuration")),
            (_("Restart WiFi Interface"), "restart_wifi", _("Restart wireless interface")),
            (_("Reload WiFi Modules"), "reload_modules", _("Reload kernel WiFi modules")),
            (_("Check System Logs"), "check_logs", _("Check system logs for WiFi errors")),
        ]

        self.current_selection = None
        self["actions"] = ActionMap(["ColorActions", "OkCancelActions"], {
            "red": self.close,
            "yellow": self.show_help,
            "cancel": self.close
        })
        self.setTitle(_("WiFi Advanced Tools"))
        self.start_timer = eTimer()
        self.start_timer.callback.append(self.execute_direct_tool)
        if self.tool_name:
            self.start_timer.start(100, True)  # 100ms delay

    def run_command(self, cmd):
        """Executes a command and returns the output"""
        try:
            result = subprocess.run(
                cmd,
                shell=True,
                capture_output=True,
                text=True,
                timeout=30)
            if result.returncode == 0:
                return result.stdout.strip()
            else:
                return None
        except Exception as e:
            print(f"Command error: {e}")
            return None

    def execute_direct_tool(self):
        """Runs the specified tool directly"""
        if not self.tool_name:
            self.close()
            return

        tool_methods = {
            "scanning": self.run_advanced_scan,
            "channel": self.get_channel_info,
            "bitrate": self.get_bitrate_info,
            "encryption": self.get_encryption_info,
            "power": self.get_power_info,
            "retry": self.get_retry_info,
            "ap": self.get_ap_info,
            "advanced_config": self.show_advanced_config,
            "restart_wifi": self.restart_wifi_interface,
            "reload_modules": self.reload_wifi_modules,
            "check_logs": self.check_system_logs,
        }

        method = tool_methods.get(self.tool_name)
        if method:
            method()
        else:
            self.session.openWithCallback(
                self.close,
                MessageBox,
                _("Tool not implemented: {}").format(self.tool_name),
                MessageBox.TYPE_ERROR
            )

    def show(self):
        """When the screen is shown, reset the state"""
        Screen.show(self)
        self.current_selection = None

    def _return_to_main_menu(self):
        """Utility method to reset interface state"""
        self.current_selection = None

    def return_to_tools(self, result=None):
        """Callback to return to the GENERAL OPTIONS screen after completing an operation"""
        if not self.instance:
            return

        tool_messages = {
            "scanning": _("Scan completed."),
            "channel": _("Channel info displayed."),
            "bitrate": _("Bitrate info displayed."),
            "encryption": _("Encryption info displayed."),
            "power": _("Power management info displayed."),
            "retry": _("Retry limits info displayed."),
            "ap": _("Access points info displayed."),
            "advanced_config": _("Advanced configuration completed."),
            "restart_wifi": _("Interface restarted."),
            "reload_modules": _("Modules reloaded."),
            "check_logs": _("Logs checked."),
        }

        message = tool_messages.get(
            self.current_selection,
            _("Operation completed."))
        self["info_label"].setText(message)

        # Force a refresh of the screen
        self.show()

    def run_advanced_scan(self):
        try:
            networks = scan_networks(self.interface, detailed=True)
            if networks:
                output = self.format_scan_results(networks)
                self.session.openWithCallback(
                    self.close,
                    ResultsScreen,
                    _("Advanced Scan Results"),
                    output
                )
            else:
                self.session.openWithCallback(
                    self.close,
                    MessageBox,
                    _("No networks found"),
                    MessageBox.TYPE_INFO
                )
        except Exception as e:
            self.session.openWithCallback(
                self.close,
                MessageBox,
                _("Scan error {}").format(e),
                MessageBox.TYPE_ERROR
            )

    def format_scan_results(self, networks):
        """Format scan results"""
        if not networks:
            return _("No networks found")
        output = _("=== ADVANCED SCAN RESULTS ===\n\n")
        output += _("Found %d networks\n\n") % len(networks)
        for i, net in enumerate(networks, 1):
            output += _("Network %d:\n") % i
            output += _("  ESSID: %s\n") % net.get('essid', _('N/A'))
            output += _("  MAC: %s\n") % net.get('bssid',
                                                 net.get('mac', _('N/A')))
            output += _("  Channel: %s\n") % net.get('channel', _('N/A'))
            output += _("  Frequency: %s\n") % net.get('frequency', _('N/A'))
            output += _("  Quality: %s\n") % net.get('quality', _('N/A'))
            output += _("  Signal: %s\n") % net.get('signal', _('N/A'))
            output += _("  Encryption: %s\n") % (_('Yes')
                                                 if net.get('encryption') else _('No'))
            output += "\n"
        return output

    def get_channel_info(self):
        """Information about available channels"""
        self.show_working_message(_("Getting channel information..."))
        try:
            cmd = f"iwlist {self.interface} freq"
            freq_result = self.run_command(cmd)
            output = _("=== CHANNEL INFORMATION ===\n\n")
            if freq_result:
                output += _("Frequency Bands:\n%s\n") % freq_result
            else:
                output += _("Frequency information not available\n")

            self.session.openWithCallback(
                self.close,
                ResultsScreen,
                _("Channel Info"),
                output
            )
        except Exception as e:
            self.session.openWithCallback(
                self.close,
                MessageBox,
                _("Error getting channel information: {}").format(e),
                MessageBox.TYPE_ERROR
            )

    def get_bitrate_info(self):
        """Bitrate information"""
        self.show_working_message(_("Getting bitrate information..."))
        try:
            cmd = f"iwlist {self.interface} bitrate"
            bitrate_result = self.run_command(cmd)
            output = _("=== BITRATE INFORMATION ===\n\n")
            if bitrate_result:
                output += _("Supported Bitrates:\n%s\n") % bitrate_result
            else:
                output += _("Bitrate information not available\n")

            self.session.openWithCallback(
                self.close,
                ResultsScreen,
                _("Bitrate Info"),
                output
            )
        except Exception as e:
            self.session.openWithCallback(
                self.close,
                MessageBox,
                _("Error getting bitrate information: {}").format(e),
                MessageBox.TYPE_ERROR
            )

    def get_encryption_info(self):
        """About encryption"""
        self.show_working_message(_("Getting encryption information..."))
        try:
            cmd = f"iwlist {self.interface} auth"
            auth_result = self.run_command(cmd)
            output = _("=== ENCRYPTION INFORMATION ===\n\n")
            if auth_result:
                output += _("Authentication:\n%s\n") % auth_result
            else:
                output += _("Encryption information not available\n")

            self.session.openWithCallback(
                self.close,
                ResultsScreen,
                _("Encryption Info"),
                output
            )
        except Exception as e:
            self.session.openWithCallback(
                self.close,
                MessageBox,
                _("Error getting encryption information: {}").format(e),
                MessageBox.TYPE_ERROR
            )

    def get_power_info(self):
        """About power management"""
        self.show_working_message(_("Getting power management information..."))
        try:
            cmd = f"iwconfig {self.interface} | grep -i power"
            power_result = self.run_command(cmd)
            output = _("=== POWER MANAGEMENT ===\n\n")
            if power_result:
                output += power_result
            else:
                output += _("Power management information not available\n")

            self.session.openWithCallback(
                self.close,
                ResultsScreen,
                _("Power Management"),
                output
            )
        except Exception as e:
            self.session.openWithCallback(
                self.close,
                MessageBox,
                _("Error getting power information: {}").format(e),
                MessageBox.TYPE_ERROR
            )

    def get_retry_info(self):
        """About retry limits"""
        self.show_working_message(_("Getting retry information..."))
        try:
            cmd = f"iwconfig {self.interface} | grep -i retry"
            retry_result = self.run_command(cmd)
            output = _("=== RETRY LIMITS ===\n\n")
            if retry_result:
                output += retry_result
            else:
                output += _("Retry limit information not available\n")

            self.session.openWithCallback(
                self.close,
                ResultsScreen,
                _("Retry Limits"),
                output
            )
        except Exception as e:
            self.session.openWithCallback(
                self.close,
                MessageBox,
                _("Error getting retry information: {}").format(e),
                MessageBox.TYPE_ERROR
            )

    def get_ap_info(self):
        """About access point"""
        self.show_working_message(_("Getting access point information..."))
        try:
            cmd = f"iw dev {self.interface} station dump"
            station_result = self.run_command(cmd)
            output = _("=== ACCESS POINTS / PEERS ===\n\n")
            if station_result:
                output += station_result
            else:
                output += _("No station/peer information available\n")

            self.session.openWithCallback(
                self.close,
                ResultsScreen,
                _("Access Points"),
                output
            )
        except Exception as e:
            self.session.openWithCallback(
                self.close,
                MessageBox,
                _("Error getting AP information: {}").format(e),
                MessageBox.TYPE_ERROR
            )

    def show_working_message(self, message):
        """Show a work in progress message"""
        self["info_label"].setText(message)

    def show_advanced_config(self):
        """Advanced Interface Configuration"""
        if self.interface:
            self.session.openWithCallback(
                self.close,
                AdvancedConfigScreen,
                self.interface
            )
        else:
            self.session.open(
                MessageBox,
                _("No WiFi interface available"),
                MessageBox.TYPE_ERROR)

    def show_help(self):
        """Show help"""
        help_text = _(
            "Select a tool from the menu to get detailed information about WiFi configuration and status.")
        self.session.open(MessageBox, help_text, MessageBox.TYPE_INFO)

    def restart_wifi_interface(self):
        """Restart the WiFi interface"""
        self.session.openWithCallback(
            self.confirm_restart,
            MessageBox,
            _("Restart WiFi interface %s?") % self.interface,
            MessageBox.TYPE_YESNO
        )

    def confirm_restart(self, result):
        """Confirm interface restart"""
        if result:
            self.show_working_message(_("Restarting interface..."))
            try:
                self.run_command(f"ifconfig {self.interface} down")
                self.run_command(f"ifconfig {self.interface} up")
                self.session.openWithCallback(
                    self.close,
                    MessageBox,
                    _("Interface restarted successfully"),
                    MessageBox.TYPE_INFO
                )
            except Exception as e:
                self.session.openWithCallback(
                    self.close,
                    MessageBox,
                    _(f"Failed to restart interface {e}"),
                    MessageBox.TYPE_ERROR
                )

    def reload_wifi_modules(self):
        """Recharge WiFi modules"""
        self.session.openWithCallback(
            self.close,
            MessageBox,
            _("Reload WiFi kernel modules?\nThis will temporarily disconnect all WiFi."),
            MessageBox.TYPE_YESNO)

    def check_system_logs(self):
        """Check system logs for WiFi errors"""
        self.show_working_message(_("Checking system logs..."))

        try:
            dmesg_result = self.run_command("dmesg | grep -i wifi | tail -20")
            syslog_result = self.run_command(
                "grep -i wifi /var/log/messages /var/log/syslog 2>/dev/null | tail -20")

            output = _("=== SYSTEM LOGS - WIFI ERRORS ===\n\n")

            output += _("Kernel Messages (dmesg):\n")
            if dmesg_result:
                output += dmesg_result + "\n\n"
            else:
                output += _("No WiFi messages in dmesg\n\n")
            output += _("System Logs:\n")
            if syslog_result:
                output += syslog_result
            else:
                output += _("No WiFi messages in system logs")
            self.session.openWithCallback(
                self.close,
                ResultsScreen,
                _("System Logs"),
                output
            )
        except Exception as e:
            print(f"Log check failed: {e}")


class AdvancedConfigScreen(ConfigListScreen, Screen):
    skin = """
    <screen position="center,center" size="800,700" title="Advanced WiFi Configuration">
        <widget name="config" position="20,20" size="760,450" scrollbarMode="showNever" />
        <widget name="info_label" position="20,490" size="760,135" font="Regular;18" />
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

    def __init__(self, session, ifname):
        Screen.__init__(self, session)
        self.session = session
        self.ifname = ifname
        self.wifi_config = ConfigSubsection()
        # Operation Mode
        self.wifi_config.mode = ConfigSelection(choices=[
            ("managed", _("Managed (Client)")),
            ("ad-hoc", _("Ad-Hoc")),
            ("master", _("Master (AP)")),
            ("monitor", _("Monitor")),
            ("auto", _("Auto"))
        ], default="managed")

        # Channel Selection
        channels = [("auto", _("Auto"))]
        channels.extend([(str(i), _("Channel {}").format(i))
                        for i in range(1, 14)])
        self.wifi_config.channel = ConfigSelection(
            choices=channels, default="auto")

        # TX Power
        self.wifi_config.txpower = ConfigSelection(choices=[
            ("auto", _("Auto")),
            ("1", _("1 dBm (Min)")),
            ("5", _("5 dBm")),
            ("10", _("10 dBm")),
            ("15", _("15 dBm")),
            ("20", _("20 dBm (Max)"))
        ], default="auto")
        self.list = [
            (_("Operation Mode"), self.wifi_config.mode),
            (_("Channel"), self.wifi_config.channel),
            (_("TX Power"), self.wifi_config.txpower),
        ]

        ConfigListScreen.__init__(self, self.list)
        self["info_label"] = Label(_("Advanced WiFi configuration settings"))
        self["key_red"] = Label(_("Cancel"))
        self["key_green"] = Label(_("Apply"))
        self["key_yellow"] = Label(_("Defaults"))
        self["key_blue"] = Button(_("Help"))
        self["actions"] = ActionMap(
            ["ColorActions", "OkCancelActions"],
            {
                "red": self.cancel,
                "green": self.apply_settings,
                "yellow": self.set_defaults,
                "blue": self.show_help,
                "cancel": self.cancel,
                "ok": self.keyOK,
            }
        )
        self.setTitle(_("Advanced Config - {}").format(ifname))
        self.load_current_settings()

    def load_current_settings(self):
        """Load current interface settings"""
        try:
            # Use iwconfig to read current settings
            result = subprocess.run(
                ['iwconfig', self.ifname], capture_output=True, text=True)
            if result.returncode == 0:
                output = result.stdout

                # Read current mode
                mode_match = search(r'Mode:(\w+)', output)
                if mode_match:
                    current_mode = mode_match.group(1).lower()
                    if current_mode in [choice[0]
                                        for choice in self.wifi_config.mode.choices]:
                        self.wifi_config.mode.value = current_mode
        except Exception as e:
            print(f"[AdvancedConfig] Error loading settings: {e}")

    def apply_settings(self):
        """Apply advanced settings"""
        try:
            commands = []

            # Apply mode
            if self.wifi_config.mode.value != "auto":
                commands.append("iwconfig {} mode {}".format(
                    self.ifname,
                    self.wifi_config.mode.value
                ))

            # Apply channel
            if self.wifi_config.channel.value != "auto":
                commands.append("iwconfig {} channel {}".format(
                    self.ifname,
                    self.wifi_config.channel.value
                ))

            # Apply TX power
            if self.wifi_config.txpower.value != "auto":
                commands.append("iwconfig {} txpower {}".format(
                    self.ifname,
                    self.wifi_config.txpower.value
                ))

            # Execute commands
            for cmd in commands:
                subprocess.run(cmd, shell=True)

            self.session.openWithCallback(
                lambda result: self.close(True),
                MessageBox,
                _("Settings applied successfully"),
                MessageBox.TYPE_INFO
            )

        except Exception as e:
            self.session.openWithCallback(
                lambda result: self.close(True),
                MessageBox,
                _("Error applying settings: {}".format(e)),
                MessageBox.TYPE_ERROR
            )

    def set_defaults(self):
        """Reset to default values"""
        self.wifi_config.mode.value = "managed"
        self.wifi_config.channel.value = "auto"
        self.wifi_config.txpower.value = "auto"
        self["config"].l.setList(self.list)

    def keyOK(self):
        """Handle OK key"""
        pass

    def keyLeft(self):
        """Handle left key"""
        ConfigListScreen.keyLeft(self)

    def keyRight(self):
        """Handle right key"""
        ConfigListScreen.keyRight(self)

    def keyUp(self):
        """Handle up key"""
        ConfigListScreen.keyUp(self)

    def keyDown(self):
        """Handle down key"""
        ConfigListScreen.keyDown(self)

    def cancel(self):
        self.close()

    def show_help(self):
        """Mostra aiuto per la configurazione avanzata"""
        help_text = _(
            "Advanced WiFi Configuration:\n\n"
            "Operation Mode: Network operation mode\n"
            "Channel: WiFi channel selection\n"
            "TX Power: Transmission power level\n\n"
            "Warning: Incorrect settings may degrade performance!"
        )
        self.session.open(MessageBox, help_text, MessageBox.TYPE_INFO)


class ResultsScreen(Screen):
    skin = """
    <screen position="center,center" size="800,700" title="Results">
        <widget name="results" position="20,20" size="760,600" font="Regular;18" />
        <widget name="key_red" position="10,635" size="180,40" zPosition="1" font="Regular;20" halign="center" valign="center" backgroundColor="red" transparent="1" />
        <eLabel name="" position="9,677" size="180,8" zPosition="3" backgroundColor="#fe0000" />
    </screen>
    """

    def __init__(self, session, title, text):
        Screen.__init__(self, session)
        self.session = session
        self["results"] = ScrollLabel(text)
        self["key_red"] = Button(_("Back"))

        self["actions"] = ActionMap(["ColorActions",
                                     "OkCancelActions",
                                     "DirectionActions"],
                                    {"red": self.close,
                                     "cancel": self.close,
                                     "pageUp": self.pageUp,
                                     "pageDown": self.pageDown,
                                     "up": self.pageUp,
                                     "down": self.pageDown,
                                     "left": self.pageUp,
                                     "right": self.pageDown,
                                     })
        self.setTitle(title)

    def pageUp(self):
        self["results"].pageUp()

    def pageDown(self):
        self["results"].pageDown()
