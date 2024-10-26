from pathlib import Path
import pandas as pd
import os

def parse(dir_path: Path, deployment: str, coords_path: Path) -> None:
    symmetric_path = "comparable_symmetric_sqrd_transmission_matrix" if "symmetric" == coords_path.name.split('_')[0] else ""
    asymmetric_path = "comparable_asymmetric_sqrd_transmission_matrix" if "asymmetric" == coords_path.name.split('_')[0] else ""
    latency_path = "comparable_all_calc_0" if "latency" == coords_path.name.split('_')[0] else ""
    max_clique_path = "max_clique_transmission_matrix" if "max" == coords_path.name.split('_')[0] else ""
    indexed_transmission_matrix = pd.read_csv('%s/results/indexed_transmission_matrices/%s%s%s%s_%s' % (dir_path, symmetric_path, asymmetric_path, latency_path, max_clique_path, deployment),
                                 usecols=['Unnamed: 0'],
                                 index_col=0)
    indexed_matlab_output = pd.read_csv('%s/results/matlab_output/%s' % (dir_path, coords_path.name),
                                        header=None,
                                        names=['x', 'y']).set_index(indexed_transmission_matrix.index)
    
    indexed_matlab_output.to_csv('%s/results/indexed_coordinate_systems/%s__indexed.csv' % (dir_path, coords_path.stem))

if __name__ == "__main__":
    dir_path = os.path.dirname(os.path.realpath(__file__))
    
    coords_pathlist = Path("%s/results/matlab_output/" % (dir_path)).rglob("*.csv")
    for coords_path in coords_pathlist:
        deployment = coords_path.name.split('_')[-1]

        parse(dir_path, deployment, coords_path)
