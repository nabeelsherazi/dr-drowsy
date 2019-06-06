# Dr. Drowsy
# Copyright Nabeel Sherazi 2019, sherazi.n@husky.neu.edu
# This code is made open source under a GPL license.
# Running on CircuitPython 3.1.1 :)

import time
from analogio import AnalogIn
from digitalio import DigitalInOut, Direction, Pull
import board
print("Compiling...")

######################### PIN DEFINITIONS #######################

# Analog input pin 0

analog_input = AnalogIn(board.A1)

# Digital out pin 3

blue_led = DigitalInOut(board.D3)
blue_led.direction = Direction.OUTPUT

######################### HELPERS ##############################

# Helper to convert analog input to voltage

def getVoltage(pin):
    return (pin.value * 3.3) / 65536


# Statistic helpers

def mean(data, filter_data=False):
    """Return the sample arithmetic mean of data. Can filter out None (but doesn't by default)."""
    if filter_data:
        data = list(filter(is_not_None_or_int, data))
    n = len(data)
    if n < 1:
        raise ValueError('mean requires at least one data point')
    return sum(data)/n


def _ss(data):
    """Return sum of square deviations of sequence data."""
    c = mean(data)
    ss = sum((x-c)**2 for x in data)
    return ss


def stddev(data, ddof=0):
    """Calculates the population standard deviation
    by default; specify ddof=1 to compute the sample
    standard deviation. Filters out None and int always."""
    data = list(filter(is_not_None_or_int, data))
    n = len(data)
    if n < 2:
        raise ValueError('variance requires at least two data points')
    ss = _ss(data)
    pvar = ss/(n-ddof)
    return pvar**0.5

def is_not_None_or_int(item):
    # Filters out the final value without us having to make a new list
    # since list is all floats and ints do not match against floats
    return item is not None and item is not 0 and item is not 1

# Window pointer helpers

def get_pointer(window):
    window[0] = (window[0] + 1) % window[1]
    return window[0]

def pointer_at_max(window):
    return window[0] == window[1] - 1

# Blink helpers and class definitions

def get_blink_voltage_threshold():
    distance = SENSITIVITY * stddev(period_average_series)
    if distance < 0.5:
        distance = 0.5
    thresh = mean(period_average_series) + distance
    return thresh

class Blink:
    def __init__(self):
        self.start_time = time.monotonic()
        self.end_time = 0.00
    def mark_end(self):
        self.end_time = time.monotonic()
        print("New blink created of length {} seconds".format(self.get_duration()))
    def get_duration(self):
        return self.end_time - self.start_time


######################### SETTINGS ###################################


RAW_WINDOW = [-1, 128]  # [pointer, window_size], list (NOT tuple) because pointer is mutable
SMA_WINDOW = [-1, 8]    # Start pointer at -1 because get_pointer increments on call (first call increments to zero)
BLINK_WINDOW = [-1, 16]

SENSITIVITY = 10        # Gain for blink detection


######################### GLOBAL FRIENDS ##############################


raw_data_series = [0.00] * RAW_WINDOW[1]  # Initialize memory as floats so that word size doesn't change on first fill
raw_data_series[-1] = 0  # Since last index is never used (pointer loops between 0 and MAX-1)
                         # we use it to store if window is ready (0 or 1)
# Important note: '0.00 is 0 -> False', this is why we use our special test for filter()
# We can differentiate the window ready variable from actual data form it being an int instead of a float
last_period_average = None
current_period_start_time = time.monotonic()
period_average_series = [0.00] * SMA_WINDOW[1]
period_average_series[-1] = 0
last_blink = None
blink_series = [None] * BLINK_WINDOW[1] # Initialize blink_series as a list of None because word size is most similar to Blink
blink_series[-1] = 0

calibration_blinks = []
CALIBRATING = True
BASELINE_BLINK_TIME = 0.00

STARTED_BLUE_LED = 0.00
DROWSY_TIMER = 30.0 # seconds

i = 0 # Diagnostic counter

######################### MAIN LOOP ##############################

time.sleep(1)
print("Initialized successfully: starting blink calibration")

while True:
    i = (i + 1) % 256

    # RECORD DATA
    # Record data in pointer position on raw data series
    current_voltage = getVoltage(analog_input)
    raw_data_series[get_pointer(RAW_WINDOW)] = current_voltage
    # print((current_voltage,)) # Uncomment to plot on Mu plotter

    # CHECK IF WINDOWS READY
    # Once window is full, flip last value to indicate window ready
    # For raw data window, average is taken every time window is full
    if pointer_at_max(RAW_WINDOW):
        raw_data_series[-1] = 1
        last_period_average = mean(raw_data_series, filter_data=True)  # Take average
        period_average_series[get_pointer(SMA_WINDOW)] = last_period_average  # Store average in pointer

    if pointer_at_max(SMA_WINDOW):
        period_average_series[-1] = 1  # Flip only, averages are done on rolling basis

    if len(list(filter(is_not_None_or_int, blink_series))) >= 5:
        # Once we have at least 5 blinks, we're ready to go
        # Flip window ready
        blink_series[-1] = 1

    # Take SMA rolling average
    if period_average_series[-1]: # Window ready
        # Start voltage comparisons
        if current_voltage >= get_blink_voltage_threshold() and last_blink is None:
            last_blink = Blink()
        elif current_voltage < get_blink_voltage_threshold() and last_blink is not None:
            last_blink.mark_end()
            if CALIBRATING:
                calibration_blinks.append(last_blink)  # If calibrating, add to calibration blinks list
                # Only store three though
                if len(calibration_blinks) >= 3:
                    # Once we have three, turn off calibrating and skip this code block on future iters
                    CALIBRATING = False
                    BASELINE_BLINK_TIME = mean(list(map(lambda b: b.get_duration(), calibration_blinks)))
                    print("Calibrated. Baseline blink time is {}".format(BASELINE_BLINK_TIME))
                    print("Starting drowsiness detection.")
                    del calibration_blinks # Delete this list once we're done with it
                    # TODO: add LED blinking to show calibration is done
            else:
                # If previous code block is skipped (not in calibrating), add to blink_series instead
                blink_series[get_pointer(BLINK_WINDOW)] = last_blink
            # Finally, unset last_blink to show blink is over
            last_blink = None

    if blink_series[-1]: # Blink window ready
        if STARTED_BLUE_LED and (time.monotonic() - STARTED_BLUE_LED) < DROWSY_TIMER:
            continue # If timer exists and is not over yet, skip all other code in this iter
                     # this prevents the LED from being shut off by blink condition being satisfied if timer
                     # isn't over yet
        elif STARTED_BLUE_LED and (time.monotonic() - STARTED_BLUE_LED) >= DROWSY_TIMER:
            # If timer exists and time is up, turn off the blue LED
            print("Turning off blue LED")
            blue_led.value = False
            STARTED_BLUE_LED = 0.00

        # Now, if we're here, then either timer is over and might be unset, or there is no timer and we should check if
        # blue LED needs to be turned on

        # First check if mean of last three blinks are significantly longer than the baseline
        if BLINK_WINDOW[0] < 3: # This is a special case if the pointer is at a position less than 3.
                                # Since Python list indexing does not wrap by language spec (list[-2:1] -> [])
                                # We use a fun modulo trick to get the correct values
            last_three_blinks = [blink_series[BLINK_WINDOW[0]], blink_series[(BLINK_WINDOW[0] - 1) % BLINK_WINDOW[1]], blink_series[(BLINK_WINDOW[0] - 2) % BLINK_WINDOW[1]]]
        else:
            # For pointer positions greater than 3, regular indexing works fine
            last_three_blinks = blink_series[BLINK_WINDOW[0] - 3 : BLINK_WINDOW[0]]
        
        last_three_blink_durations = list(map(lambda b: b.get_duration(), last_three_blinks))
        last_three_blink_mean_duration = mean(last_three_blink_durations)

        if last_three_blink_mean_duration >= 2 * BASELINE_BLINK_TIME:
            # If all condiitons met, turn on blue LED
            print("Turning on blue LED")
            blue_led.value = True
            STARTED_BLUE_LED = time.monotonic()
            
        if i == 0:
            # Diagonistic once every 256 loops
            print("Mean duration of last three blinks was {} seconds".format(last_three_blink_mean_duration))