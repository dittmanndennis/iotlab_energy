from pathlib import Path, PosixPath
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import re
import collections


SYNC_SEQUENCE = 22
CASES = 43
START_CASES_REAL_TRANSMISSION = 12
CASE_DURATION = 5 # seconds
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
  elif START_CASES_REAL_TRANSMISSION <= x <= CASES:
    if x%2 == 0:
       return "UNICAST - " + tx_power_list[int((x - 12) / 2)]
    return "BROADCAST - " + tx_power_list[int((x - 12) / 2)]
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
        visual = []
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
    cases = df[df['case_part'] == 1].groupby(['case'])
    def agg_current(x: pd.DataFrame) -> pd.Series:
        d = collections.OrderedDict()
        if x['case'].iloc[0] < START_CASES_REAL_TRANSMISSION:
            d['current_mean'] = np.mean(x['current'])*1000
            d['power_mean'] = np.mean(x['power'])*1000
        else:
            d['current_mean'] = np.max(x['current'])*1000
            d['power_mean'] = np.max(x['power'])*1000
        return pd.Series(d)
    means = cases.apply(agg_current)

    m = re.search(r"m3[-_]([0-9]*)\.oml", str(filename))
    assert(m)
    means['node'] = int(m.group(1))
    means['casetxt'] = means.apply(lambda x: casetxt(x.name),axis=1)
    means = means[means['casetxt'] != 'unknown']
    return means

def print_node_result(df):
    idle_power = np.min(df['power_mean'])   # those are sleep values, correct to idle
    idle_current = np.min(df['current_mean'])
    pll_on_df = df[df['casetxt'] == "PLL_ON"]
    pll_on_power = np.mean(pll_on_df['power_mean']) - idle_power
    pll_on_current = np.mean(pll_on_df['current_mean']) - idle_current

    print(df)

    print("Idle Power %i mW"%idle_power)
    print("Idle Current %i mA"%idle_current)

    def agg_all(x):
        d = collections.OrderedDict()
        d['casetxt'] = x['casetxt'].iloc[0]
        d['power_extra'] = "%i mW"%round(np.mean(x['power_mean'])-idle_power)
        d['current_extra'] = "%i mA"%round(np.mean(x['current_mean'])-idle_current)
        d['power_total'] = "%i mW"%round(np.mean(x['power_mean']))
        d['current_total'] = "%i mA"%round(np.mean(x['current_mean']))
        return pd.Series(d)
    df = df.groupby('case').apply(agg_all)
    print(df)

if __name__ == "__main__":
    plot = False

    pd.options.display.float_format = '{:,.2f}'.format

    first = True
    df = None

    pathlist = Path("/Users/dennis/Code/iotlab_measure_energy_consumption/raw_data/").rglob("*.oml")
    for path in pathlist:
        result = parse(path, plot)
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
    df.to_csv('energy_results.csv')
