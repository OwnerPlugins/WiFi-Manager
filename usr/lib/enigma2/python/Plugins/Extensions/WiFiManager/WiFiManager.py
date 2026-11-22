# -*- coding: utf-8 -*-

from os.path import exists
from Screens.Screen import Screen
from Screens.MessageBox import MessageBox
from Components.ActionMap import ActionMap
from Components.Label import Label
from Components.Pixmap import Pixmap
from Components.MenuList import MenuList

from .modules.scanner import WiFiScanner
from .modules.monitor import WiFiMonitor
from .modules.config import WiFiConfig
from .modules.diagnostics import WiFiDiagnostics
from .modules.detailed_info import WiFiDetailedInfo
from .modules.iwlist_tools import IWListTools
from .modules.connect import WiFiConnectZ
from .modules.speed_gauge import WiFiSpeedGauge
from .modules.updater import UpdateChecker
from .modules.signal_indicator import WiFiSignalIndicator, skin_compact

from . import _, __version__, __author__
from .modules.skin_scale import scale_skin

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


from .modules.tools import get_wifi_interfaces


class WiFiManagerMain(Screen):
    skin = scale_skin("""
    <screen position="center,center" size="800,700" title="WiFi Manager Main">
        <widget name="title" position="0,0" size="800,47" font="Regular;32" halign="center" valign="center" />

        <!-- Riga 1 -->
        <widget name="icon_scan" position="90,55" size="128,128" transparent="1" alphatest="on" scale="1" />
        <widget name="selected_scan" position="85,50" size="138,138" transparent="1" alphatest="on" scale="1" pixmap="/usr/lib/enigma2/python/Plugins/Extensions/WiFiManager/icons/selected-border.png" zPosition="1" />
        <widget name="label_scan" position="55,195" size="200,40" font="Regular;20" halign="center" valign="center" />

        <widget name="icon_monitor" position="335,55" size="128,128" transparent="1" alphatest="on" scale="1" />
        <widget name="selected_monitor" position="330,50" size="138,138" transparent="1" alphatest="on" scale="1" pixmap="/usr/lib/enigma2/python/Plugins/Extensions/WiFiManager/icons/selected-border.png" zPosition="1" />
        <widget name="label_monitor" position="295,195" size="200,40" font="Regular;20" halign="center" valign="center" />

        <widget name="icon_connect" position="570,55" size="128,128" transparent="1" alphatest="on" scale="1" />
        <widget name="selected_connect" position="565,50" size="138,138" transparent="1" alphatest="on" scale="1" pixmap="/usr/lib/enigma2/python/Plugins/Extensions/WiFiManager/icons/selected-border.png" zPosition="1" />
        <widget name="label_connect" position="530,195" size="200,40" font="Regular;20" halign="center" valign="center" />

        <!-- Riga 2 -->
        <widget name="icon_diagnostic" position="90,245" size="128,128" transparent="1" alphatest="on" scale="1" />
        <widget name="selected_diagnostic" position="85,240" size="138,138" transparent="1" alphatest="on" scale="1" pixmap="/usr/lib/enigma2/python/Plugins/Extensions/WiFiManager/icons/selected-border.png" zPosition="1" />
        <widget name="label_diagnostic" position="55,385" size="200,40" font="Regular;20" halign="center" valign="center" />

        <widget name="icon_info" position="335,245" size="128,128" transparent="1" alphatest="on" scale="1" />
        <widget name="selected_info" position="330,240" size="138,138" transparent="1" alphatest="on" scale="1" pixmap="/usr/lib/enigma2/python/Plugins/Extensions/WiFiManager/icons/selected-border.png" zPosition="1" />
        <widget name="label_info" position="295,385" size="200,40" font="Regular;20" halign="center" valign="center" />

        <widget name="icon_tools" position="570,245" size="128,128" transparent="1" alphatest="on" scale="1" />
        <widget name="selected_tools" position="565,240" size="138,138" transparent="1" alphatest="on" scale="1" pixmap="/usr/lib/enigma2/python/Plugins/Extensions/WiFiManager/icons/selected-border.png" zPosition="1" />
        <widget name="label_tools" position="530,385" size="200,40" font="Regular;20" halign="center" valign="center" />

        <!-- Riga 3 -->
        <widget name="icon_config" position="90,435" size="128,128" transparent="1" alphatest="on" scale="1" />
        <widget name="selected_config" position="85,430" size="138,138" transparent="1" alphatest="on" scale="1" pixmap="/usr/lib/enigma2/python/Plugins/Extensions/WiFiManager/icons/selected-border.png" zPosition="1" />
        <widget name="label_config" position="55,570" size="200,40" font="Regular;20" halign="center" valign="center" />

        <widget name="icon_speedtest" position="335,435" size="128,128" transparent="1" alphatest="on" scale="1" />
        <widget name="selected_speedtest" position="330,430" size="138,138" transparent="1" alphatest="on" scale="1" pixmap="/usr/lib/enigma2/python/Plugins/Extensions/WiFiManager/icons/selected-border.png" zPosition="1" />
        <widget name="label_speedtest" position="295,570" size="200,40" font="Regular;20" halign="center" valign="center" />

        <widget name="icon_lululla" position="570,435" size="128,128" transparent="1" alphatest="on" scale="1" />
        <widget name="selected_lululla" position="565,430" size="138,138" transparent="1" alphatest="on" scale="1" pixmap="/usr/lib/enigma2/python/Plugins/Extensions/WiFiManager/icons/selected-border.png" zPosition="1" />
        <widget name="label_lululla" position="535,570" size="200,40" font="Regular;20" halign="center" valign="center" />

        <widget name="description" position="24,615" size="750,70" font="Regular;18" halign="center" valign="center" />
    """ + skin_compact(546, 0) + """
    </screen>
    """)

    def __init__(self, session):
        Screen.__init__(self, session)
        self.session = session

        self["title"] = Label(_("WiFi Manager v.") + __version__)
        self["description"] = Label(_("Select an option"))

        self["icon_scan"] = Pixmap()
        self["label_scan"] = Label(_("Scanner"))
        self["selected_scan"] = Pixmap()

        self["icon_monitor"] = Pixmap()
        self["label_monitor"] = Label(_("Monitor"))
        self["selected_monitor"] = Pixmap()

        self["icon_connect"] = Pixmap()
        self["label_connect"] = Label(_("Connect"))
        self["selected_connect"] = Pixmap()

        self["icon_diagnostic"] = Pixmap()
        self["label_diagnostic"] = Label(_("Diagnostics"))
        self["selected_diagnostic"] = Pixmap()

        self["icon_info"] = Pixmap()
        self["label_info"] = Label(_("Details Info"))
        self["selected_info"] = Pixmap()

        self["icon_tools"] = Pixmap()
        self["label_tools"] = Label(_("Tools"))
        self["selected_tools"] = Pixmap()

        self["icon_config"] = Pixmap()
        self["label_config"] = Label(_("Config"))
        self["selected_config"] = Pixmap()

        self["icon_speedtest"] = Pixmap()
        self["label_speedtest"] = Label(_("Speedtest"))
        self["selected_speedtest"] = Pixmap()

        self["icon_lululla"] = Pixmap()
        self["label_lululla"] = Label(_("Info"))
        self["selected_lululla"] = Pixmap()

        # live animated WiFi signal (top-right corner)
        self.signal_indicator = WiFiSignalIndicator(self)

        self.current_selection = 0
        self.grid_items = [
            # row 1
            {'row': 0, 'col': 0, 'module': 'scanner', 'description': _(
                "Scan for available networks"), 'selected_widget': 'selected_scan'},
            {'row': 0, 'col': 1, 'module': 'monitor', 'description': _(
                "Real-time signal quality monitor"), 'selected_widget': 'selected_monitor'},
            {'row': 0, 'col': 2, 'module': 'connect', 'description': _(
                "Connect to WiFi networks"), 'selected_widget': 'selected_connect'},
            # row 2
            {'row': 1, 'col': 0, 'module': 'diagnostics', 'description': _(
                "WiFi diagnostics and tests"), 'selected_widget': 'selected_diagnostic'},
            {'row': 1, 'col': 1, 'module': 'detailed_info', 'description': _(
                "Complete iwconfig-like information"), 'selected_widget': 'selected_info'},
            {'row': 1, 'col': 2, 'module': 'iwlist_tools', 'description': _(
                "Advanced Tools"), 'selected_widget': 'selected_tools'},
            # row 3
            {'row': 2, 'col': 0, 'module': 'config', 'description': _(
                "Advanced WiFi configuration"), 'selected_widget': 'selected_config'},
            {'row': 2, 'col': 1, 'module': 'speedtest', 'description': _(
                "Speed test: download, upload, ping and jitter"), 'selected_widget': 'selected_speedtest'},
            {'row': 2, 'col': 2, 'module': 'lululla', 'description': _(
                "About, support and donations (INFO key)"), 'selected_widget': 'selected_lululla'},
        ]

        self.grid_map = {
            (0, 0): 0, (0, 1): 1, (0, 2): 2,
            (1, 0): 3, (1, 1): 4, (1, 2): 5,
            (2, 0): 6, (2, 1): 7, (2, 2): 8,
        }
        self["actions"] = ActionMap(
            ["OkCancelActions", "NavigationActions", "EPGSelectActions"],
            {
                "ok": self.run_selected,
                "cancel": self.close,
                "info": self.contactSupport,            # INFO key -> About
                "up": self.up,
                "down": self.down,
                "left": self.left,
                "right": self.right,
            }
        )
        self.setTitle(_("WiFi Manager"))
        self.onLayoutFinish.append(self.load_icons)
        self.onLayoutFinish.append(self.update_selection)
        # new release on GitHub? (background, once per Enigma2 session)
        # NB: onLayoutFinish accepts only bound methods (OpenATV exec()s
        # anything else), so no lambda here
        self.onLayoutFinish.append(self.check_updates)

    def check_updates(self):
        UpdateChecker(self.session).check(silent=True)

    def load_icons(self):
        base_path = "/usr/lib/enigma2/python/Plugins/Extensions/WiFiManager/icons/"
        icons = {
            "icon_scan": "wifi-scan.png",
            "icon_monitor": "wifi-monitor.png",
            "icon_config": "wifi-config.png",
            "icon_diagnostic": "wifi-diagnostic.png",
            "icon_info": "wifi-info.png",
            "icon_tools": "wifi-tools.png",
            "icon_connect": "wifi-on.png",
            "icon_speedtest": "wifi-speed.png",
            "icon_lululla": "wifi-lululla.png",
        }
        for name, file in icons.items():
            path = base_path + file
            try:
                if not exists(path):
                    print(f"Icon missing: {path}")
                    continue
                self[name].instance.setPixmapFromFile(path)
                print(f"Loaded {path}")
            except Exception as e:
                print(f" Error loading {path}: {e}")
        self.hide_all_selection_borders()

    def hide_all_selection_borders(self):
        """Hides all selection edges"""
        for item in self.grid_items:
            self[item['selected_widget']].hide()

    def update_selection(self):
        """Update the current selection"""
        # Hide all edges
        self.hide_all_selection_borders()

        # Show border for selected item
        selection = self.grid_items[self.current_selection]
        self[selection['selected_widget']].show()
        self["description"].setText(selection['description'])

    def get_current_position(self):
        """Returns the current position (row, column)"""
        return self.grid_items[self.current_selection]['row'], self.grid_items[self.current_selection]['col']

    def right(self):
        current_row, current_col = self.get_current_position()

        if current_col < 2:
            new_index = self.grid_map.get((current_row, current_col + 1))
            if new_index is not None and new_index < len(
                    self.grid_items) and self.grid_items[new_index]['module'] is not None:
                self.current_selection = new_index
                self.update_selection()
        else:
            if current_row < 2:
                new_index = self.grid_map.get((current_row + 1, 0))
                if new_index is not None and new_index < len(
                        self.grid_items) and self.grid_items[new_index]['module'] is not None:
                    self.current_selection = new_index
                    self.update_selection()

    def down(self):
        current_row, current_col = self.get_current_position()

        if current_row < 2:
            new_index = self.grid_map.get((current_row + 1, current_col))
            if new_index is not None and new_index < len(
                    self.grid_items) and self.grid_items[new_index]['module'] is not None:
                self.current_selection = new_index
                self.update_selection()

    def left(self):
        current_row, current_col = self.get_current_position()

        if current_col > 0:
            new_index = self.grid_map.get((current_row, current_col - 1))
            if new_index is not None and self.grid_items[new_index]['module'] is not None:
                self.current_selection = new_index
                self.update_selection()
        else:
            if current_row > 0:
                new_index = self.grid_map.get((current_row - 1, 2))
                if new_index is not None and new_index < len(
                        self.grid_items) and self.grid_items[new_index]['module'] is not None:
                    self.current_selection = new_index
                    self.update_selection()

    def up(self):
        current_row, current_col = self.get_current_position()

        if current_row > 0:
            new_index = self.grid_map.get((current_row - 1, current_col))
            if new_index is not None and self.grid_items[new_index]['module'] is not None:
                self.current_selection = new_index
                self.update_selection()

    def connect_closed(self, result=None):
        """Callback when WiFiConnectZ closes"""
        print("[DEBUG] WiFiConnectZ closed")

    def contactSupport(self):
        self.session.open(WiFiAboutScreen)

    def run_selected(self):
        selection = self.grid_items[self.current_selection]
        module_name = selection['module']

        if module_name is None:
            return

        try:
            if module_name == "scanner":
                self.session.open(WiFiScanner)
            elif module_name == "monitor":
                self.session.open(WiFiMonitor)
            elif module_name == "connect":
                self.session.open(WiFiConnectZ)
            elif module_name == "diagnostics":
                self.session.open(WiFiDiagnostics)
            elif module_name == "detailed_info":
                ifnames = get_wifi_interfaces()
                if ifnames:
                    self.session.open(WiFiDetailedInfo, ifnames[0])
                else:
                    self.session.open(
                        MessageBox,
                        _("No WiFi interfaces found"),
                        MessageBox.TYPE_ERROR)
            elif module_name == "iwlist_tools":
                self.session.open(ToolsMenuScreen)
            elif module_name == "config":
                self.session.open(WiFiConfig)
            elif module_name == "speedtest":
                self.session.open(WiFiSpeedGauge)
            elif module_name == "lululla":
                self.contactSupport()

        except Exception as e:
            self.session.open(
                MessageBox,
                _("Error opening {module}: {error}").format(
                    module=module_name,
                    error=str(e)),
                MessageBox.TYPE_ERROR)

    def open_tools_direct(self):
        """Directly opens the tools list from the main menu"""
        from Screens.ChoiceBox import ChoiceBox

        menu_list = [
            (_("Advanced Scan"), "scanning"),
            (_("Channel Info"), "channel"),
            (_("Bitrate Info"), "bitrate"),
            (_("Encryption Info"), "encryption"),
            (_("Power Management"), "power"),
            (_("Retry Limits"), "retry"),
            (_("Access Points"), "ap"),
            (_("Advanced Config"), "advanced_config"),
            (_("Restart WiFi Interface"), "restart_wifi"),
            (_("Reload WiFi Modules"), "reload_modules"),
            (_("Check System Logs"), "check_logs"),
        ]

        self.session.openWithCallback(
            self.tool_selected_callback,
            ChoiceBox,
            title=_("WiFi Advanced Tools"),
            list=menu_list
        )

    def tool_selected_callback(self, result):
        """Callback when a tool is selected from the menu"""
        if result is not None:
            tool_name = result[1]
            # Open IWListTools passing the selected tool
            self.session.openWithCallback(
                self.return_to_tools_callback,
                IWListTools,
                tool_name
            )

    def return_to_tools_callback(self, result=None):
        """Callback when finishing a tool - returns to the tools menu"""
        self.open_tools_direct()


ICONS_PATH = "/usr/lib/enigma2/python/Plugins/Extensions/WiFiManager/icons/"


class WiFiAboutScreen(Screen):
    """About: support info and 'offer a coffee' QR codes"""
    skin = scale_skin("""
    <screen position="center,center" size="800,700" title="WiFi Manager - About">
        <widget name="about_title" position="0,10" size="800,44" font="Regular;30" halign="center" valign="center" />
        <widget name="about_text" position="40,64" size="720,236" font="Regular;19" halign="center" valign="top" />
        <widget name="coffee_label" position="0,306" size="800,36" font="Regular;26" halign="center" valign="center" foregroundColor="#ffcc33" />
        <widget name="scan_label" position="0,342" size="800,26" font="Regular;17" halign="center" valign="center" foregroundColor="#bbbbbb" />
        <widget name="qr_paypal" position="150,376" size="200,200" alphatest="off" scale="1" zPosition="1" />
        <widget name="qr_kofi" position="450,376" size="200,200" alphatest="off" scale="1" zPosition="1" />
        <eLabel position="150,580" size="200,30" text="PayPal" font="Regular;22" halign="center" valign="center" transparent="1" />
        <eLabel position="450,580" size="200,30" text="Ko-fi" font="Regular;22" halign="center" valign="center" transparent="1" />
        <widget name="key_red" position="10,635" size="200,40" zPosition="1" font="Regular;20" halign="center" valign="center" backgroundColor="red" transparent="1" />
        <widget name="key_green" position="230,635" size="260,40" zPosition="1" font="Regular;20" halign="center" valign="center" transparent="1" />
        <eLabel name="" position="9,677" size="200,8" zPosition="3" backgroundColor="#fe0000" />
        <eLabel name="" position="229,677" size="260,8" zPosition="3" backgroundColor="#fe00" />
    </screen>
    """)

    def __init__(self, session):
        Screen.__init__(self, session)
        self.session = session
        self["about_title"] = Label(
            "WiFi Manager v.%s by %s" % (__version__, __author__))
        self["about_text"] = Label(
            _("Need help or have questions about WiFi Manager?\n\n") +
            _("For troubleshooting, detailed guidance, or community support, visit:\n") +
            "https://www.linuxsat-support.com\n" +
            "https://www.corvoboys.org\n\n" +
            _("These forums are great places to get help,\n") +
            _("share experiences,and connect with other users."))
        self["coffee_label"] = Label(
            _("Do you like this plugin? Offer me a coffee!"))
        self["scan_label"] = Label(
            _("Scan a QR code with your phone"))
        self["key_red"] = Label(_("Close"))
        self["key_green"] = Label(_("Check for updates"))
        self["qr_paypal"] = Pixmap()
        self["qr_kofi"] = Pixmap()
        self["actions"] = ActionMap(
            ["OkCancelActions", "ColorActions", "EPGSelectActions"],
            {"ok": self.close, "cancel": self.close, "red": self.close,
             "info": self.close,
             "green": lambda: UpdateChecker(self.session).check(silent=False)})
        self.setTitle(_("WiFi Manager - About"))
        self.onLayoutFinish.append(self.load_qr_codes)

    def load_qr_codes(self):
        """Same loading method as the main menu icons"""
        missing = []
        for widget, filename in (("qr_paypal", "qr-paypal.png"),
                                 ("qr_kofi", "qr-kofi.png")):
            path = ICONS_PATH + filename
            try:
                if exists(path) and self[widget].instance:
                    self[widget].instance.setPixmapFromFile(path)
                    print("[WiFiAbout] loaded %s" % path)
                else:
                    missing.append(filename)
            except Exception as e:
                print("[WiFiAbout] error loading %s: %s" % (path, e))
                missing.append(filename)
        if missing:
            self["scan_label"].setText(
                _("QR code image missing: {}").format(", ".join(missing)))


class ToolsMenuScreen(Screen):
    skin = scale_skin("""
    <screen position="center,center" size="800,700" title="WiFi Advanced Tools">
        <widget name="menu" position="20,20" size="760,400" font="Regular;22" itemHeight="36" scrollbarMode="showOnDemand" />
        <widget name="help_label" position="20,432" size="760,190" font="Regular;18" />
        <widget name="key_red" position="10,635" size="200,40" zPosition="1" font="Regular;20" halign="center" valign="center" backgroundColor="red" transparent="1" />
        <widget name="key_green" position="210,635" size="200,40" zPosition="1" font="Regular;20" halign="center" valign="center" backgroundColor="green" transparent="1" />
        <eLabel name="" position="645,630" size="150,20" backgroundColor="#49bbff" halign="center" valign="center" transparent="0" cornerRadius="9" font="Regular; 16" zPosition="1" text="OK - SELECT" />
        <eLabel name="" position="645,657" size="150,20" backgroundColor="#49bbff" halign="center" valign="center" transparent="0" cornerRadius="9" font="Regular; 16" zPosition="1" text="TXT - KEYBOARD" />
        <eLabel name="" position="9,677" size="200,8" zPosition="3" backgroundColor="#fe0000" />
        <eLabel name="" position="209,677" size="200,8" zPosition="3" backgroundColor="#fe00" />
    </screen>
    """)

    def __init__(self, session):
        Screen.__init__(self, session)
        self.session = session

        self.tool_list = [
            (_("Advanced Scan"), "scanning", _("Detailed network scanning with signal strength and encryption info")),
            (_("Channel Info"), "channel", _("Available frequencies and channels for your region")),
            (_("Bitrate Info"), "bitrate", _("Supported bitrates and current transmission rates")),
            (_("Encryption Info"), "encryption", _("Encryption keys and security protocols")),
            (_("Power Management"), "power", _("Power management settings and power saving modes")),
            (_("Retry Limits"), "retry", _("Packet retry limits and frame lifetime settings")),
            (_("Access Points"), "ap", _("List of access points and connected peer stations")),
            (_("Advanced Config"), "advanced_config", _("Advanced WiFi interface configuration")),
            (_("Restart WiFi Interface"), "restart_wifi", _("Restart wireless interface to reset connectivity")),
            (_("Reload WiFi Modules"), "reload_modules", _("Reload kernel WiFi modules to fix driver issues")),
            (_("Check System Logs"), "check_logs", _("Check system logs for WiFi errors and connection issues")),
        ]

        self["menu"] = MenuList([(item[0], item[1])
                                for item in self.tool_list])
        self["help_label"] = Label(_("Select a tool to see description"))
        self["key_red"] = Label(_("Close"))
        self["key_green"] = Label(_("Select"))

        self["actions"] = ActionMap(["OkCancelActions", "ColorActions", "DirectionActions"], {
            "ok": self.select_tool,
            "cancel": self.close,
            "green": self.select_tool,
            "red": self.close,
            "up": self.update_help,
            "down": self.update_help,
        })

        self["menu"].onSelectionChanged.append(self.update_help)
        self.setTitle(_("WiFi Advanced Tools"))
        self.update_help()

    def get_tool_help(self, tool):
        """Returns the help text for the specific tool"""
        help_texts = {
            "scanning": _("Performs a detailed scan of available WiFi networks showing:\n- Signal strength\n- Encryption type\n- Channels\n- Frequency bands\n- MAC addresses"),
            "channel": _("Shows available channels and frequencies for your region:\n- 2.4GHz channels (1-14)\n- 5GHz channels\n- Regulatory domain info\n- Channel widths"),
            "bitrate": _("Displays supported bitrates and current transmission rates:\n- Available bitrates\n- Current bitrate\n- MCS indexes (for 802.11n/ac)\n- HT/VHT capabilities"),
            "encryption": _("Shows encryption and security information:\n- Supported encryption types\n- Current encryption\n- Key management\n- Security protocols"),
            "power": _("Displays power management settings:\n- Current power state\n- Power saving mode\n- Transmission power\n- Power management features"),
            "retry": _("Shows packet retry limits and settings:\n- Retry short limit\n- Retry long limit\n- Frame lifetime\n- Retry statistics"),
            "ap": _("Lists access points and peer stations:\n- Connected stations\n- AP information\n- Peer statistics\n- Connection quality"),
            "advanced_config": _("Advanced WiFi interface configuration:\n- Operation mode (Managed/AP/Monitor)\n- Channel selection\n- TX power control\n- Basic interface settings"),
            "restart_wifi": _("Restarts the WiFi interface:\n- Brings interface down/up\n- Reinitializes driver\n- Preserves configuration\n- Quick connectivity reset"),
            "reload_modules": _("Reloads WiFi kernel modules:\n- Unloads/loads drivers\n- Resets hardware\n- Fixes driver issues\n- Requires root access"),
            "check_logs": _("Checks system logs for WiFi errors:\n- Kernel messages (dmesg)\n- System logs\n- Driver errors\n- Connection issues"),
        }
        return help_texts.get(tool, _("No help available for this tool."))

    def update_help(self):
        """Updates the help text when selection changes"""
        try:
            current = self["menu"].getCurrent()
            if current:
                help_text = self.get_tool_help(current[1])
                self["help_label"].setText(help_text)
            else:
                self["help_label"].setText(
                    _("Select a tool to see description"))
        except Exception as e:
            print(f"Error loading help {e}")
            self["help_label"].setText(_("Error loading help"))

    def select_tool(self):
        """Selects and opens the current tool"""
        current = self["menu"].getCurrent()
        if current:
            tool_name = current[1]
            self.session.openWithCallback(
                self.return_to_menu,
                IWListTools,
                tool_name
            )

    def return_to_menu(self, result=None):
        """Returns to the menu after finishing with a tool"""
        pass
