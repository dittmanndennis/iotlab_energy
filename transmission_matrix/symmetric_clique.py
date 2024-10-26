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

def parse(dir_path, path):
    df = pd.read_csv(path, index_col=0)

    for i in range(df.shape[0]):
        for j in range(i+1, df.shape[1]):
            max_val = max(df.iloc[i,j], df.iloc[j,i])
            df.iloc[i,j] = max_val
            df.iloc[j,i] = max_val

    df.to_csv('%s/results/symmetric/indexed_transmission_matrices/%s.csv' % (dir_path, path.name))
    df.to_csv('%s/results/symmetric/matlab_input/%s.csv' % (dir_path, path.name), header=False, index=False)

if __name__ == "__main__":
    dir_path = os.path.dirname(os.path.realpath(__file__))

    pathlist = Path("%s/results/indexed_transmission_matrices/" % (dir_path)).rglob("max_clique_transmission_matrix_*.csv")
    for path in pathlist:

        print(re.search(r"max_clique_transmission_matrix_([a-z]*)\.csv", str(path.name)).group(1))
        
        parse(dir_path, path)
