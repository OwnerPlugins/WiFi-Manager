# -*- coding: utf-8 -*-

from enigma import eTimer
from re import search
from Screens.Screen import Screen
from Components.ActionMap import ActionMap
from Components.Label import Label
from Components.ProgressBar import ProgressBar

from . import _
from .skin_scale import scale_skin
from .signal_indicator import WiFiSignalIndicator, skin_large, read_signal, _IwHelper
from .tools import (
    get_wifi_interfaces,
    get_ip_address,
    # is_interface_up,
    format_signal_quality
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


class WiFiMonitor(Screen):
    skin = scale_skin("""
    <screen position="center,center" size="800,700" title="WiFi Monitor">
        <widget name="interface_label" position="10,35" size="780,40" font="Regular;20" />
        <widget name="essid_label" position="10,100" size="780,40" font="Regular;20" />
        <widget name="ip_label" position="10,165" size="780,40" font="Regular;20" />
        <widget name="mac_label" position="10,230" size="780,40" font="Regular;20" />
        <widget name="quality_label" position="10,325" size="580,30" font="Regular;20" />
        <widget name="signal_label" position="10,457" size="580,30" font="Regular;20" />
        <widget name="quality_bar" position="10,372" size="580,60" />
        <widget name="signal_bar" position="10,503" size="580,60" />
        <widget name="key_red" position="10,635" size="180,40" zPosition="1" font="Regular;20" halign="center" valign="center" backgroundColor="red" transparent="1" />
        <widget name="key_green" position="210,635" size="180,40" zPosition="1" font="Regular;20" halign="center" valign="center" backgroundColor="green" transparent="1" />
        <widget name="key_yellow" position="410,635" size="180,40" zPosition="1" font="Regular;20" halign="center" valign="center" backgroundColor="yellow" transparent="1" />
        <widget name="key_blue" position="600,635" size="180,40" zPosition="1" font="Regular;20" halign="center" valign="center" backgroundColor="blue" transparent="1" />
        <eLabel name="" position="9,677" size="180,8" zPosition="3" backgroundColor="#fe0000" />
        <eLabel name="" position="209,677" size="180,8" zPosition="3" backgroundColor="#fe00" />
        <eLabel name="" position="409,677" size="180,8" zPosition="3" backgroundColor="#cccc40" />
        <eLabel name="" position="599,677" size="180,8" zPosition="3" backgroundColor="#1a27408b" />
    """ + skin_large(600, 330) + """
    </screen>
    """)

    def __init__(self, session):
        Screen.__init__(self, session)
        self.session = session
        self["interface_label"] = Label()
        self["essid_label"] = Label()
        self["ip_label"] = Label()
        self["mac_label"] = Label()
        self["quality_label"] = Label()
        self["signal_label"] = Label()
        self["quality_bar"] = ProgressBar()
        self["signal_bar"] = ProgressBar()
        self["signal_label"].setText(_("Signal: N/A"))
        for name in ["quality_bar", "signal_bar"]:
            self[name].setRange((0, 100))
            self[name].setValue(0)
        self["key_red"] = Label(_("Start"))
        self["key_green"] = Label(_("Stop"))
        self["key_yellow"] = Label(_("Refresh"))
        self["key_blue"] = Label(_("Exit"))
        self["actions"] = ActionMap(
            ["ColorActions", "OkCancelActions"],
            {
                "red": self.start_monitoring,
                "green": self.stop_monitoring,
                "yellow": self.update_status,
                "blue": self.close,
                "cancel": self.close,
            }
        )
        self.signal_indicator = WiFiSignalIndicator(self)
        self.monitoring = False
        self.monitor_timer = eTimer()
        self.monitor_timer.callback.append(self.update_status)
        self.ifname = None
        self.setTitle(_("WiFi Signal Monitor"))
        self.onClose.append(self.stop_monitoring)
        self.start_monitoring()

    def start_monitoring(self):
        """Start monitoring with interface check"""
        # Interface detection runs many external commands: do it once here,
        # not on every refresh
        interfaces = get_wifi_interfaces()
        if not interfaces:
            self.ifname = None
            self.show_error(_("No WiFi interfaces found"))
            return

        self.ifname = interfaces[0]
        self.monitoring = True
        self.monitor_timer.start(2000)
        self["key_red"].setText(_("Pause"))

    def stop_monitoring(self):
        self.monitoring = False
        self.monitor_timer.stop()
        self["key_red"].setText(_("Start"))

    def update_quality_bar(self, quality):
        """Update quality bar with color change using show/hide"""
        try:
            quality = int(quality)
            quality = max(0, min(100, quality))

            # Set value on the quality bar
            self["quality_bar"].hide()
            self["quality_bar"].setValue(quality)
            self["quality_bar"].show()

            # Update label
            self["quality_label"].setText(_("Quality: {}%").format(quality))

        except Exception as e:
            print(f"[WiFiMonitor] Error in update_quality_bar: {e}")

    def update_signal_bar(self, signal):
        """Update signal bar with color change using show/hide"""
        try:
            if isinstance(signal, str):
                m = search(r'(-?\d+)', signal)
                signal = int(m.group(1)) if m else -90

            # Convert dBm to percentage
            if signal >= -30:
                signal_percent = 100
            elif signal <= -90:
                signal_percent = 0
            else:
                signal_percent = int(((signal + 90) * 100) / 60)

            # Set value on the signal bar
            self["signal_bar"].hide()
            self["signal_bar"].setValue(signal_percent)
            self["signal_bar"].show()

            # Update label
            self["signal_label"].setText(_("Signal: {} dBm").format(signal))

        except Exception as e:
            print(f"[WiFiMonitor] Error in update_signal_bar: {e}")

    def update_status(self):
        if not self.monitoring:
            return

        try:
            wifi_data = self.get_wifi_info_iwconfig()
            if wifi_data:
                print(f"[WiFiMonitor] Data: {wifi_data}")
                self["interface_label"].setText(
                    _("Interface: {}").format(
                        wifi_data.get(
                            'interface', _('N/A'))))
                self["essid_label"].setText(
                    _("ESSID: {}").format(
                        wifi_data.get(
                            'essid',
                            _('Not connected'))))
                self["ip_label"].setText(
                    _("IP: {}").format(
                        wifi_data.get(
                            'ip', _('N/A'))))
                self["mac_label"].setText(
                    _("MAC: {}").format(
                        wifi_data.get(
                            'mac', _('N/A'))))

                quality = wifi_data.get('quality', 0)
                signal = wifi_data.get('signal', 0)
                print(
                    f"[WiFiMonitor] Quality: {quality}%, Signal: {signal} dBm")

                # Use format_signal_quality for a better description
                signal_description = format_signal_quality(quality)

                # signal_description already contains the percentage
                self["quality_label"].setText(
                    _("Quality: {}").format(signal_description))
                self["signal_label"].setText(
                    _("Signal: {} dBm").format(signal))

                self["quality_bar"].setValue(quality)

                # Convert dBm to percentage: -30dBm (excellent) to -90dBm (poor)
                # Also handle positive signals (rare)
                if signal > 0:
                    signal_percent = 100  # Maximum for positive signal values
                else:
                    signal_percent = max(0, min(100, (signal + 90) * 100 / 60))

                self["signal_bar"].setValue(int(signal_percent))

                # bars may have been hidden by a previous show_error()
                self["quality_bar"].show()
                self["signal_bar"].show()

            else:
                self.show_error(_("No WiFi connection data available"))

        except Exception as e:
            print(f"[WiFiMonitor] Update error: {e}")
            self.show_error(_("Monitoring error: {}").format(str(e)))

    def get_wifi_info_iwconfig(self):
        """Current link data without external commands:
        /proc/net/wireless (quality, dBm), ioctl (ESSID), sysfs (MAC, IP)"""
        try:
            ifname = self.ifname
            if not ifname:
                return None
            if not hasattr(self, "_iw"):
                self._iw = _IwHelper()
                self.onClose.append(self._iw.close)
            self._iw.load_qmax(ifname)
            sig = read_signal(ifname, self._iw.qmax, self._iw.essid)
            wifi_data = {'interface': ifname}
            if sig['state'] == 'connected':
                wifi_data['essid'] = sig['essid'] or _('Connected')
                wifi_data['quality'] = sig['quality']
                wifi_data['signal'] = sig['dbm'] if sig['dbm'] is not None \
                    else int(-100 + sig['quality'] / 2.0)
            else:
                wifi_data['essid'] = _('Not connected')
                wifi_data['quality'] = 0
                wifi_data['signal'] = -100
            try:
                with open("/sys/class/net/%s/address" % ifname) as f:
                    wifi_data['mac'] = f.read().strip()
            except Exception:
                wifi_data['mac'] = _('N/A')
            wifi_data['ip'] = get_ip_address(ifname) or _('Not connected')
            return wifi_data
        except Exception as e:
            print("[WiFiMonitor] Error: {}".format(e))
            return None

    def show_error(self, message):
        """Show error status with contextual information"""
        self["interface_label"].setText(
            _("Interface: {}").format(self.ifname or _('N/A')))
        self["essid_label"].setText(message)
        self["ip_label"].setText(_("IP: N/A"))
        self["mac_label"].setText(_("MAC: N/A"))
        self["quality_label"].setText(_("Quality: N/A"))
        self["signal_label"].setText(_("Signal: N/A"))
        # Reset bars
        self["quality_bar"].setValue(0)
        self["signal_bar"].setValue(0)
        self["quality_bar"].hide()
        self["signal_bar"].hide()
