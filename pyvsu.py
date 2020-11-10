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
# although memory is contiguous, commands for programming 
# "game" slots are separate from "custom" slots
# to lower the risk of overwriting included ROMs by accident
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
import json

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
bulk_grp.add_argument('-w', '--write', action='store_true',
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
conf_grp = par.add_mutually_exclusive_group()
conf_grp.add_argument('-i', '--info', action='store_true',
        help=('display volume and sample rate configuration\n'
            'optionally provide a filename to output data for editing '
            'in JSON format')
        )
conf_grp.add_argument('-u', '--update', action='store_true',
        help='update VSU-2 volume and sample rate configuration with data from specified file'
        )
par.add_argument('bin', metavar='F', nargs='*',
        action='store', 
        help=('input/output filename(s) with use depending on command\n'
            'when writing a ROM, separate files for U9 and U10 can be provided\n'
            '*always specify U9 and U10 in order*\n\n'
            'example - program a ROM into custom slot 0:\n'
            '\tpython pyvsu.py -p COM1 -c 0 SND_U9.716 SND_U10.716')
        )
args = par.parse_args()

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

def display_switches(slot):
    slot = '{0:b}'.format(slot).zfill(4)
    img = [
            ['\t┌──┐','\t┌──┐'],
            ['\t│  │','\t│[]│'],
            ['\t│[]│','\t│  │'],
            ['\t└──┘','\t└──┘'],
            ['\t x  ','\t x  ']
            ]
    for line in img:
        print(''.join([line[int(_)].replace('x', str(4-i)) for i, _ in enumerate(slot)]))

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
    
    # error checking is accomplished automatically in write_sector()
    for x in range(16):
        write_sector(sector+x, data[x*256:(x*256)+256])

def display_configuration(out_file=None):
    factory = read_sector(0)
    user = read_sector(1)
    print('VSU-2 Configuration:')

    print('          factory                            user')
    print('   volume │  sample rate            volume │  sample rate')

    print('  ┌───────┼────────────────        ┌───────┼────────────────')
    for x in range(8):
        f_vol = factory[x]
        u_vol = user[x]
        
        # when user values are FFh, it means they have not been set
        # volume levels above 11h will overflow
        # exceeding this value will cause the microcontroller to
        # falling back to factory settings
        if u_vol > 17: # 11h
            u_vol = 'N/A'
        else:
            u_vol = '{:3d}'.format(u_vol)

        # sample rate is ((Fosc/4)/8)/(<setting>+3)
        # Fosc = 64 Mhz
        # 4 clock ticks per instruction cycle
        # timer prescaler of 8 cycles
        #
        # the +2.5 is approximate since
        # there is extra overhead in the interrupt routine

        # speed values are stored at an 8 byte offset from volume
        # factory speeds are assumed to always be valid
        f_spd = factory[x+8]
        f_sr = 2000000.0 / (f_spd+2.5)

        u_sr = user[x+8]
        if u_sr == 255:
            u_txt = '    N/A'
        else:
            u_spd = user[x+8]
            u_sr = 2000000.0 / (u_spd+2.5)
            u_txt = '{:3d} ({:5.0f} hz)'.format(u_spd, u_sr)

        print(' {}│   {:3d} │ {:3d} ({:5.0f} hz)        {}│   {} │ {}'.format(
                x, f_vol, f_spd, f_sr, x, u_vol, u_txt))

    if out_file is None:
        return
        
    u_spd = {i:_ for i, _ in enumerate(user[8:16])}
    u_vol = {i:_ for i, _ in enumerate(user[0:8])}

    with open(out_file, 'w') as handle:
        json.dump({'volume':u_vol,'sample_rate':u_spd},
                handle, indent=4, sort_keys=True)
    print('configuration written to: {}'.format(out_file))

def update_configuration(conf_file):

    print('writing user configuration...')

    with open(conf_file, 'r') as handle:
        conf = json.load(handle)
    sector_data = bytearray(b'\xff'*256)
    for x in range(8):
        sector_data[x] = conf['volume'][str(x)]
        sector_data[x+8] = conf['sample_rate'][str(x)]

    write_sector(1, sector_data)
    display_configuration()
        
with serial.Serial(args.port[0], 115200, timeout=1) as vsu_rom:
    if len(args.bin) > 2:
        print('a maximum of 2 filenames may be specified')
        exit()


    if args.dump:
        if len(args.bin) != 1:
            print('please specify a filename to write memory contents')
            exit()
        dump_image(args.bin[0])
    elif args.write:
        if len(args.bin) != 1:
            print('please specify a filename with a valid image')
            exit()
        write_image(args.bin[0])
    elif args.info:
        out_file = args.bin[0] if len(args.bin) == 1 else None
        display_configuration(out_file=out_file)
    elif args.update:
        if len(args.bin) != 1:
            print('please specify a configuration file')
            exit()
        update_configuration(args.bin[0])

    elif args.game or args.custom:
        # offset two sectors for factory/user config
        sector = 2
        if args.game:
            # each ROM occupies 4Kb / 16 sectors
            sector += args.game[0] * 16
        else:
            # custom files come after all games, offset 112 sectors
            sector += (args.custom[0] * 16) + 112

        rom_data = bytearray()
        for f in args.bin:
            with open(f, 'rb') as rom_file:
                rom_data.extend(rom_file.read())

        # certain games (flight2000) only have one rom, U9, populated
        # in this case we pad the remaining space
        if len(rom_data) == 2048:
            rom_data.extend(b'\xff' * 2048)
        if len(rom_data) != 4096:
            print('error: ROM must be a total of 2048 or 4096 bytes')
            exit()

        write_rom(sector, rom_data)
        print('ROM programmed, use the switch settings below:')
        display_switches(int((sector-2)/16))

    print('')
    print('operation complete')
