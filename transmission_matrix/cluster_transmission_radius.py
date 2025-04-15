from collections import deque
from pathlib import Path
import pandas as pd
import numpy as np
import math
import json
import re
import os

def closest_hex_center_coordinates(x_min: float, y_min: float, x_coord: float, y_coord: float, radius: float, width: float, height: float):
    apothem = math.sqrt(3) * radius / 2
    radius_apothem_margin = radius - apothem
    number_of_rows = math.ceil(height / (2 * apothem)) - 1 # counting from 0
    number_of_columns = math.ceil((width + radius_apothem_margin) / (2 * apothem + radius_apothem_margin)) # counting from 0
    
    row_lower = 0
    row_upper = number_of_rows
    lower = 0
    upper = number_of_rows
    while(lower < upper):
        curr = math.floor(lower + (upper - lower) / 2)

        row_coord = y_min + apothem + (2 * apothem) * curr
        
        if row_coord < y_coord:
            row_lower = curr
            lower = curr + 1
        elif row_coord > y_coord:
            row_upper = curr
            upper = curr - 1
        else:
            row_lower = curr
            row_upper = curr
            break

    points = [ (0, 0) ] * 4

    lower = 0
    upper = number_of_columns
    while(lower < upper):
        curr = math.floor(lower + (upper - lower) / 2)

        if row_lower % 2 == 0:
            column_coord = x_min + apothem + (2 * apothem) * curr
        else:
            column_coord = x_min - radius + (2 * apothem) * curr
        
        if column_coord < x_coord:
            points[0] = (curr, row_lower)
            lower = curr + 1
        elif column_coord > x_coord:
            points[1] = (curr, row_lower)
            upper = curr - 1
        else:
            points[0] = (curr, row_lower)
            points[1] = (curr, row_lower)
            break

    lower = 0
    upper = number_of_columns
    while(lower < upper):
        curr = math.floor(lower + (upper - lower) / 2)

        if row_upper % 2 == 0:
            column_coord = x_min + apothem + (2 * apothem) * curr
        else:
            column_coord = x_min - radius + (2 * apothem) * curr
        
        if column_coord < x_coord:
            points[2] = (curr, row_upper)
            lower = curr + 1
        elif column_coord > x_coord:
            points[3] = (curr, row_upper)
            upper = curr - 1
        else:
            points[2] = (curr, row_upper)
            points[3] = (curr, row_upper)
            break

    # Find closest point
    cluster = 0
    distance_closest_point = math.sqrt(width**2 + height**2)
    for i in range(len(points)):
        if points[i][1] % 2 == 0:
            x_point = x_min + apothem + (2 * apothem) * points[i][0]
        else:
            x_point = x_min - radius + (2 * apothem) * points[i][0]
        y_point = y_min + apothem + (2 * apothem) * points[i][1]
        distance = math.sqrt((x_coord - x_point)**2 + (y_coord - y_point)**2)
        if distance < distance_closest_point:
            cluster = points[i][0] + (number_of_columns + 1) * points[i][1]
            distance_closest_point = distance

    return cluster

def parse(deployment: str, dir_path: Path, coords_path: Path, tranmission_energy_path: Path):    
    df_energy = pd.read_csv(tranmission_energy_path, usecols=['median__mW_mean'])
    df_coords = pd.read_csv(coords_path, usecols=['Unnamed: 0', 'x', 'y'], index_col=0)
    
    x_min = df_coords['x'].min()
    y_min = df_coords['y'].min()
    width = df_coords['x'].max() - x_min
    height = df_coords['y'].max() - y_min

    for median__mW_mean in df_energy['median__mW_mean'].values:
        radius = median__mW_mean
        for index, row in df_coords.iterrows():
            cluster = closest_hex_center_coordinates(x_min=x_min, y_min=y_min, x_coord=row['x'], y_coord=row['y'],
                                                     radius=radius, width=width, height=height)
            print(cluster)
        break
    print("x_min: ", x_min, " y_min: ", y_min, " x_max: ", df_coords['x'].max(), " y_max: ", df_coords['y'].max())

if __name__ == "__main__":
    dir_path = os.path.dirname(os.path.realpath(__file__))

    coords_pathlist = Path("%s/results/indexed_coordinate_systems/" % dir_path).rglob("*.csv")
    tranmission_energy_path = Path("%s/../transmission_energy/results/energy_results.csv" % dir_path)
    
    for coords_path in coords_pathlist:
        deployment = coords_path.name.split('_')[0]
        
        parse(deployment, dir_path, coords_path, tranmission_energy_path)
