# -*- coding: utf-8 -*-

import time
import subprocess
from re import search
from json import loads
from urllib.request import urlopen

from .. import _
from . import speed_engine

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


_ORDER = {'time': 0, 'servers': None}


def ordered_servers(stop=None):
    """Servers sorted by ping (closest LibreSpeed first), cached 10 min"""
    if _ORDER['servers'] is None or time.time() - _ORDER['time'] > 600:
        _ORDER['servers'], _pings = speed_engine.servers_by_ping(stop)
        _ORDER['time'] = time.time()
    return _ORDER['servers']


def _fmt_failed(failed):
    if not failed:
        return _("no server")
    text = "; ".join(str(f) for f in failed[:3])
    if len(failed) > 3:
        text += _(" (+{} more)").format(len(failed) - 3)
    return text


def test_download_speed(interface=None, timeout=10, stop=None, progress=None):
    """Download speed: parallel connections, 8 s measurement.

    Returns a string like "185.3 Mbps (Cloudflare, 4 conn.)"
    """
    try:
        res, failed = speed_engine.first_working(
            'download', servers=ordered_servers(stop), stop=stop, progress=progress)
        if res is None:
            return _("All download servers failed: {}").format(
                _fmt_failed(failed))
        return _("{speed} ({server}, {streams} conn.)").format(
            speed=speed_engine.format_mbps(res.mbps), server=res.server,
            streams=res.streams)
    except Exception as e:
        return _("Error: {error}").format(error=str(e))


def test_upload_speed(interface=None, timeout=10, stop=None, progress=None):
    """Real upload speed (data is sent to the server, nothing estimated)"""
    try:
        res, failed = speed_engine.first_working(
            'upload', servers=ordered_servers(stop), stop=stop, progress=progress)
        if res is None:
            return _("Upload test failed: {error}").format(
                error=_fmt_failed(failed))
        return _("{speed} ({server}, {streams} conn.)").format(
            speed=speed_engine.format_mbps(res.mbps), server=res.server,
            streams=res.streams)
    except Exception as e:
        return _("Upload test failed: {error}").format(error=str(e))


def test_ping(host="8.8.8.8", count=3):
    """Test latency/ping using the Enigma2Speedtest method"""
    try:
        result = subprocess.run(
            ["ping", "-c", str(count), "-W", "3", host],
            capture_output=True, text=True, timeout=10
        )

        if result.returncode == 0:
            for line in result.stdout.split('\n'):
                if 'min/avg/max' in line or 'rtt min/avg/max' in line:
                    stats_match = search(
                        r'([0-9.]+)/([0-9.]+)/([0-9.]+)', line)
                    if stats_match:
                        ping_time = float(stats_match.group(2))
                        return "{:.1f} ms".format(ping_time)

            # Fallback parsing
            stats_match = search(
                r'([0-9.]+)/([0-9.]+)/([0-9.]+)',
                result.stdout)
            if stats_match:
                ping_time = float(stats_match.group(2))
                return "{:.1f} ms".format(ping_time)

        return _("Ping failed")

    except subprocess.TimeoutExpired:
        return _("Timeout")
    except Exception as e:
        return _("Error: {}").format(str(e))


def extended_ping_test():
    """Extended ping test to multiple hosts"""
    hosts = [
        (_("Google DNS"), "8.8.8.8"),
        (_("Cloudflare"), "1.1.1.1"),
        (_("OpenDNS"), "208.67.222.222")
    ]

    results = []
    for name, host in hosts:
        ping_result = test_ping(host, 2)
        results.append(
            _("{name} ({host}): {ping}").format(
                name=name,
                host=host,
                ping=ping_result))

    return "\n".join(results)


def get_public_ip_info():
    """Get public IP information"""
    try:
        response = urlopen('http://ipinfo.io/json', timeout=10)
        data = loads(response.read().decode())
        return data
    except Exception as e:
        print(e)
        return None


def get_network_interfaces():
    """Get network interface information"""
    try:
        result = subprocess.run(['ip', 'addr', 'show'],
                                capture_output=True, text=True)
        interfaces = []
        current_interface = None

        for line in result.stdout.split('\n'):
            if line and not line.startswith(' '):
                current_interface = line.split()[1].rstrip(':')
                interfaces.append(current_interface)

        return interfaces
    except Exception as e:
        print(e)
        return []


def multi_server_download_test(interface=None, stop=None, progress=None,
                               duration=5.0):
    """Download speed from every server, plus the best one"""
    servers = speed_engine.SERVERS[:4] + [
        s for s in speed_engine.SERVERS if s['sponsor'] == 'OVH']
    lines = []
    best = None
    for i, server in enumerate(servers):
        if stop and stop():
            break

        def part(fraction, i=i):
            if progress:
                progress((i + fraction) / len(servers))

        res = speed_engine.measure_download(server, duration=duration,
                                            stop=stop, progress=part)
        lines.append(str(res))
        if res.ok and (best is None or res.mbps > best.mbps):
            best = res
    if best is not None:
        lines.append(_("Best: {speed} ({server})").format(
            speed=speed_engine.format_mbps(best.mbps), server=best.server))
    else:
        lines.append(_("All download servers failed"))
    return "\n".join(lines)


def multi_server_upload_test(interface=None, stop=None, progress=None):
    """Upload test on the first server that answers"""
    upload_result = test_upload_speed(interface, stop=stop, progress=progress)
    return _("Upload test: {result}").format(result=upload_result)


def connection_stability_test(interface=None, duration=5):
    """Connection stability test with timeout"""
    try:
        start_time = time.time()
        packets_sent = 0
        packets_lost = 0
        max_packets = 5

        while time.time() - start_time < duration and packets_sent < max_packets:
            try:
                result = subprocess.run(['ping',
                                         '-c',
                                         '1',
                                         '-W',
                                         '2',
                                         '8.8.8.8'],
                                        capture_output=True,
                                        text=True,
                                        timeout=5)
                packets_sent += 1
                if result.returncode != 0:
                    packets_lost += 1
                time.sleep(1)
            except subprocess.TimeoutExpired:
                packets_lost += 1
                packets_sent += 1
                continue

        if packets_sent > 0:
            loss_percentage = (packets_lost / packets_sent) * 100
            stability = _("Stable") if loss_percentage < 10 else _("Unstable")
            return _("Packets: {sent}, Lost: {lost} ({percentage:.1f}%) - {stability}").format(
                sent=packets_sent, lost=packets_lost, percentage=loss_percentage, stability=stability)
        else:
            return _("No packets sent")

    except Exception as e:
        return _("Stability test error: {error}").format(error=str(e))


def format_speed_result(speed_value):
    """Format the speed result in a readable way"""
    if isinstance(speed_value, (int, float)):
        if speed_value >= 1000:
            return f"{speed_value / 1000:.2f} Gbps"
        else:
            return f"{speed_value:.2f} Mbps"
    return speed_value


def test_connectivity():
    """Basic connectivity test"""
    return test_ping()


def quick_speed_test(interface=None):
    """Quick speed test"""
    download = test_download_speed(interface, timeout=15)
    upload = test_upload_speed(interface, timeout=15)
    ping = test_ping()

    return {
        'download': download,
        'upload': upload,
        'ping': ping
    }
