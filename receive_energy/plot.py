from pathlib import Path, PosixPath
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import math
import re

SYNC_TRANSMISSIONS = 250
# Calculation(ROW_ERROR_PER_SYNC_TRANSMISSION): (SYNC_ROWS_FOR_250_TRANSMISSIONS_AT_250_kbps_128_byte_FRAME_LENGTH - 250 * transmission_duration / interval_us) / 250
# SYNC_ROWS_FOR_250_TRANSMISSIONS_AT_250_kbps_128_byte_FRAME_LENGTH = 1120
ROW_ERROR_PER_SYNC_TRANSMISSION = 0.7620745563241412
CASES = 30
CASE_DURATION = 4 # seconds
TRANSMISSION_RATE = 250 # kb/s
FRAME_LENGTH = 128 # Byte
START_UP = 10 # seconds

def parse(path: PosixPath, isReceive: bool, plot):
    df = pd.read_csv(path,
        skiprows=9,
#       nrows=10000,
        sep='\t',
        header=None,
        usecols=[3,4,5,6,7],
        names=['time_s','time_us','power','voltage','current'])
        
    # remove outliers
    df = df[df['power'] > 0]
    df = df[df['power'] < 1000]
    df = df[df['current'] > 0]
    df = df[df['current'] < 1000]
    df = df[df['voltage'] > 0]
    df = df[df['voltage'] < 1000]

    df['time'] = 1000000 * df['time_s']+df['time_us']

    interval_us = np.mean(np.diff(df['time'].head(30)))
    case_rows = (1000000 * CASE_DURATION)/interval_us
    transmission_duration = (8 * FRAME_LENGTH) / (TRANSMISSION_RATE / 1000) # us / microseconds
#    sync_rows = math.ceil(SYNC_TRANSMISSIONS * transmission_duration / interval_us + SYNC_TRANSMISSIONS * ROW_ERROR_PER_SYNC_TRANSMISSION)
    transmission_rows = 1 + math.ceil(transmission_duration / interval_us)
    sync_rows = math.ceil(250 * transmission_duration / interval_us)

    # Generate synchronization list
    sync = np.repeat([1], sync_rows)
#    sync = np.repeat([0.85], sync_rows)

    # Remove first half of start-up
    start_up_rows = int((1000000 * START_UP / 2) / interval_us)
    df = df.iloc[start_up_rows:].reset_index()
    minpower = np.min(df['power'])
    maxpower = np.max(df['power'])

    # Correlate with first two repetitions to get start
    head = df['power'].head(int(5*case_rows))
    if isReceive:
        head = head.apply(lambda x: (x - minpower)/(maxpower-minpower))
        window_var = head.rolling(sync_rows).var()
        start = window_var.idxmax() - sync_rows
        if plot:
            plt.plot(head)
            plt.plot(window_var)
            plt.show()
    else:
        head = [(x - minpower)/(maxpower-minpower) for x in head] # normalize
        correlation = np.correlate(head,sync)
        start = np.argmax(correlation)
        if plot:
            plt.plot(head)
            plt.plot(correlation)
            plt.show()

    # Remove rows before start
    df = df.iloc[start:].reset_index()
    
    # Remove rows not relating to any case
#    df = df[:-int(len(df.index) - CASES*case_rows)]

#    # Visualize cases
#    visual = []
#    for i in range(0,CASES):
#        if i%2 == 0:
#            visual.append(0.145)
#        else:
#            visual.append(0.15)
#    visual = np.repeat(visual, case_rows)
#    # Plot the power and the synchronization sequence
#    plt.plot(np.append(sync, visual))
#    plt.plot(df['power'])
#    # ERROR ANALYSIS
#    #plt.plot(head[start:])
#    plt.plot(sync)
#    #plt.plot(correlation)
#    plt.show()

    return df

if __name__ == "__main__":
    plot = False

    pd.options.display.float_format = '{:,.2f}'.format

    pathlist = Path("/Users/dennis/Code/IOTLAB_ENERGY/receive_energy/raw_data_OS_0.4/").rglob("*.oml")
    for path in pathlist:
        m = re.search(r"m3[-_]([0-9]*)[-_](.*?(?=\.oml))", str(path.name))
        print(path.name)
        df = parse(path, m.group(2) == "receive", plot)

        plt.plot(df['power'], label=m.group(2))

    plt.legend()
    plt.show()
