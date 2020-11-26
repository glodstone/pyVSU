# pyVSU
pyVSU is a command line configuration and programming utility for the VSU-2 speech synthesizer.

## Prerequisites
* Python 3.6+
* [pySerial](https://github.com/pyserial/pyserial)
* 3.3/5v UART cable.

## Memory Organization
The VSU-2 contains ~64k of user programmable memory, divided in to 256 sectors of 256 bytes.  The first two sectors of memory contain configuration programming, followed by slots of ROM data in sequential 16 sector (4k) blocks.
Sector 0 contains factory default configuration data, and cannot be overwritten with this programming utility.

## Establishing Communication
### Connect the UART
The UART pin header is 6 pins located on the lower left corner of the board
| pin | function |
|:-:|:-:|
| 1 | GND |
| 2 | - |
| 3 | +5V |
| 4 | RX |
| 5 | TX |
| 6 | - |

### Set the power jumper
There is a single jumper on the right side of the board near header J3.  This jumper switches the power source to the 5V UART header.  Note that the green power LED may illuminate upon connecting the UART due to power backfeed, however there will be insufficient power to communicate with the microcontroller until this jumper is in the correct position.
Be certain to replace the jumper back to the GAME position before installing the board.

### Run pyVSU
Run `pyvsu.py` and specify the serial port with the `-p` parameter, followed by the '-i' option to display configuration data:
```
$ python pyvsu.py -p COM4 -i
VSU-2 Configuration:
          factory                            user
   volume │  sample rate            volume │  sample rate
  ┌───────┼────────────────        ┌───────┼────────────────
 0│    17 │ 192 (10283 hz)        0│   N/A │     N/A
 1│    12 │ 183 (10782 hz)        1│   N/A │     N/A
 2│     8 │ 167 (11799 hz)        2│   N/A │     N/A
 3│     6 │ 148 (13289 hz)        3│   N/A │     N/A
 4│     4 │ 134 (14652 hz)        4│   N/A │     N/A
 5│     3 │ 122 (16064 hz)        5│   N/A │     N/A
 6│     2 │ 112 (17467 hz)        6│   N/A │     N/A
 7│     0 │ 104 (18779 hz)        7│   N/A │     N/A

```
If you encounter the error `__main__.ReadSectorException: 'error reading from sector: 0'` check connections, power, power jumper, the correct device/com port is specified, and that TX and RX are not reversed.

### Program a ROM
Use the `-c` option followed by a number to program a ROM into a custom slot.  If your ROM is contained in two different files (one for each original 2716 IC), include both filenames.
```
$ python pyvsu.py -p COM4 -c 0 SND_U9.716 SND_U10.716
writing rom...
ROM programmed, use the switch settings below:
        ┌──┐    ┌──┐    ┌──┐    ┌──┐
        │  │    │[]│    │[]│    │[]│
        │[]│    │  │    │  │    │  │
        └──┘    └──┘    └──┘    └──┘
         4       3       2       1

```
### Custom Configuration
#### Background
Games using the VSU-100 could select one of 8 different pitches (sample rate) and volumes through the use of two MC14051B multiplexers.  These can be custom configured on the VSU-2.  This volume setting affects the PWM output of the microcontroller and is independent of the analog audio control potentiometer on the board.
These settings are global to the device, and will apply to any game ROM selected for use.
Also note that each game typically uses a limited set of pitch and volume selections for speech, you may need to experiment to determine the correct value to adjust.
#### Valid user configuration settings
* A value of 255 for either volume or sample rate will read as N/A and default to factory setting when selected.
* Volume may be a value between 0 and 17, with 17 being maximum volume.  Higher values will default to factory setting.
* Sample rate may be a value between 0 and 254.  Extremely high and low rates may not be achievable by the device. Using rates outside the range of factory settings is not recommended, and may also cause unpredictable game behavior or damage to game components.
#### Set custom configuration values
Use the `-i` option followed by a filename to write the user configuration to file.
`python pyvsu.py -p COM4 -i settings.txt`

Modify the text file to make adjustments, and then write the data back with the '-u' parameter.
`python pyvsu.py -p COM4 -u settings.txt`

In this example, sample rate setting 2 has been modified
```$ python pyvsu.py -p COM4 -u settings.txt
writing user configuration...
VSU-2 Configuration:
          factory                            user
   volume │  sample rate            volume │  sample rate
  ┌───────┼────────────────        ┌───────┼────────────────
 0│    17 │ 192 (10283 hz)        0│   N/A │     N/A
 1│    12 │ 183 (10782 hz)        1│   N/A │     N/A
 2│     8 │ 167 (11799 hz)        2│   N/A │ 130 (15094 hz)
 3│     6 │ 148 (13289 hz)        3│   N/A │     N/A
 4│     4 │ 134 (14652 hz)        4│   N/A │     N/A
 5│     3 │ 122 (16064 hz)        5│   N/A │     N/A
 6│     2 │ 112 (17467 hz)        6│   N/A │     N/A
 7│     0 │ 104 (18779 hz)        7│   N/A │     N/A
```
