import json
from pprint import pprint as pprint
from collections import defaultdict

# reads content of json file and returns
def read_json(jsonfilename):
    with open(jsonfilename, 'r') as jsonfile:
        return json.load(jsonfile)

# writes content to json file
def write_json(jsonfilename, content):
    with open(jsonfilename, 'w+') as fp:
        json.dump(content, fp, indent=4)

# maps ASns to geopresence (country) based on the facilities they are present
def map_fac_to_asns(file_data):
    # First, we map the geolocation information to each PoP using the fac object
    fac = file_data['fac']['data']    
    pop_map = dict()
    for item in fac:
        fac_id, lat, lon, city, country, name = item['id'], item['latitude'], item['longitude'], item['city'], item['country'], item['name']
        pop_map[fac_id] = {"name": name, "coord": (lat, lon), "city": city, "country": country}

    # We 'll use netfac object to map each PoP to a specific ASn.
    netfac = file_data['netfac']['data']
    pops_per_asn = defaultdict(list)
    for item in netfac:
        asn = item['local_asn']
        fac_id = item['fac_id']
        pops_per_asn[asn].append(fac_id)
    
    # We convert the PoP per ASn to ASn per PoP
    asns_per_pop = defaultdict(list)
    for asn, fac_ids in pops_per_asn.items():
        for fac_id in fac_ids:
            asns_per_pop[fac_id].append(asn)
    
    # Now we add the AS members to the pop_map and return
    for fac_id in pop_map:
        pop_map[fac_id]["as_members"] = asns_per_pop[fac_id]
    
    return pop_map, pops_per_asn



if __name__ == "__main__":
    # We downloaded the CAIDA's snapshot for PeeringDB (11/Nov/2023)'
    file_data = read_json("input/peeringdb_2_dump_2023_11_01.json")

    # If we print file_data.keys() some of the object we get are:
    # 'fac'     # Describes a facility / colocation record.
    # 'org'     # Root object for fac, ix, net, this holds information about organisation.
    # 'poc'     # Describes various role accounts (point of contact), this is currently only for net objects.
    # 'ix'      # Describes an exchange.
    # 'ixlan'   # Describes the LAN of an ix, one ix may have multiple ixlan.
    # 'ixpfx'   # Describes the IP range (IPv4 and IPv6) for an ixlan, one ixlan may have multiple ixpfx.
    # 'net'     # Describes a network / ASN.
    # 'netixlan'# Describes the presence of a network at an exchange.
    # 'netfac'  # Describes the presence of a network at a facility.

    # We 'll use netfac object and map each PoP to a specific ASn.
    # Netfac returns the facilities (datacenters) at which the ASn is present.
    pop_map, asn_map = map_fac_to_asns(file_data)
    write_json("output/asn_per_pop_map.json", pop_map)
    write_json("output/pop_per_asn_map.json", asn_map)


