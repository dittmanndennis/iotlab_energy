from collections import defaultdict
import matplotlib.pyplot as plt
from random import shuffle
from pathlib import Path
import pandas as pd
import numpy as np
import time
import math
import re
import os


'''
Here we analyze the WSN matrices for asymmetries.
'''

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
    
    all_asymmetries = []
    differences = []
    for key in results.keys():
        sending_node = key.split("', '")[0][2:]
        receiving_node = key.split("', '")[1][:-2]
        if 0 < results[key] <= 16 and sending_node in intersection and receiving_node in intersection:
            matrix.loc[sending_node, receiving_node] = results[key]
            if matrix.loc[receiving_node, sending_node] > 0 and not\
               (matrix.loc[sending_node, receiving_node] == matrix.loc[receiving_node, sending_node]):
                all_asymmetries.append((key, abs(matrix.loc[sending_node, receiving_node] - matrix.loc[receiving_node, sending_node]), matrix.loc[sending_node, receiving_node], matrix.loc[receiving_node, sending_node]))
                if not (matrix.loc[sending_node, receiving_node]+1 == matrix.loc[receiving_node, sending_node] or\
                   matrix.loc[sending_node, receiving_node]-1 == matrix.loc[receiving_node, sending_node]):
                    differences.append((key, abs(matrix.loc[sending_node, receiving_node] - matrix.loc[receiving_node, sending_node]), matrix.loc[sending_node, receiving_node], matrix.loc[receiving_node, sending_node]))
        else:
            results[key] = 'NA'

    print("Number of severe asymmetries: ", len(differences))
    print("Number of existing connections: ", len(results.keys()))
    print("Number of all asymmetries: ", len(all_asymmetries))

if __name__ == "__main__":
    slice = 20
    dir_path = os.path.dirname(os.path.realpath(__file__))

    power_pathlist = Path("%s/raw_data/" % dir_path).rglob("*.log")
    tranmission_energy_path = Path("%s/../transmission_energy/results/energy_results.csv" % dir_path)
    
    for power_path in power_pathlist:
        deployment = power_path.name.split('_')[0]
        
        parse(deployment, dir_path, power_path, tranmission_energy_path, slice)
