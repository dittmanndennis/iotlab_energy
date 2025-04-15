from pathlib import Path, PosixPath
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import os
from sklearn.preprocessing import MinMaxScaler
from sklearn.metrics import root_mean_squared_error


SYNC_SEQUENCE = 22
BASE_CASES = 8
POWER_LEVELS = 16
TRANSMISSION_REPETITIONS = 1
CASE_DURATION = 4 # seconds

def parse(dir_path: str, columns: list, plot: bool):
    index = pd.read_csv("%s/results/energy_results.csv" % dir_path, usecols=['Unnamed: 0'], index_col=0).index
    df = pd.read_csv("%s/results/energy_results.csv" % dir_path, usecols=columns)
    print(df)
    # Scale using min-max normalization
    scaled_data = MinMaxScaler().fit_transform(df)
    #df = pd.DataFrame(data=scaled_data, index=index, columns=columns)

    # Process RMSE
    #rmse_mW = {
    #    'mW_max' : root_mean_squared_error(df['median__mWh'], df['median__mW_max']),
    #    'mW_mean': root_mean_squared_error(df['median__mWh'], df['median__mW_mean'])
    #}
    #rmse_mW = pd.DataFrame(rmse_mW, ['mWh'])
    #print("RMSE of transmission energy consumption measured in mW:\n", rmse_mW)
    #rmse_mA = {
    #    'mA_max' : root_mean_squared_error(df['median__mAh'], df['median__mA_max']),
    #    'mA_mean': root_mean_squared_error(df['median__mAh'], df['median__mA_mean'])
    #}
    #rmse_mA = pd.DataFrame(rmse_mA, ['mAh'])
    #print("RMSE of transmission energy consumption measured in mA:\n", rmse_mA)
    print(df['median__mW_mean'])
    tx_power_levels = [-17, -12, -10, -7, -5, -4, -3, -2, -1, 0, 0.7, 1.3, 1.8, 2.3, 2.8, 3]
    fig, axs = plt.subplots(1, 2)
    axs[0].plot(tx_power_levels, df['median__mW_mean'], 'o--', label='mW')
    axs[0].plot(tx_power_levels, df['median__mA_mean'], 'o--', label='mA')
    #axs[0].plot(tx_power_levels, df['median__mW_max'], 'o--', label='max')
    #axs[0].plot(tx_power_levels, df['median__mWh'], 'o--', label='mWh')
    axs[0].set(xlabel="Radio Power [dBm]", ylabel="Energy Consumption")
    axs[0].legend(loc="upper left")
    #axs[1].plot(tx_power_levels, df['median__mA_mean'], 'o--', label='mean')
    #axs[1].plot(tx_power_levels, df['median__mA_max'], 'o--', label='max')
    axs[1].plot(tx_power_levels, df['median__mWh'], 'o--', label='mWh')
    axs[1].plot(tx_power_levels, df['median__mAh'], 'o--', label='mAh')
    axs[1].set(xlabel="Radio Power [dBm]", ylabel="Energy Consumption")
    axs[1].legend(loc="upper left")
    fig.tight_layout()
    plt.savefig("%s/plots/scaled_energy_power_plot.svg" % dir_path, format="svg")
    if plot:
        plt.show()
    else:
        plt.close(fig)

if __name__ == "__main__":
    plot = True

    pd.options.display.float_format = '{:,.2f}'.format
        
    dir_path = os.path.dirname(os.path.realpath(__file__))
    columns = ['median__mW_mean', 'median__mA_mean', 'median__mW_max', 'median__mA_max', 'median__mWh', 'median__mAh']

    parse(dir_path, columns, plot)
