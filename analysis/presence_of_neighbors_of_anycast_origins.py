import bz2
import sys
import json
import csv
from pprint import pprint as pprint 

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

def extract_neighbors_and_vantage_points(anycast_routing_presence):
    neighbors_and_vantage_points = list()
    bgp_paths = anycast_routing_presence.keys()
    for path in bgp_paths:
        collectors = set()
        if len(path.split()) >= 2:
            vantage_point = path.split()[0]
            neighbor = path.split()[-2]
            for metainfo in anycast_routing_presence[path]:
                collectors.add(metainfo['collector'])
            neighbors_and_vantage_points.append({"vantage_point": vantage_point, "collectors": list(collectors), "neighbor": neighbor})
    return list(neighbors_and_vantage_points)        

def read_anycast_prefixes(url1, url2):
    # open the file in read mode
    with open(url1, 'r') as f1, open(url2, 'r') as f2:
        # read the contents of the file into a list of strings
        lines1 = f1.readlines()
        lines2 = f2.readlines()

    # strip any trailing newline characters from each line
    lines1 = [line.strip() for line in lines1]
    lines2 = [line.strip() for line in lines2]

    return lines1 + lines2

# Reads content from a json file
def read_json(jsonfilename):
    with open(jsonfilename, 'r') as jsonfile:
        return json.load(jsonfile)

# Writes content to a json file
def write_json(jsonfilename, content):
    with open(jsonfilename, 'w+') as fp:
        json.dump(content, fp, indent=4)


asn = sys.argv[1]
print(asn)
# Read anycast asn to prefix map
anycast_prefixes = read_json("../anycast_prefixes/output/anycast_asn_to_prefix.json")[asn]

# Read routing tables where the given AS appears as origin AS
routing_presence = read_json("../routing_tables/output/" + asn + "_routing_presence_origin_bgpstream.json")
all_prefixes_originated = routing_presence.keys()

# Collect all routing information that correspond to the anycast prefixes
anycast_routing_presence = {key: routing_presence[key] for key in anycast_prefixes}

# Collect all neighbors that received an announcement by the given asn for an anycast prefix
neighbors_and_vantage_points_per_prefix = dict()
for i, prefix in enumerate(anycast_routing_presence):
    # Get all neighbors (next-hops) that received an announcement from Cloudflare towards an anycast prefix.
    neighbors_and_vantage_points = extract_neighbors_and_vantage_points(anycast_routing_presence[prefix])
    neighbors_and_vantage_points_per_prefix[prefix] = neighbors_and_vantage_points

# Read coverage in Maxmind and presence in PeeringDB
coverage_maxmind = read_json("../geolocation/maxmind/output/coverage_for_" + asn + "_neighbors_ripestat.json")
presence_peering = read_json("../geolocation/peeringdb/output/presence_per_AS_peeringdb.json")

# For each prefix, log the presence per all neighbors who received the announcement directly from the given AS
all_neighbors_caida = read_topology('../as_graph/20231101.as-rel2.txt.bz2')[asn]
location_information_per_prefix = dict()
# for each anycast prefix announced by the given AS...
for prefix in neighbors_and_vantage_points_per_prefix:
    location_information_per_prefix[prefix] = list()
    for entry in neighbors_and_vantage_points_per_prefix[prefix]:
        # Extract the presence of the neighbor in Maxmind
        neighbor = entry['neighbor']
        vantage_point = entry['vantage_point']
        collectors = entry['collectors']
        if neighbor in coverage_maxmind:
            presence_ipv4 = coverage_maxmind[neighbor]['ipv4']
            if coverage_maxmind[neighbor]['ipv4']:
                max_key_ipv4 = max(presence_ipv4, key=lambda k: presence_ipv4[k])
                max_value_ipv4 = presence_ipv4[max_key_ipv4]
            else:
                max_key_ipv4 = None
                max_value_ipv4 = None
            presence_ipv6 = coverage_maxmind[neighbor]['ipv6']
            if coverage_maxmind[neighbor]['ipv6']:
                max_key_ipv6 = max(presence_ipv6, key=lambda k: presence_ipv6[k])
                max_value_ipv6 = presence_ipv6[max_key_ipv6]
            else:
                max_key_ipv6 = None
                max_value_ipv6 = None
            
        # Extract the presence of the neighbor in peeringDB
        if neighbor in presence_peering:
                pdb_presence = presence_peering[neighbor]
        else:
            pdb_presence = None   

        # Extract the relationships of the neighbor who received the announcement with the origin AS
        relationship = next((entry for entry in all_neighbors_caida if entry[0] == neighbor), None)
        if relationship == None: 
                rel = None
        else:
            rel = relationship[1]
        
        data_point = {"vantage_point": vantage_point, "collectors": collectors, "neighbor": neighbor, "neighbor_relationship": rel, "ipv4_country": max_key_ipv4, "ipv4_coverage": max_value_ipv4, "ipv6_country": max_key_ipv6, "ipv6_coverage": max_value_ipv6, "peering_locations": pdb_presence}
        location_information_per_prefix[prefix].append(data_point)

write_json("presence_of_neighbors/presence_of_" + asn + "_neighbors.json", location_information_per_prefix)