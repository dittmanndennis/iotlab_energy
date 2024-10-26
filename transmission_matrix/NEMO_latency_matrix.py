from pathlib import Path
import pandas as pd
import os

def parse(dir_path: Path, energy_matrix_path: Path, deployment: str):
    path_FIT_latency = "%s/results/latency/all_calc_0.csv" % dir_path
    latency_matrix = pd.read_csv(path_FIT_latency)

    labels = []
    columns = []
    rows = []
    for idx, col in enumerate(latency_matrix.columns.values):
        if col.split('-')[0] == ("%s_m3" % deployment):
            labels.append(col.split('_')[-1])
            columns.append(col)
            rows.append(idx)
    print(labels)
    print("loc:\n",latency_matrix.loc[rows, columns])

    energy_matrix = pd.read_csv(energy_matrix_path, index_col=0)
    labels = list(set(labels).intersection(set(energy_matrix.columns.values)))
    labels = sorted(labels, key=lambda x: int(x.split('-')[-1]))
    energy_matrix = energy_matrix.loc[labels, labels]
    print("Comparable Grenoble: ", energy_matrix)

    energy_matrix.to_csv('%s/results/matlab_input/comparable_%s' % (dir_path, energy_matrix_path.name), header=False, index=False)
    energy_matrix.to_csv('%s/results/indexed_transmission_matrices/comparable_%s' % (dir_path, energy_matrix_path.name))

    updated_columns = []
    updated_rows = []
    label_idx = 0
    for idx, col in enumerate(columns):
        if col.split('_')[-1] == labels[label_idx]:
            updated_columns.append(col)
            updated_rows.append(rows[idx])
            label_idx += 1
    
    latency_matrix = latency_matrix.loc[updated_rows, updated_columns]
    latency_matrix.to_csv('%s/results/matlab_input/comparable_all_calc_0_%s.csv' % (dir_path, deployment), header=False, index=False)
    latency_matrix = latency_matrix.set_index(latency_matrix.columns)
    latency_matrix.to_csv('%s/results/indexed_transmission_matrices/comparable_all_calc_0_%s.csv' % (dir_path, deployment))

if __name__ == "__main__":
    dir_path = os.path.dirname(os.path.realpath(__file__))

    is_symmetric = False
    symmetric_path = "symmetric_*.csv" if is_symmetric else "asymmetric_*.csv"

    matrix_pathlist = Path("%s/results/indexed_transmission_matrices/" % (dir_path)).rglob(symmetric_path)
    
    for matrix_path in matrix_pathlist:
        parse(dir_path, matrix_path, matrix_path.stem.split('_')[-1])
