from collections import defaultdict
from random import shuffle
from pathlib import Path
import pandas as pd
import numpy as np
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

def max_clique(slice: int, shuffle_rounds: int, matrix: pd.DataFrame, memo_clusters: dict
                         , grouped_nodes: dict, sorted_keys: list, cluster_set: set):
    greedy = True
    for i in range(0, len(sorted_keys)):
        if slice < len(grouped_nodes[sorted_keys[i]]):
            greedy = False
    print("Greedy: ", greedy)
    max_num = 1
    max_cluster = cluster_set
    for i in range(0, len(sorted_keys)):
        print(i, " of ", len(sorted_keys))
        group = list(grouped_nodes[sorted_keys[i]])
        prev_num = max_num
        prev_cluster = max_cluster
        for j in range(0, shuffle_rounds):
            shuffle(group)
            curr_num = prev_num
            curr_cluster = prev_cluster
            for k in range(0, math.ceil(len(group) / slice)):
                begin = k * slice
                end = ((k + 1) * slice if (k + 1) * slice < len(group) else len(group))
                included = [ False ] * (end - begin)
                max_num, max_cluster, hit_max = branch_and_bound(greedy, matrix, memo_clusters, included
                                                              , group[begin:end]
                                                              , node_idx=0, curr_num=curr_num, max_num=max_num
                                                              , curr_cluster=curr_cluster, max_cluster=max_cluster)
                curr_num, curr_cluster = max_num, max_cluster

    return max_cluster

def branch_and_bound(greedy: bool, matrix: pd.DataFrame, memo_clusters: dict, included: list, nodes: list
                                 , node_idx: int, curr_num: int, max_num: int, curr_cluster: set, max_cluster: set):
    if greedy and node_idx == len(nodes):
        return max_num, max_cluster, True
    if curr_num + len(nodes) - node_idx < max_num or (curr_num + len(nodes) - node_idx == max_num
                                                      and len(curr_cluster) < len(max_cluster)):
        return max_num, max_cluster, False
    
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
        if nodes[i] in curr_cluster:
            included[i] = True
            next_cluster = curr_cluster.intersection(memo_clusters[nodes[i]])
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

def is_curr_max(matrix: pd.DataFrame, curr_num: int, max_num: int, curr_cluster: set, max_cluster: set):
    if curr_num < max_num or (curr_num == max_num and len(curr_cluster) < len(max_cluster)):
        return False
    if curr_num > max_num or (curr_num == max_num and len(curr_cluster) > len(max_cluster)):
        return True
    
    curr_cluster_list = list(curr_cluster)
    curr_cluster_energy = 0.0
    for i in range(0, len(curr_cluster_list)-1):
        for j in range(i+1, len(curr_cluster_list)):
            curr_cluster_energy += matrix.loc[curr_cluster_list[i], curr_cluster_list[j]]
            curr_cluster_energy += matrix.loc[curr_cluster_list[j], curr_cluster_list[i]]

    max_cluster_list = list(max_cluster)
    max_cluster_energy = 0.0
    for i in range(0, len(max_cluster_list)-1):
        for j in range(i+1, len(max_cluster_list)):
            max_cluster_energy += matrix.loc[max_cluster_list[i], max_cluster_list[j]]
            max_cluster_energy += matrix.loc[max_cluster_list[j], max_cluster_list[i]]
    
    return curr_cluster_energy <= max_cluster_energy

def parse(deployment: str, dir_path: Path, power_path: Path, tranmission_energy_path: Path, slice: int, shuffle_rounds: int):
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
                print("Could not parse line: ", line)

    # Filter broken nodes
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
    memo_grouped_nodes = {}
    min_total_energy = 2 * 400 * 100
    for center_node, column in matrix.items():
        memo_clusters[center_node].add(center_node)
        grouped_nodes = defaultdict(set)
        connected_nodes = 0
        total_energy = 0
        for idx, cell in column.items():
            if matrix.loc[center_node, idx] > 0.0 and cell > 0.0:
                connected_nodes += 1
                memo_clusters[center_node].add(idx)
                grouped_nodes[matrix.loc[center_node, idx] + cell].add(idx)
                total_energy += matrix.loc[center_node, idx] + cell

        if max_connected_nodes < connected_nodes or (max_connected_nodes == connected_nodes and total_energy < min_total_energy):
            max_connected_nodes = connected_nodes
            min_total_energy = total_energy
            center_nodes = [ center_node ]
            memo_grouped_nodes = { center_node : grouped_nodes }
        elif max_connected_nodes == connected_nodes and total_energy == min_total_energy:
            center_nodes.append(center_node)
            memo_grouped_nodes[center_node] = grouped_nodes

    print("Center nodes: ", center_nodes, " Connected nodes: ", max_connected_nodes)
    print("Memo grouped nodes: ", memo_grouped_nodes)

    max_cluster = set()
    for center_node in center_nodes:
        sorted_keys = sorted(list(memo_grouped_nodes[center_node].keys()))

        curr_max_cluster = max_clique(slice, shuffle_rounds, matrix, memo_clusters, memo_grouped_nodes[center_node], sorted_keys, memo_clusters[center_node])

        if is_curr_max(matrix, len(curr_max_cluster), len(max_cluster), curr_max_cluster, max_cluster):
            max_cluster = curr_max_cluster

    max_clique_keys = sorted(list(max_cluster), key=lambda idx : int(idx.split("-")[1]))
    clique = matrix.loc[max_clique_keys, max_clique_keys]
    print(clique)
    clique.to_csv('%s/results/indexed_transmission_matrices/max_clique_transmission_matrix_%s.csv' % (dir_path, deployment))
    clique.to_csv('%s/results/matlab_input/max_clique_transmission_matrix_%s.csv' % (dir_path, deployment), header=False, index=False)

if __name__ == "__main__":
    slice = 20
    shuffle_rounds = 1
    dir_path = os.path.dirname(os.path.realpath(__file__))

    power_pathlist = Path("%s/raw_data/" % dir_path).rglob("*.log")
    tranmission_energy_path = Path("%s/../transmission_energy/results/energy_results.csv" % dir_path)
    
    for power_path in power_pathlist:
        deployment = power_path.name.split('_')[0]
        
        parse(deployment, dir_path, power_path, tranmission_energy_path, slice, shuffle_rounds)
