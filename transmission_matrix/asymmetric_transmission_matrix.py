from collections import defaultdict, deque
from pathlib import Path
import pandas as pd
import numpy as np
import json
import re
import os
import itertools

def parse(deployment: str, dir_path: Path, power_path: Path, tranmission_energy_path: Path):
    power_level = {13: 0, 18: 1, 20: 2, 23: 3, 25: 4, 26: 5, 27: 6, 28: 7, 29: 8,
                   30: 9, 31: 10, 33: 11, 34: 12, 36: 13, 37: 14, 38: 15}
    
    results = defaultdict(lambda: [0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0])

    sent = set()
    received = set()

    with open(power_path) as transmission_log:
        for line in transmission_log:
            try:
                m = re.search(r".*?(?=m3[-_][0-9]+)(m3[-_][0-9]+).*?(?=m3[-_][0-9]+)(m3[-_][0-9]+).*?(?='[0-9]+)'([0-9]+) - 120 char payload packet - 12345678901234567890123456789012345678901234567890123456789012345678901234567890123456789.*", line)
                assert(m)

                # From M3-XXX to M3-XXX
                key = "('%s', '%s')" % (m.group(2), m.group(1))
                sent.add(m.group(2))
                received.add(m.group(1))
                
                results[key][power_level[int(m.group(3))]] += 1
            except:
                print("Could not parse line: ", line)

    # Filter broken nodes
    print("Unconnected/broken nodes: ", sent.symmetric_difference(received), "\n")
    intersection = sent.intersection(received)
    axis_nodes = list(intersection)
    axis_nodes.sort(key=lambda n: int(re.search(r"m3[-_]([0-9]+)", n).group(1)))
    matrix = pd.DataFrame(data=np.zeros((len(axis_nodes),len(axis_nodes))), index=axis_nodes, columns=axis_nodes)
    
    df = pd.read_csv(tranmission_energy_path, usecols=['median__mW_mean'])

    counter_flaky_connection = 0
    counter_all_asymmetries = 0
    counter_severe_asymmetries = 0
    for key in results.keys():
        sending_node = key.split("', '")[0][2:]
        receiving_node = key.split("', '")[1][:-2]
        idx_power_level = 0
        max_count_power_level = 0
        for i in range(len(power_level.keys())):
            if results[key][i] > max_count_power_level:
                max_count_power_level = results[key][i]
                idx_power_level = i + 1
                if results[key][i] == 30:
                    break
        if 0 < idx_power_level <= 16 and sending_node in intersection and receiving_node in intersection:
            max_energy = max(matrix.loc[receiving_node, sending_node], df['median__mW_mean'].iloc[16 - idx_power_level])
            if matrix.loc[receiving_node, sending_node] > 0 and matrix.loc[receiving_node, sending_node] != df['median__mW_mean'].iloc[16 - idx_power_level]:
                counter_all_asymmetries += 1
                if matrix.loc[receiving_node, sending_node] != df['median__mW_mean'].iloc[max(0, 15 - idx_power_level)] and\
                   matrix.loc[receiving_node, sending_node] != df['median__mW_mean'].iloc[min(15, 17 - idx_power_level)]:
                    counter_severe_asymmetries += 1
            matrix.loc[receiving_node, sending_node] = max_energy
            matrix.loc[sending_node, receiving_node] = max_energy
            
            if max_count_power_level < 30:
                counter_flaky_connection += 1
    
    print("Number of flaky connections: ", counter_flaky_connection)
    print("Number of all asymmetries: ", counter_all_asymmetries)
    print("Number of severe asymmetries: ", counter_severe_asymmetries)
    print("Number of existing connections: ", len(results.keys()))
    
    unconnected_nodes = deque()
    for idx, row in matrix.iterrows():
        for node in axis_nodes:
            if row[node] == 0.0 and idx != node:
                unconnected_nodes.append((idx, node))
                
    hops = 0
    while unconnected_nodes:
        hops += 1
        print("Hops: ", hops, " Number of missing connections: ", len(unconnected_nodes), "\n")
        next_unconnected_nodes = deque()
        next_matrix = matrix.copy()
        for node in unconnected_nodes:
            row = matrix.loc[[node[0]]]
            column = matrix.loc[node[1]]

            reachable_nodes = np.where(row > 0.0)
            forwarding_nodes = np.where(column > 0.0)

            intermediary_nodes = np.intersect1d(reachable_nodes, forwarding_nodes)
            if len(intermediary_nodes) == 0:
                next_unconnected_nodes.append(node)
            else:
                next_matrix.at[node[0], node[1]] = min([(np.sqrt(row.iloc[0,i]) + np.sqrt(column.iloc[i]))**2 for i in intermediary_nodes])

        matrix = next_matrix
        unconnected_nodes = next_unconnected_nodes

    # Add the RX energy consumption
    states_df = pd.read_csv(Path("%s/../transmission_energy/results/energy_states_results.csv" % dir_path), usecols=['power_median', 'casetxt']).set_index('casetxt')
    add_rx_energy = np.full(matrix.values.shape, (states_df.loc['RX_ON'] - states_df.loc['SLEEP']))
    np.fill_diagonal(add_rx_energy, 0.0)
    numeric_data = matrix.values.copy()
    numeric_data += add_rx_energy
    matrix.iloc[:] = numeric_data

    matrix.to_csv('%s/results/indexed_transmission_matrices/asymmetric_sqrd_transmission_matrix_%s.csv' % (dir_path, deployment))
    
if __name__ == "__main__":
    dir_path = os.path.dirname(os.path.realpath(__file__))

    power_pathlist = Path("%s/raw_data/" % dir_path).rglob("*.log")
    tranmission_energy_path = Path("%s/../transmission_energy/results/energy_results.csv" % dir_path)
    
    for power_path in power_pathlist:
        deployment = power_path.name.split('_')[0]
        #matrix = create_transmission_matrix(deployment, dir_path)
        
        parse(deployment, dir_path, power_path, tranmission_energy_path)
