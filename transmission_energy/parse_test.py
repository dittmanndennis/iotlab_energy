from pathlib import Path, PosixPath
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import re
import collections
import math


SYNC_SEQUENCE = 22
CASES = 43
START_CASES_REAL_TRANSMISSION = 12
TRANSMISSION_REPETITIONS = 1
CASE_DURATION = 5 # seconds
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
  elif START_CASES_REAL_TRANSMISSION <= x < START_CASES_REAL_TRANSMISSION + TRANSMISSION_REPETITIONS * (CASES - START_CASES_REAL_TRANSMISSION + 1):
    if x%2 == 0:
       return "UNICAST - " + tx_power_list[int((x - START_CASES_REAL_TRANSMISSION) / (2 * TRANSMISSION_REPETITIONS))]
    return "BROADCAST - " + tx_power_list[int((x - START_CASES_REAL_TRANSMISSION) / (2 * TRANSMISSION_REPETITIONS))]
  else:
    return "unknown"

def parse(filename: PosixPath, plot: bool):
    df = pd.read_csv(filename,
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

    df['time'] = df['time_s']+df['time_us']/1000000

    interval_s = np.mean(np.diff(df['time'].head(20)))
    case_rows = CASE_DURATION/interval_s
    transmission_duration = (8 * FRAME_LENGTH) / (TRANSMISSION_RATE / 1000) # us / microseconds
    interval_us = np.mean(np.diff(1000000 * df['time_s'].head(30) + df['time_us'].head(30)))
    transmission_rows = 1 + math.ceil(transmission_duration / interval_us)
    minpower = np.min(df['power'])
    maxpower = np.max(df['power'])

    # Generate synchronization list
    # sync_sequence = 10110
    # 10110000 & 10000000 = 0
    # sync = 00010110
    sync_sequence = SYNC_SEQUENCE
    sync = []
    visual = []
    for i in range(0,8):
        sync.append((sync_sequence & 0x80) >> 7)
        sync_sequence <<= 1
    sync = np.repeat(sync, case_rows)

    # Correlate with first two repetitions to get start
    head = df['power'].head(int(2*CASES*case_rows))
    head = [(x - minpower)/(maxpower-minpower) for x in head] # normalize
    correlation = np.correlate(head,sync)
    start = np.argmax(correlation)

    # Remove rows before start
    df = df.iloc[start:].reset_index()

    # Remove rows not relating to any case
    df = df[:-int(len(df.index)-CASES*case_rows)]
    # Generate case indicies
    df['case'] = df.apply(lambda row: (int(row.name/case_rows)%CASES)+1, axis=1)
    df['case_part'] = df.apply(lambda row: int(row.name/(case_rows/3))%3, axis=1)

    if plot:
        # Visualize cases
        for i in range(8,CASES):
            if i%2 == 0:
                visual.append(0.115)
            else:
                visual.append(0.12)
        visual = np.repeat(visual, case_rows)
        # Plot the power and the synchronization sequence
        plt.plot(df['power'])
        plt.plot(np.append(sync, visual))
        plt.show()

    # Group by case (only middle segment)
    cases = df.loc[np.where(df['case_part'].values == 1)]
    def agg_current(x: pd.DataFrame) -> pd.Series:
        d = collections.OrderedDict()
        if x['case'].iloc[0] < START_CASES_REAL_TRANSMISSION:
            d['current_mean'] = 1000 * np.mean(x['current'])
            d['power_mean'] = 1000 * np.mean(x['power'])
        else:
            d['current_mean'] = 1000 * np.max(x['current'])
            d['power_mean'] = 1000 * np.max(x['power'])
        return pd.Series(d)
    means = cases.groupby(['case']).apply(agg_current, include_groups=True)

    m = re.search(r"m3[-_]([0-9]*)\.oml", str(filename))
    assert(m)
    means['node'] = int(m.group(1))
    means['casetxt'] = means.apply(lambda x: casetxt(x.name),axis=1)
    means = means[means['casetxt'].values != 'unknown']

    # Get Wh and Ah per transmission
    sleep_power = means["power_mean"].iloc[np.where(means['casetxt'].values == "SLEEP")].values
    sleep_current = means["current_mean"].iloc[np.where(means['casetxt'].values == "SLEEP")].values
    transmissions = df.loc[np.where((df['case'].values >= START_CASES_REAL_TRANSMISSION) &
                                    (df['case_part'].values == 1))]
    def adv_agg_consumed_energy(x: pd.DataFrame) -> pd.Series:
        d = collections.OrderedDict()
        transmission_start_row = x['power'].rolling(transmission_rows).sum().idxmax() - transmission_rows + 1
        transmission_measurements = x.loc[transmission_start_row:(transmission_start_row + transmission_rows - 1)]
        y_list_mW = 1000 * transmission_measurements['power'].values - sleep_power
        y_list_mA = 1000 * transmission_measurements['current'].values - sleep_current
        x_list_us = 1000000 * transmission_measurements['time_s'].values + transmission_measurements['time_us'].values
        if y_list_mW[0] < y_list_mW[-1]:
            x_list_us[0] = x_list_us[-1] - transmission_duration
        else:
            x_list_us[-1] = x_list_us[0] + transmission_duration
        mWh = np.trapezoid(y=y_list_mW, x=x_list_us) / (3600000000 / transmission_duration)
        mAh = np.trapezoid(y=y_list_mA, x=x_list_us) / (3600000000 / transmission_duration)
        d['mWh'] = mWh
        d['mAh'] = mAh
        return pd.Series(d)
    energy_consumption = transmissions.groupby(['case']).apply(adv_agg_consumed_energy, include_groups=False)

    return means, energy_consumption

def print_node_result(df):
    sleep_power = np.min(df['power_mean'])
    sleep_current = np.min(df['current_mean'])

    print("Sleep Power %i mW"%sleep_power)
    print("Sleep Current %i mA"%sleep_current)

    def agg_all(x):
        d = collections.OrderedDict()
        d['casetxt'] = x['casetxt'].iloc[0]
        d['power_extra'] = "%i mW"%round(np.mean(x['power_mean'])-sleep_power)
        d['current_extra'] = "%i mA"%round(np.mean(x['current_mean'])-sleep_current)
        d['power_total'] = "%i mW"%round(np.mean(x['power_mean']))
        d['current_total'] = "%i mA"%round(np.mean(x['current_mean']))
        return pd.Series(d)
    df = df.groupby('case').apply(agg_all, include_groups=False)
    print(df)

if __name__ == "__main__":
    plot = False

    pd.options.display.float_format = '{:,.2f}'.format

    first = True
    df = None

    pathlist = Path("/Users/dennis/Code/iotlab_measure_energy_consumption/raw_data_transmit/").rglob("*.oml")
    for path in pathlist:
        result, energy_consumption = parse(path, plot)
        print("Node %i"%result['node'].iloc[0])
        print_node_result(result)

        if first:
            df = result
            first = False
        else:
            df = pd.concat((df,result))

    df['case'] = df.index
    df = df.pivot(index='node',columns='case',values='power_mean')
    df = df.rename(columns=casetxt)
    df.to_csv('energy_results_test.csv')
