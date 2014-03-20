import pandas as pd
import numpy as np

def infer_time_series_freq(values):
    med = np.median(np.diff(values))
    seconds = int(med.astype('timedelta64[s]').item().total_seconds())

    if seconds < 60:
        return '{}s'.format(seconds)

    if seconds < 3600:
        return freq = '{}T'.format(int(seconds / 60))

    if seconds < 86400:
        return freq = '{}H'.format(int(seconds / 3600))

    if seconds < 604800:
        return freq = '{}D'.format(int(seconds / 86400))

    if seconds < 2678400:
        return freq = '{}W'.format(int(seconds / 604800))

    if seconds < 7948800:
        return freq = '{}M'.format(int(seconds / 2678400))
    
    return '{}Q'.format(int(seconds / 7948800))
