# -*- coding: utf-8 -*-

import subprocess
from twisted.internet import threads
from re import search, IGNORECASE, MULTILINE, findall

from Screens.Screen import Screen
from Components.ActionMap import ActionMap
from Components.Button import Button
from Components.ScrollLabel import ScrollLabel
from os.path import basename, realpath

from .tools import get_wifi_interfaces
from . import _
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


class WiFiDiagnostics(Screen):
    skin = scale_skin("""
    <screen position="center,center" size="800,700" title="WiFi Diagnostics">
        <widget name="diagnostics_output" position="10,58" size="773,560" font="Regular;18" />
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
        self["diagnostics_output"] = ScrollLabel()
        self["key_red"] = Button(_("Full Test"))
        self["key_green"] = Button(_("Quick Test"))
        self["key_yellow"] = Button(_("Clear"))
        self["key_blue"] = Button(_("Exit"))
        self["actions"] = ActionMap(
            ["ColorActions", "OkCancelActions", "DirectionActions"],
            {
                "red": lambda: self.run_diagnostics(full_test=True),
                "green": lambda: self.run_diagnostics(full_test=False),
                "yellow": self.clear_output,
                "blue": self.close,
                "cancel": self.close,
                "pageUp": self.pageUp,
                "pageDown": self.pageDown,
                "up": self.pageUp,
                "down": self.pageDown,
                "left": self.pageUp,
                "right": self.pageDown,
            }
        )
        self.setTitle(_("WiFi Diagnostics"))
        self.running = False
        self.closed = False
        self.onClose.append(self._on_close)
        # start after the screen is shown (it used to block the opening)
        # bound method: OpenATV exec()s non-methods in onLayoutFinish
        self.onLayoutFinish.append(self.run_quick_diagnostics)

    def _on_close(self):
        self.closed = True

    def run_quick_diagnostics(self):
        self.run_diagnostics(full_test=False)

    def pageUp(self):
        self["diagnostics_output"].pageUp()

    def pageDown(self):
        self["diagnostics_output"].pageDown()

    def run_diagnostics(self, full_test=True):
        """Run the checks in a thread, show the result when done"""
        if self.running:
            return
        self.running = True
        self["diagnostics_output"].setText(
            _("Running diagnostics, please wait..."))

        def done(result):
            self.running = False
            if not self.closed:
                self.display_results(result)

        def failed(failure):
            self.running = False
            if not self.closed:
                self.display_results(
                    _("Diagnostic error: {}").format(
                        failure.value))

        d = threads.deferToThread(self._collect, full_test)
        d.addCallback(done)
        d.addErrback(failed)

    def _collect(self, full_test=True):
        """Runs in a worker thread: returns the report lines"""
        diagnostics = [_("=== WiFi Diagnostics (System Commands Only) ===\n")]
        diagnostics.append(_("Test Type: {test_type}\n\n").format(test_type=_(
            'Full Comprehensive Test') if full_test else _('Quick System Check')))
        # LOG INIZIALE
        print("[WiFiDiagnostics] Starting diagnostics...")

        try:
            # 1. SYSTEM LEVEL CHECKS
            diagnostics.append(_("🔧 SYSTEM LEVEL DIAGNOSTICS\n"))
            diagnostics.append("=" * 50 + "\n")

            # Kernel modules
            print("[WiFiDiagnostics] Checking kernel modules...")
            kernel_modules = self.check_kernel_modules()
            diagnostics.extend(kernel_modules)
            for line in kernel_modules:
                print(f"[WiFiDiagnostics] {line.strip()}")

            # USB devices
            print("[WiFiDiagnostics] Checking USB devices...")
            usb_wifi = self.check_usb_wifi_devices()
            diagnostics.extend(usb_wifi)
            for line in usb_wifi:
                print(f"[WiFiDiagnostics] {line.strip()}")

            # System commands availability
            print("[WiFiDiagnostics] Checking system commands...")
            commands_check = self.check_system_commands()
            diagnostics.extend(commands_check)
            for line in commands_check:
                print(f"[WiFiDiagnostics] {line.strip()}")

            # 2. NETWORK INTERFACE CHECKS
            diagnostics.append("\n📡 NETWORK INTERFACE DIAGNOSTICS\n")
            diagnostics.append("=" * 50 + "\n")

            # Get WiFi interfaces using system commands
            print("[WiFiDiagnostics] Scanning for WiFi interfaces...")
            wifi_interfaces = get_wifi_interfaces()
            all_interfaces = self.get_all_interfaces()

            diagnostics.append(_("All Network Interfaces: {interfaces}\n").format(
                interfaces=', '.join(all_interfaces) if all_interfaces else _('None found')))
            diagnostics.append(_("Wireless Interfaces: {interfaces}\n\n").format(
                interfaces=', '.join(wifi_interfaces) if wifi_interfaces else _('None found')))

            print(f"[WiFiDiagnostics] Found interfaces: {wifi_interfaces}")

            if not wifi_interfaces:
                diagnostics.append(
                    _("❌ CRITICAL: No WiFi interfaces detected!\n"))
                solutions = self.suggest_solutions(no_interfaces=True)
                diagnostics.extend(solutions)
                for line in solutions:
                    print(f"[WiFiDiagnostics] {line.strip()}")
                return diagnostics

            # 3. PER-INTERFACE DETAILED TESTS
            for ifname in wifi_interfaces:
                print(f"[WiFiDiagnostics] Testing interface: {ifname}")
                diagnostics.append(
                    _("\n🔍 DETAILED ANALYSIS: {interface}\n").format(
                        interface=ifname))
                diagnostics.append("-" * 40 + "\n")

                # Interface status
                print("[WiFiDiagnostics] Checking interface status...")
                iface_status = self.check_interface_status(ifname)
                diagnostics.extend(iface_status)
                for line in iface_status:
                    print(f"[WiFiDiagnostics] {line.strip()}")

                # Driver info
                print("[WiFiDiagnostics] Checking driver info...")
                driver_info = self.check_driver_info(ifname)
                diagnostics.extend(driver_info)
                for line in driver_info:
                    print(f"[WiFiDiagnostics] {line.strip()}")

                # Basic wireless tests
                print("[WiFiDiagnostics] Running basic wireless tests...")
                basic_tests = self.run_basic_wireless_tests(ifname)
                diagnostics.extend(basic_tests)
                for line in basic_tests:
                    print(f"[WiFiDiagnostics] {line.strip()}")

                # Full comprehensive tests (only if requested)
                if full_test:
                    print("[WiFiDiagnostics] Running advanced tests...")
                    advanced_tests = self.run_advanced_tests(ifname)
                    diagnostics.extend(advanced_tests)
                    for line in advanced_tests:
                        print(f"[WiFiDiagnostics] {line.strip()}")

                # Performance tests
                print("[WiFiDiagnostics] Running performance tests...")
                perf_tests = self.run_performance_tests(ifname)
                diagnostics.extend(perf_tests)
                for line in perf_tests:
                    print(f"[WiFiDiagnostics] {line.strip()}")

            # 4. SUMMARY AND RECOMMENDATIONS
            diagnostics.append(_("\n💡 SUMMARY & RECOMMENDATIONS\n"))
            diagnostics.append("=" * 50 + "\n")
            summary = self.generate_summary(wifi_interfaces)
            diagnostics.extend(summary)
            for line in summary:
                print(f"[WiFiDiagnostics] {line.strip()}")

            print("[WiFiDiagnostics] Diagnostics completed successfully")

        except Exception as e:
            error_msg = _("\n❌ DIAGNOSTIC ERROR: {error}\n").format(
                error=str(e))
            diagnostics.append(error_msg)
            print(f"[WiFiDiagnostics] ERROR: {e}")

        return diagnostics

    def get_all_interfaces(self):
        """Get all network interfaces"""
        interfaces = []
        try:
            result = subprocess.run(['ip', 'link', 'show'],
                                    capture_output=True, text=True)
            for line in result.stdout.split('\n'):
                if ': ' in line and 'LOOPBACK' not in line:
                    parts = line.split(': ')
                    if len(parts) > 1:
                        ifname = parts[1].strip()
                        if ifname and ifname not in interfaces:
                            interfaces.append(ifname)
        except Exception as e:
            print(e)
            pass
        return interfaces

    def check_kernel_modules(self):
        """Check loaded WiFi kernel modules"""
        results = []
        try:
            output = subprocess.check_output(["lsmod"], text=True)
            # only module names of real WiFi drivers (the old check matched
            # any module containing "rt", "mt", "wl"...)
            pattern = (r"^((?:rtl|r8\d{3}|8\d{3}|88x2|rtw|ath|carl9170|brcm|"
                       r"iwl|mt7|rt2|rt3|rt5|rt7|zd1211|mac80211|cfg80211|"
                       r"wlan|bcmdhd|dhd|aic|ssv|esp)\w*)\s+\d")
            wifi_modules = findall(pattern, output, MULTILINE | IGNORECASE)
            if wifi_modules:
                results.append(
                    _("✅ Loaded WiFi modules: {modules}\n").format(
                        modules=', '.join(
                            set(wifi_modules))))
            else:
                results.append(_("⚠️  No WiFi kernel modules detected\n"))
        except Exception as e:
            results.append(
                _("❌ Kernel module check failed: {error}\n").format(
                    error=e))
        return results

    def check_usb_wifi_devices(self):
        """Check for USB WiFi devices"""
        results = []
        try:
            output = subprocess.check_output(["lsusb"], text=True)
            wifi_adapters = []
            for vendor in [
                "Realtek",
                "Ralink",
                "Atheros",
                "Broadcom",
                "Intel",
                    "MediaTek"]:
                if vendor.lower() in output.lower():
                    matches = findall(rf".*{vendor}.*", output, IGNORECASE)
                    wifi_adapters.extend(matches)

            if wifi_adapters:
                results.append(_("✅ USB WiFi adapters detected:\n"))
                for adapter in set(wifi_adapters):
                    results.append(
                        _("   - {adapter}\n").format(adapter=adapter.strip()))
            else:
                results.append(_("ℹ️  No USB WiFi adapters found\n"))
        except Exception as e:
            results.append(
                _("❌ USB device check failed: {error}\n").format(
                    error=e))
        return results

    def check_system_commands(self):
        """Check availability of essential commands"""
        results = []
        essential_cmds = ["iwconfig", "iw", "ip", "ifconfig", "wpa_supplicant"]
        available_cmds = []
        missing_cmds = []
        for cmd in essential_cmds:
            try:
                subprocess.run([cmd, "--help"], capture_output=True, timeout=2)
                available_cmds.append(cmd)
            except Exception as e:
                print(e)
                missing_cmds.append(cmd)

        if available_cmds:
            results.append(
                _("✅ Available commands: {commands}\n").format(
                    commands=', '.join(available_cmds)))
        if missing_cmds:
            results.append(
                _("⚠️  Missing commands: {commands}\n").format(
                    commands=', '.join(missing_cmds)))

        return results

    def check_interface_status(self, ifname):
        """Check interface status using ip command"""
        results = []
        try:
            # Check if interface exists and status
            output = subprocess.check_output(
                ["ip", "link", "show", ifname], text=True)
            if "state UP" in output:
                results.append(
                    _("✅ Interface {interface}: UP and active\n").format(
                        interface=ifname))
            elif "state DOWN" in output:
                results.append(
                    _("⚠️  Interface {interface}: DOWN (needs activation)\n").format(
                        interface=ifname))
            else:
                results.append(
                    _("❌ Interface {interface}: UNKNOWN STATE\n").format(
                        interface=ifname))

            # Get MAC address
            mac_match = search(
                r"link/ether (([0-9A-Fa-f]{2}[:-]){5}([0-9A-Fa-f]{2}))", output)
            if mac_match:
                results.append(
                    _("   MAC Address: {mac}\n").format(
                        mac=mac_match.group(1)))

        except subprocess.CalledProcessError:
            results.append(
                _("❌ Interface {interface}: NOT FOUND\n").format(
                    interface=ifname))
        except Exception as e:
            results.append(
                _("❌ Interface check failed: {error}\n").format(
                    error=e))

        return results

    def check_driver_info(self, ifname):
        """Get driver information for interface"""
        results = []
        try:
            driver_path = f"/sys/class/net/{ifname}/device/driver"
            # Check if the folder exists
            if subprocess.run(["test", "-d", driver_path],
                              capture_output=True).returncode == 0:
                # Read the symbolic link to get the real driver name
                driver_link = realpath(driver_path)
                driver_name = basename(driver_link)
                results.append(
                    _("   Driver: {driver}\n").format(
                        driver=driver_name))
            else:
                results.append(_("   Driver: Unknown\n"))
        except Exception as e:
            results.append(
                _("   Driver check failed: {error}\n").format(
                    error=str(e)))
        return results

    def run_basic_wireless_tests(self, ifname):
        """Run basic wireless functionality tests using system commands only"""
        print(f"[WiFiDiagnostics] Running basic tests for {ifname}")
        results = []

        # Test ESSID con iwconfig
        try:
            print(f"[WiFiDiagnostics] Running iwconfig for {ifname}...")
            output = subprocess.check_output(
                ["iwconfig", ifname], text=True, timeout=5)
            # Prime 200 caratteri
            print(f"[WiFiDiagnostics] iwconfig output: {output[:200]}...")

            essid_match = search(r'ESSID:"([^"]*)"', output)
            if essid_match:
                results.append(
                    _("📶 ESSID: {essid}\n").format(
                        essid=essid_match.group(1)))
                print(f"[WiFiDiagnostics] ESSID found: {essid_match.group(1)}")
            else:
                results.append(_("📶 ESSID: Not connected\n"))
                print("[WiFiDiagnostics] No ESSID found")
        except Exception as e:
            error_msg = _("❌ ESSID check: {error}\n").format(error=e)
            results.append(error_msg)
            print(f"[WiFiDiagnostics] {error_msg}")

        # Test signal quality con iwconfig
        try:
            output = subprocess.check_output(
                ["iwconfig", ifname], text=True, timeout=5)
            quality_match = search(r'Link Quality=(\d+)/(\d+)', output)
            signal_match = search(r'Signal level=(-?\d+)', output)

            if quality_match:
                current = int(quality_match.group(1))
                max_val = int(quality_match.group(2))
                quality_percent = int((current / max_val) * 100)
                signal_dbm = signal_match.group(
                    1) if signal_match else _("N/A")
                results.append(
                    _("📊 Signal: {quality}% quality, {signal} dBm\n").format(
                        quality=quality_percent, signal=signal_dbm))
            else:
                results.append(_("📊 Signal: No quality data available\n"))
        except Exception as e:
            results.append(_("❌ Signal check: {error}\n").format(error=e))

        # Test operation mode con iwconfig
        try:
            output = subprocess.check_output(
                ["iwconfig", ifname], text=True, timeout=5)
            mode_match = search(r'Mode:(\w+)', output)
            if mode_match:
                results.append(
                    _("🔧 Mode: {mode}\n").format(
                        mode=mode_match.group(1)))
            else:
                results.append(_("🔧 Mode: Unknown\n"))
        except Exception as e:
            results.append(_("❌ Mode check: {error}\n").format(error=e))

        return results

    def run_advanced_tests(self, ifname):
        """Run advanced comprehensive tests"""
        results = []
        results.append(_("\n   🔬 ADVANCED TESTS:\n"))

        # one iwconfig call, values parsed here (the old "grep BitRate"
        # never matched: iwconfig prints "Bit Rate")
        try:
            output = subprocess.run(["iwconfig", ifname], capture_output=True,
                                    text=True, timeout=5).stdout
        except Exception as e:
            output = ""
            results.append(_("   ❌ iwconfig: {error}\n").format(error=e))
        advanced_tests = [
            (_("Frequency/Channel"), r"Frequency[:=]\s*([0-9.]+\s*GHz)"),
            (_("Bitrate"), r"Bit Rate[:=]\s*([0-9.]+\s*\S+)"),
            (_("Encryption"), r"Encryption key:\s*(\S+)"),
            (_("Access Point"), r"Access Point:\s*(\S+)"),
            (_("TX Power"), r"Tx-Power[:=]\s*(\S+\s*dBm)"),
            (_("Power Management"), r"Power Management[:=]\s*(\S+)"),
        ]
        for test_name, pattern in advanced_tests:
            match = search(pattern, output)
            if match:
                results.append(_("   ✅ {test}: {output}\n").format(
                    test=test_name, output=match.group(1)))
            else:
                results.append(_("   ⚠️  {test}: No data\n").format(
                    test=test_name))

        return results

    def run_performance_tests(self, ifname):
        """Run performance tests using system commands"""
        results = []
        results.append(_("\n   🚀 PERFORMANCE TESTS:\n"))

        # Test scan capability con iwlist
        try:
            output = subprocess.check_output(["iwlist", ifname, "scan"],
                                             text=True, timeout=10,
                                             stderr=subprocess.STDOUT)
            cell_count = output.count("Cell ")
            results.append(
                _("   📡 Scan: Found {count} networks\n").format(
                    count=cell_count))
        except subprocess.CalledProcessError as e:
            if "Device or resource busy" in e.output:
                results.append(
                    _("   ⚠️  Scan: Interface busy (connected to network)\n"))
            else:
                results.append(
                    _("   ❌ Scan test: {error}\n").format(
                        error=e.output.strip()))
        except Exception as e:
            results.append(_("   ❌ Scan test: {error}\n").format(error=e))

        # Test connectivity
        try:
            from Components.Network import iNetwork
            ip = iNetwork.getAdapterAttribute(ifname, "ip")
            if ip and ip != [0, 0, 0, 0]:
                results.append(
                    _("   🌐 Connectivity: IP {ip} - ONLINE\n").format(ip='.'.join(map(str, ip))))
            else:
                results.append(
                    _("   🌐 Connectivity: No IP address - OFFLINE\n"))
        except Exception as e:
            print(e)
            results.append(_("   🌐 Connectivity: Unknown status\n"))

        return results

    def suggest_solutions(self, no_interfaces=False):
        """Provide solution suggestions based on problems found"""
        suggestions = []
        suggestions.append(_("\n🔧 POSSIBLE SOLUTIONS:\n"))

        if no_interfaces:
            suggestions.append(
                _("1. Check if WiFi adapter is properly connected\n"))
            suggestions.append(
                _("2. Verify WiFi adapter is supported by your receiver\n"))
            suggestions.append(
                _("3. Try different USB port for USB WiFi adapters\n"))
            suggestions.append(_("4. Check if WiFi drivers are installed\n"))
            suggestions.append(_("5. Restart the receiver and try again\n"))

        else:
            suggestions.append(_("✅ All systems operational\n"))
            suggestions.append(_("💡 Tips:\n"))
            suggestions.append(
                _("   • Monitor signal strength for best performance\n"))
            suggestions.append(_("   • Keep drivers updated\n"))
            suggestions.append(_("   • Use 5GHz band for less interference\n"))

        return suggestions

    def generate_summary(self, wifi_interfaces):
        """Generate diagnostic summary"""
        summary = []
        if wifi_interfaces:
            summary.append(
                _("✅ SYSTEM STATUS: WiFi hardware detected and functional\n"))
            summary.append(
                _("🔧 METHOD: Using system commands (no root required)\n"))
            summary.append(_("💡 All basic diagnostics available\n"))
        else:
            summary.append(_("❌ SYSTEM STATUS: No WiFi interfaces detected\n"))
            summary.append(_("🚨 Check hardware connection and drivers\n"))
        return summary

    def display_results(self, results):
        if isinstance(results, list):
            self["diagnostics_output"].setText("".join(results))
        else:
            self["diagnostics_output"].setText(results)

    def clear_output(self):
        self["diagnostics_output"].setText("")

    def test_wireless_protocol(self, wireless):
        try:
            protocol = wireless.getWirelessName()
            return True, protocol
        except Exception as e:
            return False, str(e)

    def test_essid(self, wireless):
        try:
            essid = wireless.getEssid()
            return True, essid if essid else "Not connected"
        except Exception as e:
            return False, str(e)

    def test_ap_address(self, wireless):
        try:
            ap_addr = wireless.getAPaddr()
            return True, ap_addr
        except Exception as e:
            return False, str(e)

    def test_operation_mode(self, wireless):
        try:
            mode = wireless.getMode()
            return True, mode
        except Exception as e:
            return False, str(e)

    def test_frequency(self, wireless):
        try:
            freq = wireless.getFrequency()
            return True, freq
        except Exception as e:
            return False, str(e)

    def test_bitrate(self, wireless):
        try:
            bitrate = wireless.getBitrate()
            return True, bitrate
        except Exception as e:
            return False, str(e)

    def test_signal_quality(self, wireless):
        try:
            quality = wireless.getQualityAvg()
            if quality:
                return True, "Quality: {}%, Signal: {} dBm".format(
                    quality.quality,
                    quality.siglevel
                )
            return False, "No quality data"
        except Exception as e:
            return False, str(e)

    def test_tx_power(self, wireless):
        try:
            txpower = wireless.getTXPower()
            return True, txpower
        except Exception as e:
            return False, str(e)

    def test_scan_capability(self, wireless):
        try:
            scan_results = wireless.scan()
            return True, f"Found {len(scan_results)} networks"
        except Exception as e:
            return False, str(e)

    def test_iwconfig_compatibility(self, wireless):
        """Test compatibilità funzioni iwconfig"""
        try:
            from .iwconfig import getBitrate, getTXPower, getEncryption
            bitrate_info = getBitrate(wireless)
            txpower_info = getTXPower(wireless)
            encryption_info = getEncryption(wireless)

            result = "iwconfig functions available - "
            if bitrate_info:
                result += "Bitrate OK "
            if txpower_info:
                result += "TXPower OK "
            if encryption_info:
                result += "Encryption OK"

            return True, result.strip()
        except Exception as e:
            return False, f"iwconfig error: {str(e)}"
