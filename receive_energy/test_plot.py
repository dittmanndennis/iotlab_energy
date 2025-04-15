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

    start = 0

    # Remove rows before start
    df = df.iloc[start:].reset_index()

#    # Plot the power and the synchronization sequence
#    plt.plot(df['power'])
#    # ERROR ANALYSIS
#    #plt.plot(head[start:])
#    #plt.plot(correlation)
#    plt.show()

    return df

if __name__ == "__main__":
    plot = False

    pd.options.display.float_format = '{:,.2f}'.format

    pathlist = Path("/Users/dennis/Code/IOTLAB_ENERGY/receive_energy/test_data_OS_0.4/").rglob("*.oml")
    for path in pathlist:
        m = re.search(r"m3[-_]([0-9]*)[-_](.*?(?=\.oml))", str(path.name))
        print(path.name)
        df = parse(path, m.group(2) == "receive", plot)

        plt.plot(df['power'], label=m.group(2))

    plt.legend(loc='upper right')
    plt.show()
