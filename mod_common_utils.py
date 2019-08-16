import numpy as np
import json_tricks
import os


def list_cache(folder):

    valid = []
    for item in os.listdir(folder):
        compress_name, compress_ext = os.path.splitext(item)
        json_name, json_ext = os.path.splitext(compress_name)
    
        if json_ext+compress_ext=='.json.gz':
            valid += [json_name]
            
    return valid


def to_cache(name, folder, data):
    path = os.path.join(folder, name+'.json.gz')
    with open(path, 'wb') as f:
        json_tricks.dump(data, f, compression=9)

        print('Saved data to',  path)


def from_cache(name, folder):
    path = os.path.join(folder, name+'.json.gz')
    with open(path, 'rb') as f:
        data = json_tricks.load(f, decompression=True)
        
        return data


def stats_eval(my_stats, fn=np.mean, selected=None):

    my_stats_fn = { }
    for key in my_stats:
        my_stats_fn[key] = { }

        for metric in my_stats[key]:
            if selected is not None and metric not in selected:
                continue
            my_stats_fn[key][metric] = fn(my_stats[key][metric],axis=0)

    return my_stats_fn