from pathlib import Path, PosixPath
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import math
import collections
import re

SYNC_TRANSMISSIONS = 250
# Calculation(ROW_ERROR_PER_SYNC_TRANSMISSION): (SYNC_ROWS_FOR_250_TRANSMISSIONS_AT_250_kbps_128_byte_FRAME_LENGTH - 250 * transmission_duration / interval_us) / 250
# SYNC_ROWS_FOR_250_TRANSMISSIONS_AT_250_kbps_128_byte_FRAME_LENGTH = 1120
ROW_ERROR_PER_SYNC_TRANSMISSION = 0.7620745563241412
CASES = 30
CASE_DURATION = 4 # seconds
TRANSMISSION_RATE = 250 # kb/s
FRAME_LENGTH = 128 # Byte
START_UP = 9 # seconds

def parse(path: PosixPath):
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
    df = df[:-int(len(df.index) - CASES*case_rows - sync_rows)]

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

    # Remove SYNC rows
    df = df.iloc[sync_rows:].reset_index(drop=True)
    # Generate case indicies
    df['case'] = df.apply(lambda row: (int(row.name/case_rows)%CASES)+1, axis=1)
    df['case_part'] = df.apply(lambda row: int(row.name/(case_rows/3))%3, axis=1)

    # Group by case (only middle segment)
    csma_rx_idle_power = 1000 * np.mean(df["power"].loc[np.where(df['case_part'].values == 0)].values)
    csma_rx_idle_current = 1000 * np.mean(df["current"].loc[np.where(df['case_part'].values == 0)].values)
    cases = df.loc[np.where(df['case_part'].values == 1)]
    def agg_current(x: pd.DataFrame) -> pd.Series:
        d = collections.OrderedDict()
        d['current_max_extra'] = 1000 * np.max(x['current']) - csma_rx_idle_current
        d['power_max_extra'] = 1000 * np.max(x['power']) - csma_rx_idle_power
        return pd.Series(d)
    maxs = cases.groupby(['case']).apply(agg_current, include_groups=False)

    avg_power_max_extra = np.mean(maxs["power_max_extra"])
    avg_current_max_extra = np.mean(maxs["current_max_extra"])

    # Get Wh and Ah per reception
    transmissions = df.loc[np.where(df['case_part'].values == 1)]
    def adv_agg_consumed_energy(x: pd.DataFrame) -> pd.Series:
        d = collections.OrderedDict()
        transmission_start_row = x['power'].rolling(transmission_rows).sum().idxmax() - transmission_rows + 1
        transmission_measurements = x.loc[transmission_start_row:(transmission_start_row + transmission_rows - 1)]
        y_list_mW = 1000 * transmission_measurements['power'].values - csma_rx_idle_power
        y_list_mA = 1000 * transmission_measurements['current'].values - csma_rx_idle_current
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

    avg_mWh_extra = np.mean(energy_consumption["mWh"])
    avg_mAh_extra = np.mean(energy_consumption["mAh"])
    csma_rx_idle_mWh_per_frame = np.trapezoid(y=[csma_rx_idle_power, csma_rx_idle_power], x=[0, transmission_duration]) / (3600000000 / transmission_duration)
    csma_rx_idle_mAh_per_frame = np.trapezoid(y=[csma_rx_idle_current, csma_rx_idle_current], x=[0, transmission_duration]) / (3600000000 / transmission_duration)

    return avg_power_max_extra, avg_current_max_extra, csma_rx_idle_power, csma_rx_idle_current, avg_mWh_extra, avg_mAh_extra, csma_rx_idle_mWh_per_frame, csma_rx_idle_mAh_per_frame

def print_result(df):
    df['avg_power_max_extra'] = df['avg_power_max_extra'].apply(lambda x: "%f mW"%x)
    df['avg_current_max_extra'] = df['avg_current_max_extra'].apply(lambda x: "%f mA"%x)
    df['csma_rx_idle_power'] = df['csma_rx_idle_power'].apply(lambda x: "%f mW"%x)
    df['csma_rx_idle_current'] = df['csma_rx_idle_current'].apply(lambda x: "%f mA"%x)
    df['avg_mWh_extra'] = df['avg_mWh_extra'].apply(lambda x: "%f mWh"%x)
    df['avg_mAh_extra'] = df['avg_mAh_extra'].apply(lambda x: "%f mAh"%x)
    df['csma_rx_idle_mWh_per_frame'] = df['csma_rx_idle_mWh_per_frame'].apply(lambda x: "%f mWh"%x)
    df['csma_rx_idle_mAh_per_frame'] = df['csma_rx_idle_mAh_per_frame'].apply(lambda x: "%f mAh"%x)
    
    print(df)


if __name__ == "__main__":
    pd.options.display.float_format = '{:,.2f}'.format

    index = []
    data = {
        "avg_power_max_extra": [],
        "avg_current_max_extra": [],
        "csma_rx_idle_power": [],
        "csma_rx_idle_current": [],
        "avg_power_max_total": [],
        "avg_current_max_total": [],
        "avg_mWh_extra": [],
        "avg_mAh_extra": [],
        "csma_rx_idle_mWh_per_frame": [],
        "csma_rx_idle_mAh_per_frame": [],
        "avg_mWh_total": [],
        "avg_mAh_total": []
    }

    pathlist = Path("/Users/dennis/Code/iotlab_measure_energy_consumption/raw_data_receive/").rglob("*.oml")
    for path in pathlist:
        print(path.name)
        m = re.search(r"m3[-_]([0-9]*)[-_](.*?(?=\.oml))", str(path.name))
        assert(m)
        index.append(m.group(2))

        avg_power_max_extra, avg_current_max_extra, csma_rx_idle_power, csma_rx_idle_current, avg_mWh_extra, avg_mAh_extra, csma_rx_idle_mWh_per_frame, csma_rx_idle_mAh_per_frame = parse(path)
        data['avg_power_max_extra'].append(avg_power_max_extra)
        data['avg_current_max_extra'].append(avg_current_max_extra)
        data['csma_rx_idle_power'].append(csma_rx_idle_power)
        data['csma_rx_idle_current'].append(csma_rx_idle_current)
        data['avg_power_max_total'].append(avg_power_max_extra + csma_rx_idle_power)
        data['avg_current_max_total'].append(avg_current_max_extra + csma_rx_idle_current)
        data['avg_mWh_extra'].append(avg_mWh_extra)
        data['avg_mAh_extra'].append(avg_mAh_extra)
        data['csma_rx_idle_mWh_per_frame'].append(csma_rx_idle_mWh_per_frame)
        data['csma_rx_idle_mAh_per_frame'].append(csma_rx_idle_mAh_per_frame)
        data['avg_mWh_total'].append(avg_mWh_extra + csma_rx_idle_mWh_per_frame)
        data['avg_mAh_total'].append(avg_mAh_extra + csma_rx_idle_mAh_per_frame)

    df = pd.DataFrame(data, index)
    df.to_csv('receive_energy_results.csv')
    print_result(df)
