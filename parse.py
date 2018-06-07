#!/usr/bin/env python3

import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import argparse
import re
import collections

SYNC_SEQUENCE = 22
CASES = 32
CASE_DURATION = 5 # seconds

def casetxt(x):
  if x == 12:
    return "Idle"
  elif x == 9:
    return "Green LED"
  elif x == 10:
    return "Yellow LED"
  elif x == 11:
    return "Red LED"
  elif x == 14:
    return "TRX_OFF"
  elif x == 15:
    return "PLL_ON"
  elif x == 16:
    return "RX_ON"
  elif 17 <= x <= 17+0xF:
    power = x - 17;
    return "TX TX_PWR %i"%power
  else:
    return "unknown"

def parse(filename,plot):
  df = pd.read_csv(filename,
          skiprows=9,
#          nrows=10000,
          sep='\t',
          header=None,
          usecols=[3,4,5,6,7],
          names=['time_s','time_us','power','voltage','current'])

  df = df[df['power'] > 0]
  df = df[df['power'] < 1000]
  df = df[df['current'] > 0]
  df = df[df['current'] < 1000]
  df = df[df['voltage'] > 0]
  df = df[df['voltage'] < 1000]

  df['time'] = df['time_s']+df['time_us']/1000000

  interval = np.mean(np.diff(df['time'].head(20)))
  case_rows = CASE_DURATION/interval
  minpower = np.min(df['power'])
  maxpower = np.max(df['power'])

  # Generate synchronization list
  sync_sequence = SYNC_SEQUENCE
  sync = []
  for i in range(0,8):
    sync.append((sync_sequence & 0x80) >> 7)
    sync_sequence <<= 1 
  sync = np.repeat(sync,case_rows)

  # Correlate with first two repetitions to get start
  head = df['power'].head(int(2*CASES*case_rows))
  head = [(x - minpower)/(maxpower-minpower) for x in head] # normalize
  correlation = np.correlate(head,sync)
  start = np.argmax(correlation)

  # Remove rows before start
  df = df.iloc[start:].reset_index()

  # Generate case indicies
  df['case'] = df.apply(lambda row: (int(row.name/case_rows)%CASES)+1, axis=1)
  df['case_part'] = df.apply(lambda row: int(row.name/(case_rows/3))%3, axis=1)

  if plot:
      # Plot the power and the synchronization sequence
      plt.plot(df['power'])
      plt.plot(sync)
      plt.show()

  # Group by case (only middle segment)
  cases = df[df['case_part'] == 1].groupby(['case'])
  def agg_current(x):
    d = collections.OrderedDict()
    d['current_mean'] = np.mean(x['current'])*1000
    d['power_mean'] = np.mean(x['power'])*1000
    return pd.Series(d)
  means = cases.apply(agg_current)

  m = re.search("m3[-_]([0-9]*)\.oml",filename)
  assert(m)
  means['node'] = int(m.group(1))
  means['casetxt'] = means.apply(lambda x: casetxt(x.name),axis=1)
  means = means[means['casetxt'] != 'unknown']
  return means

def print_node_result(df):
    idle_power = np.min(df['power_mean'])
    idle_current = np.min(df['current_mean'])

    print("Idle Power %i mW"%idle_power)
    print("Idle Current %i mA"%idle_current)

    def agg_all(x):
      d = collections.OrderedDict()
      d['casetxt'] = x['casetxt'].iloc[0]
      d['power_extra'] = "%i mW"%round(np.mean(x['power_mean'])-idle_power)
      d['current_extra'] = "%i mA"%round(np.mean(x['current_mean'])-idle_current)
      d['power_total'] = "%i mW"%round(np.mean(x['power_mean']))
      d['current_total'] = "%i mA"%round(np.mean(x['current_mean']))
      return pd.Series(d)
    df = df.groupby('case').apply(agg_all)
    print(df)

if __name__ == "__main__":
  parser = argparse.ArgumentParser()
  parser.add_argument('file',nargs='+')
  parser.add_argument('-noplot',action="store_true",default=False)
  args = parser.parse_args()
  pd.options.display.float_format = '{:,.2f}'.format

  first = True
  df = None
  for filename in args.file:
    result = parse(filename,plot=not args.noplot)
    print("Node %i"%result['node'].iloc[0])
    print_node_result(result)

    if first:
      df = result
      first = False
    else:
      df = pd.concat((df,result))

  df['case'] = df.index
  df = df.pivot(index='node',columns='case',values='power_mean')
  df = df.rename(columns=casetxt)
  df.to_csv('energy_results.csv')
