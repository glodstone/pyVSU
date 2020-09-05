#! /usr/bin/env python3

try:
    import serial
    import serial.tools.list_ports as comports
except ImportError:
    print('Unable to load pySerial - is it installed?')
import argparse

par = argparse.ArgumentParser(
        description='pyVSU-2 ROM programming and configuration utility',
        formatter_class=argparse.RawTextHelpFormatter
        )
par.add_argument('-p', '--port', type=str, nargs=1,
        action='store', choices=[_.device for _ in list(comports.comports())],
        help='name of serial device conected to VSU-2',
        required=True
        )
par.add_argument('-d', '--dump', action='store_true',
        help='dump device image to specified filename'
        )
par.add_argument('-i', '--image', action='store_false',
        help='write specified image file to device'
        )
par.add_argument('-g', '--game', type=int, nargs=1,
        action='store', choices=list(range(7)),
        help='game ROM slot number to program - THIS WILL OVERWRITE FACTORY PROGRAMMED ROM DATA'
        )
par.add_argument('-c', '--custom', type=int, nargs=1,
        action='store', choices=list(range(7)),
        help='custom ROM slot number to program'
        )
par.add_argument('bin', metavar='F', nargs='*',
        action='store', 
        help=('output filename for reading from VSU-2, or input filesname for writing to VSU-2\n'
            'separate files for U9 and U10 can be provided:\n'
            'ex:\n'
            '\tpython pyvsu.py -c 0 SND_U9.716 SND_U10.716')
        )
args = par.parse_args()
print(args)
#par.add_argument('-d', 
