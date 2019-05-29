#!/usr/bin/python3
import math
import subprocess
import datetime
import psutil
import pandas as pd
import matplotlib.pyplot as plt
import seaborn as sns

# -----------------------------------------------------------------------------
# Script to generate plots regarding various system/network metrics as function
# of time. Designed to be used as cron/Windows scheduler job
# -----------------------------------------------------------------------------
COLUMNS = ['Download speed', 'Upload speed', 'Packages out',
           'Packages in', 'Errors in', 'Errors out', 'Drop in',
           'Drop out', 'CPU perc use', 'Average load',
           'Free memory (bytes)', 'Percent free memory', 'Datetime']


def get_speed_metrics():
    '''
    Run speedest-cli bash command, parse results to get metrics about
    connection

    Returns
    -------
    dict:
            dict containing distance from tower (km), time to ping tower (ms),
            download speed (Mbit/s), and upload speed (Mbit/s)
    '''
    cmd = 'speedtest-cli > speedtest.txt'
    process = subprocess.run(cmd, shell=True)

    metrics = []
    unit_scale_factors = []
    with open('speedtest.txt', 'r') as f:
        for line in f:
            for word in line.split():
                try:
                    if word[-1].isdigit():
                        metrics.append(word)
                    # parse out units of download & upload
                    elif word[-2] == '/':
                        if word[-6] == 'M':
                            unit_scale_factors.append(1)
                        if word[-6] == 'G':
                            unit_scale_factors.append(1000)
                except IndexError:
                    pass

    # distance parses as [3.14159
    metrics[0] = metrics[0][1:]
    # scale speeds to Mbit/s
    metrics[2] = metrics[2]*unit_scale_factors[0]
    metrics[3] = metrics[3]*unit_scale_factors[1]

    return dict(zip(('distance', 'time', 'download', 'upload'), metrics))
# -----------------------------------------------------------------------------


def get_network_metrics():
    '''
    Use psutil to return network metrics

    Returns
    -------
    dict:
            containing N bytes out/in, N packages out/in, N errors out/in,
            & N dropped packets
    '''
    metrics = tuple(psutil.net_io_counters())
    return dict(zip(('byte_out', 'byte_in', 'pack_out', 'pack_in', 'err_in',
                     'err_out', 'drop_in', 'drop_out'), metrics))
# -----------------------------------------------------------------------------


def get_system_metrics():
    '''
    Use psutil to get metrics about home system

    Returns
    -------
    dict:
            containing cpu % use, average load over past minute,
            amount free memory (bytes), and percent memory used

    cpu % use reflects % of cpu utilization over interval of past minute
    average load reflects N processes waiting to be run by OS
    '''
    cpu_perc = psutil.cpu_percent(interval=1)
    avg_load = psutil.getloadavg()[0]  # only want sysload for last minute
    amt_free_memory = psutil.virtual_memory()[1]
    memory_perc = round(psutil.virtual_memory()[2]/100, 3)
    return dict(zip(('cpu_perc', 'avg_load', 'free_memory', 'perc_memory'),
                    (cpu_perc, avg_load, amt_free_memory, memory_perc)))
# -----------------------------------------------------------------------------


def update_df():
    '''
    loads metrics.csv as df, populates with most recent metrics
    '''
    df = pd.read_csv('metrics.csv', encoding='utf-8')

    # unflattened list of tuples from various data streams
    metrics = [list(get_speed_metrics().values())[-2:],
               list(get_network_metrics().values())[-6:],
               list(get_system_metrics().values())]
    # flatten list of tuples, append current datetime
    metrics = [float(item) for metric in metrics for item in metric]
    metrics.append(datetime.datetime.now())

    metrics = pd.DataFrame([metrics], columns=COLUMNS)
    df = df.append(metrics, ignore_index=True, sort=True)
    df = df.set_index('Datetime', inplace=False)
    df.to_csv('metrics.csv', sep=',', index=True, header=True)
# -----------------------------------------------------------------------------


def generate_plots():
    '''
    generates plots for all metrics vs datetime

    #(TODO): figure out how to set x-axis to be more user friendly
    '''
    df = pd.read_csv('metrics.csv', encoding='utf-8')
    df['Datetime'] = pd.to_datetime(df['Datetime']).dt.strftime('%H:%M')

    # plot all metrics as function of datetime
    fig, axs = plt.subplots(nrows=4, ncols=3)
    for col in enumerate(COLUMNS[:-1]):
        sns.lineplot(x=df['Datetime'], y=df[col[1]], data=df,
                     ax=axs[col[0] % 4][math.floor(col[0]/4)])
    plt.show()
