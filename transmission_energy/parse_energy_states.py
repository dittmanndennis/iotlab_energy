from pathlib import Path, PosixPath
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import re
import collections
import math
import os


SYNC_SEQUENCE = 22
POWER_LEVELS = 16
SYNC_CASES = 8
BASE_CASES = 11
TRANSMISSION_REPETITIONS = 1
TOTAL_CASES = BASE_CASES + TRANSMISSION_REPETITIONS
CASE_DURATION = 4 # seconds
TRANSMISSION_RATE = 250 # kb/s
FRAME_LENGTH = 128 # Byte

tx_power_list = [
    "PHY_POWER_m17dBm",
    "PHY_POWER_m12dBm",
    "PHY_POWER_m10dBm",
    "PHY_POWER_m7dBm",
    "PHY_POWER_m5dBm",
    "PHY_POWER_m4dBm",
    "PHY_POWER_m3dBm",
    "PHY_POWER_m2dBm",
    "PHY_POWER_m1dBm",
    "PHY_POWER_0dBm",
    "PHY_POWER_0_7dBm",
    "PHY_POWER_1_3dBm",
    "PHY_POWER_1_8dBm",
    "PHY_POWER_2_3dBm",
    "PHY_POWER_2_8dBm",
    "PHY_POWER_3dBm"
]

def casetxt(x: int) -> str:
  if x == 8:
     return "SLEEP"
  elif x == 9:
    return "RX_ON"
  elif x == 10:
     return "PLL_ON"
  elif x == 11:
    return "Idle"
  else:
    return "unknown"
  
def remove_outliers(series: pd.Series) -> pd.Series:
    q1, q3 = series.quantile([0.25, 0.75])
    iqr = q3 - q1
    return series.iloc[np.where((q1 - 1.5 * iqr <= series.values) &
                               (series.values <= q3 + 1.5 * iqr))]

def parse(path: PosixPath, plot: bool):
    df = pd.read_csv(path,
        skiprows=9,
#       nrows=10000,
        sep='\t',
        header=None,
        usecols=[3,4,5,6,7],
        names=['time_s','time_us','power','voltage','current'])
        
    # remove outliers
    df = df.loc[np.where((df['power'].values > 0) &
                         (df['power'].values < 1000) &
                         (df['current'].values > 0) &
                         (df['current'].values < 1000) &
                         (df['voltage'].values > 0) &
                         (df['voltage'].values < 1000))]

    interval_us = np.mean(np.diff(1000000 * df['time_s'].head(30) + df['time_us'].head(30)))
    case_rows = (1000000 * CASE_DURATION)/interval_us
    minpower = np.min(df['power'])
    maxpower = np.max(df['power'])

    # Generate synchronization list
    # sync_sequence = 10110
    # 10110000 & 10000000 = 0
    # sync = 00010110
    sync_sequence = SYNC_SEQUENCE
    sync = []
    for i in range(0,SYNC_CASES):
        sync.append((sync_sequence & 0x80) >> 7)
        sync_sequence <<= 1
    sync = np.repeat(sync, case_rows)
    
    # Correlate with first two repetitions to get start
    head = df['power'].head(int(TOTAL_CASES*case_rows))
    head = [(x - minpower)/(maxpower-minpower) for x in head] # normalize
    correlation = np.correlate(head,sync)
    start = np.argmax(correlation)

    plt.plot(correlation)
    plt.plot(head)
    plt.show()

    # Remove rows before start
    df = df.iloc[start:]
        
    df = df.reset_index(drop=True)
    
    # Generate case indicies
    df['case'] = df.apply(lambda row: int(row.name/case_rows)+1, axis=1)
    df['case_part'] = df.apply(lambda row: int(row.name/(case_rows/3))%3, axis=1)

    if plot:
        # Visualize cases
        visual = []
        for j in range(SYNC_CASES,TOTAL_CASES):
            if j%2 == 0:
                visual.append(0.115)
            else:
                visual.append(0.12)
        visual = np.repeat(visual, case_rows)
        # Plot the power and the synchronization sequence
        plt.plot(df['power'])
        #plt.plot(sync, label="Synchronization Sequence")
        #plt.plot(np.append(np.repeat([0], len(sync)), visual), label="Cases")
        plt.legend()
        plt.xlabel("Measurement Number")
        plt.ylabel("Energy Consumption [W]")
        plt.show()

    # Group by case (only middle segment)
    cases = df.loc[np.where((df['case'] >= SYNC_CASES) &
                            (df['case'] <= BASE_CASES) &
                            (df['case_part'].values == 1))]
    def agg_current(x: pd.DataFrame) -> pd.Series:
        d = collections.OrderedDict()
        d['power_median'] = 1000 * np.median(remove_outliers(x['power']))
        d['current_median'] = 1000 * np.median(remove_outliers(x['current']))
        return pd.Series(d)
    node_medians = cases.groupby(['case']).apply(agg_current, include_groups=False)

    node_medians['casetxt'] = node_medians.apply(lambda x: casetxt(x.name),axis=1)
    node_medians = node_medians[node_medians['casetxt'].values != 'unknown']

    print(node_medians)

    return node_medians

def print_node_result(df: pd.DataFrame) -> None:
    sleep_power = np.min(df['power_median'])
    sleep_current = np.min(df['current_median'])

    print("Sleep Power %i mW"%sleep_power)
    print("Sleep Current %i mA"%sleep_current)

    def agg_all(x):
        d = collections.OrderedDict()
        d['casetxt'] = x['casetxt'].iloc[0]
        d['power_extra'] = "%i mW"%round(np.mean(x['power_median'])-sleep_power)
        d['current_extra'] = "%i mA"%round(np.mean(x['current_median'])-sleep_current)
        d['power_total'] = "%i mW"%round(np.mean(x['power_median']))
        d['current_total'] = "%i mA"%round(np.mean(x['current_median']))
        return pd.Series(d)
    df = df.groupby('case').apply(agg_all, include_groups=False)
    print(df)

if __name__ == "__main__":
    plot = True

    pd.options.display.float_format = '{:,.2f}'.format
        
    dir_path = os.path.dirname(os.path.realpath(__file__))

    pathlist = Path("%s/raw_data_energy_states/" % dir_path).rglob("*.oml")
    for path in pathlist:
        m = re.search(r"m3[-_]([0-9]*)[-_](.*?(?=\.oml))", str(path.name))
        assert(m)
        print(m.group(2))
        print(path)
        df = parse(path, plot)

        df.to_csv('%s/results/energy_states_results.csv' % dir_path)

        print_node_result(df)
