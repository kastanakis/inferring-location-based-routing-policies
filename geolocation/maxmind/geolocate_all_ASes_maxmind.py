import csv
import sys
import bz2
import json
import requests
import concurrent.futures
from requests.exceptions import ConnectionError, JSONDecodeError

# Prints a progress bar
def print_progress_bar(progress, total, width=25):
    percent = width * ((progress + 1) / total)
    bar = chr(9608) * int(percent) + "-" * (width - int(percent))
    print(f"\rCompletion progress: |{bar}| {(100/width)*percent:.2f}%", end="\r")

# Writes contents to a json file
def write_json(jsonfilename, content):
    with open(jsonfilename, 'w+') as fp:
        json.dump(content, fp, indent=4)

# Reads the AS topology dataset in a dictionary 
def read_topology(as2rel_mapping):
    as2rel_dict = dict()
    with bz2.BZ2File(as2rel_mapping, 'rb') as compressed_file:
        decompressed_data = compressed_file.read().decode('utf-8').splitlines()
        csvreader = csv.reader(decompressed_data, delimiter='|')
        for row in csvreader:
            if row[0][0] != '#':  # ignore lines starting with "#"
                as1 = row[0]
                as2 = row[1]
                rel = int(row[2])
                if as1 not in as2rel_dict:
                    as2rel_dict[as1] = list()
                as2rel_dict[as1].append([as2, rel])
                if as2 not in as2rel_dict:
                    as2rel_dict[as2] = list()
                as2rel_dict[as2].append([as1, -rel])
    return as2rel_dict

def geolocate_AS_maxmind(AS):
    coverage_per_country = dict()
    coverage_per_country['ipv4'] = dict()
    coverage_per_country['ipv6'] = dict()
    
    URL = "https://stat-ui.stat.ripe.net/data/maxmind-geo-lite-announced-by-as/data.json"
    PARAMS = {'resource':AS}
    try:
        req = requests.get(url=URL, params=PARAMS)
        res = req.json()['data']['located_resources']
        for item in res:
            prefix = item['resource']
            if ':' in prefix:
                version = 'ipv6'
            else:
                version = 'ipv4'
            for location in item['locations']:
                country_iso = location['country']
                coverage = location['covered_percentage']
                if country_iso in coverage_per_country[version]:
                    coverage_per_country[version][country_iso] += coverage
                else:
                    coverage_per_country[version][country_iso] = coverage
    except Exception as e:
        print(f"An exception occurred: {e}")

    return coverage_per_country

def process_asn(asn):
    return asn, geolocate_AS_maxmind(asn)

# Adjust the number of threads based on your system and requirements
num_threads = 8
coverage_per_as = dict()
all_ases = read_topology('../../as_graph/20231101.as-rel2.txt.bz2').keys()
with concurrent.futures.ThreadPoolExecutor(max_workers=num_threads) as executor:
    # Use executor.map to process ASNs concurrently
    results = executor.map(process_asn, all_ases)
    for i, (asn, coverage) in enumerate(results):
        coverage_per_as[asn] = coverage
        print_progress_bar(i, len(all_ases))

write_json('output/presence_per_AS_maxmind.json', coverage_per_as)