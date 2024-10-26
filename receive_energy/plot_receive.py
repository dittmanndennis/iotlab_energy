from pathlib import Path, PosixPath
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import math

SYNC_TRANSMISSIONS = 250
# Calculation(ROW_ERROR_PER_SYNC_TRANSMISSION): (SYNC_ROWS_FOR_250_TRANSMISSIONS_AT_250_kbps_128_byte_FRAME_LENGTH - 250 * transmission_duration / interval_us) / 250
# SYNC_ROWS_FOR_250_TRANSMISSIONS_AT_250_kbps_128_byte_FRAME_LENGTH = 1120
ROW_ERROR_PER_SYNC_TRANSMISSION = 0.7620745563241412
CASES = 30
CASE_DURATION = 4 # seconds
TRANSMISSION_RATE = 250 # kb/s
FRAME_LENGTH = 128 # Byte
START_UP = 9 # seconds

def parse(filename: PosixPath):
    df = pd.read_csv(filename,
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

    df['time'] = df['time_s']+df['time_us']/1000000

    interval_s = np.mean(np.diff(df['time'].head(20)))
    # Remove start-up
    start_up_rows = int(START_UP/interval_s)
    df = df.iloc[start_up_rows:].reset_index()
    case_rows = CASE_DURATION/interval_s
    transmission_duration = (8 * FRAME_LENGTH) / (TRANSMISSION_RATE / 1000) # us / microseconds
    interval_us = np.mean(np.diff(1000000 * df['time_s'].head(30) + df['time_us'].head(30)))
    sync_rows = math.ceil(SYNC_TRANSMISSIONS * transmission_duration / interval_us + SYNC_TRANSMISSIONS * ROW_ERROR_PER_SYNC_TRANSMISSION)
    transmission_rows = 1 + math.ceil(transmission_duration / interval_us)
    minpower = np.min(df['power'])
    maxpower = np.max(df['power'])

    sync = np.repeat([0.85], sync_rows)

    # Correlate with first two repetitions to get start
    head = df['power'].head(int(2*CASES*case_rows))
    head = [(x - minpower)/(maxpower-minpower) for x in head] # normalize
    correlation = np.correlate(head,sync)
    start = np.argmax(correlation)

    # Remove rows before start
    df = df.iloc[start:].reset_index()
    
    # Remove rows not relating to any case
    df = df[:-int(len(df.index) - CASES*case_rows)]

    # Visualize cases
    visual = []
    for i in range(0,CASES):
        if i%2 == 0:
            visual.append(0.145)
        else:
            visual.append(0.15)
    visual = np.repeat(visual, case_rows)
    # Plot the power and the synchronization sequence
    plt.plot(df['power'])
    plt.plot(np.append(sync, visual))
    # ERROR ANALYSIS
    #plt.plot(head[start:])
    #plt.plot(sync)
    #plt.plot(correlation)
    plt.show()

if __name__ == "__main__":
    pd.options.display.float_format = '{:,.2f}'.format

    pathlist = Path("/Users/dennis/Code/iotlab_measure_energy_consumption/NEW_raw_data_receive/").rglob("*.oml")
    for path in pathlist:
        parse(path.name)
