#!/usr/bin/env python3

import pandas as pd
import numpy as np
import argparse

parser = argparse.ArgumentParser()
parser.add_argument('file',nargs='+')
args = parser.parse_args()

for filename in args.file:
  print(filename)

  df = pd.read_csv(filename,
          skiprows=9,
          sep='\t',
          header=None,
          usecols=[3,4,5,6,7],
          names=['time_s','time_us','power','voltage','current'])

  df['time'] = df['time_s']+df['time_us']/1000000
  df['difftime'] = df['time'] - df['time'].shift(1)
  df = df.iloc[1:]

  df['energy'] = df['difftime']*df['power']

  duration = df.iloc[-1]['time'] - df.iloc[0]['time']
  print("Total duration: %.0f s"%duration)
  print("Average voltage: %.2f V"%df['voltage'].mean())
  print("Average current: %i mA"%round(df['current'].mean()*1000))
  print("Average power: %i mW"%round(df['power'].mean()*1000))
  print("Total energy consumption: %i Ws"%df['energy'].sum())
