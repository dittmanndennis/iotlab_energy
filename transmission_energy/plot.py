from pathlib import Path, PosixPath
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt


SYNC_SEQUENCE = 22
CASES = 42
CASE_DURATION = 5 # seconds

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

    interval = np.mean(np.diff(df['time'].head(20)))
    case_rows = CASE_DURATION/interval
    minpower = np.min(df['power'])
    maxpower = np.max(df['power'])

    # Generate synchronization list
    # sync_sequence = 10110
    # 10110000 & 10000000 = 0
    # sync = 00010110
    sync_sequence = SYNC_SEQUENCE
    sync = []
    for i in range(0,8):
        sync.append((sync_sequence & 0x80) >> 7)
        sync_sequence <<= 1
    for i in range(8,42):
        if i%2 == 0:
            sync.append(0.115)
        else:
            sync.append(0.12)
    sync = np.repeat(sync,case_rows)

    # Correlate with first two repetitions to get start
    head = df['power'].head(int(2*CASES*case_rows))
    head = [(x - minpower)/(maxpower-minpower) for x in head] # normalize
    correlation = np.correlate(head,sync)
    start = np.argmax(correlation)

    # Remove rows before start
    df = df.iloc[start:].reset_index()

    # Remove rows not relating to any case
    df = df[:-int(len(df.index)-CASES*case_rows)]

    # Plot the power and the synchronization sequence
    plt.plot(df['power'])
    plt.plot(sync)
    plt.show()

if __name__ == "__main__":
    pd.options.display.float_format = '{:,.2f}'.format

    pathlist = Path("/Users/dennis/Code/iotlab_measure_energy_consumption/raw_data_test/").rglob("*.oml")
    for path in pathlist:
        parse(path)
