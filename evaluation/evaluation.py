import matplotlib.pyplot as plt
from pathlib import Path
import pandas as pd
import numpy as np
import statistics
import math
import os

def dfs(latency_matrix: pd.DataFrame, parents: list, idx: int, latency: float, seen: list, deployment: str = "grenoble") -> float:
    if parents[idx] <= 0 or seen[idx]:
        return latency
    seen[idx] = True
    latency += latency_matrix.loc['%s_m3-%d' % (deployment, idx+1), '%s_m3-%d' % (deployment, parents[idx])]
    return dfs(latency_matrix, parents, parents[idx] - 1, latency, seen, deployment)

def plot_latency_dfs(dir_path: Path, grenoble_parents: list, grenoble_titles: list) -> None:
    grenoble_latency_matrix = pd.read_csv("%s/../transmission_matrix/results/indexed_transmission_matrices/comparable_all_calc_0_grenoble.csv" % (dir_path), index_col=0)
    number_of_nodes = len(grenoble_latency_matrix.columns)

    ls = ['-','-.','--',':','-','-.']
    for i, parents in enumerate(grenoble_parents):
        latencies = [ 0 ] * 380
        for j in range(len(parents)):
            seen = [ False ] * 380
            latencies[j] = dfs(grenoble_latency_matrix, parents, j, latencies[j], seen)
        plt.plot(sorted(latencies)[-number_of_nodes:], label=grenoble_titles[i], linestyle=ls[i])
    
    plt.xlabel("Nodes Sorted by Latency")
    plt.ylabel("Latency [ms]")
    plt.legend(loc="upper left")
    plt.title("Grenoble")
    plt.show()

    fig, axs = plt.subplots(1, 2, figsize=(8,4))
    ls = ['-','-.','--',':','-','-.']
    for i, parents in enumerate(grenoble_parents):
        latencies = [ 0 ] * 380
        for j in range(len(parents)):
            seen = [ False ] * 380
            latencies[j] = dfs(grenoble_latency_matrix, parents, j, latencies[j], seen)
        axs[0].plot(sorted(latencies)[-number_of_nodes:], label=grenoble_titles[i], linestyle=ls[i])
    axs[0].set(ylabel="Latency [ms]")
    axs[0].legend(loc="upper left")
    for i, parents in enumerate(grenoble_parents):
        if grenoble_titles[i] == 'MST' or grenoble_titles[i] == 'Chain':
            continue
        latencies = [ 0 ] * 380
        for j in range(len(parents)):
            seen = [ False ] * 380
            latencies[j] = dfs(grenoble_latency_matrix, parents, j, latencies[j], seen)
        print(grenoble_titles[i], " max: ", max(latencies))
        axs[1].plot(sorted(latencies)[-number_of_nodes:], label=grenoble_titles[i], linestyle=ls[i])
        axs[1].hlines(y=max(latencies), xmin=0, xmax=number_of_nodes-1, alpha=0.7)
        axs[1].text(0, max(latencies)+5, grenoble_titles[i], ha='left', va='center')
    fig.supxlabel("Nodes Sorted by Latency")
    plt.suptitle("Grenoble")
    plt.show()

    fig, axs = plt.subplots(1, 2, figsize=(8,4))
    ls = ['-','-.','--',':','-','-.']
    for i, parents in enumerate(grenoble_parents):
        latencies = [ 0 ] * 380
        for j in range(len(parents)):
            seen = [ False ] * 380
            latencies[j] = dfs(grenoble_latency_matrix, parents, j, latencies[j], seen)
        axs[0].plot(np.cumsum(sorted(latencies)[-number_of_nodes:]), label=grenoble_titles[i], linestyle=ls[i])
        axs[0].hlines(y=max(latencies), xmin=0, xmax=number_of_nodes-1, alpha=0.7)
    axs[0].set(ylabel="Cumulative Latency [ms]")
    axs[0].legend(loc="upper left")
    for i, parents in enumerate(grenoble_parents):
        if grenoble_titles[i] == 'MST' or grenoble_titles[i] == 'Chain':
            continue
        latencies = [ 0 ] * 380
        for j in range(len(parents)):
            seen = [ False ] * 380
            latencies[j] = dfs(grenoble_latency_matrix, parents, j, latencies[j], seen)
        print(grenoble_titles[i], " sum: ", sum(latencies))
        axs[1].plot(np.cumsum(sorted(latencies)[-number_of_nodes:]), label=grenoble_titles[i], linestyle=ls[i])
        axs[1].hlines(y=max(np.cumsum(latencies)), xmin=0, xmax=number_of_nodes-1, alpha=0.7)
        axs[1].text(0, max(np.cumsum(latencies))+80, grenoble_titles[i], ha='left', va='center')
    fig.supxlabel("Nodes Sorted by Latency")
    plt.suptitle("Grenoble")
    plt.show()

def plot(dir_path: Path, grenoble_parents: list, grenoble_titles: list, debug: bool = False):
    energy_states = pd.read_csv(Path("%s/../transmission_energy/results/energy_states_results.csv" % dir_path), usecols=['power_median', 'casetxt']).set_index('casetxt')
    RX_ON = energy_states.loc['RX_ON', 'power_median'] - energy_states.loc['SLEEP', 'power_median']
    SLEEP = energy_states.loc['SLEEP', 'power_median']

    grenoble_energy_matrix = pd.read_csv("%s/../transmission_matrix/results/indexed_transmission_matrices/comparable_asymmetric_sqrd_transmission_matrix_grenoble.csv" % (dir_path), index_col=0)
    
    
    plot_latency_dfs(dir_path, grenoble_parents, grenoble_titles)

    dict_node_energy_consumptions = {}
    max_in_degrees = []
    max_energy_operators = []
    for i, (parents, title) in enumerate(zip(grenoble_parents, grenoble_titles)):
        node_energy_consumption = [ 0 ] * 380
        sink = -1
        in_degrees = [ 0 ] * 380
        for node, parent in enumerate(parents):
            if parent == -1:
                continue
            if parent == 0:
                print(title, " sink: ", node)
                sink = node
                continue
            
            if debug:
                print("from: ", "m3-{}".format(node+1), " to: ", "m3-{}".format(parent))

            node_energy_consumption[node] += grenoble_energy_matrix.loc["m3-{}".format(node+1), "m3-{}".format(parent)] - RX_ON
            node_energy_consumption[parent-1] += RX_ON
            in_degrees[parent - 1] += 1

        print(title, " max in-degree: ", max(in_degrees))
        in_degrees = [1] if title == 'Chain' else in_degrees
        max_in_degrees.append(max(in_degrees))
        max_energy_operators.append(max([ node_energy_consumption[i] for i in range(len(in_degrees)) if in_degrees[i] > 0 ]))
        print("Energy consumption of sink: ", node_energy_consumption[sink])
        dict_node_energy_consumptions[title] = [ i for i in node_energy_consumption if i != 0 ]

    fig, axs = plt.subplots(1, 2, figsize=(8,4))
    ls = ['-','-.','--',':','-','-.']
    for i, title in enumerate(grenoble_titles):
        axs[0].plot(sorted(dict_node_energy_consumptions[title]), label=title, linestyle=ls[i])
    axs[0].set(ylabel="Energy Consumption [mW]")
    axs[0].legend(loc="upper left")
    for i, title in enumerate(grenoble_titles):
        axs[1].plot(np.cumsum(sorted(dict_node_energy_consumptions[title])), label=title, linestyle=ls[i])
        print(title, " sum: ", sum(dict_node_energy_consumptions[title]))
    axs[1].set(ylabel="Cumulative Energy Consumption [mW]")
    fig.supxlabel("Nodes Sorted by Transceiver Energy Consumption")
    plt.suptitle("Grenoble")
    plt.show()

    fig, ax = plt.subplots()
    ax.boxplot(dict_node_energy_consumptions.values())
    ax.set_xticklabels(dict_node_energy_consumptions.keys())
    plt.ylabel("Energy Consumption [mW]")
    plt.title("Grenoble")
    plt.show()

    sum_energy_consumption = np.array([sum(dict_node_energy_consumptions[title]) for title in grenoble_titles])
    plt.bar(grenoble_titles, sum_energy_consumption)
    plt.ylabel("Energy Consumption [mW]")
    plt.title("Grenoble")
    plt.show()

    max_Transmission_utilization = 100 / (np.array(max_in_degrees) + 1)
    for title, throughput in zip(grenoble_titles, max_Transmission_utilization):
        print(title, " throughput: ", throughput)
    plt.bar(grenoble_titles, max_Transmission_utilization)
    plt.ylabel("Maximum Throughput [%]")
    plt.title("Grenoble")
    plt.show()
    
    x = np.linspace(0, math.ceil(100/(max(max_in_degrees) + 1)), math.ceil(1000/(max(max_in_degrees) + 1)))
    ls = ['-','-.','--',':','-','-.']
    debs = []
    debs_min = 1000000
    debs_max = 0
    fig, axs = plt.subplots(1, 2, figsize=(8,4))
    for i, title in enumerate(grenoble_titles):
        debs.append(sum_energy_consumption[i] * 0.0102 + len(grenoble_asymmetric_ea_nemo_parents) * SLEEP)
        print(title, " DEBS energy consumption: ", sum_energy_consumption[i] * 0.0102 + len(grenoble_asymmetric_ea_nemo_parents) * SLEEP)
        y = sum_energy_consumption[i] * (x / 100) + len(grenoble_asymmetric_ea_nemo_parents) * SLEEP
        debs_min = min(y) if min(y) < debs_min else debs_min
        debs_max = max(y) if max(y) > debs_max else debs_max
        axs[0].plot(x, y, label=title, linestyle=ls[i])
    
    debs_min = debs_min if debs_min > 0.9 * min(debs) else 0.9 * min(debs)
    debs_max = debs_max if debs_max < 1.1 * max(debs) else 1.1 * max(debs)
    axs[0].vlines(x=1.02, ymin=debs_min, ymax=debs_max, label='DEBS', ls='--', alpha=0.5)
    axs[0].legend(loc="upper left")
    axs[0].set(xlabel="Transmission Utilization [%]", ylabel="Mean Network Energy Consumption [mW]")

    ls = ['-','-.','--',':','-','-.']
    for i, title in enumerate(grenoble_titles):
        energy_values = np.array(dict_node_energy_consumptions[title])
        energy_values = energy_values * 0.0102 + SLEEP
        axs[1].plot(sorted(energy_values), label= title, linestyle=ls[i])
    axs[1].set(xlabel="Nodes Sorted by Energy Consumption", ylabel="Energy Consumption [mW]")
    axs[1].legend(loc="upper left")
    plt.suptitle("Grenoble")
    plt.show()

    # Death of median node
    ea_nemo__median_energy_node = statistics.median(dict_node_energy_consumptions[grenoble_titles[0]])
    # [0] overlaps
    ls = ['-.',':','--','-','--']
    debs = []
    debs_min = 1000000
    debs_max = 0
    for i in range(1, len(grenoble_titles)):
        median_energy_node = statistics.median(dict_node_energy_consumptions[grenoble_titles[i]])
        debs.append((median_energy_node * 0.0102 + SLEEP) / (ea_nemo__median_energy_node * 0.0102 + SLEEP))
        print(grenoble_titles[i], " death of median node DEBS: ", (median_energy_node * 0.0102 + SLEEP) / (ea_nemo__median_energy_node * 0.0102 + SLEEP))
        y = (median_energy_node * (x / 100) + SLEEP) / (ea_nemo__median_energy_node * (x / 100) + SLEEP)
        debs_min = min(y) if min(y) < debs_min else debs_min
        debs_max = max(y) if max(y) > debs_max else debs_max
        plt.plot(x, y, label=grenoble_titles[i], linestyle=ls[i-1])

    debs_min = debs_min if debs_min > 0.9 * min(debs) else 0.9 * min(debs)
    debs_max = debs_max if debs_max < 1.1 * max(debs) else 1.1 * max(debs)
    plt.vlines(x=1.02, ymin=debs_min, ymax=debs_max, label='DEBS', ls='--', alpha=0.5)
    plt.legend(loc="upper left")
    plt.xlabel("Transmission Utilization [%]")
    plt.ylabel("Relative Death of Median Node")
    plt.title("Grenoble")
    plt.show()

    # Death of mean node
    ea_nemo__mean_energy_node = statistics.mean(dict_node_energy_consumptions[grenoble_titles[0]])
    ls = ['-.','-',':','-','--']
    debs = []
    debs_min = 1000000
    debs_max = 0
    for i in range(1, len(grenoble_titles)):
        mean_energy_node = statistics.mean(dict_node_energy_consumptions[grenoble_titles[i]])
        debs.append((mean_energy_node * 0.0102 + SLEEP) / (ea_nemo__mean_energy_node * 0.0102 + SLEEP))
        print(grenoble_titles[i], " death of mean node DEBS: ", (mean_energy_node * 0.0102 + SLEEP) / (ea_nemo__mean_energy_node * 0.0102 + SLEEP))
        y = (mean_energy_node * (x / 100) + SLEEP) / (ea_nemo__mean_energy_node * (x / 100) + SLEEP)
        debs_min = min(y) if min(y) < debs_min else debs_min
        debs_max = max(y) if max(y) > debs_max else debs_max
        plt.plot(x, y, label=grenoble_titles[i], linestyle=ls[i-1])
        
    debs_min = debs_min if debs_min > 0.9 * min(debs) else 0.9 * min(debs)
    debs_max = debs_max if debs_max < 1.1 * max(debs) else 1.1 * max(debs)
    plt.vlines(x=1.02, ymin=debs_min, ymax=debs_max, label='DEBS', ls='--', alpha=0.5)
    plt.legend(loc="upper left")
    plt.xlabel("Transmission Utilization [%]")
    plt.ylabel("Relative Death of Mean Node")
    plt.title("Grenoble")
    plt.show()

    # Death of first node & operator
    fig, axs = plt.subplots(1, 2, figsize=(8,4))
    ea_nemo__max_energy_node = max(dict_node_energy_consumptions[grenoble_titles[0]])
    ls = ['-.','-','--','-',':']
    debs = []
    debs_min = 1000000
    debs_max = 0
    for i in range(1, len(grenoble_titles)):
        max_energy_node = max(dict_node_energy_consumptions[grenoble_titles[i]])
        debs.append((max_energy_node * 0.0102 + SLEEP) / (ea_nemo__max_energy_node * 0.0102 + SLEEP))
        print(grenoble_titles[i], " death of first node & operator: ", (max_energy_node * 0.0102 + SLEEP) / (ea_nemo__max_energy_node * 0.0102 + SLEEP))
        y = (max_energy_node * (x / 100) + SLEEP) / (ea_nemo__max_energy_node * (x / 100) + SLEEP)
        debs_min = min(y) if min(y) < debs_min else debs_min
        debs_max = max(y) if max(y) > debs_max else debs_max
        axs[0].plot(x, y, label=grenoble_titles[i], linestyle=ls[i-1])
    debs_min = debs_min if debs_min > 0.9 * min(debs) else 0.9 * min(debs)
    debs_max = debs_max if debs_max < 1.1 * max(debs) else 1.1 * max(debs)
    axs[0].vlines(x=1.02, ymin=debs_min, ymax=debs_max, label='DEBS', ls='--', alpha=0.5)
    axs[0].set(ylabel="Relative Death of First Node")
    axs[0].legend(loc="upper left")
    ea_nemo__max_energy_operator = max_energy_operators[0]
    debs = []
    debs_min = 1000000
    debs_max = 0
    for i in range(1, len(grenoble_titles)):
        debs.append((max_energy_operators[i] * 0.0102 + SLEEP) / (ea_nemo__max_energy_operator * 0.0102 + SLEEP))
        y = (max_energy_operators[i] * (x / 100) + SLEEP) / (ea_nemo__max_energy_operator * (x / 100) + SLEEP)
        debs_min = min(y) if min(y) < debs_min else debs_min
        debs_max = max(y) if max(y) > debs_max else debs_max
        axs[1].plot(x, y, label=grenoble_titles[i], linestyle=ls[i-1])
    debs_min = debs_min if debs_min > 0.9 * min(debs) else 0.9 * min(debs)
    debs_max = debs_max if debs_max < 1.1 * max(debs) else 1.1 * max(debs)
    axs[1].vlines(x=1.02, ymin=debs_min, ymax=debs_max, label='DEBS', ls='--', alpha=0.5)
    axs[1].set(ylabel="Relative Death of First Operator")
    fig.supxlabel("Transmission Utilization [%]")
    plt.suptitle("Grenoble")
    plt.show()

    # Death of first node
    ea_nemo__max_energy_node = max(dict_node_energy_consumptions[grenoble_titles[0]])
    for i in range(1, len(grenoble_titles)):
        max_energy_node = max(dict_node_energy_consumptions[grenoble_titles[i]])
        y = (max_energy_node * (x / 100) + SLEEP) / (ea_nemo__max_energy_node * (x / 100) + SLEEP)
        plt.plot(x, y, label=grenoble_titles[i])
        
    plt.legend(loc="center right")
    plt.xlabel("Transmission Utilization [%]")
    plt.ylabel("Relative Death of First Node")
    plt.title("Grenoble")
    plt.show()

    # Death of first operator
    ea_nemo__max_energy_operator = max_energy_operators[0]
    for i in range(1, len(grenoble_titles)):
        y = (max_energy_operators[i] * (x / 100) + SLEEP) / (ea_nemo__max_energy_operator * (x / 100) + SLEEP)
        plt.plot(x, y, label=grenoble_titles[i])
        
    #plt.xscale("log")
    plt.legend(loc="center right")
    plt.xlabel("Transmission Utilization [%]")
    plt.ylabel("Relative Death of First Operator")
    plt.title("Grenoble")
    plt.show()


if __name__ == "__main__":
    # TODO: Probably no real gain from this, because the topology and the networks properties are the same.
    #       maybe do some 5ish random selection on the reduced grenoble matrix of 80 nodes?
    #       to see if results are consistent.
    dir_path = os.path.dirname(os.path.realpath(__file__))

    grenoble_asymmetric_ea_nemo_parents = [-1, 0, -1, -1, -1, -1, -1, -1, -1, -1, 232, -1, 208, 237, 232, 208, -1, 26, -1, 265, 232, 26, -1, 232, 283, 2, 246, 26, -1, 237, 265, 237, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, 280, 265, 232, -1, 280, 232, 232, 237, 237, -1, -1, 280, 237, -1, 232, 265, 265, -1, 280, 232, 265, 26, 283, 280, 283, 232, 237, 237, 237, -1, 280, 2, 280, 280, 265, 265, -1, 232, 246, 265, -1, 280, 280, 280, 265, 265, 237, 246, 265, 237, 265, 237, 208, 283, 283, 2, 232, 237, 26, 232, 2, 280, 26, 280, 280, -1, -1, 246, 265, 2, 26, 280, 265, 237, -1, 271, -1, 232, 280, 265, 283, -1, 246, 280, 232, -1, -1, 26, 2, -1, 237, -1, 26, 246, 2, 208, 208, 280, 237, 26, 280, 237, 280, 2, -1, 280, 2, 246, 280, 246, -1, 208, 237, 232, -1, -1, 237, -1, -1, -1, 237, 246, 232, -1, -1, -1, 237, -1, -1, -1, 280, -1, 237, 208, 237, 237, 26, 237, -1, -1, 237, 26, -1, -1, 280, 237, -1, 237, 280, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1]
    grenoble_symmetric_ea_nemo_parents = [-1, 0, -1, -1, -1, -1, -1, -1, -1, -1, 216, -1, 216, 216, 232, 280, -1, 25, -1, 236, 256, 235, -1, 236, 2, 236, 231, 195, -1, 259, 256, 289, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, 195, 235, 235, -1, 195, 289, 289, 231, 236, -1, -1, 195, 235, -1, 195, 195, 231, -1, 2, 256, 235, 289, 289, 256, 235, 25, 259, 280, 231, -1, 235, 195, 256, 259, 235, 25, -1, 195, 236, 2, -1, 235, 231, 256, 235, 235, 231, 235, 231, 256, 195, 256, 235, 256, 2, 2, 195, 235, 2, 2, 256, 235, 231, 235, 235, -1, -1, 235, 195, 216, 195, 256, 195, 256, -1, 195, -1, 216, 259, 2, 256, -1, 2, 235, 289, -1, -1, 231, 235, -1, 25, -1, 236, 231, 195, 195, 289, 216, 256, 259, 256, 256, 256, 2, -1, 259, 195, 256, 289, 231, -1, 289, 2, 289, -1, -1, 195, -1, -1, -1, 256, 195, 256, -1, -1, -1, 289, -1, -1, -1, 232, -1, 236, 195, 195, 280, 25, 235, -1, -1, 216, 259, -1, -1, 235, 259, -1, 25, 280, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1]
    grenoble_nemo_parents = [-1, 0, -1, -1, -1, -1, -1, -1, -1, -1, 15, -1, 2, 250, 2, 250, -1, 250, -1, 13, 13, 13, -1, 13, 13, 13, 13, 13, -1, 13, 13, 250, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, 13, 13, 198, -1, 13, 219, 13, 13, 198, -1, -1, 13, 198, -1, 228, 15, 13, -1, 13, 303, 13, 2, 13, 198, 13, 198, 250, 198, 228, -1, 250, 250, 228, 15, 198, 219, -1, 228, 198, 219, -1, 228, 2, 13, 15, 228, 198, 15, 228, 13, 15, 2, 198, 303, 13, 15, 303, 219, 198, 250, 228, 13, 250, 228, 13, -1, -1, 250, 13, 250, 13, 219, 250, 2, -1, 13, -1, 303, 13, 13, 303, -1, 13, 250, 13, -1, -1, 250, 13, -1, 13, -1, 13, 250, 13, 13, 13, 13, 219, 13, 13, 15, 13, 250, -1, 250, 198, 13, 2, 303, -1, 303, 13, 2, -1, -1, 13, -1, -1, -1, 13, 219, 228, -1, -1, -1, 2, -1, -1, -1, 13, -1, 219, 13, 13, 13, 219, 13, -1, -1, 13, 13, -1, -1, 13, 250, -1, 13, 13, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1]
    grenoble_leach = [-1, 0, -1, -1, -1, -1, -1, -1, -1, -1, 288, -1, 207, 309, 15, 309, -1, 207, -1, 314, 15, 22, -1, 309, 314, 269, 314, 220, -1, 318, 318, 220, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, 314, 318, 179, -1, 314, 309, 318, 231, 314, -1, -1, 314, 179, -1, 309, 314, 255, -1, 220, 288, 318, 309, 314, 179, 318, 314, 309, 179, 314, -1, 207, 220, 309, 288, 179, 309, -1, 309, 179, 309, -1, 314, 309, 220, 288, 309, 179, 288, 309, 318, 314, 309, 309, 288, 231, 314, 288, 309, 314, 220, 309, 15, 239, 314, 269, -1, -1, 207, 220, 207, 314, 309, 220, 207, -1, 269, -1, 288, 255, 314, 288, -1, 220, 220, 318, -1, -1, 207, 231, -1, 220, -1, 269, 207, 318, 314, 318, 318, 309, 314, 318, 231, 314, 239, -1, 239, 314, 318, 231, 231, -1, 288, 318, 288, -1, -1, 318, -1, -1, -1, 318, 309, 314, -1, -1, -1, 15, -1, -1, -1, 318, -1, 309, 314, 318, 318, 318, 314, -1, -1, 314, 318, -1, -1, 318, 309, -1, 318, 318, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1]
    grenoble_mst = [-1, 24, -1, -1, -1, -1, -1, -1, -1, -1, 324, -1, 273, 314, 27, 272, -1, 25, -1, 256, 310, 20, -1, 240, 205, 235, 283, 247, -1, 317, 210, 288, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, 224, 233, 221, -1, 192, 222, 225, 191, 212, -1, -1, 216, 322, -1, 16, 244, 219, -1, 228, 198, 309, 182, 248, 237, 214, 223, 204, 227, 257, -1, 230, 238, 303, 199, 249, 260, -1, 282, 208, 32, -1, 297, 181, 299, 218, 202, 185, 200, 211, 179, 189, 215, 0, 209, 275, 321, 312, 284, 31, 325, 311, 274, 267, 259, 220, -1, -1, 245, 28, 271, 289, 195, 14, 203, -1, 298, -1, 234, 313, 307, 201, -1, 197, 293, 178, -1, -1, 277, 30, -1, 183, -1, 261, 318, 226, 279, 15, 21, 265, 278, 286, 285, 290, 254, -1, 196, 11, 232, 177, 188, -1, 276, 26, 269, -1, -1, 241, -1, -1, -1, 252, 207, 246, -1, -1, -1, 280, -1, -1, -1, 239, -1, 184, 231, 22, 255, 193, 270, -1, -1, 264, 2, -1, -1, 250, 18, -1, 13, 236, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1]
    grenoble_chain = [-1, 0, -1, -1, -1, -1, -1, -1, -1, -1, 232, -1, 18, 321, 279, 244, -1, 236, -1, 310, 15, 184, -1, 14, 256, 267, 25, 259, -1, 261, 325, 208, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, 276, 277, 211, -1, 197, 309, 261, 241, 202, -1, -1, 177, 179, -1, 225, 221, 270, -1, 289, 257, 293, 322, 314, 202, 284, 235, 14, 223, 218, -1, 2, 245, 248, 224, 200, 216, -1, 223, 204, 322, -1, 299, 228, 249, 233, 205, 229, 11, 237, 273, 192, 198, 222, 221, 184, 177, 11, 298, 283, 203, 214, 303, 252, 218, 252, -1, -1, 250, 220, 207, 272, 182, 260, 18, -1, 269, -1, 196, 280, 30, 230, -1, 220, 282, 318, -1, -1, 2, 231, -1, 259, -1, 26, 264, 274, 27, 318, 28, 234, 303, 30, 265, 199, 246, -1, 246, 218, 312, 290, 278, -1, 224, 31, 254, -1, -1, 277, -1, -1, -1, 197, 228, 181, -1, -1, -1, 199, -1, -1, -1, 284, -1, 298, 181, 274, 31, 297, 25, -1, -1, 188, 311, -1, -1, 195, 16, -1, 311, 183, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1]

    grenoble_parents = [ grenoble_asymmetric_ea_nemo_parents, grenoble_symmetric_ea_nemo_parents, grenoble_nemo_parents, grenoble_leach, grenoble_mst, grenoble_chain ]
    grenoble_titles = [ "Asymmetric EA-NEMO", "Symmetric EA-NEMO", "NEMO", "LEACH", "MST", "Chain" ]

    plot(dir_path, grenoble_parents, grenoble_titles)
