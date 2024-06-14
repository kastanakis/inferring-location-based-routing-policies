import os
import csv
import sys
import json
from itertools import groupby
from operator import itemgetter
from pprint import pprint as pprint

# Writes content to a json file
def write_json(jsonfilename, content):
    with open(jsonfilename, 'w+') as fp:
        json.dump(content, fp, indent=4)

# Removes consecutive duplicates in a sequence
def remove_prepending(seq):
    # https://stackoverflow.com/questions/5738901/removing-elements-that-have-consecutive-duplicates
    return list(map(itemgetter(0), groupby(seq)))

# Finds all csv files in a dir
def find_csv_files(directory):
    csv_files = [f for f in os.listdir(directory) if f.endswith('.csv')]
    return csv_files

# Reads routing table and collects prefix, as path and communities.
def preprocess_routing_table(routing_table):
    to_return = dict()
    with open(routing_table, 'r') as input_csv_file:
        csv_reader = csv.reader(input_csv_file, delimiter='|')
        for route in csv_reader:
            collector = route[4]
            peer_ip = route[8]
            prefix = route[9]
            as_path = route[11].split(" ")
            communities = route[12]
            as_path_without_prepending = " ".join(remove_prepending(as_path))
            if prefix not in to_return: to_return[prefix] = dict()
            if as_path_without_prepending not in to_return[prefix]: to_return[prefix][as_path_without_prepending] = list()
            data = {"communities": communities, "collector": collector, "vp_ip": peer_ip}
            if data not in to_return[prefix][as_path_without_prepending]:
                to_return[prefix][as_path_without_prepending].append(data)
    return to_return

bgp_streams_per_origin = "input/bgp_streams_per_origin/"
all_csv_files = find_csv_files(bgp_streams_per_origin)
for idx, file in enumerate(all_csv_files):
    file_loc = bgp_streams_per_origin + file
    network = file.split("_")[1].split("_")[0]
    print('Completion percentage {}\r'.format(idx/len(all_csv_files)), end='')
    raw_routing_table = preprocess_routing_table(file_loc)
    write_json("output/" + network + "_routing_presence_origin_bgpstream.json", raw_routing_table)