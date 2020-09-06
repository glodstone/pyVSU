#! /usr/bin/env python3

# Copyright (c) 2020 Jarret Whetstone, GLODSTONE LLC
# 
# Permission is hereby granted, free of charge, to any person obtaining a copy
# of this software and associated documentation files (the "Software"), to deal
# in the Software without restriction, including without limitation the rights
# to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
# copies of the Software, and to permit persons to whom the Software is
# furnished to do so, subject to the following conditions:
# 
# The above copyright notice and this permission notice shall be included in all
# copies or substantial portions of the Software.
# 
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
# IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
# FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
# AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
# LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
# OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
# SOFTWARE.


# the core of the VSU-2 is the PIC 18F47Q10
# which has 128Kb of program memory, the upper 64Kb of which
# is reserved for configuration information and game ROMs
# 
# this 64Kb of memory is organized into 256 "sectors" of 256 bytes
# all game ROMs occupy 4Kb (16 contiguous sectors) as sequential slots
# selectable by the 4 dip switches on the board
# regardless of the actual space the game requires 
#
# sector 0 is reserved for "factory programming" and can
# not be modified over the serial interface
#
# sector 1 is reserved for "user configuration" and will
# override the factory values unless they are absent
# or violate system constraints
# 
# sector 2+ is the start of ROM data
# commands for programming separate "game" slots from
# "custom" slots to lower the risk of overwriting
# included ROMs by accident
#
# all ROM files provided must be in binary format
# i.e. not in HEX file format



try:
    import serial
    import serial.tools.list_ports as comports
except ImportError:
    print('Unable to load pySerial - is it installed?')
import argparse
import time

par = argparse.ArgumentParser(
        description='pyVSU-2 ROM programming and configuration utility',
        formatter_class=argparse.RawTextHelpFormatter
        )
par.add_argument('-p', '--port', type=str, nargs=1,
        action='store', choices=[_.device for _ in list(comports.comports())],
        help='name of serial device conected to VSU-2',
        required=True
        )
bulk_grp = par.add_mutually_exclusive_group()
bulk_grp.add_argument('-d', '--dump', action='store_true',
        help='dump device image to specified filename'
        )
bulk_grp.add_argument('-i', '--image', action='store_true',
        help='write specified image file to device'
        )
rom_grp = par.add_mutually_exclusive_group()
rom_grp.add_argument('-g', '--game', type=int, nargs=1,
        action='store', choices=list(range(7)),
        help='game ROM slot number to program - THIS WILL OVERWRITE FACTORY PROGRAMMED ROM DATA'
        )
rom_grp.add_argument('-c', '--custom', type=int, nargs=1,
        action='store', choices=list(range(7)),
        help='custom ROM slot number to program'
        )
par.add_argument('bin', metavar='F', nargs='*',
        action='store', 
        help=('output filename for reading from VSU-2, or input filesname for writing to VSU-2\n'
            'separate files for U9 and U10 can be provided\n'
            'always specify U9 and U10 in order\n'
            'ex:\n'
            '\tpython pyvsu.py -c 0 SND_U9.716 SND_U10.716')
        )
args = par.parse_args()
print(args)

class WriteSectorException(Exception):
    def __init__(self, sector):
        self.sector = sector
    def __str__(self):
        return repr('Error writing to sector: {}'.format(self.sector))

class ReadSectorException(Exception):
    def __init__(self, sector):
        self.sector = sector
    def __str__(self):
        return repr('error reading from sector: {}'.format(self.sector))

class IncompleteDataException(Exception):
    def __init__(self, length):
        self.length = length
    def __str__(self):
        return repr('data written to sector must be 256 bytes, size provided: {} bytes'.format(self.length))

def read_sector(sector):
    # the read command is 'r' followed by a sector number
    # command 'r' + sector number
    vsu_rom.write(bytes([114,sector]))

    # response will be the 256 bytes of the sector
    sector_data = vsu_rom.read(256)

    # successful command will be followed by a '+'
    if vsu_rom.read(1) != b'+':
        raise ReadSectorException(sector)

    return sector_data

def write_sector(sector, data):
    # write command is 'w' followed by a sector number: 0h to FFh
    # device does not allow writes to sector zero (factory data)
    # will wait until nonzero value is provided
    # sector zero must be programmed via ICSP
    if sector == 0 or sector >= 256:
        return
    if len(data) != 256:
        raise IncompleteDataException(len(data))

    # send command 'w' + sector number
    vsu_rom.write(bytes([119,sector]))

    vsu_rom.write(data)
    # the microcontroller CPU will stall for a few milliseconds
    # while the write completes
    time.sleep(.01)
    # successful command will be followed by a '+'
    if vsu_rom.read(1) != b'+':
        raise WriteSectorException(sector)

    # error checking is accomplished by reading the
    # newly written data and comparing
    if read_sector(sector) != data:
        raise WriteSectorException(sector)

    return

def dump_image(filename):
    print('dumping memory...')
    data = bytearray()
    for x in range(256):
        print('\rreading sector: {}/255'.format(x), end='', flush=True)
        data.extend(read_sector(x))
    print('\nwriting file: {}'.format(filename))
    with open(filename, 'wb') as output:
        output.write(data)

def write_image(filename):
    print('writing image...')
    with open(filename, 'rb') as image:
        image_data = image.read()
        if len(image_data) != 65536:
            print('error: image file size should be 65536 bytes (64Kb), aborting operation')
            exit()
        image.seek(0)
        sector = 0
        for x in range(256):
            print('\rwriting sector: {}/255'.format(x), end='', flush=True)
            write_sector(x, image.read(256))

def write_rom(sector, data):
    print('writing rom...')
    for x in range(16):
        write_sector(sector+x, data[x*256:(x*256)+256])


with serial.Serial(args.port[0], 115200, timeout=1) as vsu_rom:
    if len(args.bin) > 2:
        print('a maximum of 2 filenames may be specified')
        exit()


    if args.dump:
        if len(args.bin) != 1:
            print('please specify a filename to write memory contents')
            exit()
        dump_image(args.bin[0])
    elif args.image:
        if len(args.bin) != 1:
            print('please specify a filename with a valid image')
            exit()
        write_image(args.bin[0])
    elif args.game or args.custom:
        # offset two sectors for factory/user config
        sector = 2
        if args.game:
            # each ROM occupies 4Kb / 16 sectors
            sector += args.game[0] * 16
        else:
            # custom files come after all games, offset 96 sectors
            sector += (args.custom[0] * 16) + 96

        rom_data = bytearray()
        for f in args.bin:
            with open(f, 'rb') as rom_file:
                rom_data.extend(rom_file.read())
        if len(rom_data) == 2048:
            rom_data.extend(b'\xff' * 2048)
        if len(rom_data) != 4096:
            print('error: ROM must be a total of 2048 or 4096 bytes')
            exit()

        write_rom(sector, rom_data)
    print('operation complete')
