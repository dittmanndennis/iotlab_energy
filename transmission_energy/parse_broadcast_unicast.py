from pathlib import Path, PosixPath
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import re
import collections
import math
import os
from scipy import integrate


SYNC_SEQUENCE = 22
POWER_LEVELS = 16
BASE_CASES = 8
TRANSMISSION_REPETITIONS = 40
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

def parse(path: PosixPath, plot: bool, save_boxplots: bool, save_transmission_energy_dist: bool):
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
    transmission_duration = (8 * FRAME_LENGTH) / (TRANSMISSION_RATE / 1000) # us / microseconds
    transmission_rows = 1 + math.ceil(transmission_duration / interval_us)
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

    index = []
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
        "median__mAh": [],
        #"mean__mW_mean": [],
        #"mean__mA_mean": [],
        #"mean__mW_max": [],
        #"mean__mA_max": [],
        #"mean__mWh": [],
        #"mean__mAh": []
    }
    
    for i in range(0, POWER_LEVELS):
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

        if plot:
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

        # Group by case (only middle segment)
        cases = df.loc[np.where((df['case'] <= BASE_CASES) &
                                (df['case_part'].values == 1))]
        def agg_current(x: pd.DataFrame) -> pd.Series:
            d = collections.OrderedDict()
            d['power_median'] = 1000 * np.median(remove_outliers(x['power']))
            d['current_median'] = 1000 * np.median(remove_outliers(x['current']))
            return pd.Series(d)
        node_medians = cases.groupby(['case']).apply(agg_current, include_groups=False)

        node_medians['casetxt'] = node_medians.apply(lambda x: casetxt(x.name),axis=1)
        node_medians = node_medians[node_medians['casetxt'].values != 'unknown']

        # Get transmission energy consumption (in mW, mA, mWh, mAh)
        sleep_power = node_medians["power_median"].iloc[np.where(node_medians['casetxt'].values == "SLEEP")].values
        sleep_current = node_medians["current_median"].iloc[np.where(node_medians['casetxt'].values == "SLEEP")].values
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
                transmission_dist_padding_mW[int((transmission_rows + 1) * transmission_duration / (transmission_rows - 1))].append(curr_transmission_mW[-1])
                transmission_dist_padding_mA[0].append(curr_transmission_mA[0])
                transmission_dist_padding_mA[int((transmission_rows + 1) * transmission_duration / (transmission_rows - 1))].append(curr_transmission_mA[-1])
                for j in range(transmission_rows):
                    transmission_dist_mW[int((j + 1) * transmission_duration / (transmission_rows - 1))].append(curr_transmission_mW[j + 1])
                    transmission_dist_mA[int((j + 1) * transmission_duration / (transmission_rows - 1))].append(curr_transmission_mA[j + 1])

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

            shorten = x_list_us[-1] - x_list_us[0] - transmission_duration
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
            d['mW_mean'] = mW_mean / transmission_duration
            d['mA_mean'] = mA_mean / transmission_duration
            
            d['mWh'] = np.trapezoid(y=y_list_mW, x=x_list_us) / (3600000000 / transmission_duration)
            d['mAh'] = np.trapezoid(y=y_list_mA, x=x_list_us) / (3600000000 / transmission_duration)
            d['mW_max'] = np.max(y_list_mW)
            d['mA_max'] = np.max(y_list_mA)

            return pd.Series(d)
        
        if save_transmission_energy_dist:
            transmission_dist_padding_mW = {
                0: [],
                int((transmission_rows + 1) * transmission_duration / (transmission_rows - 1)): []
            }
            transmission_dist_mW = {}
            transmission_dist_padding_mA = {
                0: [],
                int((transmission_rows + 1) * transmission_duration / (transmission_rows - 1)): []
            }
            transmission_dist_mA = {}
            for j in range(transmission_rows):
                transmission_dist_mW[int((j + 1) * transmission_duration / (transmission_rows - 1))] = []
                transmission_dist_mA[int((j + 1) * transmission_duration / (transmission_rows - 1))] = []

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

        index.append(tx_power_list[i])

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
        data['median__mW_max'].append(np.median(remove_outliers(transmission_energy_consumption['mW_max']).values))     # Preferred
        data['median__mA_max'].append(np.median(remove_outliers(transmission_energy_consumption['mA_max']).values))     # Preferred
        data['median__mWh'].append(np.median(remove_outliers(transmission_energy_consumption['mWh']).values))           # Preferred
        data['median__mAh'].append(np.median(remove_outliers(transmission_energy_consumption['mAh']).values))           # Preferred
        #data['mean__mW_mean'].append(np.mean(remove_outliers(transmission_energy_consumption['mW_mean']).values))
        #data['mean__mA_mean'].append(np.mean(remove_outliers(transmission_energy_consumption['mA_mean']).values))
        #data['mean__mW_max'].append(np.mean(remove_outliers(transmission_energy_consumption['mW_max']).values))
        #data['mean__mA_max'].append(np.mean(remove_outliers(transmission_energy_consumption['mA_max']).values))
        #data['mean__mWh'].append(np.mean(remove_outliers(transmission_energy_consumption['mWh']).values))
        #data['mean__mAh'].append(np.mean(remove_outliers(transmission_energy_consumption['mAh']).values))

        # Remove rows of current POWER_LEVEL
        df = df.loc[int(TOTAL_CASES*case_rows + int(1.9 * case_rows)):]

    return pd.DataFrame(data, index)

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
    save_boxplots = True
    save_energy_power_plots = True
    save_transmission_energy_dist = True

    pd.options.display.float_format = '{:,.2f}'.format
        
    dir_path = os.path.dirname(os.path.realpath(__file__))

    pathlist = Path("%s/raw_data_transmit/" % dir_path).rglob("*.oml")
    for idx, path in enumerate(pathlist):
        m = re.search(r"m3[-_]([0-9]*)[-_](.*?(?=\.oml))", str(path.name))
        assert(m)
        print(m.group(2))

        df = parse(path, plot, save_boxplots, save_transmission_energy_dist)

        df.to_csv('%s/radios_measurements/%i_energy_results.csv' % (dir_path, idx))
        #df.to_csv('%s/results/energy_results.csv' % dir_path)

        if save_energy_power_plots:
            tx_power_levels = [-17, -12, -10, -7, -5, -4, -3, -2, -1, 0, 0.7, 1.3, 1.8, 2.3, 2.8, 3]

            fig, axs = plt.subplots(1, 3, figsize=(30,4))
            axs[0].plot(df['median__mW_max'], tx_power_levels, 'o--', label='mW')
            #axs[0].plot(df['median__mA_max'], tx_power_levels, 'o--', label='mA')
            axs[0].set(xlabel="Max Transmission Energy", ylabel="Radio Power")
            axs[0].legend(loc="upper left")
            axs[1].plot(df['median__mW_mean'], tx_power_levels, 'o--', label='mW')
            #axs[1].plot(df['median__mA_mean'], tx_power_levels, 'o--', label='mA')
            axs[1].set(xlabel="Mean Transmission Energy", ylabel="Radio Power")
            axs[1].legend(loc="upper left")
            axs[2].plot(df['median__mWh'], tx_power_levels, 'o--', label='mWh')
            #axs[2].plot(df['median__mAh'], tx_power_levels, 'o--', label='mAh')
            axs[2].set(xlabel="Transmission Energy Consumption", ylabel="Radio Power")
            axs[2].legend(loc="upper left")
            fig.tight_layout()
            plt.savefig("%s/plots/mW_inverse_energy_power_plot.svg" % dir_path, format="svg")
            if plot:
                plt.show()
            else:
                plt.close(fig)

        print_result(df)
