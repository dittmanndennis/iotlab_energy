import matplotlib.pyplot as plt
from scipy import integrate
import pandas as pd
import numpy as np
import statistics
import time

TRANSMISSION_RATE = 250 # kb/s
FRAME_LENGTH = 128 # Byte
TRANSMISSION_DURATION = (8 * FRAME_LENGTH) / (TRANSMISSION_RATE / 1000) # us / microseconds
SLEEP_POWER = 10

def adv_agg_consumed_energy(x: pd.DataFrame, transmission_rows: int) -> float:
    transmission_end_row = x['power'].rolling(transmission_rows).apply(integrate.trapezoid).idxmax()
    
    transmission_measurements = x.loc[(transmission_end_row - transmission_rows + 1):transmission_end_row]
    y_list_mW = 1000 * transmission_measurements['power'].values - SLEEP_POWER
    x_list_us = transmission_measurements['time'].values

    shorten = x_list_us[-1] - x_list_us[0] - TRANSMISSION_DURATION
    # shorten measurement 0
    shorten_first_value_mW = y_list_mW[0] + (y_list_mW[1] - y_list_mW[0]) * (shorten / (x_list_us[1] - x_list_us[0]))
    shorten_first_time = x_list_us[0] + shorten
    mWh_shorten_zero_value = np.trapezoid(y=([shorten_first_value_mW] + y_list_mW[1:]), x=([shorten_first_time] + x_list_us[1:]))
    # shorten measurement -1
    shorten_last_value_mW = y_list_mW[-1] + (y_list_mW[-2] - y_list_mW[-1]) * (shorten / (x_list_us[-1] - x_list_us[-2]))
    shorten_last_time = x_list_us[-1] - shorten
    mWh_shorten_last_value = np.trapezoid(y=(y_list_mW[:-1] + [shorten_last_value_mW]), x=(x_list_us[:-1] + [shorten_last_time]))

    if mWh_shorten_zero_value < mWh_shorten_last_value:
        y_list_mW[-1] = shorten_last_value_mW
        x_list_us[-1] = shorten_last_time
    else:
        y_list_mW[0] = shorten_first_value_mW
        x_list_us[0] = shorten_first_time

    mW_mean = 0
    for j in range(len(x_list_us) - 1):
        mW_mean += (y_list_mW[j] + y_list_mW[j+1]) / 2 * (x_list_us[j+1] - x_list_us[j])

    return mW_mean / TRANSMISSION_DURATION

if __name__ == "__main__":
    benchmark_time = []
    for i in range(10, 110):
        measurements = []
        for k in range(1000):
            benchmark_data = pd.DataFrame()
            benchmark_data["power"] = np.random.uniform(10, 20, i + 20)
            start = time.time()
            benchmark_data["time"] = [ start + j * (TRANSMISSION_DURATION / i) for j in range(i + 20) ]

            start = time.time()
            adv_agg_consumed_energy(benchmark_data, i)
            duration = time.time() - start
            measurements.append(duration)

        benchmark_time.append(statistics.median(measurements) * 1000)

    plt.plot(range(10, 110), benchmark_time)
    plt.xlabel("Number of Transmission Measurements")
    plt.ylabel("Time to Compute [ms]")
    plt.title("Parse Transceiver Energy Time Series")
    plt.show()
