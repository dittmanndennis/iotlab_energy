from pathlib import Path, PosixPath
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import re
import collections
import math
import os
from scipy import integrate
import time


SYNC_SEQUENCE = 22
POWER_LEVELS = 16
BASE_CASES = 8
ENERGY_STATES = 3
TRANSMISSION_REPETITIONS = 40
TOTAL_CASES = BASE_CASES + TRANSMISSION_REPETITIONS
CASE_DURATION = 4 # seconds
TRANSMISSION_RATE = 250 # kb/s
FRAME_LENGTH = 128 # Byte
TRANSMISSION_DURATION = (8 * FRAME_LENGTH) / (TRANSMISSION_RATE / 1000) # us / microseconds

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

def parse_energy_states(df: pd.DataFrame, case_rows: int, save_energy_states: bool):
    # Group by case (only middle segment)
    cases = df.loc[np.where((df['case'] <= BASE_CASES + ENERGY_STATES) &
                            (df['case_part'].values == 1))]
    def agg_states(x: pd.DataFrame) -> pd.Series:
        d = collections.OrderedDict()
        d['power_median'] = 1000 * np.median(remove_outliers(x['power']))
        d['current_median'] = 1000 * np.median(remove_outliers(x['current']))
        return pd.Series(d)
    node_medians = cases.groupby(['case']).apply(agg_states, include_groups=False)

    node_medians['casetxt'] = node_medians.apply(lambda x: casetxt(x.name),axis=1)
    node_medians = node_medians[node_medians['casetxt'].values != 'unknown']
    
    sleep_power = node_medians["power_median"].iloc[np.where(node_medians['casetxt'].values == "SLEEP")].values
    sleep_current = node_medians["current_median"].iloc[np.where(node_medians['casetxt'].values == "SLEEP")].values

    # Remove rows of current POWER_LEVEL
    df = df.loc[int((BASE_CASES + ENERGY_STATES)*case_rows + int(1.9 * case_rows)):]

    return df, sleep_power, sleep_current, node_medians

def correlate(df: pd.DataFrame, case_rows: int, minpower: float, maxpower: float, sync: list) -> pd.DataFrame:
    # Correlate with first two repetitions to get start
    head = df['power'].head(int(TOTAL_CASES*case_rows))
    head = [(x - minpower)/(maxpower-minpower) for x in head] # normalize
    correlation = np.correlate(head,sync)
    start = np.argmax(correlation)

    # Remove rows before start
    df = df.iloc[start:]

    df = df.reset_index(drop=True)
    
    # Generate case indicies
    df['case'] = df.apply(lambda row: int(row.name/case_rows)+1, axis=1)
    df['case_part'] = df.apply(lambda row: int(row.name/(case_rows/3))%3, axis=1)

    return df

def parse(path: PosixPath, plot: bool, save_energy_states: bool, save_boxplots: bool, save_transmission_energy_dist: bool):
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

    df['time'] = 1000000 * df['time_s'] + df['time_us']

    interval_us = np.mean(np.diff(1000000 * df['time_s'].head(30) + df['time_us'].head(30)))
    case_rows = (1000000 * CASE_DURATION)/interval_us
    transmission_rows = 1 + math.ceil(TRANSMISSION_DURATION / interval_us)
    minpower = np.min(df['power'])
    maxpower = np.max(df['power'])

    # Generate synchronization list
    # sync_sequence = 10110
    # 10110000 & 10000000 = 0
    # sync = 00010110
    sync_sequence = SYNC_SEQUENCE
    sync = []
    for i in range(0,BASE_CASES):
        sync.append((sync_sequence & 0x80) >> 7)
        sync_sequence <<= 1
    sync = np.repeat(sync, case_rows)

    # DEBUG
    if False:
        # Visualize cases
        visual = []
        for j in range(BASE_CASES,TOTAL_CASES):
            if j%2 == 0:
                visual.append(0.115)
            else:
                visual.append(0.12)
        visual = np.repeat(visual, case_rows)
        # Plot the power and the synchronization sequence
        plt.plot(df['power'])
        plt.plot(np.append(sync, visual))
        plt.show()
            
    df, sleep_power, sleep_current, node_medians = parse_energy_states(correlate(df, case_rows, minpower, maxpower, sync), case_rows, save_energy_states)

    data = {
        #"median__total_mW_mean": [],
        #"median__total_mA_mean": [],
        #"median__total_mW_max": [],
        #"median__total_mA_max": [],
        "median__mW_mean": [],
        "median__mA_mean": [],
        "median__mW_max": [],
        "median__mA_max": [],
        "median__mWh": [],
        "median__mAh": []
    }
    
    for i in range(0, POWER_LEVELS):
        try:
            df = correlate(df, case_rows, minpower, maxpower, sync)
        except ValueError as e:
            print("Failed to correlate at power level %s." % tx_power_list[i])

            # reload DataFrame
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

            # Visualize cases
            visual = []
            for j in range(BASE_CASES,TOTAL_CASES):
                if j%2 == 0:
                    visual.append(0.115)
                else:
                    visual.append(0.12)
            visual = np.repeat(visual, case_rows)
            # Plot the power and the synchronization sequence
            plt.plot(df['power'])
            plt.plot(np.append(sync, visual))
            plt.show()

            raise ValueError(e)

        if plot:
            print("Power level: ", i)
            # Visualize cases
            visual = []
            for j in range(BASE_CASES,TOTAL_CASES):
                if j%2 == 0:
                    visual.append(0.115)
                else:
                    visual.append(0.12)
            visual = np.repeat(visual, case_rows)
            # Plot the power and the synchronization sequence
            plt.plot(df.loc[:int(TOTAL_CASES*case_rows + int(1.9 * case_rows))]['power'])
            plt.plot(np.append(sync, visual))
            plt.show()

        # Get transmission energy consumption (in mW, mA, mWh, mAh)
        transmissions = df.loc[np.where((df['case'].values <= TOTAL_CASES) &
                                        (BASE_CASES < df['case'].values) &
                                        (df['case_part'].values == 1))]
        def adv_agg_consumed_energy(x: pd.DataFrame):# -> pd.Series:
            d = collections.OrderedDict()
            transmission_end_row = x['power'].rolling(transmission_rows).apply(integrate.trapezoid).idxmax()
            
            transmission_measurements = x.loc[(transmission_end_row - transmission_rows + 1):transmission_end_row]
            y_list_mW = 1000 * transmission_measurements['power'].values - sleep_power
            y_list_mA = 1000 * transmission_measurements['current'].values - sleep_current
            x_list_us = transmission_measurements['time'].values

            if save_transmission_energy_dist:
                curr_transmission_mW = 1000 * x.loc[(transmission_end_row - transmission_rows - 0):(transmission_end_row + 1)]['power'].values - sleep_power
                curr_transmission_mA = 1000 * x.loc[(transmission_end_row - transmission_rows - 0):(transmission_end_row + 1)]['current'].values - sleep_current
                transmission_dist_padding_mW[0].append(curr_transmission_mW[0])
                transmission_dist_padding_mW[int((transmission_rows + 1) * TRANSMISSION_DURATION / (transmission_rows - 1))].append(curr_transmission_mW[-1])
                transmission_dist_padding_mA[0].append(curr_transmission_mA[0])
                transmission_dist_padding_mA[int((transmission_rows + 1) * TRANSMISSION_DURATION / (transmission_rows - 1))].append(curr_transmission_mA[-1])
                for j in range(transmission_rows):
                    transmission_dist_mW[int((j + 1) * TRANSMISSION_DURATION / (transmission_rows - 1))].append(curr_transmission_mW[j + 1])
                    transmission_dist_mA[int((j + 1) * TRANSMISSION_DURATION / (transmission_rows - 1))].append(curr_transmission_mA[j + 1])

            if plot:
                curr_transmission = x.loc[(transmission_end_row - transmission_rows - 9):(transmission_end_row + 10)]
                fig, axs = plt.subplots(1, 2, figsize=(8,4))
                axs[0].plot(curr_transmission['time'].values - curr_transmission['time'].values[0], 1000 * curr_transmission['power'].values - sleep_power, 'o--', label='sensor')
                axs[0].plot(x_list_us - curr_transmission['time'].values[0], y_list_mW, 'o--', label='transmission')
                axs[0].set(xlabel="\u03bcs", ylabel="mW")
                axs[0].legend(loc="lower left")
                axs[1].plot(curr_transmission['time'].values - curr_transmission['time'].values[0], 1000 * curr_transmission['current'].values - sleep_current, 'o--', label='sensor')
                axs[1].plot(x_list_us - curr_transmission['time'].values[0], y_list_mA, 'o--', label='transmission')
                axs[1].set(xlabel="\u03bcs", ylabel="mA")
                axs[1].legend(loc="lower left")
                fig.tight_layout()
                plt.show()

            shorten = x_list_us[-1] - x_list_us[0] - TRANSMISSION_DURATION
            # shorten measurement 0
            shorten_first_value_mW = y_list_mW[0] + (y_list_mW[1] - y_list_mW[0]) * (shorten / (x_list_us[1] - x_list_us[0]))
            shorten_first_value_mA = y_list_mA[0] + (y_list_mA[1] - y_list_mA[0]) * (shorten / (x_list_us[1] - x_list_us[0]))
            shorten_first_time = x_list_us[0] + shorten
            mWh_shorten_zero_value = np.trapezoid(y=([shorten_first_value_mW] + y_list_mW[1:]), x=([shorten_first_time] + x_list_us[1:]))
            # shorten measurement -1
            shorten_last_value_mW = y_list_mW[-1] + (y_list_mW[-2] - y_list_mW[-1]) * (shorten / (x_list_us[-1] - x_list_us[-2]))
            shorten_last_value_mA = y_list_mA[-1] + (y_list_mA[-2] - y_list_mA[-1]) * (shorten / (x_list_us[-1] - x_list_us[-2]))
            shorten_last_time = x_list_us[-1] - shorten
            mWh_shorten_last_value = np.trapezoid(y=(y_list_mW[:-1] + [shorten_last_value_mW]), x=(x_list_us[:-1] + [shorten_last_time]))

            if mWh_shorten_zero_value < mWh_shorten_last_value:
                y_list_mW[-1] = shorten_last_value_mW
                y_list_mA[-1] = shorten_last_value_mA
                x_list_us[-1] = shorten_last_time
            else:
                y_list_mW[0] = shorten_first_value_mW
                y_list_mA[0] = shorten_first_value_mA
                x_list_us[0] = shorten_first_time

            mW_mean = 0
            mA_mean = 0
            for j in range(len(x_list_us) - 1):
                mW_mean += (y_list_mW[j] + y_list_mW[j+1]) / 2 * (x_list_us[j+1] - x_list_us[j])
                mA_mean += (y_list_mA[j] + y_list_mA[j+1]) / 2 * (x_list_us[j+1] - x_list_us[j])
            d['mW_mean'] = mW_mean / TRANSMISSION_DURATION
            d['mA_mean'] = mA_mean / TRANSMISSION_DURATION
            
            d['mWh'] = np.trapezoid(y=y_list_mW, x=x_list_us) / (3600000000 / TRANSMISSION_DURATION)
            d['mAh'] = np.trapezoid(y=y_list_mA, x=x_list_us) / (3600000000 / TRANSMISSION_DURATION)
            d['mW_max'] = np.max(y_list_mW)
            d['mA_max'] = np.max(y_list_mA)

            return pd.Series(d)
        
        if save_transmission_energy_dist:
            transmission_dist_padding_mW = {
                0: [],
                int((transmission_rows + 1) * TRANSMISSION_DURATION / (transmission_rows - 1)): []
            }
            transmission_dist_mW = {}
            transmission_dist_padding_mA = {
                0: [],
                int((transmission_rows + 1) * TRANSMISSION_DURATION / (transmission_rows - 1)): []
            }
            transmission_dist_mA = {}
            for j in range(transmission_rows):
                transmission_dist_mW[int((j + 1) * TRANSMISSION_DURATION / (transmission_rows - 1))] = []
                transmission_dist_mA[int((j + 1) * TRANSMISSION_DURATION / (transmission_rows - 1))] = []

        transmission_energy_consumption = transmissions.groupby(['case']).apply(adv_agg_consumed_energy, include_groups=False)

        if save_transmission_energy_dist:
            dir_path = os.path.dirname(os.path.realpath(__file__))

            fig, axs = plt.subplots(1, 2, figsize=(8,4))
            axs[0].boxplot([transmission_dist_mW[key] for key in transmission_dist_mW.keys()], positions=transmission_dist_mW.keys(), widths=500, label='transmission')
            bplot = axs[0].boxplot([transmission_dist_padding_mW[key] for key in transmission_dist_padding_mW.keys()], positions=transmission_dist_padding_mW.keys(), widths=500, patch_artist=True, label='sensor')
            for patch in bplot['boxes']:
                patch.set_facecolor('peachpuff')
            axs[0].set(xlabel="\u03bcs", ylabel="mW")
            axs[0].legend(loc="lower left")
            axs[1].boxplot([transmission_dist_mA[key] for key in transmission_dist_mA.keys()], positions=transmission_dist_mA.keys(), widths=500, label='transmission')
            bplot = axs[1].boxplot([transmission_dist_padding_mA[key] for key in transmission_dist_padding_mA.keys()], positions=transmission_dist_padding_mA.keys(), widths=500, patch_artist=True, label='sensor')
            for patch in bplot['boxes']:
                patch.set_facecolor('peachpuff')
            axs[1].set(xlabel="\u03bcs", ylabel="mA")
            axs[1].legend(loc="lower left")
            fig.tight_layout()
            plt.savefig("%s/boxplots/transmission_energy_dist_%s.svg" % (dir_path, tx_power_list[i]), format="svg")
            if plot:
                plt.show()
            else:
                plt.close()

        if save_boxplots:
            dir_path = os.path.dirname(os.path.realpath(__file__))

            fig, axs = plt.subplots(1, 2)
            axs[0].boxplot([transmission_energy_consumption['mW_max'], transmission_energy_consumption['mW_mean']])
            axs[0].set_ylabel('mW')
            axs[0].set_xticklabels(['max', 'mean'])
            axs[1].boxplot([transmission_energy_consumption['mA_max'], transmission_energy_consumption['mA_mean']])
            axs[1].set_ylabel('mA')
            axs[1].set_xticklabels(['max', 'mean'])
            fig.tight_layout()
            plt.savefig("%s/boxplots/mW_mA_%s.svg" % (dir_path, tx_power_list[i]), format="svg")
            if plot:
                plt.show()
            else:
                plt.close(fig)

            fig, axs = plt.subplots(1, 2)
            axs[0].boxplot([transmission_energy_consumption['mWh']])
            axs[0].set_ylabel('mWh')
            axs[0].set_xticklabels(['-17 dBm'])
            axs[1].boxplot([transmission_energy_consumption['mAh']])
            axs[1].set_ylabel('mAh')
            axs[1].set_xticklabels(['-17 dBm'])
            fig.tight_layout()
            plt.savefig("%s/boxplots/mWh_mAh_%s.svg" % (dir_path, tx_power_list[i]), format="svg")
            if plot:
                plt.show()
            else:
                plt.close(fig)

        #data['median__total_mW_mean'].append(np.median(remove_outliers(transmission_energy_consumption['mW_mean'] + sleep_power).values))
        #data['median__total_mA_mean'].append(np.median(remove_outliers(transmission_energy_consumption['mA_mean'] + sleep_current).values))
        #data['median__total_mW_max'].append(np.median(remove_outliers(transmission_energy_consumption['mW_max'] + sleep_power).values))
        #data['median__total_mA_max'].append(np.median(remove_outliers(transmission_energy_consumption['mA_max'] + sleep_current).values))
        data['median__mW_mean'].append(np.median(remove_outliers(transmission_energy_consumption['mW_mean']).values))
        data['median__mA_mean'].append(np.median(remove_outliers(transmission_energy_consumption['mA_mean']).values))
        data['median__mW_max'].append(np.median(remove_outliers(transmission_energy_consumption['mW_max']).values))
        data['median__mA_max'].append(np.median(remove_outliers(transmission_energy_consumption['mA_max']).values))
        data['median__mWh'].append(np.median(remove_outliers(transmission_energy_consumption['mWh']).values))
        data['median__mAh'].append(np.median(remove_outliers(transmission_energy_consumption['mAh']).values))

        # Remove rows of current POWER_LEVEL
        df = df.loc[int(TOTAL_CASES*case_rows + int(1.9 * case_rows)):]

    return pd.DataFrame(data, tx_power_list), node_medians

def print_node_result(df: pd.DataFrame) -> None:
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

def print_result(df: pd.DataFrame) -> None:
    #df['median__mW_mean'] = df['median__mW_mean'].apply(lambda x: "%f mW"%x)
    #df['median__mA_mean'] = df['median__mA_mean'].apply(lambda x: "%f mA"%x)
    df['median__mW_max'] = df['median__mW_max'].apply(lambda x: "%f mW"%x)
    df['median__mA_max'] = df['median__mA_max'].apply(lambda x: "%f mA"%x)
    df['median__mWh'] = df['median__mWh'].apply(lambda x: "%f mWh"%x)
    df['median__mAh'] = df['median__mAh'].apply(lambda x: "%f mAh"%x)
    #df['mean__mW_mean'] = df['mean__mW_mean'].apply(lambda x: "%f mW"%x)
    #df['mean__mA_mean'] = df['mean__mA_mean'].apply(lambda x: "%f mA"%x)
    #df['mean__mW_max'] = df['mean__mW_max'].apply(lambda x: "%f mW"%x)
    #df['mean__mA_max'] = df['mean__mA_max'].apply(lambda x: "%f mA"%x)
    #df['mean__mWh'] = df['mean__mWh'].apply(lambda x: "%f mWh"%x)
    #df['mean__mAh'] = df['mean__mAh'].apply(lambda x: "%f mAh"%x)

    print(df)

if __name__ == "__main__":
    plot = False
    save_energy_states = True
    save_boxplots = True
    save_energy_power_plots = True
    save_transmission_energy_dist = True
    save_deployment_plot = True
    save_total_plot = True

    tx_power_levels = [-17, -12, -10, -7, -5, -4, -3, -2, -1, 0, 0.7, 1.3, 1.8, 2.3, 2.8, 3]

    pd.options.display.float_format = '{:,.2f}'.format
        
    dir_path = os.path.dirname(os.path.realpath(__file__))

    deployments = ["grenoble", "lille", "paris", "saclay", "strasbourg"]

    mW_mean_total_arr = np.empty((len(deployments),len(tx_power_list)))
    mA_mean_total_arr = np.empty((len(deployments),len(tx_power_list)))
    mW_max_total_arr = np.empty((len(deployments),len(tx_power_list)))
    mA_max_total_arr = np.empty((len(deployments),len(tx_power_list)))
    mWh_total_arr = np.empty((len(deployments),len(tx_power_list)))
    mAh_total_arr = np.empty((len(deployments),len(tx_power_list)))

    for i, deployment in enumerate(deployments):
        deployment_start_time = time.time()

        if not os.path.exists("%s/raw_data_transmit/%s/" % (dir_path, deployment)):
            continue

        nodes_in_deployment = len(os.listdir("%s/raw_data_transmit/%s/" % (dir_path, deployment)))
        
        if nodes_in_deployment == 0:
            continue

        pathlist = Path("%s/raw_data_transmit/%s/" % (dir_path, deployment)).rglob("*.oml")

        mW_mean_arr = np.empty((nodes_in_deployment,len(tx_power_list)))
        mA_mean_arr = np.empty((nodes_in_deployment,len(tx_power_list)))
        mW_max_arr = np.empty((nodes_in_deployment,len(tx_power_list)))
        mA_max_arr = np.empty((nodes_in_deployment,len(tx_power_list)))
        mWh_arr = np.empty((nodes_in_deployment,len(tx_power_list)))
        mAh_arr = np.empty((nodes_in_deployment,len(tx_power_list)))

        for j, path in enumerate(pathlist):
            node_start_time = time.time()

            m = re.search(r"m3[-_]([0-9]*)", str(path.name))
            assert(m)
            print("Current node: ", m.group(1))

            if os.path.isfile('%s/radios_parsed_energy/transmission_results/%s/%s_transmission_results.csv' % (dir_path, deployment, m.group(1))):
                df = pd.read_csv('%s/radios_parsed_energy/transmission_results/%s/%s_transmission_results.csv' % (dir_path, deployment, m.group(1)),
                                 usecols=['Unnamed: 0', 'median__mW_mean', 'median__mA_mean', 'median__mW_max', 'median__mA_max', 'median__mWh', 'median__mAh'],
                                 index_col=0)
                node_medians = pd.read_csv('%s/radios_parsed_energy/state_results/%s/%s_state_results.csv' % (dir_path, deployment, m.group(1)),
                                 usecols=['case', 'power_median', 'current_median', 'casetxt'],
                                 index_col=0)
            else:
                df, node_medians = parse(path, plot, save_energy_states, save_boxplots, save_transmission_energy_dist)

                df.to_csv('%s/radios_parsed_energy/transmission_results/%s/%s_transmission_results.csv' % (dir_path, deployment, m.group(1)))
                #df.to_csv('%s/results/energy_results.csv' % dir_path)
                node_medians.to_csv('%s/radios_parsed_energy/state_results/%s/%s_state_results.csv' % (dir_path, deployment, m.group(1)))

            mW_mean_arr[j] = df['median__mW_mean']
            mA_mean_arr[j] = df['median__mA_mean']
            mW_max_arr[j] = df['median__mW_max']
            mA_max_arr[j] = df['median__mA_max']
            mWh_arr[j] = df['median__mWh']
            mAh_arr[j] = df['median__mAh']

            if save_energy_power_plots:
                fig, axs = plt.subplots(1, 3, figsize=(30,4))
                axs[0].plot(tx_power_levels, df['median__mW_max'], 'o--', label='mW')
                axs[0].plot(tx_power_levels, df['median__mA_max'], 'o--', label='mA')
                axs[0].set(xlabel="Radio Power", ylabel="Max Transmission Energy")
                axs[0].legend(loc="upper left")
                axs[1].plot(tx_power_levels, df['median__mW_mean'], 'o--', label='mW')
                axs[1].plot(tx_power_levels, df['median__mA_mean'], 'o--', label='mA')
                axs[1].set(xlabel="Radio Power", ylabel="Mean Transmission Energy")
                axs[1].legend(loc="upper left")
                axs[2].plot(tx_power_levels, df['median__mWh'], 'o--', label='mWh')
                axs[2].plot(tx_power_levels, df['median__mAh'], 'o--', label='mAh')
                axs[2].set(xlabel="Radio Power", ylabel="Transmission Energy Consumption")
                axs[2].legend(loc="upper left")
                fig.tight_layout()
                plt.savefig("%s/plots/%s_energy_power_plot.svg" % (dir_path, m.group(1)), format="svg")
                if plot:
                    plt.show()
                else:
                    plt.close(fig)

            print_result(df)

            print("\nNode M3-%s analysis time: " % m.group(1), time.time() - node_start_time, "\n")

        deployment_data = {
            "median__mW_mean": np.median(mW_mean_arr, axis=0),
            "median__mA_mean": np.median(mA_mean_arr, axis=0),
            "median__mW_max": np.median(mW_max_arr, axis=0),
            "median__mA_max": np.median(mA_max_arr, axis=0),
            "median__mWh": np.median(mWh_arr, axis=0),
            "median__mAh": np.median(mAh_arr, axis=0)
        }

        mW_mean_total_arr[i] = deployment_data['median__mW_mean']
        mA_mean_total_arr[i] = deployment_data['median__mA_mean']
        mW_max_total_arr[i] = deployment_data['median__mW_max']
        mA_max_total_arr[i] = deployment_data['median__mA_max']
        mWh_total_arr[i] = deployment_data['median__mWh']
        mAh_total_arr[i] = deployment_data['median__mAh']

        deployment_df = pd.DataFrame(deployment_data, tx_power_list)
        deployment_df.to_csv('%s/results/deployments/%s_transmission_results.csv' % (dir_path, deployment))

        print("%s median data:\n" % deployment, deployment_df)

        if save_deployment_plot:
            fig, axs = plt.subplots(2, 3, figsize=(30,8))
            axs[0,0].plot(tx_power_levels, deployment_df['median__mW_max'], 'o--', label='mW')
            axs[0,0].plot(tx_power_levels, deployment_df['median__mA_max'], 'o--', label='mA')
            axs[0,0].set(xlabel="Radio Power", ylabel="Max Transmission Energy")
            axs[0,0].legend(loc="upper left")
            axs[0,1].plot(tx_power_levels, deployment_df['median__mW_mean'], 'o--', label='mW')
            axs[0,1].plot(tx_power_levels, deployment_df['median__mA_mean'], 'o--', label='mA')
            axs[0,1].set(xlabel="Radio Power", ylabel="Mean Transmission Energy")
            axs[0,1].legend(loc="upper left")
            axs[0,2].plot(tx_power_levels, deployment_df['median__mWh'], 'o--', label='mWh')
            axs[0,2].plot(tx_power_levels, deployment_df['median__mAh'], 'o--', label='mAh')
            axs[0,2].set(xlabel="Radio Power", ylabel="Transmission Energy Consumption")
            axs[0,2].legend(loc="upper left")
            axs[1,0].boxplot(mW_mean_arr, positions=tx_power_levels, widths=500, label='mW')
            axs[1,0].boxplot(mA_mean_arr, positions=tx_power_levels, widths=500, label='mA')
            axs[1,0].set(xlabel="Radio Power", ylabel="Max Transmission Energy")
            axs[1,0].legend(loc="upper left")
            axs[1,1].boxplot(mW_max_arr, positions=tx_power_levels, widths=500, label='mW')
            axs[1,1].boxplot(mA_max_arr, positions=tx_power_levels, widths=500, label='mA')
            axs[1,1].set(xlabel="Radio Power", ylabel="Mean Transmission Energy")
            axs[1,1].legend(loc="upper left")
            axs[1,2].boxplot(mAh_arr, positions=tx_power_levels, widths=500, label='mAh')
            axs[1,2].boxplot(mWh_arr, positions=tx_power_levels, widths=500, label='mWh')
            axs[1,2].set(xlabel="Radio Power", ylabel="Transmission Energy Consumption")
            axs[1,2].legend(loc="upper left")
            fig.tight_layout()
            plt.savefig("%s/plots/deployment/%s_plot.svg" % (dir_path, deployment), format="svg")
            if plot:
                plt.show()
            else:
                plt.close(fig)

        print("\nDeployment %s analysis time: " % deployment, time.time() - deployment_start_time, "\n")

    delete_empty_rows = mW_mean_total_arr.any(axis=1)
    total_data = {
        "median__mW_mean": np.median(mW_mean_total_arr[delete_empty_rows], axis=0),
        "median__mA_mean": np.median(mA_mean_total_arr[delete_empty_rows], axis=0),
        "median__mW_max": np.median(mW_max_total_arr[delete_empty_rows], axis=0),
        "median__mA_max": np.median(mA_max_total_arr[delete_empty_rows], axis=0),
        "median__mWh": np.median(mWh_total_arr[delete_empty_rows], axis=0),
        "median__mAh": np.median(mAh_total_arr[delete_empty_rows], axis=0)
    }

    total_df = pd.DataFrame(total_data, tx_power_list)
    total_df.to_csv('%s/results/transmission_results.csv' % dir_path)

    print("Total median data:\n", total_df)

    if save_total_plot:
        fig, axs = plt.subplots(2, 3, figsize=(30,8))
        axs[0,0].plot(tx_power_levels, total_df['median__mW_max'], 'o--', label='mW')
        axs[0,0].plot(tx_power_levels, total_df['median__mA_max'], 'o--', label='mA')
        axs[0,0].set(xlabel="Radio Power", ylabel="Max Transmission Energy")
        axs[0,0].legend(loc="upper left")
        axs[0,1].plot(tx_power_levels, total_df['median__mW_mean'], 'o--', label='mW')
        axs[0,1].plot(tx_power_levels, total_df['median__mA_mean'], 'o--', label='mA')
        axs[0,1].set(xlabel="Radio Power", ylabel="Mean Transmission Energy")
        axs[0,1].legend(loc="upper left")
        axs[0,2].plot(tx_power_levels, total_df['median__mWh'], 'o--', label='mWh')
        axs[0,2].plot(tx_power_levels, total_df['median__mAh'], 'o--', label='mAh')
        axs[0,2].set(xlabel="Radio Power", ylabel="Transmission Energy Consumption")
        axs[0,2].legend(loc="upper left")
        axs[1,0].boxplot(mW_mean_total_arr, positions=tx_power_levels, widths=500, label='mW')
        axs[1,0].boxplot(mA_mean_total_arr, positions=tx_power_levels, widths=500, label='mA')
        axs[1,0].set(xlabel="Radio Power", ylabel="Max Transmission Energy")
        axs[1,0].legend(loc="upper left")
        axs[1,1].boxplot(mW_max_total_arr, positions=tx_power_levels, widths=500, label='mW')
        axs[1,1].boxplot(mA_max_total_arr, positions=tx_power_levels, widths=500, label='mA')
        axs[1,1].set(xlabel="Radio Power", ylabel="Mean Transmission Energy")
        axs[1,1].legend(loc="upper left")
        axs[1,2].boxplot(mWh_total_arr, positions=tx_power_levels, widths=500, label='mWh')
        axs[1,2].boxplot(mAh_total_arr, positions=tx_power_levels, widths=500, label='mAh')
        axs[1,2].set(xlabel="Radio Power", ylabel="Transmission Energy Consumption")
        axs[1,2].legend(loc="upper left")
        fig.tight_layout()
        plt.savefig("%s/plots/total/total_plot.svg" % dir_path, format="svg")
        if plot:
            plt.show()
        else:
            plt.close(fig)
