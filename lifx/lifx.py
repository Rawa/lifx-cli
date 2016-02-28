#!/usr/bin/python3

#
# Simple script to control your LIFX lamps using the cli by doing RESTful calls
# to the lifx api. Needs a valid lifx token to make requests, the token should
# be saved in $HOME/.config/lifx/lifx_token
#
# @author David Göransson
#

import requests
import sys
import json
import argparse
from pathlib import Path  # Requires python >= 3.5

version = 'v1.1'
verbose = False
URL = 'https://api.lifx.com/v1/lights/SELECTOR/ACTION'
actions = ("on", "off", "toggle", "list", "state", "--version")
config_path = Path.home() / ".config/lifx/lifx_token"
token = None

if config_path.exists():
    token = config_path.read_text().strip()
else:
    print("No personal access token found!")
    print("  1. Get your developer lifx token:")
    print("     https://cloud.lifx.com/settings")
    token = input("  2. Paste it here:  ")
    if not config_path.parent.exists():
        config_path.parent.mkdir(parents=True)
    config_path.write_text(token.strip())

headers = {
    "Authorization": "Bearer %s" % token,
}


############### ConnectionHandle ###################
class ConnectionHandle:
    def ___init__(self):
        pass

    def _handle_response(self, response):
        code = response.status_code
        content = response.content.decode('iso-8859-1')

        if code in (200, 201, 202, 207):
            # Everything is fine, exit program peacefully
            return code, content
        elif code == 401:
            print("Unauthorized request - Verify your lifx token")
        elif code == 408:
            print("Request timed out -  Light unreachable!")
        elif code == 422:
            print("Unprocessable Entity - Missing or malformed parameters.")
        elif code == 429:
            print("Too many requests!")
        elif code in (500, 502, 503, 523):
            print("Server error!")
        else:
            print("Unknown error! HTTP Code: " + str(code))

        decoded = json.loads(content)
        if decoded['error']:
            error_exit("Error: " + decoded['error'])
        else:
            print("Server response:")
            error_exit(content)

    def _build_url(self, selector, action=""):
        url = URL.replace("SELECTOR", selector)
        url = url.replace("ACTION", action)
        return url

    def send_put(self, selector, action, data):
        r = requests.put(self._build_url(selector, action),
                         data=data, headers=headers)
        return self._handle_response(r)

    def send_post(self, selector, action, data):
        r = requests.post(self._build_url(selector, action),
                          data=data, headers=headers)
        return self._handle_response(r)

    def send_get(self, selector):
        r = requests.get(self._build_url(selector), headers=headers)
        return self._handle_response(r)


############### LIFX ###################
class LIFX:
    def ___init__(self):
        pass

    ############### LIST ################
    # LIST: GET /v1/lights/:selector
    def list(self, args):
        selector = self._get_selector(args)
        code, content = ConnectionHandle().send_get(selector)

        # Parse and print response
        decoded = json.loads(content)

        if verbose:
            print("[Label] - [Location]/[Group]\n")
            for item in decoded:
                print(item['label'] + " - " + item['location']['name'] + "/" + item['group']['name'])
                print("  power      : " + item['power'])
                print("  hue        : " + str(item['color']['hue']))
                print("  kelvin     : " + str(item['color']['kelvin']))
                ("  saturation : " + str(item['color']['saturation']))
                print("  brightness : " + str(item['brightness']))
        else:
            longestLabel = len(max([item['label'] for item in decoded], key=len))
            for item in decoded:
                print(("{:" + str(longestLabel) + "} {}").format(item['label'], item['power']))


    ############### TOGGLE ################
    # TOGGLE: POST /v1/lights/:selector/toggle
    def toggle(self, args):
        data = {}

        if args.duration is not None:
            data['duration'] = str(args.duration)

        return ConnectionHandle().send_post(self._get_selector(args), "toggle", data)

    ############### POWER ################
    # STATE: PUT /v1/lights/:selector/state
    def power(self, args):
        data = {}

        # power=
        if args.power:
            data['power'] = args.power

        # duration=
        if args.duration is not None:
            data['duration'] = str(args.duration)

        selector = self._get_selector(args)
        ConnectionHandle().send_put(selector, "state", data)

    ############### STATE ################
    # STATE: PUT /v1/lights/:selector/state
    def state(self, args):
        data = {}

        # power=
        if args.power:
            data['power'] = args.power

        # duration=
        if args.duration is not None:
            data['duration'] = str(args.duration)

        # color=
        color = self._get_color(args)
        if color is not None:
            data['color'] = color

        selector = self._get_selector(args)
        ConnectionHandle().send_put(selector, "state", data)

    ############### PULSE ################
    # PULSE: PUT /v1/lights/:selector/pulse
    def pulse(self, args):
        self._base_effect(args, "effects/pulse")

    def breathe(self, args):
        self._base_effect(args, "effects/breathe")

    def _base_effect(self, args, action):
        data = {}

        if args.period is not None:
            data['period'] = str(args.period)

        if args.cycles is not None:
            data['cycles'] = str(args.cycles)

        if args.peak is not None:
            data['peak'] = str(args.peak)

        data['persist'] = args.persist

        data['power_on'] = args.power_on

        color = self._get_color(args)
        if color is not None:
            data['color'] = color

        from_color = self._get_color(args, "from_")
        if from_color is not None:
            data['from_color'] = from_color

        selector = self._get_selector(args)
        ConnectionHandle().send_post(selector, action, data)

    def _get_color(self, args, prefix=""):
        color = ""
        args = vars(args)
        # color=
        c = prefix + "color"
        r = prefix + "rgb"
        h = prefix + "hue"
        s = prefix + "saturation"
        b = prefix + "brightness"
        k = prefix + "kelvin"

        # If no color value is set return None
        if all(v is None for v in [args[c],
                                   args[r],
                                   args[h],
                                   args[s],
                                   args[b],
                                   args[k]]):
            return None

        color = ""
        if args[c]:
            color += args[c]
        elif args[r]:
            color += "rgb:" + (",").join(map(str, args[r]))

        # 0 = False, thus compare with None
        if args[h] is not None:
            color += " hue:" + str(args[h])
        if args[s] is not None:
            color += " saturation:" + str(args[s])
        if args[h] is not None:
            color += " brightness:" + str(args[h])
        if args[h] is not None:
            color += " kelvin:" + str(args[h])

        if color.startswith(' '):
            color = color[1:]

        return color

    def _get_selector(self, args):
        if args.label:
            return "label:" + args.label
        elif args.location:
            return "location:" + args.location
        elif args.group:
            return "group:" + args.group
        else:
            return "all"


############### Parser ###################
class Parser:
    def ___init__(self):
        pass

    def parser(self):
        parser = argparse.ArgumentParser(description='Command line interface for LIFX light bulbs.')
        parser.add_argument('-V', '--version', action='version', version=version)
        subparsers = parser.add_subparsers(dest="sub_cmd", title='Subcommands',
            description='To run the lifx cli simply use on of the sub commands listed below.')
        self._on_parser(subparsers)
        self._off_parser(subparsers)
        self._list_parser(subparsers)
        self._state_parser(subparsers)
        self._pulse_parser(subparsers)
        self._breathe_parser(subparsers)
        self._toggle_parser(subparsers)
        return parser

    def _on_parser(self, subparsers):
        on_parser = subparsers.add_parser('on')
        on_parser.set_defaults(power='on')
        self._addVerboseArgument(on_parser)
        self._addDurationArgument(on_parser)
        self._addSelectorGroup(on_parser)

    def _off_parser(self, subparsers):
        off_parser = subparsers.add_parser('off')
        off_parser.set_defaults(power='off')
        self._addVerboseArgument(off_parser)
        self._addDurationArgument(off_parser)
        self._addSelectorGroup(off_parser)

    def _list_parser(self, subparsers):
        list_parser = subparsers.add_parser('list')
        self._addVerboseArgument(list_parser)
        self._addSelectorGroup(list_parser)

    def _state_parser(self, subparsers):
        state_parser = subparsers.add_parser('state')
        state_parser.add_argument("-p", "--power", type=str, choices=["on", "off"], default="on",
                                  help='Whether to set power to "on" or "off"')
        self._addVerboseArgument(state_parser)
        self._color_parser(state_parser)
        self._addDurationArgument(state_parser)
        self._addSelectorGroup(state_parser)

    def _breathe_parser(self, subparsers):
        return self._base_effect_parser(subparsers, 'breathe')

    def _pulse_parser(self, subparsers):
        return self._base_effect_parser(subparsers, 'pulse')

    def _base_effect_parser(self, subparsers, name):
        base_effect_parser = subparsers.add_parser(name)
        base_effect_parser.add_argument("-P", "--power_on", action='store_false', default=True,
            help='If true, turn the bulb on if it is not already on.')
        base_effect_parser.add_argument("-p", "--period", type=float, default=1.0,
            help='The time in seconds for one cyles of the effect.')
        base_effect_parser.add_argument("-C", "--cycles", type=float, default=1.0,
            help='The number of times to repeat the effect.')
        base_effect_parser.add_argument("-e", "--persist",  action='store_true', default=False,
            help='If true, turn the bulb on if it is not already on.')
        base_effect_parser.add_argument("-E", "--peak", type=float, default=0.5,
            help='Defines where in a period the target color is at its maximum. Minimum 0.0, maximum 1.0.')
        self._addVerboseArgument(base_effect_parser)
        self._color_parser(base_effect_parser)
        self._color_parser(base_effect_parser, "f", "from_")
        self._addSelectorGroup(base_effect_parser)

    def _toggle_parser(self, subparsers):
        toggle_parser = subparsers.add_parser('toggle')
        self._addVerboseArgument(toggle_parser)
        self._addDurationArgument(toggle_parser)
        self._addSelectorGroup(toggle_parser)

    def _addSelectorGroup(self, parser):
        groupSelector = parser.add_mutually_exclusive_group(required=False)
        groupSelector.set_defaults(selector='all')
        groupSelector.add_argument("-g", "--group", type=str,
            help='The lights belonging to the groups matching the given label.')
        groupSelector.add_argument("-l", "--label", type=str,
            help='Lights that match the label.')
        groupSelector.add_argument("-L", "--location", type=str,
            help='The lights belonging to the locations matching the given label.')

    def _color_parser(self, parser, prefix="", long_prefix=""):
        p = "-" + prefix
        lp = "--" + long_prefix
        parser.add_argument(p + "b", lp + "brightness", type=float,
            help='Sets brightness without affecting other components')
        parser.add_argument(p + "H", lp + "hue", type=float,
            help='Sets hue without affecting other components')
        parser.add_argument(p + "k", lp + "kelvin", type=int,
            help='Sets kelvin to the given value and saturation to 0.0. Other components are not affected.Kelvin help')
        parser.add_argument(p + "s", lp + "saturation", type=float,
            help='Sets saturation without affecting other components')

        groupColor = parser.add_mutually_exclusive_group(required=False)
        groupColor.add_argument(p + "c", lp + "color", type=str,
            help='Color or hex value, e.g. "red" alternatively RRGGBB')
        groupColor.add_argument(p + "r", lp + "rgb", type=int, nargs=3,
            help='rgb in format [1-255] [1-255] [1-255]')

    def _addDurationArgument(self, parser):
        parser.add_argument("-d", "--duration", type=float, default=1.0,
            help='How long in seconds you want the power action to take.')

    def _addVerboseArgument(self, parser):
        parser.add_argument("-v", "--verbose", dest='verbose', action='store_true',
             help='be verbose')


######################################
def error_exit(msg=None):
    if msg != None:
        print(msg)
    sys.exit(1)


############### MAIN ################
def main():

    # Create the parser
    parser = Parser().parser()

    if len(sys.argv) == 1:
        parser.print_help()
        sys.exit(1)

    # Parse arguments
    args = parser.parse_args()

    if hasattr(args, 'verbose') and args.verbose is True:
        global verbose
        verbose = True

    binds = {"on":      LIFX.power,
             "off":     LIFX.power,
             "state":   LIFX.state,
             "pulse":   LIFX.pulse,
             "breathe": LIFX.breathe,
             "list":    LIFX.list,
             "toggle":  LIFX.toggle}

    # Run command with arguments
    binds[args.sub_cmd](LIFX(), args)

    sys.exit(0)


if __name__ == '__main__':
    main()
