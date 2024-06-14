import json
import csv
from pprint import pprint as pprint 
import os
import geoip2.database
from collections import defaultdict

# Finds all json files in a dir
def find_json_files(directory):
    json_files = [f for f in os.listdir(directory) if f.endswith('.json')]
    return json_files

# Reads content from a json file
def read_json(jsonfilename):
    with open(jsonfilename, 'r') as jsonfile:
        return json.load(jsonfile)

# Writes content to a json file
def write_json(jsonfilename, content):
    with open(jsonfilename, 'w+') as fp:
        json.dump(content, fp, indent=4)

# Reads content from the route collectors csv file
def read_csv(data):
    result = dict()
    with open(data, 'r') as file:
        csv_reader = csv.reader(file, skipinitialspace=True, delimiter=",")
        # Skip first line
        next(csv_reader, None)
        for line in csv_reader:
            result[line[0]] = {"country":line[1], "multihop":line[2]}
    return result

# Geolocates an ip and returns the respective country
def geolocate_ip(ip):
    with geoip2.database.Reader('../geolocation/maxmind/input/GeoLite2-Country_20231103/GeoLite2-Country.mmdb') as country_reader:
        response_country = country_reader.country(ip)
        return response_country.country.iso_code

# Prints a progress bar
def print_progress_bar(progress, total, width=25):
    percent = width * ((progress + 1) / total)
    bar = chr(9608) * int(percent) + "-" * (width - int(percent))
    print(f"\rCompletion progress: |{bar}| {(100/width)*percent:.2f}%", end="\r")

# Extracts for each anycast prefix of an anycast origin all the neighbors of the origin AS grouped per vantage point region.
# I.e., which neighbors are right before the origin AS in the AS path when the vantage point is in a specific region.
def extract_neighbors_per_vantage_point_region(anycast_routing_presence, all_collectors, iso2region):
    neighbors_per_region = dict()
    bgp_paths = anycast_routing_presence.keys()
    for path in bgp_paths:
        if len(path.split()) >= 2:
            neighbor = path.split()[-2]
            for as_path_info in anycast_routing_presence[path]:
                collector_name = as_path_info['collector']
                collector_ip = as_path_info['vp_ip']
                multihop = all_collectors[collector_name]['multihop']
                country = all_collectors[collector_name]['country']
                # If the collector is multihop router then geolocate its IP with MaxMindDB
                if multihop == 'multihop':
                    country = geolocate_ip(collector_ip)
                # We reduce the country of the collector to the respective region
                region = iso2region[country]   
                if region not in neighbors_per_region:
                    neighbors_per_region[region] = dict()
                if country not in neighbors_per_region[region]:
                    neighbors_per_region[region][country] = list()
                if neighbor not in neighbors_per_region[region][country]:
                    neighbors_per_region[region][country].append(neighbor)
    return dict(neighbors_per_region)        

# Get all collectors geoinfo
riperis = read_csv("../geolocation/route_collectors/riperis.csv")
routeviews = read_csv("../geolocation/route_collectors/routeviews.csv")
all_collectors = dict()
all_collectors.update(riperis)
all_collectors.update(routeviews)

# Get the UN dataset with regions and countries
iso2region = read_json("../geolocation/united_nations/output/region_per_country.json")

# Get all anycast asns for which we have routing tables
anycast_asns = list()
for file in find_json_files("../routing_tables/output/"):
    asn = file.split("_")[0]
    anycast_asns.append(asn)

# Parse all routing tables and extract src AS, origin AS and penultimate AS. Then geolocate them and log them.
anycast_catchment_per_anycast_as_dict = dict()
for idx, anycast_asn in enumerate(anycast_asns):  
    print_progress_bar(idx, len(anycast_asns))
    # Read anycast asn to prefix map
    anycast_prefixes = read_json("../anycast_prefixes/output/anycast_asn_to_prefix.json")[anycast_asn]
    # Read routing tables where the given AS appears as origin AS
    routing_presence = read_json("../routing_tables/output/" + anycast_asn + "_routing_presence_origin_bgpstream.json")

    # Collect all routing information that correspond to the anycast prefixes of the aforementioned origin AS
    anycast_routing_presence = {prefix: routing_presence[prefix] for prefix in anycast_prefixes if prefix in routing_presence}
    if not anycast_routing_presence:
        print("No anycast presence in the routing tables...")
        continue
    
    # Collect all neighbors that received an announcement by the given asn for an anycast prefix
    prefix_level_catchment = dict()
    for i, prefix in enumerate(anycast_routing_presence):
        # Get all neighbors (next-hops) that received an announcement from Cloudflare towards an anycast prefix.
        prefix_level_catchment[prefix] = extract_neighbors_per_vantage_point_region(anycast_routing_presence[prefix], all_collectors, iso2region)
    anycast_catchment_per_anycast_as_dict[anycast_asn] = prefix_level_catchment

write_json("output/as_level_anycast_catchment_per_region.json", anycast_catchment_per_anycast_as_dict)