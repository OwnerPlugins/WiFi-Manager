#!/usr/bin/env python
# -*- coding: utf-8 -*-

import time
import subprocess
import socket
from json import loads
from re import search
from urllib.request import urlopen
from urllib.error import URLError, HTTPError

from .. import _
from . import speed_engine
from . import speedtest


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


class Enigma2Speedtest:
    def __init__(self, stop=None):
        self.stop = stop    # callable: True when the test must stop
        self.results = {
            'download': 0,
            'upload': 0,
            'ping': 0,
            'server': {},
            'client': {},
            'timestamp': '',
            'sponsor': '',
            'host': '',
            'distance': 0,
            'ip_address': ''
        }

    def _check_internet_connection(self):
        """Check if there is an internet connection"""
        try:
            # Try connecting to Google DNS
            socket.create_connection(("8.8.8.8", 53), timeout=5)
            return True
        except OSError:
            return False

    def get_client_info(self):
        """Get client information"""
        try:
            if not self._check_internet_connection():
                print("No internet connection in get_client_info")
                return False
            try:
                # Get public IP
                ip_response = urlopen('http://ipinfo.io/json', timeout=10)
                ip_data = loads(ip_response.read().decode())
                self.results['client'] = {
                    'ip': ip_data.get('ip', _('Unknown')),
                    'city': ip_data.get('city', _('Unknown')),
                    'region': ip_data.get('region', _('Unknown')),
                    'country': ip_data.get('country', _('Unknown')),
                    'isp': ip_data.get('org', _('Unknown'))
                }
                print("Client info obtained successfully")
                return True
            except (URLError, HTTPError) as e:
                print(f" ipinfo.io failed: {e}")
                try:
                    ip_response = urlopen('http://api.ipify.org', timeout=5)
                    self.results['client'] = {
                        'ip': ip_response.read().decode().strip()}
                    print("IP obtained via fallback")
                    return True
                except Exception as e2:
                    print(f"Fallback IP also failed: {e2}")
                    return False
        except Exception as e:
            print(f"Client info error: {e}")
            self.results['client'] = {'ip': _('Unknown')}
            return False

    def test_specific_ping(self, host):
        """Test ping to a specific host"""
        try:
            print(f"Pinging {host}...")
            result = subprocess.run(
                ["ping", "-c", "2", "-W", "3", host],
                capture_output=True, text=True, timeout=10
            )

            if result.returncode == 0:
                for line in result.stdout.split('\n'):
                    if 'min/avg/max' in line or 'rtt min/avg/max' in line:
                        # Robust pattern for different formats
                        stats_match = search(
                            r'([0-9.]+)/([0-9.]+)/([0-9.]+)', line)
                        if stats_match:
                            ping_time = float(stats_match.group(2))
                            print(
                                _("Ping {host}: {time} ms").format(
                                    host=host, time=ping_time))
                            return ping_time

                # Fallback if min/avg/max line not found
                stats_match = search(
                    r'([0-9.]+)/([0-9.]+)/([0-9.]+)', result.stdout)
                if stats_match:
                    ping_time = float(stats_match.group(2))
                    print(
                        _("Ping {host} (fallback): {time} ms").format(
                            host=host, time=ping_time))
                    return ping_time

            print(
                _("Ping failed for {host} (returncode: {code})").format(
                    host=host, code=result.returncode))
            print(_("Output: {output}...").format(output=result.stdout[:200]))
            return 999

        except subprocess.TimeoutExpired:
            print(_("Ping timeout for {host}").format(host=host))
            return 999
        except Exception as e:
            print(
                _("Ping error for {host}: {error}").format(
                    host=host, error=e))
            return 999

    def test_ping(self):
        """Improved ping test with multiple servers"""
        try:
            print("Starting ping test...")
            ping_hosts = [
                ("Google DNS", "8.8.8.8"),
                ("Cloudflare", "1.1.1.1"),
                ("OpenDNS", "208.67.222.222")
            ]

            ping_results = []
            total_ping = 0
            valid_pings = 0

            for name, host in ping_hosts:
                ping_time = self.test_specific_ping(host)
                if ping_time < 999:
                    ping_results.append(
                        _("{}: {:.1f} ms").format(
                            name, ping_time))
                    total_ping += ping_time
                    valid_pings += 1
                else:
                    ping_results.append(_("{}: Failed").format(name))

            if valid_pings > 0:
                avg_ping = total_ping / valid_pings
                self.results['ping_details'] = ping_results
                self.results['ping'] = avg_ping
                print(
                    _("Ping test completed: {avg:.1f} ms average ({success}/{total} successful)").format(
                        avg=avg_ping,
                        success=valid_pings,
                        total=len(ping_hosts)))
                return avg_ping
            else:
                self.results['ping_details'] = [_("All ping tests failed")]
                self.results['ping'] = 999
                print(_("All ping tests failed"))
                return 999

        except Exception as e:
            print(_("Ping test error: {error}").format(error=e))
            self.results['ping'] = 999
            self.results['ping_details'] = [
                _("Ping test error: {error}").format(error=e)]
            return 999

    def test_download_simple(self):
        """Download speed: parallel connections, timed measurement"""
        try:
            if not self._check_internet_connection():
                print("No internet connection for download test")
                return 0

            res, failed = speed_engine.first_working(
                'download', servers=speedtest.ordered_servers(self.stop),
                stop=self.stop)
            details = []
            for r in failed + ([res] if res else []):
                details.append({
                    'server': r.server,
                    'speed_mbps': r.mbps or 0,
                    'time_seconds': r.seconds,
                    'data_mb': r.megabytes,
                    'error': r.error,
                })
            self.results['download_details'] = details

            if res is None:
                print("All download tests failed")
                return 0

            self.results['download'] = res.mbps * 1000000  # bps
            print("Download: {}".format(res))
            return self.results['download']

        except Exception as e:
            print("Download test error: {}".format(e))
            return 0

    def test_upload(self):
        """Real upload measurement (data is sent to the server)"""
        try:
            res, failed = speed_engine.first_working(
                'upload', servers=speedtest.ordered_servers(self.stop),
                stop=self.stop)
            if res is None:
                self.results['upload_error'] = "; ".join(
                    str(f) for f in failed[:3])
                print("Upload test failed: {}".format(
                    self.results['upload_error']))
                return 0
            self.results['upload'] = res.mbps * 1000000
            self.results['upload_server'] = res.server
            print("Upload: {}".format(res))
            return self.results['upload']
        except Exception as e:
            print("Upload test error: {}".format(e))
            return 0

    def get_best_server(self):
        """Trova il server migliore basato sul ping"""
        try:
            servers = [
                {
                    'name': 'Google DNS',
                    'url': 'http://8.8.8.8',
                    'sponsor': 'Google',
                    'host': '8.8.8.8',
                    'country': 'Global'
                },
                {
                    'name': 'Cloudflare DNS',
                    'url': 'http://1.1.1.1',
                    'sponsor': 'Cloudflare',
                    'host': '1.1.1.1',
                    'country': 'Global'
                },
                {
                    'name': 'OpenDNS',
                    'url': 'http://208.67.222.222',
                    'sponsor': 'OpenDNS',
                    'host': '208.67.222.222',
                    'country': 'Global'
                }
            ]

            best_server = None
            best_ping = 9999

            for server in servers:
                ping_time = self.test_specific_ping(server['host'])
                if ping_time < best_ping and ping_time < 999:
                    best_ping = ping_time
                    best_server = server
                    best_server['ping'] = ping_time

            if best_server:
                self.results['server'] = best_server
                self.results['sponsor'] = best_server.get(
                    'sponsor', _('Unknown'))
                self.results['host'] = best_server.get('host', _('Unknown'))
                print(f"Best server: {best_server['name']} ({best_ping} ms)")
                return best_server

            print("No suitable server found")
            return None

        except Exception as e:
            print(f"Server selection error: {e}")
            return None

    def run_test(self, callback=None):
        """Run all tests"""
        try:
            print("Starting detailed speed test...")
            self.results['timestamp'] = time.strftime('%Y-%m-%d %H:%M:%S')

            # Initial internet connection test
            if callback:
                callback('checking_connection')

            if not self._check_internet_connection():
                error_msg = _("No internet connection detected")
                print(error_msg)
                if callback:
                    callback('error', error_msg)
                return None

            # Client information
            if callback:
                callback('client_info_start')
            self.get_client_info()
            if callback:
                callback('client_info_complete')

            # Ping test
            if callback:
                callback('ping_start')
            self.test_ping()
            if callback:
                callback('ping_complete')

            # Find best server
            if callback:
                callback('server_selection_start')

            server = self.get_best_server()
            if callback:
                callback(f'server_found {str(server)}')

            # Download test
            if callback:
                callback('download_start')
            download_result = self.test_download_simple()
            if callback:
                callback('download_complete')

            # Upload test (stima)
            if callback:
                callback('upload_start')
            self.test_upload()
            if callback:
                callback('upload_complete')

            # Verifica che almeno il ping sia riuscito
            if self.results['ping'] == 999 and download_result == 0:
                print("Test failed completely")
                return None

            print("All tests completed successfully")
            return self.results

        except Exception as e:
            error_msg = _("Speedtest failed: {}").format(str(e))
            print(error_msg)
            if callback:
                callback('error', error_msg)
            return None

    def format_results(self):
        """Format the results for display"""
        # Check if the test was successful
        has_ping = self.results.get(
            'ping', 0) > 0 and self.results.get(
            'ping', 0) < 999
        has_download = self.results.get('download', 0) > 0

        if not has_ping and not has_download:
            return _(
                "Speedtest failed - No internet connection or all tests failed")

        download_mbps = self.results['download'] / \
            1000000 if has_download else 0
        upload_mbps = self.results['upload'] / \
            1000000 if self.results['upload'] > 0 else 0
        ping_ms = self.results.get('ping', 0) if has_ping else 999

        result_text = _(
            "📊 ENIGMA2 DETAILED SPEEDTEST\n"
            "============================\n"
            "🕐 Timestamp: {timestamp}\n\n"
        ).format(timestamp=self.results['timestamp'])

        # Client Information
        if self.results.get('client'):
            result_text += _("👤 CLIENT INFORMATION:\n")
            result_text += _("IP: {ip}\n").format(
                ip=self.results['client'].get('ip', _('Unknown')))
            if 'city' in self.results['client']:
                result_text += _("Location: {city}, {country}\n").format(
                    city=self.results['client'].get('city', _('Unknown')),
                    country=self.results['client'].get('country', _('Unknown'))
                )
            if 'isp' in self.results['client']:
                result_text += _("ISP: {isp}\n").format(
                    isp=self.results['client'].get('isp', _('Unknown')))
            result_text += "\n"

        # Server Information
        if self.results.get('server'):
            result_text += _("🏢 SERVER INFORMATION:\n")
            result_text += _("Name: {name}\n").format(
                name=self.results['server'].get('name', _('Unknown')))
            result_text += _("Sponsor: {sponsor}\n").format(
                sponsor=self.results['server'].get('sponsor', _('Unknown')))
            result_text += _("Host: {host}\n\n").format(
                host=self.results['server'].get('host', _('Unknown')))

        # Main Results
        result_text += _("📈 TEST RESULTS:\n")
        if has_ping:
            result_text += _("Ping: {:.1f} ms\n").format(ping_ms)
        else:
            result_text += _("Ping: Failed\n")

        if has_download:
            result_text += _("Download: {:.2f} Mbps\n").format(download_mbps)
        else:
            result_text += _("Download: Failed\n")

        if self.results['upload'] > 0:
            result_text += _("Upload: {:.2f} Mbps\n").format(upload_mbps)
        else:
            result_text += _("Upload: Not available\n")
            if self.results.get('upload_error'):
                result_text += "({})\n".format(self.results['upload_error'])

        # Additional Details
        if 'ping_details' in self.results:
            result_text += _("\n📡 PING DETAILS:\n")
            for ping_detail in self.results['ping_details']:
                result_text += f"{ping_detail}\n"

        if 'download_details' in self.results and has_download:
            result_text += _("\n⬇️ DOWNLOAD DETAILS:\n")
            for detail in self.results['download_details']:
                if detail.get('error'):
                    result_text += "{}: {}\n".format(
                        detail['server'], detail['error'])
                    continue
                result_text += _("{server}: {speed:.2f} Mbps ({data:.1f} MB in {time:.1f}s)\n").format(
                    server=detail['server'],
                    speed=detail['speed_mbps'],
                    data=detail['data_mb'],
                    time=detail['time_seconds']
                )

        # Quality Assessment
        result_text += _("\n📊 QUALITY ASSESSMENT:\n")
        if has_ping:
            if ping_ms < 50:
                result_text += _("✅ Excellent latency\n")
            elif ping_ms < 100:
                result_text += _("⚠️ Good latency\n")
            elif ping_ms < 200:
                result_text += _("⚠️ Average latency\n")
            else:
                result_text += _("❌ Poor latency\n")
        else:
            result_text += _("❌ Latency test failed\n")

        if has_download:
            if download_mbps > 50:
                result_text += _("✅ Excellent download speed\n")
            elif download_mbps > 20:
                result_text += _("⚠️ Good download speed\n")
            elif download_mbps > 5:
                result_text += _("⚠️ Average download speed\n")
            else:
                result_text += _("❌ Poor download speed\n")
        else:
            result_text += _("❌ Download test failed\n")

        return result_text
