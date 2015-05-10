#!/usr/bin/python
from StringIO import StringIO
import pycurl, sys, getopt

version = '1.0'
verbose = False
URL = 'https://api.lifx.com/v1beta1/lights/SELECTOR/ACTION'
login = 'c211d86e8043859c811ecec2853f334ec0b1a1997e00ea4c113e2132305109e3'
actions = ("power", "toggle", "list", "color", "--version", "-h", "--help")

def print_help():
    print("PRINT HELP SCREEN")

def send_request(c):
    storage = StringIO()
    c.setopt(c.WRITEFUNCTION, storage.write)
    c.setopt(pycurl.CONNECTTIMEOUT, 3)
    c.setopt(pycurl.TIMEOUT, 3)
    c.setopt(pycurl.USERPWD, login)
    c.perform()
    print(c.getinfo(pycurl.HTTP_CODE))
    print(c.getinfo(pycurl.EFFECTIVE_URL))
    content = storage.getvalue()
    c.close()
    print(content)

def build_url(selector, action):
    url = URL.replace("SELECTOR", selector)
    url = url.replace("ACTION", action)
    return url

def send_put(selector, action, data):
    c = pycurl.Curl()
    c.setopt(pycurl.CUSTOMREQUEST, "PUT")
    c.setopt(pycurl.URL, build_url(selector, action))
    c.setopt(pycurl.POSTFIELDS, data)
    send_request(c)

def send_post(selector, action, data):
    c = pycurl.Curl()
    c.setopt(pycurl.POST, 1)
    c.setopt(pycurl.POSTFIELDS, data)
    c.setopt(pycurl.URL, build_url(selector, action))
    send_request(c)

def send_get(selector):
    c = pycurl.Curl()
    c.setopt(pycurl.URL, build_url(selector, ""))
    send_request(c)

#############33 PARSER ##################3

def parse_duration(options):
    for opt, arg in options:
        if opt in ('-d', '--duration'):
            return arg
    #Return default value
    return "1.0"

def parse_selector(options):
    #Default select all
    selector="all"

    count=0
    for opt, arg in options:
        if opt in ('-a', '--all'):
            selector = "all"
            count += 1
        elif opt in ('-l', '--label'):
            selector = "label:" + arg
            count += 1
        elif opt in ('-g', '--group'):
            selector = "group:" + arg
            count += 1
        elif opt in ('-L', '--location'):
            selector = "location:" + arg
            count += 1
    if(count > 1):
        sys.exit("Too many selectors!")
    return selector

######################################

def handle_remainder(remainder):
    if len(remainder) == 0:
        return
    print("Error, unknown command: " + ' '.join(remainder))
    sys.exit(1)

############### POWER ################
#PUT /v1beta1/lights/:selector/power
def _power(state, duration, selector):
    send_put(selector, "power", "state=" + state + "&duration=" + duration)

def help_power():
    print("lifx power on/off [SELECTOR]")

def handle_power(arg):
    if len(arg) < 1 or arg[0] not in ("on", "off"):
        help_power()
        sys.exit()

    options, remainder = getopt.getopt(arg[1:], 'd:al:g:L:')
    duration = parse_duration(options)
    selector = parse_selector(options)

    handle_remainder(remainder)
    _power(arg[0], duration, selector)

############### TOGGLE ################
#POST /v1beta1/lights/:selector/toggle
def _toggle(selector):
    send_post(selector, "toggle", "")

def handle_toggle(arg):
    options, remainder = getopt.getopt(arg, 'al:g:L:')
    selector = parse_selector(options)
    handle_remainder(remainder)
    _toggle(selector)

############### LIST ################
def _list(selector):
    send_get(selector)

def handle_list(arg):
    options, remainder = getopt.getopt(arg, 'al:g:L:')
    selector = parse_selector(options)
    handle_remainder(remainder)
    _list(selector)

############### COLOR ################
#PUT /v1beta1/lights/:selector/color
def print_help_color():
    print("COLOR HELP")

def _color(color, duration, selector):
    send_put(selector, "color", "color=" + color + "&duration=" + duration)

def parse_color(arg):
    colors = ("white", "red", "orange", "yellow", "cyan", "green", "blue", "purple", "pink")
    if arg[0] in colors or arg[0].startswith("#"):
        print("HEX or Color found")
        return (arg[0], arg[1:])

    options, remainder = getopt.getopt(arg, 'h:b:s:k:r:d:al:g:L:')

    duration = 1.0
    count = 0
    for opt, arg in options:
        if opt in ('-h', '--hue'):
            color = "hue:" + arg
            print("HUE!")
            count += 1
        elif opt in ('-b', '--brightness'):
            color = "brightness:" + arg
            count += 1
        elif opt in ('-s', '--saturation'):
            color = "saturation:" + arg
            count += 1
        elif opt in ('-k', '--kelvin'):
            color = "kelvin:" + arg
            count += 1
        elif opt in ('-r', '--rgb'):
            color = "rgb:" + arg
            count += 1

    if(count != 1):
        sys.exit("Bad color argument!")

    duration = parse_duration(options)
    selector = parse_selector(options)

    handle_remainder(remainder)

    return [color, duration, selector]

def handle_color(arg):
    if len(arg) < 1:
        print_help_color()
        sys.exit()
    arr = parse_color(arg)
    _color(arr[0], arr[1], arr[2])

def main(argv):
    if(len(argv) < 1 or argv[0] not in actions):
        print_help()
        sys.exit()

    action = argv[0]
    if(action == "power"):
        handle_power(argv[1:])
    elif(action == "toggle"):
        handle_toggle(argv[1:])
    elif(action == "list"):
        handle_list(argv[1:])
    elif(action == "color"):
        handle_color(argv[1:])
    elif(action == "--version"):
        print(version)
    elif(action in ("-h", "--help")):
        print_help()
    sys.exit()


if __name__ == "__main__":
   main(sys.argv[1:])

