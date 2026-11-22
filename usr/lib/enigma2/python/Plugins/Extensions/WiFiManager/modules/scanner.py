# -*- coding: utf-8 -*-

import subprocess
from twisted.internet import threads

from Screens.Screen import Screen
from Components.ActionMap import ActionMap
from Components.Button import Button
from Components.ScrollLabel import ScrollLabel

from . import _
from .skin_scale import scale_skin
from .signal_indicator import WiFiSignalIndicator, skin_compact
from .tools import (
    get_wifi_interfaces,
    is_interface_up,
    ensure_interface_up,
    parse_iwlist_detailed,
    group_networks,
    get_current_connected_essid,
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


class WiFiScanner(Screen):
    skin = scale_skin("""
    <screen position="center,center" size="800,700" title="WiFi Scanner">
        <widget name="scan_output" position="10,58" size="782,560" font="Regular;18" />
        <widget name="key_red" position="10,635" size="180,40" zPosition="1" font="Regular;20" halign="center" valign="center" backgroundColor="red" transparent="1" />
        <widget name="key_green" position="210,635" size="180,40" zPosition="1" font="Regular;20" halign="center" valign="center" backgroundColor="green" transparent="1" />
        <widget name="key_yellow" position="410,635" size="180,40" zPosition="1" font="Regular;20" halign="center" valign="center" backgroundColor="yellow" transparent="1" />
        <widget name="key_blue" position="600,635" size="180,40" zPosition="1" font="Regular;20" halign="center" valign="center" backgroundColor="blue" transparent="1" />
        <eLabel name="" position="9,677" size="180,8" zPosition="3" backgroundColor="#fe0000" />
        <eLabel name="" position="209,677" size="180,8" zPosition="3" backgroundColor="#fe00" />
        <eLabel name="" position="409,677" size="180,8" zPosition="3" backgroundColor="#cccc40" />
        <eLabel name="" position="599,677" size="180,8" zPosition="3" backgroundColor="#1a27408b" />
    """ + skin_compact(540, 2) + """
    </screen>
    """)

    def __init__(self, session):
        Screen.__init__(self, session)
        self.signal_indicator = WiFiSignalIndicator(self)
        self.session = session

        self["scan_output"] = ScrollLabel()
        self["key_red"] = Button(_("Scan"))
        self["key_green"] = Button(_("All APs"))
        self["key_yellow"] = Button(_("Details"))
        self["key_blue"] = Button(_("Exit"))

        self["actions"] = ActionMap(
            ["ColorActions", "OkCancelActions", "DirectionActions"],
            {
                "red": self.start_scan,
                "green": self.toggle_grouping,
                "yellow": self.toggle_details,
                "blue": self.close,
                "cancel": self.close,
                "pageUp": self.pageUp,
                "pageDown": self.pageDown,
                "up": self.pageUp,
                "down": self.pageDown,
                "left": self.pageUp,
                "right": self.pageDown,
                "ok": self.start_scan,
            }
        )

        self.detailed_view = False
        self.grouped = True          # one line per network name
        self.scanning = False
        self.closed = False
        self.last_scan = None        # (interface, networks, connected, error)
        self.setTitle(_("WiFi Scanner"))
        self.onClose.append(self._on_close)
        self.onLayoutFinish.append(self.start_scan)

    def _on_close(self):
        self.closed = True

    def pageUp(self):
        self["scan_output"].pageUp()

    def pageDown(self):
        self["scan_output"].pageDown()

    # -- scan (worker thread) ---------------------------------------------

    def start_scan(self):
        if self.scanning:
            return
        self.scanning = True
        self["key_red"].setText(_("Scanning..."))
        self["scan_output"].setText(_("Scanning for WiFi networks..."))
        d = threads.deferToThread(self._scan_worker)
        d.addCallback(self._scan_done)
        d.addErrback(self._scan_failed)

    def _scan_worker(self):
        """Runs in a thread: no GUI access here"""
        ifaces = get_wifi_interfaces()
        if not ifaces:
            return None, [], None, _("No WiFi interfaces found")
        last_error = None
        for iface in ifaces:
            if not is_interface_up(iface):
                ensure_interface_up(iface)
            try:
                result = subprocess.run(['iwlist', iface, 'scan'],
                                        capture_output=True, text=True,
                                        timeout=20)
            except subprocess.TimeoutExpired:
                last_error = _("iwlist timeout on {}").format(iface)
                continue
            except Exception as e:
                last_error = str(e)
                continue
            output = result.stdout + result.stderr
            if result.returncode != 0 and 'Cell' not in output:
                if 'busy' in output.lower():
                    last_error = _(
                        "Interface {} busy, try again in a few seconds").format(iface)
                else:
                    last_error = output.strip() or _("Scan failed")
                continue
            networks = parse_iwlist_detailed(output)
            connected = get_current_connected_essid(iface)
            return iface, networks, connected, None
        return None, [], None, last_error or _("Scan failed")

    def _scan_done(self, result):
        self.scanning = False
        if self.closed:
            return
        self["key_red"].setText(_("Scan"))
        self.last_scan = result
        self.show_results()

    def _scan_failed(self, failure):
        self.scanning = False
        if self.closed:
            return
        self["key_red"].setText(_("Scan"))
        self["scan_output"].setText(_("Scan error: ") + str(failure.value))

    # -- display ------------------------------------------------------------

    @staticmethod
    def _band(net):
        freq = net.get('frequency')
        ch = net.get('channel') or 0
        if (freq and freq >= 5) or ch > 14:
            return "5 GHz"
        return "2.4 GHz"

    @staticmethod
    def _bar(percent):
        filled = int(round(percent / 20.0))
        return "|" * filled + "." * (5 - filled)

    def show_results(self):
        if not self.last_scan:
            return
        iface, networks, connected, error = self.last_scan
        if error:
            self["scan_output"].setText(error + "\n\n" + "".join(
                self.get_detailed_network_status()))
            return
        shown = group_networks(
            networks, include_hidden=not self.grouped) if self.grouped else sorted(
            networks, key=lambda n: n.get(
                'quality_percent', 0), reverse=True)
        hidden = len([n for n in networks if not n.get('essid')])

        lines = [
            _("{count} networks on {iface} ({aps} access points, {hidden} hidden)").format(
                count=len(
                    group_networks(networks)),
                iface=iface,
                aps=len(networks),
                hidden=hidden),
            "\n\n"]
        for i, net in enumerate(shown, 1):
            essid = net.get('essid') or _("<hidden>")
            mark = ">> " if connected and net.get(
                'essid') == connected else "   "
            q = net.get('quality_percent', 0)
            sig = net.get('signal')
            sig_txt = ("%d dBm" % sig) if sig is not None else "-"
            lines.append("%s%2d. %s\n" % (mark, i, essid))
            lines.append("       %s %3d%%  %s  |  %s  ch %s  |  %s" % (
                self._bar(q), q, sig_txt, self._band(net),
                net.get('channel', '?'), net.get('security', '?')))
            if self.grouped and net.get('aps', 1) > 1:
                lines.append(_("  |  {} APs").format(net['aps']))
            lines.append("\n")
            if self.detailed_view:
                lines.append("       BSSID %s" % net.get('bssid', '?'))
                if net.get('frequency'):
                    lines.append("  |  %.3f GHz" % net['frequency'])
                if net.get('mode'):
                    lines.append("  |  %s" % net['mode'])
                lines.append("\n")
        if connected:
            lines.append(
                "\n" + _(">> = connected network ({})").format(connected))
        self["scan_output"].setText("".join(lines))

    def toggle_details(self):
        self.detailed_view = not self.detailed_view
        self["key_yellow"].setText(
            _("Basic") if self.detailed_view else _("Details"))
        self.show_results()

    def toggle_grouping(self):
        self.grouped = not self.grouped
        self["key_green"].setText(
            _("By name") if not self.grouped else _("All APs"))
        self.show_results()

    def get_detailed_network_status(self):
        """Hints when the scan does not work"""
        info = ["\n" + _("POSSIBLE SOLUTIONS:") + "\n"]
        info.append(_("   1. Check that the WiFi adapter is connected\n"))
        info.append(_("   2. Restart the WiFi interface (Tools menu)\n"))
        info.append(_("   3. Check that the WiFi driver is installed\n"))
        info.append(
            _("   4. Some drivers cannot scan while connecting: retry\n"))
        return info
