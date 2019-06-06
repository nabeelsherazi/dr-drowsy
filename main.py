# Dr. Drowsy
# Running on CircuitPython 3.1.1 :)

import time
from analogio import AnalogIn
from digitalio import DigitalInOut, Direction, Pull
import board
print("Compiling...")

######################### PIN DEFINITIONS #######################

# Analog input pin 1

analog_input = AnalogIn(board.A2)

# Digital out pin 3

blue_led = DigitalInOut(board.D3)
blue_led.direction = Direction.OUTPUT

######################### SETTINGS ##############################

settings = {
    "_tracked_pin": analog_input,
    "_sensitivity": 10,
    "_sma_period": 0.5,
    "_max_sma_window": 6,
    "_max_blink_window": 64,
    "log_mode": "blinks only"
}

# Log mode in ["blinks only", "essentials", "verbose", "plotting"]

######################### HELPERS ##############################

# Helper to convert analog input to voltage


def getVoltage(pin):
    return (pin.value * 3.3) / 65536


# Statistic helpers

def mean(data):
    """Return the sample arithmetic mean of data."""
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
    standard deviation."""
    n = len(data)
    if n < 2:
        raise ValueError('variance requires at least two data points')
    ss = _ss(data)
    pvar = ss/(n-ddof)
    return pvar**0.5

# Object definitions


class Blink:
    def __init__(self):
        self.start_time = time.monotonic()

    def mark_end(self):
        self.end_time = time.monotonic()

    def get_duration(self):
        return float(self.end_time - self.start_time)


class SignalTracker:
    # Object for collecting and managing input data.
    def __init__(self, _tracked_pin, _sensitivity, _sma_period=1, _max_sma_window=16, _max_blink_window=256, log_mode="essentials"):
        self.TRACKING = _tracked_pin
        self.SENSITIVITY = _sensitivity
        self.SMA_PERIOD = _sma_period  # Period to average over, in seconds
        self.MAX_SMA_WINDOW = _max_sma_window  # Maximum length of period_average_series
        print("Initialized to roll averages over a {} second window".format(
            self.MAX_SMA_WINDOW * self.SMA_PERIOD))
        self.MAX_BLINK_WINDOW = _max_blink_window
        print("Keeping last {} blinks, approximately {} minutes of data (average conditions).".format(
            self.MAX_BLINK_WINDOW, self.MAX_BLINK_WINDOW // 20))
        print("Sensitivity is {}".format(self.SENSITIVITY))
        # Flips to True when period average window long enough to compare values to
        self.SMA_WINDOW_READY = False
        self.BLINK_WINDOW_READY = False  # Same
        if log_mode not in ["blinks only", "essentials", "verbose", "plotting"]:
            raise TypeError("Initialization failed: Log mode not valid")
        self.LOG_MODE = log_mode
        print("Log mode set to {}".format(self.LOG_MODE.upper()))
        self.current_period_start_time = time.monotonic()
        self.raw_data_series = []
        self.last_period_average = None
        self.period_average_series = []
        self.blink_series = []
        self.current_blink = None
        self.timer = None  # Utility

    def record_data(self):
        _current_voltage = getVoltage(self.TRACKING)
        self.raw_data_series.append(_current_voltage)
        # print((_current_voltage,))
        return _current_voltage

    def period_is_over(self):
        # Checks if current SMA period is over. Returns bool.
        return (time.monotonic() - self.current_period_start_time) >= self.SMA_PERIOD

    def take_average(self):
        self.last_period_average = mean(self.raw_data_series)
        # Add current average to series
        self.period_average_series.append(self.last_period_average)
        if self.LOG_MODE == "plotting":
            # Formatted for Mu serial plotter (print a tuple)
            print((self.last_period_average,))
        # Set new period current start time
        self.current_period_start_time = time.monotonic()

    def flush_raw_data_series(self):
        self.raw_data_series = []

    def roll_average_window(self, frac_to_keep):
        # Needed because average series is used on a rolling basis
        try:
            self.period_average_series = self.period_average_series[round(
                (1 - frac_to_keep) * self.MAX_SMA_WINDOW):]
        except IndexError as e:
            e.message = "frac_to_keep must be in range (0, 1)."

        if self.LOG_MODE == "essentials":
            print("Rolled averaging window")

    def roll_blink_window(self, frac_to_keep):
        # Same
        try:
            self.blink_series = self.blink_series[round(
                (1 - frac_to_keep) * self.MAX_BLINK_WINDOW):]
        except IndexError as e:
            e.message = "frac_to_keep must be in range (0, 1)."

        if self.LOG_MODE == "essentials":
            print("Rolled averaging window")

    def average_series_over_max_size(self):
        return len(self.period_average_series) >= self.MAX_SMA_WINDOW

    def blink_series_over_max_size(self):
        return len(self.blink_series) >= self.MAX_BLINK_WINDOW

    def get_blink_voltage_threshold(self):
        distance = self.SENSITIVITY * stddev(self.period_average_series)
        if distance < 0.5:
            distance = 0.5
        thresh = self.period_average_series[-1] - distance
        return thresh

    def start_blink(self):
        self.current_blink = Blink()
        if self.LOG_MODE in ["blinks only", "essentials", "verbose"]:
            print("Detected start of blink.")

    def end_blink(self):
        self.current_blink.mark_end()
        self.blink_series.append(self.current_blink)
        if self.LOG_MODE in ["blinks only", "essentials", "verbose"]:
            print("Detected end of blink, duration: {}".format(
                self.current_blink.get_duration()))
        self.current_blink = None

    def status_report(self):
        print('-'*80)
        current_stddev = stddev(self.period_average_series)
        print("Current standard deviation of period averages is {}".format(
            current_stddev))
        print("Current threshold for blink detection is input voltage less than {} V.".format(
            self.get_blink_voltage_threshold()))
        print("Current SMA window size is {}".format(
            len(self.period_average_series)))
        print("Current number of recorded blinks is {}.".format(
            len(self.blink_series)))
        print('-'*80)


######################### MAIN LOOP ##############################

i = 0
st = SignalTracker(**settings)
time.sleep(1)

print("Initialized successfully: starting main loop")
while True:

    current_voltage = st.record_data()

    if st.period_is_over():
        st.take_average()
        st.flush_raw_data_series()

    if st.average_series_over_max_size():
        st.SMA_WINDOW_READY = True
        st.roll_average_window(frac_to_keep=0.75)

    if st.blink_series_over_max_size():
        st.BLINK_WINDOW_READY = True
        st.roll_blink_window(frac_to_keep=0.75)

    if st.SMA_WINDOW_READY:
        # Start voltage comparisons
        if current_voltage <= st.get_blink_voltage_threshold() and st.current_blink is None:
            st.start_blink()
        elif current_voltage > st.get_blink_voltage_threshold() and st.current_blink is not None:
            st.end_blink()

        if i % 256 == 0 and st.LOG_MODE == "verbose":
            st.status_report()

    if st.BLINK_WINDOW_READY:
        # Start blink comparisons
        if (time.monotonic() - st.timer) < 30:
            continue  # Short circuit
        if mean(st.blink_series[-3:]) >= mean(st.blink_series) + 1.5 * stddev(st.blink_series):
            blue_led.value = True
            st.timer = time.monotonic()
        else:
            blue_led.value = False
            st.timer = None

    # END REAL PROCESSING
    i = (i+1) % 256
