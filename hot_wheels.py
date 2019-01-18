
# ------------__ Hacking STEM – hot_wheels.py – micro:bit __-----------
# For use with the Hot Wheels Measuring Speed to Understand Forces and
# Motion Lesson plan available from Microsoft Education Workshop at
# http://aka.ms/hackingSTEM
#
#  Overview:
#  This project makes use of 2 to 9 digital pins connected as
#  gate switches along a Hot Wheels race track as well as the micro:bit
#  internal accelerometer. Project allows users to track interval
#  between gates and gforce of impact with end stop.
#
#  This project uses a BBC micro:bit microcontroller, information at:
#  https://microbit.org/
#
#  Comments, contributions, suggestions, bug reports, and feature
#  requests are welcome! For source code and bug reports see:
#  http://github.com/[TODO github path to Hacking STEM]
#
#  Copyright 2018, Jeremy Franklin-Ross
#  Microsoft EDU Workshop - HackingSTEM
#  MIT License terms detailed in LICENSE.txt
# ===---------------------------------------------------------------===

from microbit import *

# 9 possible gate pins
gate_switch_pins = [pin6, pin7, pin8, pin9, pin10, pin13, pin14, pin15, pin16]

# gate one trigger time
first_gate_switch_triggered_millis = 0

# time passed since first gate triggered
gate_switch_triggered_millis = [0,0,0,0,0,0,0,0,0]

# number of gates, can be set by Serial control
gate_switch_count = 3

# largest Y value seen
max_y = 0

# minimum Y change needed to consider movement to have occured
delta_Y_threshold = 70

# calculated to account for gravity effecting tilted accelerometer
base_y = 0

# toggled when accelerometer read is complete
read_complete = False

# End of line string
EOL="\n"

# The microbit analog scale factor
SCALE_FACTOR_4G = 0.001953125

def command(a, c):
    """ send command to accelerometer """
    i2c.write(a, bytearray(c))

def i2c_read(a, register):
    """ read accelerometer register """
    i2c.write(a, bytearray(register), repeat=True)
    read_byte = i2c.read(a, 1)
    return read_byte

# Detect accelerometer variant and configure accelerometer to 8G
MMA8653_ACCEL = 0x1d # (0x3A/0x3B)
LSM303_ACCEL =  0x19 #(0x3C/0x3D)
FXOS8700_ACCEL = 0x1E #(0x32/0x33)

i2c_addresses = i2c.scan()

if (MMA8653_ACCEL in i2c_addresses and 
		i2c_read(MMA8653_ACCEL, [0x0D]) == bytes([0x5A])):
	command(MMA8653_ACCEL, [0x2a, 0x00]) #STAND BY
	command(MMA8653_ACCEL, [0x0e, 0x01]) # Set to 4G
	command(MMA8653_ACCEL, [0x2a, 0x01]) # ACTIVE
elif (LSM303_ACCEL in i2c_addresses and
		i2c_read(LSM303_ACCEL, [0x0F]) == bytes([0x33])):
	command(LSM303_ACCEL, [0x23, 0x80 |  0x10 ]) #SET 4 g
elif (FXOS8700_ACCEL in i2c_addresses and
		i2c_read(FXOS8700_ACCEL, [0x0D]) == bytes([0xC7])):
	command(FXOS8700_ACCEL, [0x0E, 0x1]) #UNTESTED!
else:
	while True:
		display.scroll("Unsupported microbit model", delay=90)




def convert_to_g(f):
    """ Convert a reading from accelerometer into Gs """
    return f*SCALE_FACTOR_4G

def read_accelerometer():
    """ Read the important axis from accelerometer and invert it """
    return 0 - accelerometer.get_y()

def reset_state():
    global first_gate_switch_triggered_millis, first_gate_switch_triggered_millis, max_y, base_y, read_complete
    uart.write("999,0,0,0,0,0,0,0,0,0,"+EOL)
    first_gate_switch_triggered_millis = 0
    for i in range(0,gate_switch_count):
        gate_switch_triggered_millis[i] = 0
    read_complete = False
    max_y = 0

    # wait for a second before base_y, the microbit may be moving
    sleep(1000)
    base_y = read_accelerometer()
    #TODO delete
#    uart.write("0,0,0,0,0,0,0,0,0,0,RESET,"+EOL)

# Set up & config
display.off() # liberates display pins for use as i/o
uart.init(baudrate=9600) # set serial data rate


# initialize all pins to digital read, this clears internal state
for i in range(0,9):
    gate_switch_pins[i].read_digital()

# initialize base_y to current accelerometer read """
base_y = read_accelerometer()

def last_gate_was_triggered():
    """ returns true if final gate was triggered """
    return gate_switch_triggered_millis[gate_switch_count - 1] > 0

def first_gate_was_triggered():
    """ return true if first gate was triggered """
    return first_gate_switch_triggered_millis > 0

def poll_gates():
    """ Poll all gates until last gate is triggered or reset """
    global gate_switch_triggered_millis
    #TODO rename get_data() to something clearer
    while not(last_gate_was_triggered()) and not get_data():
        # examine each gate and update the interval milliseconds
        for i in range(1, gate_switch_count):
            if gate_switch_pins[i].read_digital() == 1 and gate_switch_triggered_millis[i] == 0:
                gate_switch_triggered_millis[i] = running_time() - first_gate_switch_triggered_millis
                write_results_to_serial()

def write_results_to_serial():
    #TODO replace with more succinct csv assembly
    for i in range(0,9):
        uart.write(""+str(gate_switch_triggered_millis[i])+",")
#    uart.write(str(convert_to_g(max_y))+",RESULT,"+EOL)
    uart.write(str(convert_to_g(max_y))+","+EOL)

def poll_accelerometer():
    """
    Poll accelerometer until it moves more than threshold,
    then take highest measurement over 100 reads
    """
    # TODO will hang here until Y moves, add timeout
    global max_y, base_y, read_complete

    # wait for movement beyond threshold
    cur_y = read_accelerometer()

    while ((cur_y-base_y) < delta_Y_threshold):
        # sleep(1)
        sleep(1) # accelerometer produces noise if read too fast
        cur_y = read_accelerometer()

    max_y = cur_y # update max_y to highest value seen

    # take 100 samples Y (including the above) and keep the highest
    for i in range(0,99):
        cur_y = read_accelerometer()
        max_y = max_y if (max_y > cur_y) else cur_y
        sleep(1) # accelerometer produces noise if read too fast

    max_y = max_y - base_y #peel off base value

    write_results_to_serial()
    read_complete = True

def get_data():
    """
        gets comma delimited data from serial
        applies changes appropriately

        returns true if reset received
    """
    global gate_switch_count
    built_string = ""
    while uart.any() is True:
        byte_in = uart.read(1)
        if byte_in == b'\n':
            continue
        byte_in = str(byte_in)
        split_byte = byte_in.split("'")
        built_string += split_byte[1]
    if built_string is not "":
        if built_string != "":
            parsed_data = built_string.split(",")
            try:
                reset_str = parsed_data[0]
                gate_count_str = parsed_data[1]
            except IndexError:
                return

            if gate_count_str:
                if int(gate_count_str) > 1:
                    gate_switch_count = int(gate_count_str)

            if reset_str and int(reset_str) == 1:
                reset_state()
                return True
    return False

#uart.write(EOL+"0,0,0,0,0,0,0,0,0,0,BEGIN,"+EOL) # start with a clear line
uart.write(EOL+"999,0,0,0,0,0,0,0,0,0,"+EOL) # start with a clear line

""" Main program loop """
while (True):
    max_y = 0

    #Check serial for reset and new gate switch count
    get_data()

    if first_gate_was_triggered() and not read_complete:
        write_results_to_serial()
        # hangs in poll_gates until last gate is hit
        poll_gates()

        if last_gate_was_triggered():
            #hangs in poll_accelerometer() until accel is hit
            poll_accelerometer()
    elif gate_switch_pins[0].read_digital() == 1:
        """
        check first pin only if it wasn't triggered
        AND read is not complete
        """
        first_gate_switch_triggered_millis = running_time()
