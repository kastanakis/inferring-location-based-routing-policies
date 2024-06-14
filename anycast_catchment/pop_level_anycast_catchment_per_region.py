import csv
import json

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

# Reads the topology dataset in a dictionary 
def read_topology(as2rel_mapping):
    as2rel_dict = dict()
    # Unbox the as2rel dataset
    with open(as2rel_mapping, 'r') as csvfile:
        csvreader = csv.reader(csvfile, delimiter='|')
        for row in csvreader:
            if row[0][0] != '#':  # ignore lines starting with "#"
                as1 = int(row[0])
                as2 = int(row[1])
                rel = int(row[2])
                if as1 not in as2rel_dict:
                    as2rel_dict[as1] = list()
                as2rel_dict[as1].append([as2, rel])
                if as2 not in as2rel_dict:
                    as2rel_dict[as2] = list()
                as2rel_dict[as2].append([as1, -rel])
    return as2rel_dict

if __name__ == "__main__":
    as2rel_dict = read_topology("../as_graph/20231101.as-rel2.txt")
    as_level_catchment_data = read_json("output/as_level_anycast_catchment_per_region.json")
    asn_per_pop = read_json("../geolocation/peeringdb/output/asn_per_pop_map.json")
    pop_per_asn = read_json("../geolocation/peeringdb/output/pop_per_asn_map.json")
    availabe_pops_per_country = dict()
    anycast_as_relationships = dict()
    # For each anycast ASn
    for idx, asn in enumerate(as_level_catchment_data):
        print_progress_bar(idx, len(as_level_catchment_data))
        availabe_pops_per_country[asn] = dict()
        # Find all business related ASes
        if int(asn) not in as2rel_dict:
            continue
        for rel in as2rel_dict[int(asn)]:
            anycast_as_relationships[str(rel[0])] = rel[1]
        # Find all PoPs in which the origin/anycast is present
        if asn in pop_per_asn:
            origin_pop_presence = pop_per_asn[asn] 
        else:
            origin_pop_presence = []
        # For each anycast prefix and all source AS regions and countries
        for prefix in as_level_catchment_data[asn]:
            availabe_pops_per_country[asn][prefix] = dict()
            for region in as_level_catchment_data[asn][prefix]:
                availabe_pops_per_country[asn][prefix][region] = dict()
                # ... find the penultimate ASes that receive the traffic towards the anycast ASn
                for country in as_level_catchment_data[asn][prefix][region]:
                    availabe_pops_per_country[asn][prefix][region][country] = list()
                    penultimate_ases = as_level_catchment_data[asn][prefix][region][country]
                    pop_presence_union = set()
                    # Then, get all PoPs in which these penultimate ASes are present.
                    for pen_asn in penultimate_ases:
                        # Keep only the ASes which exist in at least one PoP and are business related with the origin AS 
                        if pen_asn in pop_per_asn and pen_asn in anycast_as_relationships.keys():
                            pop_presence_union.update(pop_per_asn[pen_asn])
                    # Be careful: keep only the PoPs in which the origin anycast AS is present
                    pops_where_origin_present = list(pop_presence_union.intersection(origin_pop_presence))
                    final_pop_list = list()
                    for pop in pops_where_origin_present:
                        entry = asn_per_pop[str(pop)]
                        final_entry = {"pop_id":str(pop), "name":entry['name'], "coord":entry['coord'], "city":entry['city'], "country":entry['country']}
                        final_pop_list.append(final_entry)
                    availabe_pops_per_country[asn][prefix][region][country] = final_pop_list

    write_json("output/available_pops_per_country.json", availabe_pops_per_country)