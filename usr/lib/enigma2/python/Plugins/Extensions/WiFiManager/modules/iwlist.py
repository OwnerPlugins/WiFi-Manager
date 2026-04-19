#!/usr/bin/env python
# -*- coding: utf-8 -*-

from __future__ import division
from __future__ import print_function

import errno
import io
import sys

from Screens.Screen import Screen
from Screens.MessageBox import MessageBox
from Components.ActionMap import ActionMap
from Components.Label import Label
from Components.MenuList import MenuList
from Components.ScrollLabel import ScrollLabel

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

try:
    from .iwlibs import Wireless, Iwrange, getWNICnames, getNICnames, KILO, MEGA, ifname
    from .iwlist import get_matching_command
    from . import flags
except ImportError as e:
    print(f"Error importing pythonwifi: {e}")


class IWListTools(Screen):
    skin = """
    <screen position="center,center" size="700,500" title="Advanced WiFi Tools">
        <widget name="menu" position="10,10" size="680,300" scrollbarMode="showOnDemand" />
        <widget name="description" position="10,320" size="680,60" font="Regular;18" />
        <widget name="output" position="10,390" size="680,100" font="Regular;16" />
    </screen>
    """

    def __init__(self, session):
        Screen.__init__(self, session)
        self.session = session
        self.menu_entries = [
            (_("Advanced Scan"), "scanning", _("Detailed network scanning")),
            (_("Channel Info"), "channel", _("Available frequencies/channels")),
            (_("Bitrate Info"), "bitrate", _("Supported bit rates")),
            (_("Encryption Info"), "encryption", _("Encryption keys and security")),
            (_("Power Management"), "power", _("Power management settings")),
            (_("Retry Limits"), "retry", _("Retry limits and lifetime")),
            (_("Access Points"), "ap", _("List of access points/peers")),
        ]
        self["menu"] = MenuList(self.menu_entries)
        self["description"] = Label(self.menu_entries[0][2])
        self["output"] = Label(_("Select a tool to view detailed information"))
        self["actions"] = ActionMap(
            ["ColorActions", "OkCancelActions", "DirectionActions"],
            {
                "red": self.refresh_info,
                "green": self.close,
                "cancel": self.close,
                "pageUp": self.pageUp,
                "pageDown": self.pageDown,
                "up": self.pageUp,
                "down": self.pageDown,
                "left": self.pageUp,
                "right": self.pageDown,
            }
        )
        self.setTitle(_("Advanced WiFi Tools"))

    def up(self):
        self["menu"].up()
        self.update_description()

    def down(self):
        self["menu"].down()
        self.update_description()

    def update_description(self):
        current = self["menu"].getCurrent()
        if current:
            self["description"].setText(current[2])

    def run_tool(self):
        selection = self["menu"].getCurrent()
        if selection:
            tool_name = selection[1]

            try:
                ifnames = getWNICnames()
                if not ifnames:
                    self.session.open(
                        MessageBox,
                        _("No WiFi interfaces found"),
                        MessageBox.TYPE_ERROR)
                    return

                ifname = ifnames[0]
                wifi_obj = Wireless(ifname)

                # Execute the selected iwlist tool
                tool_function = get_matching_command(tool_name)

            if tool_function:
                # Capture the output
                old_stdout = sys.stdout
                sys.stdout = mystdout = io.StringIO()

                try:
                    # Run the function
                    tool_function(wifi_obj)
                finally:
                    sys.stdout = old_stdout

                output_text = mystdout.getvalue()

                # Display the output in a dedicated screen
                self.session.open(
                    IWListOutputScreen,
                    "{} - {}".format(selection[0], ifname),
                    output_text
                )
            else:
                self["output"].setText(_("Tool not available"))

            except Exception as e:
                self.session.open(
                    MessageBox,
                    _("Error running {tool}: {error}").format(
                        tool=tool_name,
                        error=str(e)),
                    MessageBox.TYPE_ERROR)


class IWListOutputScreen(Screen):
    skin = """
    <screen position="center,center" size="800,600" title="IWList Output">
        <widget name="output" position="10,10" size="780,540" font="Regular;18" />
        <ePixmap position="10,560" size="140,40" pixmap="buttons/red.png" transparent="1" alphatest="on" />
        <widget name="key_red" position="10,560" size="140,40" zPosition="1" font="Regular;20" halign="center" valign="center" backgroundColor="red" transparent="1" />
    </screen>
    """

    def __init__(self, session, title, output_text):
        Screen.__init__(self, session)
        self.session = session
        self["output"] = ScrollLabel()
        self["key_red"] = Label(_("Close"))
        self["actions"] = ActionMap(
            ["ColorActions", "OkCancelActions"],
            {
                "red": self.close,
                "cancel": self.close,
            })
        self.setTitle(title)
        self["output"].setText(output_text)


def print_scanning_results(wifi, args=None):
    """Print the access points detected nearby."""
    try:
        iwrange = Iwrange(wifi.ifname)
        print("iwrange: {}".format(iwrange))
    except IOError as e:
        if sys.version_info[0] == 3:
            error_number, error_string = e.args
        else:
            error_number, error_string = e[0], e[1]

        sys.stderr.write(
            _("{interface:<8.16}  Interface doesn't support scanning.\n\n").format(
                interface=wifi.ifname))
        return

    try:
        results = wifi.scan()
    except IOError as e:
        if sys.version_info[0] == 3:
            error_number, error_string = e.args
        else:
            error_number, error_string = e[0], e[1]

        if error_number != errno.EPERM:
            sys.stderr.write(
                _("{interface:<8.16}  Interface doesn't support scanning : {error}\n\n").format(
                    interface=wifi.ifname, error=error_string))
        return

    if not results or len(results) == 0:
        print("{:<8.16}  No scan results".format(wifi.ifname))
        print()
        return

    num_channels, frequencies = wifi.getChannelInfo()
    print("{:<8.16}  Scan completed :".format(wifi.ifname))

    for index, ap in enumerate(results.aplist, start=1):
        print("          Cell {:02d} - Address: {}".format(index, ap.bssid))
        print("                    ESSID:\"{}\"".format(ap.essid))
        print("                    Mode:{}".format(ap.mode))

        freq_str = wifi._formatFrequency(ap.frequency.getFrequency())
        try:
            channel_number = frequencies.index(freq_str) + 1
        except ValueError:
            channel_number = 0

        print("                    Frequency:{} (Channel {})".format(
            freq_str, channel_number
        ))

        quality_updated = "=" if ap.quality.updated & flags.IW_QUAL_QUAL_UPDATED else ":"
        signal_updated = "=" if ap.quality.updated & flags.IW_QUAL_LEVEL_UPDATED else ":"
        noise_updated = "=" if ap.quality.updated & flags.IW_QUAL_NOISE_UPDATED else ":"

        print(
            "                    Quality{} {}/{}  Signal level{} {}/100  Noise level{} {}/100".format(
                quality_updated,
                ap.quality.quality,
                wifi.getQualityMax().quality,
                signal_updated,
                ap.quality.getSignallevel(),
                noise_updated,
                ap.quality.getNoiselevel()))

        if ap.encode.flags & flags.IW_ENCODE_DISABLED:
            key_status = _("off")
        elif ap.encode.flags & flags.IW_ENCODE_NOKEY and ap.encode.length <= 0:
            key_status = _("on")
        else:
            key_status = ""

        print("                    Encryption key:{}".format(key_status))

        if ap.rate:
            for rate_list in ap.rate:
                rate_lines = len(rate_list) // 5
                rate_remainder = len(rate_list) % 5

                for line in range(rate_lines):
                    label = _("                    Bit Rates:") if line == 0 else _(
                        "                              ")
                    rates = "; ".join(
                        wifi._formatBitrate(x)
                        for x in rate_list[line * 5:(line * 5) + 5]
                    )
                    print("{}{}".format(label, rates))

                if rate_remainder > 0:
                    label = _("                              ") if rate_lines > 0 else _(
                        "                    Bit Rates:")
                    partial_rates = "; ".join(
                        wifi._formatBitrate(x)
                        for x in rate_list[-rate_remainder:]
                    )
                    print("{}{}".format(label, partial_rates))

    print()


def print_channels(wifi, args=None):
    """Print all frequencies/channels available on the card."""
    try:
        num_frequencies, channels = wifi.getChannelInfo()
        current_freq = wifi.getFrequency()
    except IOError as e:
        if sys.version_info[0] == 3:
            error_number, error_string = e.args
        else:
            error_number, error_string = e[0], e[1]

        if error_number in (errno.EOPNOTSUPP, errno.EINVAL, errno.ENODEV):
            sys.stderr.write(
                _("{interface:<8.16}  no frequency information.\n\n").format(
                    interface=wifi.ifname))
        else:
            report_error("channel", wifi.ifname, error_number, error_string)
        return

    print(f"{wifi.ifname:<8.16}  {num_frequencies:02d} channels in total; available frequencies :")

    for idx, channel in enumerate(channels, start=1):
        print(f"          Channel {idx:02d} : {channel}")

    iwfreq = wifi.wireless_info.getFrequency()
    fixed = "=" if iwfreq.flags & flags.IW_FREQ_FIXED else ":"
    return_type = _("Channel") if iwfreq.getFrequency(
    ) < KILO else _("Frequency")

    current_freq = wifi.getFrequency()
    try:
        current_channel = channels.index(current_freq) + 1
    except ValueError:
        current_channel = 0  # if current_freq not found

    print(
        f"          Current {return_type}{fixed}{current_freq} (Channel {current_channel})\n")


def print_bitrates(wifi, args=None):
    """ Print all bitrates available on the card.

    """
    try:
        num_bitrates, bitrates = wifi.getBitrates()
    except IOError as e:
        if sys.version_info[0] == 3:
            error_number, error_string = e.args
        else:
            error_number, error_string = e[0], e[1]

        if error_number in (errno.EOPNOTSUPP, errno.EINVAL, errno.ENODEV):
            sys.stderr.write(
                _("{interface:<8.16}  no bit-rate information.\n\n").format(interface=wifi.ifname)
            )
        else:
            report_error("bit rate", wifi.ifname, error_number, error_string)
    else:
        if 0 < num_bitrates <= flags.IW_MAX_BITRATES:
            # wireless device with bit rate info, so list 'em
            print(f"{wifi.ifname:<8.16}  {num_bitrates:02d} available bit-rates :")

            for rate in bitrates:
                print("\t  %s" % rate)
        else:
            # wireless device, but no bit rate info available
            print("%-8.16s  unknown bit-rate information." % (wifi.ifname, ))
    # current bit rate
    try:
        bitrate = wifi.wireless_info.getBitrate()
    except IOError as e:
        if (sys.version_info[0] == 3):
            error_number, error_string = e.args
        else:
            error_number = e[0]
            error_string = e[1]
        # no bit rate info is okay, error was given above
        pass
    else:
        if bitrate.fixed:
            fixed = "="
        else:
            fixed = ":"
        print("          Current Bit Rate%c%s" % (fixed, wifi.getBitrate()))
        # broadcast bit rate
        # XXX add broadcast bit rate
        print("")


def print_encryption(wifi, args=None):
    """Print encryption keys on the card."""
    try:
        keys = wifi.getKeys()

    except IOError as e:
        if sys.version_info[0] == 3:
            error_number, error_string = e.args
        else:
            error_number, error_string = e[0], e[1]

        print(
            "error_number: {}  error_string: {}".format(
                error_number,
                error_string))

        if error_number in (errno.EOPNOTSUPP, errno.EINVAL, errno.ENODEV):
            sys.stderr.write(
                _("{interface:<8.16}  no encryption keys information.\n\n").format(
                    interface=wifi.ifname))
        return

    range_info = Iwrange(wifi.ifname)

    key_sizes = ", ".join(
        str(range_info.encoding_size[i] * 8)
        for i in range(range_info.num_encoding_sizes)
    ) + _(" bits")

    print("{:<8.16}  {} key sizes : {}".format(
        wifi.ifname,
        range_info.num_encoding_sizes,
        key_sizes
    ))

    print("          {} keys available :".format(len(keys)))

    for key in keys:
        print("\t\t[{}]: {}".format(key[0], key[1]))

    tx_key_index = wifi.wireless_info.getKey().flags & flags.IW_ENCODE_INDEX
    print("          Current Transmit Key: [{}]".format(tx_key_index))

    key_flags = wifi.wireless_info.getKey().flags

    if key_flags & flags.IW_ENCODE_RESTRICTED:
        print("          Security mode:restricted")

    if key_flags & flags.IW_ENCODE_OPEN:
        print("          Security mode:open")

    print()


def format_pm_value(value, args=None):
    """ Return formatted PM value.

    """
    if (value >= MEGA):
        fvalue = "%gs" % (value // MEGA, )
    else:
        if (value >= KILO):
            fvalue = "%gms" % (value // KILO, )
        else:
            fvalue = "%dus" % (value, )
    return fvalue


def print_power(wifi, args=None):
    """Print power management info for the card."""
    try:
        pm_capa, power_period, power_timeout, power_saving, power_params = wifi.getPowermanagement()

    except IOError as e:
        if sys.version_info[0] == 3:
            error_number, error_string = e.args
        else:
            error_number, error_string = e[0], e[1]

        print(
            "error_number: {}  error_string: {}".format(
                error_number,
                error_string))

        if error_number == errno.ENODEV:
            sys.stderr.write(
                _("{interface:<8.16}  no power management information.\n\n").format(
                    interface=wifi.ifname))
        return

    print("{:<8.16} ".format(wifi.ifname), end="")

    if pm_capa & flags.IW_POWER_MODE:
        print("Supported modes :")

        if pm_capa & (flags.IW_POWER_UNICAST_R | flags.IW_POWER_MULTICAST_R):
            print("\t\t\to Receive all packets (unicast & multicast)")
            print("\t ", end="")

        if pm_capa & flags.IW_POWER_UNICAST_R:
            print("\t\to Receive Unicast only (discard multicast)")
            print("\t ", end="")

        if pm_capa & flags.IW_POWER_MULTICAST_R:
            print("\t\to Receive Multicast only (discard unicast)")
            print("\t ", end="")

        if pm_capa & flags.IW_POWER_FORCE_S:
            print("\t\to Force sending using Power Management")
            print("\t ", end="")

        if pm_capa & flags.IW_POWER_REPEATER:
            print("\t\to Repeat multicast")
            print("\t ", end="")

    if power_period[0] & flags.IW_POWER_PERIOD:
        mode = "Auto" if power_period[0] & flags.IW_POWER_MIN else "Fixed"
        print("{}  period  ; ".format(mode), end="")
        print(
            "min period:{}".format(
                format_pm_value(
                    power_period[1])),
            end="\n\t\t\t  ")
        print(
            "max period:{}".format(
                format_pm_value(
                    power_period[2])),
            end="\n\t ")

    if power_timeout[0] & flags.IW_POWER_TIMEOUT:
        mode = "Auto" if power_timeout[0] & flags.IW_POWER_MIN else "Fixed"
        print("{}  timeout ; ".format(mode), end="")
        print(
            "min period:{}".format(
                format_pm_value(
                    power_timeout[1])),
            end="\n\t\t\t  ")
        print(
            "max period:{}".format(
                format_pm_value(
                    power_timeout[2])),
            end="\n\t ")

    if power_saving[0] & flags.IW_POWER_SAVING:
        mode = "Auto" if power_saving[0] & flags.IW_POWER_MIN else "Fixed"
        print("{}  saving  ; ".format(mode), end="")
        print(
            "min period:{}".format(
                format_pm_value(
                    power_saving[1])),
            end="\n\t\t\t  ")
        print(
            "max period:{}".format(
                format_pm_value(
                    power_saving[2])),
            end="\n\t ")

    if power_params.disabled:
        print("Current mode:off")
    else:
        mode_flags = power_params.flags & flags.IW_POWER_MODE

        if mode_flags == flags.IW_POWER_UNICAST_R:
            print("Current mode:Unicast only received")
        elif mode_flags == flags.IW_POWER_MULTICAST_R:
            print("Current mode:Multicast only received")
        elif mode_flags == flags.IW_POWER_ALL_R:
            print("Current mode:All packets received")
        elif mode_flags == flags.IW_POWER_FORCE_S:
            print("Current mode:Force sending")
        elif mode_flags == flags.IW_POWER_REPEATER:
            print("Current mode:Repeat multicasts")

    print()


def print_txpower(wifi, args=None):
    """ Print transmit power info for the card.

    """
    pass


def print_retry(wifi, args=None):
    try:
        range_info = Iwrange(wifi.ifname)
    except IOError as e:
        if sys.version_info[0] == 3:
            error_number, error_string = e.args
        else:
            error_number, error_string = e[0], e[1]
        print(f"error_number: {error_number}  error_string: {error_string}")
        if error_number in (errno.EOPNOTSUPP, errno.EINVAL, errno.ENODEV):
            sys.stderr.write(
                _("{interface:<8.16}  no retry limit/lifetime information.\n\n").format(
                    interface=wifi.ifname))
    else:
        ifname = "%-8.16s  " % (wifi.ifname, )
        if (range_info.retry_flags & flags.IW_RETRY_LIMIT):
            if (range_info.retry_flags & flags.IW_RETRY_MIN):
                limit = _("Auto  limit    ;  min limit:{limit}").format(
                    limit=range_info.min_retry)
            else:
                limit = _("Fixed limit    ;  min limit:{limit}").format(
                    limit=range_info.min_retry)
            print(ifname + limit)
            ifname = None
            print("                            max limit:%d" % (
                range_info.max_retry, ))
        if (range_info.r_time_flags & flags.IW_RETRY_LIFETIME):
            if (range_info.r_time_flags & flags.IW_RETRY_MIN):
                lifetime = "Auto  lifetime ;  min lifetime:%d" % (
                    range_info.min_r_time, )
            else:
                lifetime = _("Fixed lifetime ;  min lifetime:{lifetime}").format(
                    lifetime=range_info.min_r_time)
            if ifname:
                print(ifname + lifetime)
                ifname = None
            else:
                print("          " + lifetime)
            print("                            max lifetime:%d" % (
                range_info.max_r_time, ))
        iwparam = wifi.wireless_info.getRetry()
        if iwparam.disabled:
            print("          Current mode:off")
        else:
            print("          Current mode:on")
            if (iwparam.flags & flags.IW_RETRY_TYPE):
                if (iwparam.flags & flags.IW_RETRY_LIFETIME):
                    mode_type = _("lifetime")
                else:
                    mode_type = _("limit")
                mode = _("                 ")
                if (iwparam.flags & flags.IW_RETRY_MIN):
                    mode = mode + \
                        _(" min {type}:{value}").format(type=mode_type, value=iwparam.value)
                if (iwparam.flags & flags.IW_RETRY_MAX):
                    mode = mode + \
                        _(" max {type}:{value}").format(type=mode_type, value=iwparam.value)
                if (iwparam.flags & flags.IW_RETRY_SHORT):
                    mode = mode + \
                        _(" short {type}:{value}").format(type=mode_type, value=iwparam.value)
                if (iwparam.flags & flags.IW_RETRY_LONG):
                    mode = mode + \
                        _(" long {type}:{value}").format(type=mode_type, value=iwparam.value)
                print(mode)


def print_aps(wifi, args=None):
    """ Print the access points detected nearby.

        iwlist.c uses the deprecated SIOCGIWAPLIST, but iwlist.py uses
        regular scanning (i.e. Wireless.scan()).

    """
    # "Check if the interface could support scanning"
    try:
        iwrange = Iwrange(wifi.ifname)
        print(f"iwrange: {iwrange}")
    except IOError as e:
        if (sys.version_info[0] == 3):
            error_number, error_string = e.args
        else:
            error_number = e[0]
            error_string = e[1]
        sys.stderr.write(
            _("{interface:<8.16}  Interface doesn't support scanning.\n\n").format(
                interface=wifi.ifname))
    else:
        # "Check for Active Scan (scan with specific essid)"
        # "Check for last scan result (do not trigger scan)"
        # "Initiate Scanning"
        try:
            results = wifi.scan()
        except IOError as e:
            if (sys.version_info[0] == 3):
                error_number, error_string = e.args
            else:
                error_number = e[0]
                error_string = e[1]
            if error_number != errno.EPERM:
                sys.stderr.write(
                    _("{interface:<8.16}  Interface doesn't support scanning : {error}\n\n").format(
                        interface=wifi.ifname, error=error_string))
        else:
            if len(results) == 0:
                print(
                    f"{wifi.ifname:<8.16}  Interface doesn't have a list of Peers/Access-Points"
                )
            else:
                print(
                    "%-8.16s  Peers/Access-Points in range:" %
                    (wifi.ifname, ))
                for ap in results:
                    if ap.quality.quality:
                        if ap.quality.updated & flags.IW_QUAL_QUAL_UPDATED:
                            quality_updated = "="
                        else:
                            quality_updated = ":"

                        if ap.quality.updated & flags.IW_QUAL_LEVEL_UPDATED:
                            signal_updated = "="
                        else:
                            signal_updated = ":"

                        if ap.quality.updated & flags.IW_QUAL_NOISE_UPDATED:
                            noise_updated = "="
                        else:
                            noise_updated = ":"

                        print(
                            "    %s : Quality%c%s/%s  Signal level%c%s/%s  Noise level%c%s/%s" %
                            (ap.bssid,
                             quality_updated,
                             ap.quality.quality,
                             wifi.getQualityMax().quality,
                                signal_updated,
                                ap.quality.getSignallevel(),
                                "100",
                                noise_updated,
                                ap.quality.getNoiselevel(),
                                "100",
                             ))
                    else:
                        print("    %s" % (ap.bssid, ))
                print


def report_error(function, interface, error_number, error_string):
    """Print error to user."""
    print(
        f"Uncaught error condition. Please report this to the developers' "
        f"mailing list (information available at "
        f"http://lists.berlios.de/mailman/listinfo/pythonwifi-dev). "
        f"While attempting to print {function} information for {interface}, "
        f"the error \"{error_number} - {error_string}\" occurred."
    )


def usage():
    print("""\
Usage: iwlist.py [interface] scanning [essid NNN] [last]
                 [interface] frequency
                 [interface] channel
                 [interface] bitrate
                 [interface] encryption
                 [interface] keys
                 [interface] power
                 [interface] txpower
                 [interface] retry
                 [interface] ap
                 [interface] accesspoints
                 [interface] peers""")


def get_matching_command(option):
    """ Return a function for the command.
        'option' -- string -- command to match
        Return None if no match found.
    """
    # build dictionary of commands and functions
    iwcommands = {
        "s": ("scanning", print_scanning_results),
        "c": ("channel", print_channels),
        "f": ("frequency", print_channels),
        "b": ("bitrate", print_bitrates),
        "ra": ("rate", print_bitrates),
        "en": ("encryption", print_encryption),
        "k": ("keys", print_encryption),
        "po": ("power", print_power),
        "t": ("txpower", print_txpower),
        "re": ("retry", print_retry),
        "ap": ("ap", print_aps),
        "ac": ("accesspoints", print_aps),
        "pe": ("peers", print_aps),
        # "ev": ("event", print_event),
        # "au": ("auth", print_auth),
        # "w": ("wpakeys", print_wpa),
        # "g": ("genie", print_genie),
        # "m": ("modulation", print_modulation),
    }

    function = None
    for command in iwcommands.keys():
        if option.startswith(command):
            if iwcommands[command][0].startswith(option):
                function = iwcommands[command][1]
    return function


def main():
    # if only program name is given, print usage info
    if len(sys.argv) == 1:
        usage()

    # if program name and one argument are given
    if len(sys.argv) == 2:
        option = sys.argv[1]
        # look for matching command
        list_command = get_matching_command(option)
        # if the one argument is a command
        if list_command is not None:
            for ifnameX in getNICnames():
                wifi = Wireless(ifnameX)
                list_command(wifi)
        else:
            print(
                "iwlist.py: unknown command `%s' (check 'iwlist.py --help')." %
                (option, ))

    # if program name and more than one argument are given
    if len(sys.argv) > 2:
        # Get the interface and command from command line
        ifname, option = sys.argv[1:]
        # look for matching command
        list_command = get_matching_command(option)
        # if the second argument is a command
        if list_command is not None:
            wifi = Wireless(ifname)
            list_command(wifi, sys.argv[3:])
        else:
            print(
                "iwlist.py: unknown command `%s' (check 'iwlist.py --help')." %
                (option, ))


if __name__ == "__main__":
    main()
