import json

# Writes content to a json file
def write_json(jsonfilename, content):
    with open(jsonfilename, 'w+') as fp:
        json.dump(content, fp, indent=4)

# Reads anycast IPv4 and IPv6 prefixes
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

# Reads bgp.tools API https://bgp.tools/kb/api
def read_bgp_tools_table(bgptoolsurl):
    prefix_to_asn = dict()
    with open(bgptoolsurl, 'r') as file:
        for line in file:
            json_obj = json.loads(line)
            prefix = json_obj['CIDR']
            asn = json_obj['ASN']
            if prefix not in prefix_to_asn:
                prefix_to_asn[prefix] = list()
            if asn not in prefix_to_asn[prefix]:
                prefix_to_asn[prefix].append(asn)
    return prefix_to_asn

all_prefixes = read_bgp_tools_table('input/bgp.tools_table-24-11-23.jsonl')
anycast_prefixes = read_anycast_prefixes("input/anycatch-v4-prefixes.txt", "input/anycatch-v6-prefixes.txt")

counter = 0
anycast_asn_to_prefix = dict()
for prefix in all_prefixes:
    if prefix in anycast_prefixes:
        counter += 1
        anycast_asns = all_prefixes[prefix]
        for asn in anycast_asns:
            if asn not in anycast_asn_to_prefix:
                anycast_asn_to_prefix[asn] = list()
            if prefix not in anycast_asn_to_prefix[asn]:
                anycast_asn_to_prefix[asn].append(prefix)

write_json('output/anycast_asn_to_prefix.json', anycast_asn_to_prefix)

