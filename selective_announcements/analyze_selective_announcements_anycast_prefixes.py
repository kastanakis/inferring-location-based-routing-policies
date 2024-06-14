import json
import os
import matplotlib.pyplot as plt
import statsmodels.api as sm

FONT_SIZE = 13

# Reads content of json file and returns
def read_json(jsonfilename):
    with open(jsonfilename, 'r') as jsonfile:
        return json.load(jsonfile)
    
# Writes content to a json file
def write_json(jsonfilename, content):
    with open(jsonfilename, 'w+') as fp:
        json.dump(content, fp, indent=4)

# Finds all json files in a dir
def find_json_files(directory):
    json_files = [f for f in os.listdir(directory) if f.endswith('.json')]
    return json_files

# Prints a progress bar
def print_progress_bar(progress, total, width=25):
    percent = width * ((progress + 1) / total)
    bar = chr(9608) * int(percent) + "-" * (width - int(percent))
    print(f"\rCompletion progress: |{bar}| {(100/width)*percent:.2f}%", end="\r")

# Returns top N anycast ASes based on their customer cone
def select_topN_anycast_ases(asns, N=100):
    asrank = read_json("../as_graph/as_rank/as2rank.json")
    sorted_asns = sorted(asns, key=lambda asn: asrank.get(asn, float('inf')))
    return sorted_asns[:N]

# Plots the CDF of selans ratio per origin anycaster
def plot_selans_for_anycast_prefixes(data):
    fig, ax = plt.subplots()
    ecdf = sm.distributions.ECDF(data)
    ax.step(ecdf.x, ecdf.y, where='post', color='black')
    ax.set_xlabel("Anycast Selective Announcers")
    ax.set_ylabel("Selective Announced Anycast Prefixes ratio")
    ax.set_title("CDF of Selective Announced Prefixes per Anycast Origin AS")
    ax.set_xlim(-0.05, 1.05)
    ax.set_ylim(-0.05, 1.05)
    ax.grid()
    plt.rcParams.update({'font.size': FONT_SIZE})
    # Save the plot
    plt.savefig("output/ecdf_selective_announced_anycast_prefixes_per_origin.png")

if __name__ == '__main__':
    selans_ratio_per_asn = dict()
    # Get all selective announced prefixes by selective anycast announcers
    sel_prefixes = read_json("output/selective_announced_anycast_prefixes_per_as.json")
    # Get all anycast asns for which we have routing tables
    anycast_asns = list()
    for file in find_json_files("../routing_tables/output/"):
        asn = file.split("_")[0]
        anycast_asns.append(asn)
    
    # Get top 100 anycast ASes and compile their selective announcements ratio against all observed prefixes.
    # top100anycastASes = select_topN_anycast_ases(anycast_asns, len(anycast_asns))
    for idx, asn in enumerate(anycast_asns):
        print_progress_bar(idx, len(anycast_asns))
        # if asn not in top100anycastASes: continue    
        # Read anycast asn to prefix map and all observed prefixes (anycast and unicast)
        anycast_prefixes = read_json("../anycast_prefixes/output/anycast_asn_to_prefix.json")[asn]
        routing_presence = read_json("../routing_tables/output/" + asn + "_routing_presence_origin_bgpstream.json")
        # For each anycast ASn in the top 100 anycast ASns, compile the ratio of observed selans prefixes against the 
        # total number of observed anycast prefixes.
        selans_sum = 0
        selans_denom = 0
        for anycast_prefix in anycast_prefixes:
            if anycast_prefix in routing_presence:
                if anycast_prefix in sel_prefixes[asn]:
                    selans_sum += 1
                selans_denom += 1
        if selans_denom: 
            selans_ratio_per_asn[asn] = selans_sum / selans_denom
    write_json("output/selective_announced_anycast_prefixes_ratio_per_as.json", selans_ratio_per_asn)
    plot_selans_for_anycast_prefixes(list(selans_ratio_per_asn.values()))
    
