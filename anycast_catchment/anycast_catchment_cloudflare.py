import csv
import json
import random 
import geoip2.database
from geopy.distance import geodesic
from pprint import pprint as pprint

ANYCAST_ASN = '13335'

# Prints a progress bar
def print_progress_bar(progress, total, width=25):
    percent = width * ((progress + 1) / total)
    bar = chr(9608) * int(percent) + "-" * (width - int(percent))
    print(f"\rCompletion progress: |{bar}| {(100/width)*percent:.2f}%", end="\r")

# Reads content from a json file
def read_json(jsonfilename):
    with open(jsonfilename, 'r') as jsonfile:
        return json.load(jsonfile)

# Writes content to a json file
def write_json(jsonfilename, content):
    with open(jsonfilename, 'w+') as fp:
        json.dump(content, fp, indent=4)

# Returns true if the given prefix is anycast prefix
def is_anycast(prefix, anycast_prefixes):
    return prefix in anycast_prefixes

# Geolocates ip in coord level granularity
def geolocate_per_ip_city_level(ip):
    with geoip2.database.Reader('../geolocation/maxmind/input/GeoLite2-City_20240119/GeoLite2-City.mmdb') as city_reader:
        response_city = city_reader.city(ip)
        return response_city.location.latitude, response_city.location.longitude

# Geolocates ip in country level granularity
def geolocate_per_ip_country_level(ip):
    with geoip2.database.Reader('../geolocation/maxmind/input/GeoLite2-Country_20231103/GeoLite2-Country.mmdb') as country_reader:
        response_country = country_reader.country(ip)
        return response_country.country.iso_code 

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

if __name__ == '__main__':
    bgp_routes_destined_to_cloudflare = read_json("../routing_tables/output/" + ANYCAST_ASN + "_routing_presence_origin_bgpstream.json")
    anycast_prefixes = read_json("../anycast_prefixes/output/anycast_asn_to_prefix.json")[ANYCAST_ASN]
    pops_per_asn = read_json("../geolocation/peeringdb/output/pop_per_asn_map.json")
    asns_per_pop = read_json("../geolocation/peeringdb/output/asn_per_pop_map.json")
    region_per_country = read_json("../geolocation/united_nations/output/region_per_country.json")

    # Map each anycast prefix to the respective vp-AS, vp-ISO, closest_pop and all_valid_pops.
    pop_level_catchment = dict()
    temp_pop_level_catchment = dict()
    # Given a an anycast prefix...
    for idx, prefix in enumerate(bgp_routes_destined_to_cloudflare):
        print_progress_bar(idx, len(bgp_routes_destined_to_cloudflare))
        pop_level_catchment[prefix] = dict()
        temp_pop_level_catchment[prefix] = dict()
        if is_anycast(prefix, anycast_prefixes):
            # ... extract the AS path, the vp IP and the penultimate AS in the AS path
            for as_path in bgp_routes_destined_to_cloudflare[prefix]:
                as_path_list = as_path.split(" ")
                vp_as = as_path_list[0]
                pen_as = as_path_list[-2]
                # Skip to the next iteration if the penultimate AS is not existent in any pop
                if pen_as not in pops_per_asn: continue
                # Geolocate the source IP
                random_source_ip = random.choice(bgp_routes_destined_to_cloudflare[prefix][as_path])['vp_ip']
                source_country = geolocate_per_ip_country_level(random_source_ip)
                source_coord = geolocate_per_ip_city_level(random_source_ip)
                # Find in which PoPs is the pen-as present.
                pen_asn_pop_presence = pops_per_asn[pen_as]
                # Keep the PoPs in which the ANYCAST AS is present AND the REGION of the PoP is the same as the vp_ip REGION.
                valid_pops = list()
                for possible_pop in pen_asn_pop_presence:
                    possible_pop = str(possible_pop)
                    if int(ANYCAST_ASN) in asns_per_pop[possible_pop]["as_members"] and region_per_country[asns_per_pop[possible_pop]["country"]] == region_per_country[source_country]:
                        valid_pops.append(int(possible_pop))
                if not valid_pops:
                    valid_pops = pen_asn_pop_presence
                
                # Finally, find the closest pop from the ones in which the anycast AS exists utilizing the geodesic distance
                minimum_distance = 100000000000
                closest_pop = -1
                for pop in valid_pops:
                    pop = str(pop)
                    if asns_per_pop[pop]['as_members']:
                        pop_coord = asns_per_pop[pop]['coord']
                        distance = geodesic(source_coord, pop_coord).kilometers
                        if distance < minimum_distance:
                            minimum_distance = distance
                            closest_pop = int(pop)

                # Log the results into the respective dict
                if vp_as not in temp_pop_level_catchment[prefix]:
                    pop_level_catchment[prefix][vp_as] = dict()
                    temp_pop_level_catchment[prefix][vp_as] = dict()
                    temp_pop_level_catchment[prefix][vp_as]["all_valid_pops"] = set()
                    temp_pop_level_catchment[prefix][vp_as]["best_pop"] = set()
                    temp_pop_level_catchment[prefix][vp_as]["source_iso"] = set()
                temp_pop_level_catchment[prefix][vp_as]["all_valid_pops"].update(valid_pops)
                temp_pop_level_catchment[prefix][vp_as]["best_pop"].add(closest_pop)
                temp_pop_level_catchment[prefix][vp_as]["source_iso"].add(source_country)
                #Convert the results into list to serialize them into JSON format
                pop_level_catchment[prefix][vp_as]["all_valid_pops"] = list(temp_pop_level_catchment[prefix][vp_as]["all_valid_pops"])
                pop_level_catchment[prefix][vp_as]["best_pop"] = list(temp_pop_level_catchment[prefix][vp_as]["best_pop"])
                pop_level_catchment[prefix][vp_as]["source_iso"] = list(temp_pop_level_catchment[prefix][vp_as]["source_iso"])
    write_json("output/cloudflare_pop_level_catchment.json", pop_level_catchment)