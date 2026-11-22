# -*- coding: utf-8 -*-

import subprocess
from threading import Thread

from twisted.internet import reactor

from Screens.Screen import Screen
from Screens.MessageBox import MessageBox
from Components.ActionMap import ActionMap
from Components.Label import Label
from Components.Button import Button
from Components.ScrollLabel import ScrollLabel
from Components.ProgressBar import ProgressBar

try:
    from .speedtest_simple import Enigma2Speedtest
except ImportError as e:
    print(f"SpeedtestSimple import error: {e}")
    Enigma2Speedtest = None

from .tools import get_wifi_interfaces, get_interface_info
from . import speedtest
from .. import _
from .skin_scale import scale_skin
from .signal_indicator import WiFiSignalIndicator, skin_compact

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


class WiFiSpeedtestManager(Screen):
    skin = scale_skin("""
    <screen position="center,center" size="800,700" title="WiFi Speed Test">
        <widget name="status_label" position="20,12" size="510,40" font="Regular;24" halign="center" valign="center" />
        <widget name="progress" position="20,60" size="760,30" />
        <widget name="results" position="20,100" size="760,512" font="Regular;20" />
        <widget name="key_red" position="10,635" size="180,40" zPosition="1" font="Regular;20" halign="center" valign="center" backgroundColor="red" transparent="1" />
        <widget name="key_green" position="210,635" size="180,40" zPosition="1" font="Regular;20" halign="center" valign="center" backgroundColor="green" transparent="1" />
        <widget name="key_yellow" position="410,635" size="180,40" zPosition="1" font="Regular;20" halign="center" valign="center" backgroundColor="yellow" transparent="1" />
        <widget name="key_blue" position="600,635" size="180,40" zPosition="1" font="Regular;20" halign="center" valign="center" backgroundColor="blue" transparent="1" />
        <eLabel name="" position="9,677" size="180,8" zPosition="3" backgroundColor="#fe0000" />
        <eLabel name="" position="209,677" size="180,8" zPosition="3" backgroundColor="#fe00" />
        <eLabel name="" position="409,677" size="180,8" zPosition="3" backgroundColor="#cccc40" />
        <eLabel name="" position="599,677" size="180,8" zPosition="3" backgroundColor="#1a27408b" />
    """ + skin_compact(540, 4) + """
    </screen>
    """)

    def __init__(self, session):
        Screen.__init__(self, session)
        self.signal_indicator = WiFiSignalIndicator(self)
        self.session = session
        self.speedtest = None
        self.is_testing = False
        self.current_test = None
        self.interface = None       # detected when a test starts
        self.debug = False
        self.cancelled = False      # set when the screen is closed
        self.closed = False

        self["status_label"] = Label(_("Select a speed test type"))
        self["progress"] = ProgressBar()
        self["results"] = ScrollLabel()

        self["key_red"] = Button(_("Close"))
        self["key_green"] = Button(_("Quick Test"))
        self["key_yellow"] = Button(_("Full Test"))
        self["key_blue"] = Button(_("Details"))

        self["progress"].setRange((0, 100))
        self["progress"].setValue(0)

        self["actions"] = ActionMap(["ColorActions",
                                     "OkCancelActions",
                                     "DirectionActions"],
                                    {"red": self.close,
                                     "green": self.quick_test,
                                     "yellow": self.full_test,
                                     "blue": self.detailed_test,
                                     "cancel": self.close,
                                     "ok": self.show_results,
                                     "up": self.keyUp,
                                     "down": self.keyDown,
                                     "left": self.keyLeft,
                                     "right": self.keyRight})

        self.setTitle(_("WiFi Speed Test Manager"))
        self.update_buttons()

    def update_buttons(self):
        """Update the state of the buttons"""
        # self["results"].setText("")
        if self.is_testing:
            self["key_green"].setText("")
            self["key_yellow"].setText("")
            self["key_blue"].setText("")
        else:
            self["key_green"].setText(_("Quick Test"))
            self["key_yellow"].setText(_("Full Test"))
            self["key_blue"].setText(_("Details"))

    def keyUp(self):
        """Handle UP key - navigate and auto-select"""
        print("[DEBUG] UP pressed")
        self["results"].pageUp()
        self.update_buttons()

    def keyDown(self):
        """Handle DOWN key - navigate and auto-select"""
        print("[DEBUG] DOWN pressed")
        self["results"].pageDown()
        self.update_buttons()

    def keyLeft(self):
        """Handle LEFT key - navigate and auto-select"""
        print("[DEBUG] LEFT pressed")
        self["results"].pageUp()
        self.update_buttons()

    def keyRight(self):
        """Handle RIGHT key - navigate and auto-select"""
        print("[DEBUG] RIGHT pressed")
        self["results"].pageDown()
        self.update_buttons()

    def _check_cancellation(self):
        """False if the test must stop (screen closed)"""
        return not self.cancelled

    def _stop_requested(self):
        return self.cancelled

    def _ui(self, func, *args):
        """Run func in the GUI thread: Enigma2 widgets must not be touched
        from the worker thread"""
        def run():
            if not self.closed:
                func(*args)
        reactor.callFromThread(run)

    def _progress_range(self, low, high, status):
        """Progress callback mapping 0..1 into low..high"""
        def cb(fraction):
            self.update_progress(int(low + (high - low) * fraction), status)
        return cb

    def _start(self, target, status):
        if self.is_testing:
            return
        self.is_testing = True
        self.cancelled = False
        self.update_buttons()
        self["results"].setText(_("wait..."))
        self["status_label"].setText(status)
        self["progress"].setValue(0)
        t = Thread(target=target)
        t.daemon = True
        t.start()

    def quick_test(self):
        """Quick speed test"""
        self._start(self._run_quick_test, _("Running quick speed test..."))

    def full_test(self):
        """Full speed test"""
        self._start(self._run_full_test, _("Running full speed test..."))

    def detailed_test(self):
        """Detailed test with more information"""
        self._start(self._run_detailed_test,
                    _("Running detailed speed test..."))

    def _get_client_information(self):
        """Get client network information"""
        try:
            import socket
            import json
            from urllib.request import urlopen

            info = []

            # Hostname
            hostname = socket.gethostname()
            info.append(_("Hostname: {hostname}").format(hostname=hostname))

            # Public IP and ISP info
            try:
                ip_response = urlopen('http://ipinfo.io/json', timeout=5)
                ip_data = json.loads(ip_response.read().decode())
                info.append(
                    _("Public IP: {ip}").format(
                        ip=ip_data.get(
                            'ip', _('Unknown'))))
                info.append(_("Location: {city}, {country}").format(
                    city=ip_data.get('city', _('Unknown')),
                    country=ip_data.get('country', _('Unknown'))
                ))
                info.append(
                    _("ISP: {isp}").format(
                        isp=ip_data.get(
                            'org', _('Unknown'))))
            except Exception as e:
                print(e)
                info.append(_("Public IP: Unable to determine"))

            return "\n".join(info)
        except Exception as e:
            return _("Client info error: {error}").format(error=str(e))

    def _get_server_information(self):
        """Get server information"""
        try:
            servers = [
                (_("Primary DNS"), "8.8.8.8", _("Google")),
                (_("Secondary DNS"), "1.1.1.1", _("Cloudflare")),
                (_("Tertiary DNS"), "208.67.222.222", _("OpenDNS"))
            ]

            server_info = []
            for name, host, sponsor in servers:
                ping_result = speedtest.test_ping(host, 1)
                server_info.append(_("{name} ({sponsor}): {ping}").format(
                    name=name, sponsor=sponsor, ping=ping_result
                ))

            return "\n".join(server_info)
        except Exception as e:
            return _("Server info error: {error}").format(error=str(e))

    def _get_network_information(self):
        """Get detailed network information"""
        try:
            info = []

            # Interface information
            interfaces = get_wifi_interfaces()
            if interfaces:
                info.append(
                    _("Network Interface: {interface}").format(
                        interface=interfaces[0]))
                info.append(self._wifi_link_info(interfaces[0]))

            # Gateway
            try:
                result = subprocess.run(
                    ['ip', 'route'], capture_output=True, text=True)
                for line in result.stdout.split('\n'):
                    if 'default' in line:
                        gateway = line.split()[2]
                        info.append(
                            _("Gateway: {gateway}").format(
                                gateway=gateway))
                        break
            except Exception as e:
                print(e)
                pass

            return "\n".join(info) if info else _(
                "Network information unavailable")
        except Exception as e:
            return _("Network info error: {error}").format(error=str(e))

    def _wifi_link_info(self, ifname):
        """WiFi link rate: the real speed over WiFi is about 50-70% of it,
        so it is the ceiling of what the receiver can measure"""
        try:
            info = get_interface_info(ifname)
            rate = info.get('bitrate', '')
            text = _("WiFi link rate: {rate}").format(rate=rate)
            freq = info.get('frequency', '')
            if freq:
                text += " - " + freq
            return text + "\n" + _(
                "(real WiFi throughput is about 50-70% of the link rate)")
        except Exception as e:
            print(e)
            return _("WiFi link rate: unknown")

    def _run_quick_test(self):
        """Run a quick test using speedtest.quick_speed_test"""
        try:
            self.current_test = "quick"

            self.update_progress(5, _("Testing connectivity..."))
            ping_result = speedtest.test_ping()
            if not self._check_cancellation():
                return

            download_result = speedtest.test_download_speed(
                stop=self._stop_requested,
                progress=self._progress_range(
                    10, 55, _("Testing download speed...")))
            if not self._check_cancellation():
                return

            upload_result = speedtest.test_upload_speed(
                stop=self._stop_requested,
                progress=self._progress_range(
                    55, 100, _("Testing upload speed...")))
            if not self._check_cancellation():
                return

            self.update_progress(100, _("Quick test completed"))

            # Formatta i risultati
            results_text = _("=== QUICK SPEED TEST RESULTS ===\n\n")
            results_text += _("Ping/Latency: {ping}\n").format(
                ping=ping_result)
            results_text += _("Download Speed: {download}\n").format(
                download=download_result)
            results_text += _("Upload Speed: {upload}\n").format(
                upload=upload_result)
            results_text += self._evaluate_connection_quality(
                download_result, ping_result)

            self.show_results_success(results_text)

        except Exception as e:
            self.show_error(
                _("Quick test error: {error}").format(
                    error=str(e)))

    def _run_full_test(self):
        """Runs full test in a separate thread with timeout handling"""
        try:
            self.current_test = "full"
            results_text = _("=== COMPREHENSIVE SPEED TEST ===\n\n")

            # 0. Client information
            if not self._check_cancellation():
                return
            self.update_progress(5, _("Gathering client information..."))
            client_info = self._get_client_information()
            results_text += _("=== CLIENT INFORMATION ===\n{info}\n\n").format(
                info=client_info)

            # 1. Extended ping test
            if not self._check_cancellation():
                return
            self.update_progress(15, _("Testing latency to multiple hosts..."))
            extended_ping = speedtest.extended_ping_test()
            results_text += _("=== LATENCY TEST ===\n{ping}\n\n").format(
                ping=extended_ping)

            # 2. Server information
            if not self._check_cancellation():
                return
            self.update_progress(25, _("Finding best server..."))
            server_info = self._get_server_information()
            results_text += _("=== SERVER INFORMATION ===\n{server}\n\n").format(
                server=server_info)

            # 3. Multiple download tests
            if not self._check_cancellation():
                return
            multi_download = speedtest.multi_server_download_test(
                stop=self._stop_requested,
                progress=self._progress_range(
                    30, 65, _("Testing download speed (multiple servers)...")))
            results_text += _("=== DOWNLOAD SPEED TEST ===\n{download}\n\n").format(
                download=multi_download)

            # 4. Upload test
            if not self._check_cancellation():
                return
            upload_result = speedtest.test_upload_speed(
                stop=self._stop_requested,
                progress=self._progress_range(
                    65, 80, _("Testing upload speed...")))
            results_text += _("=== UPLOAD SPEED TEST ===\n{upload}\n\n").format(
                upload=upload_result)

            # 5. Stability test
            if not self._check_cancellation():
                return
            self.update_progress(80, _("Testing connection stability..."))
            stability = speedtest.connection_stability_test()
            results_text += _("=== CONNECTION STABILITY ===\n{stability}\n\n").format(
                stability=stability)

            # 6. Network information
            if not self._check_cancellation():
                return
            self.update_progress(85, _("Gathering network details..."))
            network_info = self._get_network_information()
            results_text += _("=== NETWORK INFORMATION ===\n{network}\n\n").format(
                network=network_info)

            # 7. Final connectivity test
            if not self._check_cancellation():
                return
            self.update_progress(90, _("Final connectivity check..."))
            connectivity = speedtest.test_connectivity()
            results_text += _("=== FINAL CHECK ===\nConnectivity: {conn}\n").format(
                conn=connectivity)

            # summary at the top: the numbers people look for
            best = [ln for ln in multi_download.split("\n") if ln.startswith(
                _("Best: ").strip()) or ln.startswith("Best")]
            dl_text = best[-1].split(":",
                                     1)[1].strip() if best else _("failed")
            summary = _("=== RESULT ===\nDownload: {dl}\nUpload: {ul}\nPing: {ping}\n\n").format(
                dl=dl_text, ul=upload_result, ping=connectivity)
            header = _("=== COMPREHENSIVE SPEED TEST ===\n\n")
            results_text = header + summary + results_text[len(header):]

            # Complete
            self.update_progress(100, _("Full test completed"))
            self.show_results_success(results_text)

        except Exception as e:
            self.show_error(_("Full test error: {error}").format(error=str(e)))

    def _run_detailed_test(self):
        """Run detailed test using SpeedtestSimple"""
        try:
            self.current_test = "detailed"

            if not Enigma2Speedtest:
                self.show_error(_("SpeedtestSimple not available"))
                return

            def callback(stage, message=None):
                stages = {
                    'checking_connection': (10, _("Checking internet connection...")),
                    'client_info_start': (20, _("Getting client information...")),
                    'client_info_complete': (25, _("Client info completed")),
                    'ping_start': (30, _("Testing latency...")),
                    'ping_complete': (40, _("Latency test completed")),
                    'server_selection_start': (45, _("Finding best server...")),
                    'server_found': (50, _("Server found")),
                    'download_start': (60, _("Testing download speed...")),
                    'download_complete': (80, _("Download test completed")),
                    'upload_start': (85, _("Testing upload speed...")),
                    'upload_complete': (95, _("Upload test completed")),
                    'error': (0, _("Test failed")),
                }
                if stage in stages:
                    progress, default_status = stages[stage]
                    status = message if message else default_status
                    self.update_progress(progress, status)

            self.update_progress(5, _("Initializing detailed speed test..."))
            speedtest_simple = Enigma2Speedtest(stop=self._stop_requested)

            results = speedtest_simple.run_test(callback=callback)
            if not self._check_cancellation():
                return

            if results:
                self.update_progress(100, _("Detailed test completed"))
                results_text = speedtest_simple.format_results()
                self.show_results_success(results_text)
            else:
                self.show_error(
                    _("Detailed speed test failed - Check internet connection"))

        except Exception as e:
            self.show_error(
                _("Detailed test error: {error}").format(
                    error=str(e)))

    def _evaluate_connection_quality(self, download_result, ping_result):
        """Evaluate connection quality based on test results"""
        evaluation = _("\n=== CONNECTION QUALITY ===\n")

        try:
            # Analyze download speed
            download_speed = None
            if download_result and "Mbps" in download_result:
                try:
                    # Extract number from strings like "25.4 Mbps" or "Error:
                    # 10.5 Mbps"
                    from re import search as re_search
                    speed_match = re_search(
                        r'(\d+\.\d+|\d+)\s*Mbps', download_result)
                    if speed_match:
                        download_speed = float(speed_match.group(1))
                except (ValueError, AttributeError, IndexError):
                    pass

            if download_speed is not None:
                if download_speed > 50:
                    evaluation += _("📈 Excellent download speed ({:.1f} Mbps)\n").format(
                        download_speed)
                elif download_speed > 20:
                    evaluation += _("📊 Good download speed ({:.1f} Mbps)\n").format(
                        download_speed)
                elif download_speed > 5:
                    evaluation += _("📉 Average download speed ({:.1f} Mbps)\n").format(
                        download_speed)
                else:
                    evaluation += _("📉 Poor download speed ({:.1f} Mbps)\n").format(
                        download_speed)
            else:
                evaluation += _("❓ Download speed unavailable\n")

            # Analyze latency/ping
            ping_time = None
            if ping_result and "ms" in ping_result:
                try:
                    # Extract number from strings like "25.4 ms" or "Error: 100
                    # ms"
                    from re import search as re_search
                    ping_match = re_search(r'(\d+\.\d+|\d+)\s*ms', ping_result)
                    if ping_match:
                        ping_time = float(ping_match.group(1))
                except (ValueError, AttributeError, IndexError):
                    pass

            if ping_time is not None:
                if ping_time < 30:
                    evaluation += _(
                        "⚡ Excellent latency ({:.1f} ms)\n").format(ping_time)
                elif ping_time < 60:
                    evaluation += _(
                        "✅ Good latency ({:.1f} ms)\n").format(ping_time)
                elif ping_time < 100:
                    evaluation += _(
                        "⚠️ Average latency ({:.1f} ms)\n").format(ping_time)
                elif ping_time < 200:
                    evaluation += _(
                        "🐢 Poor latency ({:.1f} ms)\n").format(ping_time)
                else:
                    evaluation += _(
                        "❌ Very poor latency ({:.1f} ms)\n").format(ping_time)
            else:
                evaluation += _("❓ Latency unavailable\n")

            # Overall evaluation
            evaluation += _("\n--- OVERALL ASSESSMENT ---\n")

            if download_speed is not None and ping_time is not None:
                # Combined scoring
                speed_score = min(
                    download_speed / 50.0,
                    1.0)  # Normalize to 0-1
                ping_score = max(0, 1.0 - (ping_time / 200.0)
                                 )  # Normalize to 0-1

                overall_score = (speed_score + ping_score) / 2.0

                if overall_score > 0.8:
                    evaluation += _("🎯 EXCELLENT connection\n")
                elif overall_score > 0.6:
                    evaluation += _("👍 GOOD connection\n")
                elif overall_score > 0.4:
                    evaluation += _("👌 FAIR connection\n")
                elif overall_score > 0.2:
                    evaluation += _("👎 POOR connection\n")
                else:
                    evaluation += _("🚫 VERY POOR connection\n")

            elif download_speed is not None:
                # Only download available
                if download_speed > 20:
                    evaluation += _("📶 Connection appears good (based on download)\n")
                else:
                    evaluation += _("📶 Connection may be limited (based on download)\n")

            elif ping_time is not None:
                # Only ping available
                if ping_time < 100:
                    evaluation += _("📶 Connection appears responsive (based on ping)\n")
                else:
                    evaluation += _("📶 Connection may be slow (based on ping)\n")
            else:
                evaluation += _("❓ Cannot assess connection quality\n")

        except Exception as e:
            if self.debug:
                print(f"[DEBUG] Evaluation error: {e}")
            evaluation += _("❓ Quality assessment unavailable\n")

        return evaluation

    def update_progress(self, value, status):
        """Update progress and status (thread-safe)"""
        self._ui(self._do_update_progress, value, status)

    def _do_update_progress(self, value, status):
        self["progress"].setValue(value)
        self["status_label"].setText(status)

    def _format_results(self, download, upload, ping):
        """Format speed test results"""
        results = _("=== SPEED TEST RESULTS ===\n\n")
        results += _("Download Speed: %s\n") % (download if download else _("Failed"))
        results += _("Upload Speed: %s\n") % (upload if upload else _("Failed"))
        results += _("Latency: %s\n") % (ping if ping else _("Failed"))

        # Quality evaluation
        results += _("\n=== QUALITY ASSESSMENT ===\n")
        if download and isinstance(download, str) and 'Mbps' in download:
            try:
                download_value = float(download.split()[0])
                if download_value > 10:
                    results += _("Excellent download speed\n")
                elif download_value > 5:
                    results += _("Good download speed\n")
                else:
                    results += _("Poor download speed\n")
            except Exception as e:
                print(e)
                results += _("Unable to assess download quality\n")
        else:
            results += _("Unable to assess download quality\n")
        return results

    def show_results_success(self, results):
        """Show results (called from the worker thread)"""
        self._ui(self._do_show_results_success, results)

    def _do_show_results_success(self, results):
        self.is_testing = False
        self.update_buttons()
        self["results"].setText(results)
        self["status_label"].setText(_("Test completed - See results below"))

        try:
            def callback(result=None):
                pass

            self.session.openWithCallback(callback, MessageBox,
                                          _("Test completed!"),
                                          MessageBox.TYPE_INFO,
                                          timeout=4)
        except Exception as e:
            print(e)
            pass

    def show_error(self, message):
        """Show error (called from the worker thread)"""
        self._ui(self._do_show_error, message)

    def _do_show_error(self, message):
        self.is_testing = False
        self.update_buttons()
        self["status_label"].setText(_("Test failed"))

        def error_callback(result=None):
            pass

        self.session.openWithCallback(error_callback, MessageBox,
                                      message,
                                      MessageBox.TYPE_ERROR)

    def show_results(self):
        """Show/hide detailed results"""
        if self["results"].isVisible():
            self["results"].hide()
        else:
            self["results"].show()

    def close(self):
        """Close the screen; a running test stops by itself in a moment"""
        self.cancelled = True
        self.closed = True
        self.is_testing = False
        Screen.close(self)
