from collections import defaultdict
from random import shuffle
from pathlib import Path
import pandas as pd
import numpy as np
import time
import math
import re
import os


'''
We implemented two methods to approximate the maximum clique in a WSN.

1. Greedy - this method has no guarantee of terminating in a reasonable amount of time (not NP-Complete)
    - The first time the last element of a group of nodes is hit,
      we terminate the branch and bound algorithm for this group.

2. Slicing
    - We slice groups into sizes that have a reasonable runtime.
'''

def max_clique(slice: int, matrix: pd.DataFrame, memo_clusters: dict, cluster_set: set, plot: bool=False, debug: bool=False) -> set:
    # Pre-processing
    nodes = [( 0, 0, node ) for node in cluster_set]

    greedy = True
    if slice > 1:
        greedy = False
    if debug:
        print("Greedy: ", greedy)
    max_num = 0
    max_cluster = cluster_set
    while nodes:
        filtered_nodes = []
        for i in range(len(nodes)):
            if nodes[i][2] not in max_cluster:
                continue
            
            if plot:
                nodes_in_common = set()
                for node in max_cluster:
                    if node in memo_clusters[nodes[i][2]]:
                        nodes_in_common.add(node)
            else:
                nodes_in_common = max_cluster.intersection(memo_clusters[nodes[i][2]])
            transmission_energy = 0
            filtered_nodes.append(    ( -len(nodes_in_common), transmission_energy, nodes[i][2] )    )

        nodes = sorted(filtered_nodes)

        if debug:
            print("Slices left: ", math.ceil(len(nodes) / slice))

        group = nodes[:min(len(nodes), slice)]
        included = [ False ] * min(len(nodes), slice)
        nodes = nodes[min(len(nodes), slice):]
        
        max_num, max_cluster, hit_max = branch_and_bound(greedy, matrix, memo_clusters, included, group
                                                      , node_idx=0, curr_num=max_num, max_num=max_num
                                                      , curr_cluster=max_cluster, max_cluster=max_cluster)

    return max_cluster

def branch_and_bound(greedy: bool, matrix: pd.DataFrame, memo_clusters: dict, included: list, nodes: list
                                 , node_idx: int, curr_num: int, max_num: int, curr_cluster: set, max_cluster: set
                                 , debug: bool=False):
    if greedy and node_idx == len(nodes):
        return max_num, max_cluster, True
    if curr_num + len(nodes) - node_idx < max_num or (curr_num + len(nodes) - node_idx == max_num
                                                      and len(curr_cluster) < len(max_cluster)):
        return max_num, max_cluster, False

    if debug:
        if node_idx == 0:
            print('branch_and_bound 0: ', max_num)
        elif node_idx == 1:
            print('branch_and_bound 1: ', max_num)
        elif node_idx == 2:
            print('branch_and_bound 2: ', max_num)
        elif node_idx == 4:
            print('branch_and_bound 4: ', max_num)
        elif node_idx == 6:
            print('branch_and_bound 6: ', max_num)
        elif node_idx == 8:
            print('branch_and_bound 8: ', max_num)

    for i in range(node_idx, len(nodes)):
        if nodes[i][2] in curr_cluster and not included[i]:
            included[i] = True
            next_cluster = curr_cluster.intersection(memo_clusters[nodes[i][2]])
            curr_is_max = is_curr_max(matrix, curr_num+1, max_num, next_cluster, max_cluster)
            curr_max_num, curr_max_cluster, hit_max = branch_and_bound(greedy, matrix, memo_clusters, included, nodes
                           , node_idx=i+1, curr_num=curr_num+1
                           , max_num=(curr_num+1 if curr_is_max else max_num)
                           , curr_cluster=next_cluster
                           , max_cluster=(next_cluster if curr_is_max else max_cluster))
            included[i] = False
            if is_curr_max(matrix, curr_max_num, max_num, curr_max_cluster, max_cluster):
                max_num = curr_max_num
                max_cluster = curr_max_cluster
            if greedy and hit_max:
                return max_num, max_cluster, True

    return max_num, max_cluster, False

def is_curr_max(matrix: pd.DataFrame, curr_num: int, max_num: int, curr_cluster: set, max_cluster: set, debug: bool=False):
    if curr_num > max_num or (curr_num == max_num and len(curr_cluster) > len(max_cluster)):
        return True
    return False

def parse(deployment: str, dir_path: Path, power_path: Path, tranmission_energy_path: Path, slice: int, plot: bool=True, debug: bool=False) -> None:
    results = {}

    sent = set()
    received = set()

    with open(power_path) as transmission_log:
        for line in transmission_log:
            try:
                m = re.search(r".*?(?=m3[-_][0-9]+)(m3[-_][0-9]+).*?(?=m3[-_][0-9]+)(m3[-_][0-9]+).*", line)
                assert(m)

                # From M3-XXX to M3-XXX
                key = "('%s', '%s')" % (m.group(2), m.group(1))
                sent.add(m.group(2))
                received.add(m.group(1))
                
                results[key] = results.get(key, 0) + 1
            except:
                if debug:
                    print("Could not parse line: ", line)

    # Filter broken nodes
    if debug:
        print("Unconnected/broken nodes: ", sent.symmetric_difference(received), "\n")
    intersection = sent.intersection(received)
    axis_nodes = list(intersection)
    axis_nodes.sort(key=lambda n: int(re.search(r"m3[-_]([0-9]+)", n).group(1)))
    matrix = pd.DataFrame(data=np.zeros((len(axis_nodes),len(axis_nodes))), index=axis_nodes, columns=axis_nodes)
    
    df = pd.read_csv(tranmission_energy_path, usecols=['median__mW_mean'])

    for key in results.keys():
        sending_node = key.split("', '")[0][2:]
        receiving_node = key.split("', '")[1][:-2]
        if 0 < results[key] <= 16 and sending_node in intersection and receiving_node in intersection:
            results[key] = [df['median__mW_mean'].iloc[16 - results[key]]]
            matrix.loc[sending_node, receiving_node] = results[key][0]
        else:
            results[key] = 'NA'

    center_nodes = []
    max_connected_nodes = 0
    memo_clusters = defaultdict(set)
    for center_node, column in matrix.items():
        memo_clusters[center_node].add(center_node)
        connected_nodes = 0
        for idx, cell in column.items():
            if matrix.loc[center_node, idx] > 0.0 and cell > 0.0:
                connected_nodes += 1
                memo_clusters[center_node].add(idx)

        if max_connected_nodes < connected_nodes:
            max_connected_nodes = connected_nodes
            center_nodes = [ center_node ]
        elif max_connected_nodes == connected_nodes:
            center_nodes.append(center_node)

    if debug:
        print("Center nodes: ", center_nodes, " Connected nodes: ", max_connected_nodes)

    if plot:
        max_center_node = None

    max_cluster = set()
    max_slices = defaultdict(list)
    for center_node in center_nodes:
        for i in range(1, slice+1):
            curr_max_cluster = max_clique(i, matrix, memo_clusters, memo_clusters[center_node])

            if len(curr_max_cluster) == len(max_cluster):
                max_slices[center_node].append(i)
            elif len(curr_max_cluster) > len(max_cluster):
                max_slices = defaultdict(list)
                max_slices[center_node].append(i)
            if is_curr_max(matrix, len(curr_max_cluster), len(max_cluster), curr_max_cluster, max_cluster):
                max_cluster = curr_max_cluster
                if plot:
                    max_center_node = center_node

    if plot:
        greedy_time_stats = []
        for i in range(30):
            start = time.time()
            curr_max_cluster = max_clique(1, matrix, memo_clusters, memo_clusters[max_center_node], True)
            elapsed_time = time.time() - start
            greedy_time_stats.append(elapsed_time)
        
        benchmark_df = pd.read_csv('%s/benchmark/benchmark.csv' % dir_path, index_col=0)
        benchmark_df['%s Baseline' % deployment.title()] = greedy_time_stats
        benchmark_df.to_csv('%s/benchmark/benchmark.csv' % dir_path)

    max_clique_keys = sorted(list(max_cluster), key=lambda idx : int(idx.split("-")[1]))
    clique = matrix.loc[max_clique_keys, max_clique_keys]

    # Add the RX energy consumption
    states_df = pd.read_csv(Path("%s/../transmission_energy/results/energy_states_results.csv" % dir_path), usecols=['power_median', 'casetxt']).set_index('casetxt')
    add_rx_energy = np.full(clique.values.shape, (states_df.loc['RX_ON'] - states_df.loc['SLEEP']))
    np.fill_diagonal(add_rx_energy, 0.0)
    numeric_data = clique.values.copy()
    numeric_data += add_rx_energy
    clique.iloc[:] = numeric_data

    print(clique)
    print("Slices with max cluster: ", max_slices)
    clique.to_csv('%s/results/indexed_transmission_matrices/max_clique_transmission_matrix_%s.csv' % (dir_path, deployment))
    clique.to_csv('%s/results/matlab_input/max_clique_transmission_matrix_%s.csv' % (dir_path, deployment), header=False, index=False)

if __name__ == "__main__":
    slice = 1
    dir_path = os.path.dirname(os.path.realpath(__file__))

    power_pathlist = Path("%s/raw_data/" % dir_path).rglob("*.log")
    tranmission_energy_path = Path("%s/../transmission_energy/results/energy_results.csv" % dir_path)
    
    for power_path in power_pathlist:
        deployment = power_path.name.split('_')[0]
        
        parse(deployment, dir_path, power_path, tranmission_energy_path, slice)
