import json
import random
from pprint import pprint as pprint

# Reads content of json file and returns
def read_json(jsonfilename):
    with open(jsonfilename, 'r') as jsonfile:
        return json.load(jsonfile)

# Writes content to a json file
def write_json(jsonfilename, content):
    with open(jsonfilename, 'w+') as fp:
        json.dump(content, fp, indent=4)

def select_topN_anycast_ases(asns, N=100):
    asrank = read_json("../as_graph/as_rank/as2rank.json")
    sorted_asns = sorted(asns, key=lambda asn: asrank.get(asn, float('inf')))
    return sorted_asns[:N]

# Prints a progress bar
def print_progress_bar(progress, total, width=25):
    percent = width * ((progress + 1) / total)
    bar = chr(9608) * int(percent) + "-" * (width - int(percent))
    print(f"\rCompletion progress: |{bar}| {(100/width)*percent:.2f}%", end="\r")

all_anycasters = read_json("../anycast_prefixes/output/anycast_asn_to_prefix.json").keys()
selective_announced_anycast_prefixes = [ip for sublist in read_json("../selective_announcements/output/selective_announced_anycast_prefixes_per_as.json").values() for ip in sublist]
print(selective_announced_anycast_prefixes)
filenames = list()
for asn in select_topN_anycast_ases(all_anycasters):
    filename = '../routing_tables/output/' + asn + '_routing_presence_origin_bgpstream.json'
    filenames.append(filename)

# Initialize an empty dictionary to hold the merged data
merged_data = {}
merged_data_selective_announced_prefixes = {}

# Iterate over each file
for idx, file_name in enumerate(filenames):
    print_progress_bar(idx,len(filenames))
    with open(file_name, 'r') as file:
        data = json.load(file)
        # Merge the data from the current file into the merged_data dictionary
        for ip_address, nested_data in data.items():
            if ip_address not in merged_data:
                rand_sam = random.sample(nested_data.keys(), 1)[0]
                entry = {rand_sam: nested_data[rand_sam]}
                merged_data[ip_address] = entry
                if ip_address in selective_announced_anycast_prefixes:
                    merged_data_selective_announced_prefixes[ip_address] = entry
write_json("output/merged_routing_tables/all_observed_anycast_prefixes_and_one_random_as_path_per_prefix.json", merged_data)
write_json("output/merged_routing_tables/all_observed_anycast_prefixes_and_one_random_as_path_per_prefix_selective_announcements_only.json", merged_data_selective_announced_prefixes)