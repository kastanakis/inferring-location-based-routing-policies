from pprint import pprint as pprint
import matplotlib.pyplot as plt
import pandas as pd
import json

REGIONALITY_THRESHOLD = 90
FONT_SIZE = 13
TOP_ANYCAST_ASES = 100 

# Reads content from a json file
def read_json(jsonfilename):
    with open(jsonfilename, 'r') as jsonfile:
        return json.load(jsonfile)

# Prints a progress bar
def print_progress_bar(progress, total, width=25):
    percent = width * ((progress + 1) / total)
    bar = chr(9608) * int(percent) + "-" * (width - int(percent))
    print(f"\rCompletion progress: |{bar}| {(100/width)*percent:.2f}%", end="\r")

def select_topN_anycast_ases(asns, N=100):
    sorted_asns = list(read_json("../as_graph/as_rank/cdnperf.json").keys())
    # asrank = read_json("../as_graph/as_rank/as2rank.json")
    # sorted_asns = sorted(asns, key=lambda asn: asrank.get(asn, float('inf')))
    # as2prefnum = read_json("../as_graph/as_rank/as2prefnum.json")
    # sorted_asns = sorted(asns, key=lambda asn: as2prefnum.get(asn, float('inf')))
    return sorted_asns[:N]

# Return 1 if an AS is regional, 0 if global
def is_regional(asn, peering_presence, prefix_presence, un_regions_data):
    # An AS is considered regional if it peers with other ASes in a single REGION in >REGIONALITY_THRESHOLD% of the times, AND
    # it announces its prefixes to the SAME REGION in >REGIONALITY_THRESHOLD% of the times.
    peering_regions = dict()
    # for each country in the peering_presence dict...
    if asn in peering_presence:
        for country in peering_presence[asn]:
            # Initialize a variable, which is the presence of the AS in this country in %
            country_coverage = peering_presence[asn][country]
            # reduce the country into the respective region...
            if country == '?': continue
            region = un_regions_data[country]
            if region not in peering_regions:
                peering_regions[region] = 0
            peering_regions[region] += country_coverage
    
    # We repeat the above process for the ipv4 and ipv6 prefix coverages of the same AS
    prefix_regions = dict()
    prefix_regions["ipv4"] = dict()
    prefix_regions["ipv6"] = dict()
    if asn in prefix_presence:
        for ip_version in prefix_presence[asn]:
            for country in prefix_presence[asn][ip_version]:
                country_coverage = prefix_presence[asn][ip_version][country]
                if country == '?': continue
                region = un_regions_data[country]
                if region not in prefix_regions[ip_version]:
                    prefix_regions[ip_version][region] = 0
                prefix_regions[ip_version][region] += country_coverage

    # We raise a flag when there are no prefixes announced (ipv4, or ipv6 or both)
    NO_PREFIXES_ANNOUNCED = 0
    if not prefix_regions["ipv4"] and not prefix_regions["ipv6"]:
        NO_PREFIXES_ANNOUNCED = 1
    elif not prefix_regions["ipv4"] and prefix_regions["ipv6"]:
        max_region_prefixes, max_value_prefixes = max(prefix_regions["ipv6"].items(), key=lambda x: x[1])
    elif prefix_regions["ipv4"] and not prefix_regions["ipv6"]:
        max_region_prefixes, max_value_prefixes = max(prefix_regions["ipv4"].items(), key=lambda x: x[1])
    elif prefix_regions["ipv4"] and prefix_regions["ipv6"]:
        max_region_ipv4, max_value_ipv4 = max(prefix_regions["ipv4"].items(), key=lambda x: x[1])
        max_region_ipv6, max_value_ipv6 = max(prefix_regions["ipv6"].items(), key=lambda x: x[1])
        if max_region_ipv4 == max_region_ipv6: 
            max_region_prefixes = max_region_ipv4
            # If ipv4 and v6 have the same region as the maximum value, then select the minimum
            max_value_prefixes = max(max_value_ipv4, max_value_ipv6)
        else:
            # If there are two different regions in IPv4 and v6 there is no chance that the AS is regional
            return 0

    # We raise a flag when there are no peering links
    NO_PEERING_LINKS = 0
    if not peering_regions:
        NO_PEERING_LINKS = 1
    else:
        max_region_peering, max_value_peering = max(peering_regions.items(), key=lambda x: x[1])

    # There are 4 possible scenarios: peering coverage is 0, prefix coverage is 0, both coverages are 0, both coverages are larger than 0
    # Scenario a: peering and prefixes coverages are 0. This indicates a problem in the process. Return -1.
    if NO_PEERING_LINKS and NO_PREFIXES_ANNOUNCED:
        return 1
    # Scenario b: peering coverage is 0. That means that we determine the regionality only through prefixes.
    elif NO_PEERING_LINKS:
        if max_value_prefixes > REGIONALITY_THRESHOLD:
            return 1
        return 0
    # Scenario c: prefix coverage is 0. That means that we determine the regionality only through peering links.
    elif NO_PREFIXES_ANNOUNCED:
        if max_value_peering > REGIONALITY_THRESHOLD:
            return 1
        return 0
    # Scenario d: both coverages are non-zero. The AS is regional if both coverages are above REGIONALITY_THRESHOLD% for the same region.
    elif not NO_PREFIXES_ANNOUNCED and not NO_PEERING_LINKS:
        if max_region_peering == max_region_prefixes and max_value_peering > REGIONALITY_THRESHOLD and max_value_prefixes > REGIONALITY_THRESHOLD:
            return 1
        return 0

def calculate_average_regionality_per_region_for_all_prefixes(regionality_dict):
    region_sum_count = {region: {'sum': 0.0, 'count': 0} for region in regionality_dict[next(iter(regionality_dict))].keys()}

    # Calculate sums and counts
    for ip_range, inner_dict in regionality_dict.items():
        for region, value in inner_dict.items():
            region_sum_count[region]['sum'] += value
            region_sum_count[region]['count'] += 1

    # Calculate averages and create a new dictionary with regions and averages
    average_regionality = {region: region_sum_count[region]['sum'] / region_sum_count[region]['count'] for region in region_sum_count}

    return average_regionality

def boxplot(overall_dict_of_regionality_dictionaries):
    # Convert the dictionary to a Pandas DataFrame for easier manipulation
    df = pd.DataFrame(overall_dict_of_regionality_dictionaries).T
    # Create a boxplot
    plt.rcParams.update({'font.size': FONT_SIZE})
    plt.figure(figsize=(12, 6))
    bp = df.boxplot(rot=60)
    new_labels = ['North. Africa', 'Sub-Sah. Africa', 'Latin America', 'North. America', 'Antarctica', 'Central Asia', 'East. Asia', 'South-east. Asia', 'South. Asia', 'West. Asia', 'East. Europe', 'North. Europe', 'South. Europe', 'West. Europe', 'Australia', 'Melanesia', 'Micronesia', 'Polynesia']
    bp.set_xticklabels(new_labels)
    plt.xlabel('Regions of Vantage Points')
    plt.ylabel('Regionality of Direct Neighbors')
    plt.ylim(-0.05, 1.05)
    plt.tight_layout()
    num_of_entries = len(overall_dict_of_regionality_dictionaries.keys())
    plt.savefig("output/figures/average_regionality_per_vp_region_for_top_" + str(num_of_entries) + "_anycasters.png")

def barplot(dict_of_regionality_dicts, asn):
    # Convert the dictionary to a Pandas DataFrame for easier manipulation
    df = pd.DataFrame(dict_of_regionality_dicts)
    # Create a barplot
    plt.rcParams.update({'font.size': FONT_SIZE})
    plt.figure(figsize=(12, 6))
    bp = df.plot.bar()
    new_labels = ['North. Africa', 'Sub-Sah. Africa', 'Latin America', 'North. America', 'Antarctica', 'Central Asia', 'East. Asia', 'South-east. Asia', 'South. Asia', 'West. Asia', 'East. Europe', 'North. Europe', 'South. Europe', 'West. Europe', 'Australia', 'Melanesia', 'Micronesia', 'Polynesia']
    bp.set_xticklabels(new_labels)
    plt.xlabel('Regions of Vantage Points')
    plt.ylabel('Regionality of Direct Neighbors')
    plt.ylim(-0.05, 1.05)
    plt.tight_layout()
    plt.grid()
    plt.savefig("output/figures/average_regionality_per_vp_region_for_" + asn + ".png")
    # plt.savefig("output/figures/average_regionality_per_vp_region_for_top_" + str(num_of_entries) + "_anycasters.png")

if __name__ == "__main__":
    as_level_catchment_data = read_json("output/as_level_anycast_catchment_per_region.json")
    pref_presence = read_json("../geolocation/maxmind/output/presence_per_AS_maxmind.json")
    peer_presence = read_json("../geolocation/peeringdb/output/presence_per_AS_peeringdb.json")
    un_regions_data = read_json("../geolocation/united_nations/output/region_per_country.json")
    regions = ["Northern Africa",
        "Sub-Saharan Africa",
        "Latin America and the Caribbean",
        "Northern America",
        "Antarctica",
        "Central Asia",
        "Eastern Asia",
        "South-eastern Asia",
        "Southern Asia",
        "Western Asia",
        "Eastern Europe",
        "Northern Europe",
        "Southern Europe",
        "Western Europe",
        "Australia and New Zealand",
        "Melanesia",
        "Micronesia",
        "Polynesia"
    ]

    # Select the top 100 anycast ASes
    # topN_anycasters = list(as_level_catchment_data.keys())
    topN_anycasters = select_topN_anycast_ases(as_level_catchment_data.keys(), N=TOP_ANYCAST_ASES)
    # topN_anycasters = read_json("../as_graph/as_rank/cdnperf.json").keys()
    print(topN_anycasters)
    overall_dict_of_regionality_dictionaries = dict()
    for asn in topN_anycasters:
        dict_of_regionality_dictionaries = dict()
        # print_progress_bar(idx, len(as_level_catchment_data))
        regionality_per_prefix = dict()
        for prefix in as_level_catchment_data[asn]:
            regionality_of_neighbors_per_region = dict()
            regionality_of_neighbors_per_region = {region: 0.0 for region in regions}

            for region in as_level_catchment_data[asn][prefix]:
                unique_ases_per_region = set()
                regionality_counter = 0
                for country in as_level_catchment_data[asn][prefix][region]:
                    for neighbor in as_level_catchment_data[asn][prefix][region][country]:
                        unique_ases_per_region.add(neighbor)
                for asN in unique_ases_per_region:
                    regionality_counter += is_regional(asN, peer_presence, pref_presence, un_regions_data)
                regionality_of_neighbors_per_region[region] = regionality_counter/len(unique_ases_per_region)
            regionality_per_prefix[prefix] = regionality_of_neighbors_per_region
        average_regionality_per_region = calculate_average_regionality_per_region_for_all_prefixes(regionality_per_prefix)
        dict_of_regionality_dictionaries[asn] = average_regionality_per_region
        overall_dict_of_regionality_dictionaries[asn] = average_regionality_per_region
        barplot(dict_of_regionality_dictionaries, asn)
    boxplot(overall_dict_of_regionality_dictionaries)