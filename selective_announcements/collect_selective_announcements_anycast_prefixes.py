import os
import json
from pprint import pprint as pprint
import sys
import csv
import networkx as nx
from collections import defaultdict
from pprint import pprint as pprint
import glob

# Reads the topology dataset in a NetworkX graph
def get_AS_relationships_graph(as2rel_mapping):
    G = nx.DiGraph()
    with open(as2rel_mapping, 'r') as csvfile:
        csvreader = csv.reader(csvfile, delimiter='|')
        for row in csvreader:
            if row[0][0] != '#':  # ignore lines starting with "#"
                as1 = row[0]
                as2 = row[1]
                rel = int(row[2])
                if rel == -1:
                    G.add_edge(as1, as2)
                elif rel == 0:
                    G.add_edge(as1, as2)
                    G.add_edge(as2, as1)
    return G

# Algorithm for inferring export policy: Phases 1 and 2
def customer_cone_dfs(G, u):
    # Phase 1
    visited = set()
    customer_cone = set()
    S = [u]
    # Phase 2
    while S:
        node = S.pop()
        if node not in visited:
            visited.add(node)
            if node not in G:
                return customer_cone
            for neighbor in G.neighbors(node):
                # If node is not in neighbor's neighbors, then node is a provider of neighbor, else peer/customer
                # We only want to traverse customer paths in this phase, not peer paths.
                if node not in G.neighbors(neighbor):
                    # If is a direct/indirect customer of u, add it into customer cone
                    if neighbor not in visited:
                        customer_cone.add(neighbor)
                        S.append(neighbor)
    return customer_cone

# Algorithm for inferring export policy: Phase 3
def is_provider(G, w, u):
    if u not in G or w not in G: return False
    return w in G.neighbors(u) and u not in G.neighbors(w)

# Algorithm for inferring export policy: Phase 3
def is_peer(G, w, u):
    if u not in G or w not in G: return False
    return w in G.neighbors(u) and u in G.neighbors(w)

# Wrapper function for inferring export policy of direct/indirect customers
def is_selective_announcement_customer(AS_relationships_graph, vantage_point, next_hop_as, origin_as, customer_cone_graph):
    # Phases 1 and 2
    if origin_as in customer_cone_graph:
        # Phase 3
        if not is_provider(AS_relationships_graph, next_hop_as, vantage_point):
            return True
        return False
    return False

# Wrapper function for inferring export policy of direct/indirect customers
def is_selective_announcement_peer(AS_relationships_graph, vantage_point, next_hop_as, origin_as):
    # Phases 1 and 2
    if is_peer(AS_relationships_graph, origin_as, vantage_point):
        # Phase 3
        if is_provider(AS_relationships_graph, vantage_point, next_hop_as):
            return True
        return False
    return False

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

# Prints a progress bar
def print_progress_bar(progress, total, width=25):
    percent = width * ((progress + 1) / total)
    bar = chr(9608) * int(percent) + "-" * (width - int(percent))
    print(f"\rCompletion progress: |{bar}| {(100/width)*percent:.2f}%", end="\r")

# Returns true if the VP received a peer/provider route towards a customer/peer prefix.
def is_selans(anycast_prefix, routing_presence, as_graph):
    # For an anycast prefix to be selective announced prefix, two things could happen:
    # 1. The AS relationship between VP and first-hop AS is peer and the origin AS is a direct/indirect customer of the VP, OR,
    # 2. The AS relationship between VP and first-hop AS is provider and the origin is either a direct/indirect customer or peer of the VP.
    for path in routing_presence[anycast_prefix]:
        path_as_list = path.split(" ")
        if len(path_as_list) <= 2: continue
        vp = path_as_list[0]
        first_hop = path_as_list[1]
        origin = path_as_list[-1]
        cc_vp = customer_cone_dfs(as_graph, vp)
        # If the VP has no customers check only peer SA prefixes.
        if not cc_vp: 
            if is_selective_announcement_peer(as_graph, vp, first_hop, origin): 
                return True
        else:
            if is_selective_announcement_customer(as_graph, vp, first_hop, origin, cc_vp) or is_selective_announcement_peer(as_graph, vp, first_hop, origin):
                return True
    # If there was no path to label the anycast prefix as SA then return False
    return False

if __name__ == '__main__':
    # Get all anycast asns for which we have routing tables
    anycast_asns = list()
    for file in find_json_files("../routing_tables/output/"):
        asn = file.split("_")[0]
        anycast_asns.append(asn)
    
    # Initialize the AS graph
    as_graph = get_AS_relationships_graph("../as_graph/20231101.as-rel2.txt")

    # Initialize the dictionary which holds the selective announced anycast prefixes
    selans_per_AS = dict()
    for idx, anycast_asn in enumerate(anycast_asns):
        print_progress_bar(idx, len(anycast_asns))
        # Read routing tables where the given AS appears as origin AS
        routing_presence = read_json("../routing_tables/output/" + anycast_asn + "_routing_presence_origin_bgpstream.json")
        # Read anycast asn to prefix map
        anycast_prefixes = read_json("../anycast_prefixes/output/anycast_asn_to_prefix.json")[anycast_asn]
        # Initialize the respective dictionary entry (i.e., the list which holds all selans anycast prefixes per anycast ASn)
        selans_per_AS[anycast_asn] = list()
        for anycast_prefix in anycast_prefixes:
            if anycast_prefix in routing_presence:
                if is_selans(anycast_prefix, routing_presence, as_graph):
                    selans_per_AS[anycast_asn].append(anycast_prefix)
                else:
                    print(anycast_prefix)
    write_json("output/selective_announced_anycast_prefixes_per_as.json", selans_per_AS)