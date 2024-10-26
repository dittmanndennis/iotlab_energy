from pathlib import Path
import pandas as pd
import os

def calculate_triangle_inequality_violations(grenoble_energy_matrix):
    tiv_counter = 0
    triangle_counter = 0
    for i in range(len(grenoble_energy_matrix)):
        for j in range(i, len(grenoble_energy_matrix)):
            for k in range(len(grenoble_energy_matrix)):
                if k == j or k == i:
                    continue
                if grenoble_energy_matrix[i][j] > grenoble_energy_matrix[i][k] + grenoble_energy_matrix[k][j]:
                    tiv_counter += 1
                triangle_counter += 1

    print("Number of TIVs", tiv_counter)
    print("Number of evaluated triangles: ", triangle_counter)
    print("Ratio of TIV to non-TIV: ", 100 * (tiv_counter / triangle_counter), "%")

if __name__ == "__main__":
    dir_path = os.path.dirname(os.path.realpath(__file__))

    asymmetric_grenoble_df = pd.read_csv("%s/../transmission_matrix/results/indexed_transmission_matrices/comparable_asymmetric_sqrd_transmission_matrix_grenoble.csv" % (dir_path), index_col=0)
    asymmetric_grenoble_energy_matrix = asymmetric_grenoble_df.values.tolist()

    symmetric_grenoble_df = pd.read_csv("%s/../transmission_matrix/results/indexed_transmission_matrices/comparable_symmetric_sqrd_transmission_matrix_grenoble.csv" % (dir_path), index_col=0)
    symmetric_grenoble_energy_matrix = asymmetric_grenoble_df.values.tolist()

    grenoble_latency_df = pd.read_csv("%s/../transmission_matrix/results/indexed_transmission_matrices/comparable_all_calc_0_grenoble.csv" % (dir_path), index_col=0)
    grenoble_latency_matrix = grenoble_latency_df.values.tolist()

    print("Grenoble asymmetric transmission energy TIV analysis:")
    calculate_triangle_inequality_violations(asymmetric_grenoble_energy_matrix)
    print("Grenoble symmetric transmission energy TIV analysis:")
    calculate_triangle_inequality_violations(symmetric_grenoble_energy_matrix)
    print("Grenoble latency TIV analysis:")
    calculate_triangle_inequality_violations(grenoble_latency_matrix)
