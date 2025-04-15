from pathlib import Path, PosixPath
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import os


SYNC_SEQUENCE = 22
BASE_CASES = 8
POWER_LEVELS = 16
TRANSMISSION_REPETITIONS = 1
CASE_DURATION = 4 # seconds

def parse(filename: Path, dir_path: str):
    df = pd.read_csv(filename,
        skiprows=9,
#       nrows=10000,
        sep='\t',
        header=None,
        usecols=[3,4,5,6,7],
        names=['time_s','time_us','power','voltage','current'])
    energy_states = pd.read_csv("%s/results/energy_states_results.csv" % dir_path,
                    usecols=['power_median', 'current_median', 'casetxt'])
        
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
    sync = np.repeat(sync,case_rows)

    # Correlate with first two repetitions to get start
    head = df['power'].head(int(2*BASE_CASES*case_rows))
    head = [(x - minpower)/(maxpower-minpower) for x in head] # normalize
    correlation = np.correlate(head,sync)
    start = np.argmax(correlation)

    # Remove rows before start
    df = df.iloc[start:].reset_index()

    # Remove rows not relating to any case
    df = df[:-int(len(df.index)-(BASE_CASES + TRANSMISSION_REPETITIONS * POWER_LEVELS)*case_rows)]

    # Visualize cases
    energy_results = pd.read_csv("%s/results/energy_results.csv" % dir_path)
    visual_max = []
    sleep_power = energy_states['power_median'].iloc[np.where(energy_states['casetxt'].values == "SLEEP")].values
    for i in range(0, TRANSMISSION_REPETITIONS * POWER_LEVELS):
        visual_max.append((energy_results['median__mW_max'][i] + sleep_power) / 1000)
    visual_max = np.repeat(visual_max, case_rows)
    # Plot the power and the synchronization sequence
    plt.plot(df['power'])
    plt.plot(np.append(sync, visual_max))
    plt.xlabel("Measurement Number")
    plt.ylabel("Energy Consumption [W]")
    plt.show()

if __name__ == "__main__":
    pd.options.display.float_format = '{:,.2f}'.format
        
    dir_path = os.path.dirname(os.path.realpath(__file__))

    pathlist = Path("%s/A8_M3_raw_data/" % dir_path).rglob("*.oml")
    for path in pathlist:
        parse(path, dir_path)
