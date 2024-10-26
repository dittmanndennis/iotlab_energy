import matplotlib.pyplot as plt
import pandas as pd
import os

if __name__ == "__main__":
    debug = True

    dir_path = os.path.dirname(os.path.realpath(__file__))

    benchmark_df = pd.read_csv('%s/benchmark/benchmark.csv' % dir_path)

    fig, ax = plt.subplots()
    ax.boxplot([benchmark_df['Saclay Baseline'],benchmark_df['Saclay'],benchmark_df['Grenoble Baseline'],benchmark_df['Grenoble']])
    ax.set_xticklabels(['Saclay Baseline', 'Saclay', 'Grenoble Baseline', 'Grenoble'])
    ax.set_ylabel('Time to Calculate [s]')
    plt.savefig("%s/plots/deployments_max_clique_time_benchmark.svg" % (dir_path), format="svg")
    if debug:
        plt.show()
    else:
        plt.close()
