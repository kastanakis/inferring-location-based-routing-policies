import json
from pprint import pprint as pprint
from collections import Counter
# PeeringDB, as the name suggests, was set up to facilitate peering between networks and peering coordinators. 
# In recent years, the vision of PeeringDB has developed to keep up with the speed and diverse manner in which 
# the Internet is growing. The database is no longer just for peering and peering related information. It now 
# includes all types of interconnection data for networks, clouds, services, and enterprise, as well as 
# interconnection facilities that are developing at the edge of the Internet.

# reads content of json file and returns
def read_json(jsonfilename):
    with open(jsonfilename, 'r') as jsonfile:
        return json.load(jsonfile)

# writes content to json file
def write_json(jsonfilename, content):
    with open(jsonfilename, 'w+') as fp:
        json.dump(content, fp, indent=4)

# maps ASns to geopresence (country) based on the facilities they are present
def map_fac_countries_to_asns(file_data):
    # We 'll use netfac object to map each country to a specific ASn.
    netfac = file_data['netfac']['data']
    # To do so, we'll use a dictionary, with ASns as keys and countries as values.
    # An ASn may have multiple values, hence the value of each entry will be a list.
    geographical_presence_per_asn = dict()

    # For each item of netfac object, we collect asn, city, country and create an entry
    # If this entry doesn't exist in dict, we add it
    for item in netfac:
        # city = item['city']
        country = item['country']
        if country == "":
                continue
        # value = (city, country)
        asn = str(item['local_asn'])
        if asn not in geographical_presence_per_asn:
            geographical_presence_per_asn[asn] = list()
        
        # if country not in geographical_presence_per_asn[asn]:
        geographical_presence_per_asn[asn].append(country)
    
    # Return the dict
    return geographical_presence_per_asn


# maps ASns to geopresence (city, country) based on the IXPs they are present
def map_ix_countries_to_asns(file_data):
    # We 'll use netixlan and ix objects to map each country/city to a specific ASn.
    ix = file_data['ix']['data']
    netixlan = file_data['netixlan']['data']
    # For each ix we collect the id and map it to a specific country
    ix_dict = dict()
    for item in ix:
        id = str(item['id'])
        country = item['country']
        ix_dict[id] = country
    # For each netixlan we collect the asn and map it to the country that corresponds
    # to the respective ix_id
    # To do so, we'll use a dictionary, with ASns as keys and countries as values.
    # An ASn may have multiple values, hence the value of each entry will be a list.
    geographical_presence_per_asn = dict()
    for item in netixlan:
        asn = str(item['asn'])
        id = str(item['ix_id'])
        if asn not in geographical_presence_per_asn:
            geographical_presence_per_asn[asn] = list()
        
        # We extract the country of the respective ix and add it in the list
        country = ix_dict[id]
        # if country not in geographical_presence_per_asn[asn]:
        geographical_presence_per_asn[asn].append(country)

    # Return the dict
    return geographical_presence_per_asn


# Merges dictionaries
def merge(d1, d2):
    dd = dict()
    for d in (d1, d2):  
        for key, value in d.items():
            # Since value is a list of country, we flatten this list by passing one by one 
            # the countries into the merged dictionary
            if key not in dd:
                dd[key] = list()
            for val in value:
                dd[key].append(val)
    # The following one liner generates a new dictionary (dd_final) that maps each key from the original dictionary (dd) to a sub-dictionary. 
    # Each sub-dictionary contains the ratio of occurrences for each unique item in the corresponding list of the original dictionary. 
    dd_final = {key: {item: dd[key].count(item) / len(dd[key]) for item in set(dd[key])} for key in dd}
    result_dict = {key: {sub_key: value * 100 for sub_key, value in sub_dict.items()} for key, sub_dict in dd_final.items()}
    return result_dict


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

    # We 'll use netfac object and map each country/city to a specific ASn.
    # Netfac returns the facilities (datacenters) at which the ASn is present.
    map_1 = map_fac_countries_to_asns(file_data)
    map_2 = map_ix_countries_to_asns(file_data)
    merged = merge(map_1, map_2)
    
    # Write results into json
    write_json('output/presence_per_AS_peeringdb.json', merged)

