import json

# writes content to json file
def write_json(jsonfilename, content):
    with open(jsonfilename, 'w+') as fp:
        json.dump(content, fp, indent=4)

# Function to read JSONL file and create the dictionary
def create_asn_rank_dict(jsonl_file):
    asn_rank_dict = {}
    asn_prefnum_dict = {}
    with open(jsonl_file, 'r') as file:
        for line in file:
            data = json.loads(line)
            asn = data.get("asn")
            rank = data.get("rank")
            prefnum = data.get("cone")['numberPrefixes']
            if asn is not None and rank is not None:
                asn_rank_dict[asn] = rank
            if asn is not None and prefnum is not None:
                asn_prefnum_dict[asn] = prefnum

    return asn_rank_dict, asn_prefnum_dict

# Example usage
jsonl_file_path = 'asns.jsonl'
asn_rank_dict, asn_prefnum_dict = create_asn_rank_dict(jsonl_file_path)

# Print the resulting dictionary
write_json("as2rank.json", asn_rank_dict)
write_json("as2prefnum.json", asn_prefnum_dict)