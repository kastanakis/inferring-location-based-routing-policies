import sys
import csv
import pytricia
import pybgpstream
from datetime import date
from itertools import groupby
from operator import itemgetter
from bogons import is_public_ip as is_public_ip
import json

# reads content of json file and returns
def read_json(jsonfilename):
    with open(jsonfilename, 'r') as jsonfile:
        return json.load(jsonfile)

# Populates bogus prefixes in a pytricia tree
def create_bogons_trees(filename1, filename2):
    # Create one structure for IPv4 and one for IPv6
    bogons_pyt_v4 = pytricia.PyTricia()
    bogons_pyt_v6 = pytricia.PyTricia(128)

    # Read bogons from Cymru website: https://www.team-cymru.com/bogon-reference-http
    with open(filename1, 'r') as ipv4_bogon:
        ipv4_bog = csv.reader(ipv4_bogon)
        # Skip first line of CSV
        next(ipv4_bog)
        for row in ipv4_bog:
            bogus_pref = row[0]
            bogons_pyt_v4.insert(bogus_pref, 'bogus')

    with open(filename2, 'r') as ipv6_bogon:
        ipv6_bog = csv.reader(ipv6_bogon)
        # Skip first line of CSV
        next(ipv6_bog)
        for row in ipv6_bog:
            bogus_pref = row[0]
            bogons_pyt_v6.insert(bogus_pref, 'bogus')

    return (bogons_pyt_v4, bogons_pyt_v6)

# Returns true if prefix is not private/unallocated/reserved
def is_valid(prefix, bogons_pyt_v4, bogons_pyt_v6):
    # First of all discard exact prefix matches from fullbogons tree
    if ((bogons_pyt_v4.has_key(prefix)) or (bogons_pyt_v6.has_key(prefix))):
        return False

    # Then discard bogons using the bogons library and the leftmost part of the prefix
    leftmost_part_of_prefix = prefix.split('/')[0]  # network addr
    if not is_public_ip(leftmost_part_of_prefix):
        return False

    # Extract the subnet mask
    rightmost_part_of_prefix = int(prefix.split('/')[1])  # subnet size
    # Distinguish if IPv4 or IPv6
    if (leftmost_part_of_prefix.find(':') == -1):   # v4
        # Drop prefixes with subnet size less than /8 or more than /24
        if ((rightmost_part_of_prefix > 24) or (rightmost_part_of_prefix < 8)):
            return False
    else:                                           # v6
        # Drop prefixes with subnet size more than /64
        if ((rightmost_part_of_prefix > 64)):
            return False

    # In all other occassions return True
    return True

# Removes consecutive duplicates in a sequence
def remove_prepending(seq):
    # https://stackoverflow.com/questions/5738901/removing-elements-that-have-consecutive-duplicates
    return list(map(itemgetter(0), groupby(seq)))

# Returns 1 if a sequence has cycles
def has_cycle(seq):
    unique_seq = set(seq)
    if (len(seq) == len(list(unique_seq))):
        return 0  # same length means no duplicates
    return 1  # else, there is a cycle

# Writes the routing table of the respective peer ASn into a file
def write_from_stream_to_file(routing_tables_location, stream, date, next_index):
    # We populate two pytricia trees to keep track of the bogus prefixes
    filename1 = '../bogus_prefixes/fullbogons-ipv4.txt'
    filename2 = '../bogus_prefixes/fullbogons-ipv6.txt'
    bogons_pyt_v4, bogons_pyt_v6 = create_bogons_trees(filename1, filename2)
    # We filter out element with cycles or invalid prefixes
    for elem in stream:
        row = str(elem).split('|')
        # Discard {ASn} occurences
        res = [i for i in row if '{' in i]
        if res:
            continue
        record_type = row[0]
        type = row[1]
        prefix = row[9]
        as_path = row[11]

        if record_type == "rib" and type == "R":
            if is_valid(prefix, bogons_pyt_v4, bogons_pyt_v6):
                # Get the list of ASes in the AS path
                as_path_list = as_path.split(" ")
                # Remove path prepending
                as_path_filtered = remove_prepending(as_path_list)
                # Discard paths with cycles and with less than 2 ASes
                if not has_cycle(as_path_filtered) and len(as_path_filtered) > 1:
                    # Write the original entry into the filtered csv
                    with open(routing_tables_location + date + '_all_anycast_asns_' + str(next_index) + '_routing_tables.csv', 'a+') as output_csv_file:
                        csv_writer = csv.writer(output_csv_file, delimiter='|')
                        csv_writer.writerow(row)


def main(date, next_index):
    ''' 
    BGP Elem Format: check https://bgpstream.caida.org/docs/tools/bgpreader#elem.
    <dump-type>|<elem-type>|<record-ts>|<project>|<collector>|<router-name>|<router-ip>| \
    <peer-ASn>|<peer-IP>|<prefix>|<next-hop-IP>|<AS-path>|<communities>|<old-state>|<new-state>
    '''
    from_time = date + " 00:00:00"
    until_time = date + " 00:00:00 UTC"
    print((from_time, until_time))

    # if AS == "test":
    # Check the full list of providers here: https://bgpstream.caida.org/data#!ris and here: https://bgpstream.caida.org/data#!routeviews
    stream = pybgpstream.BGPStream(
        from_time=from_time, until_time=until_time,
        # this implies that we are using all possible route collectors
        projects=['ris', 'routeviews'],
        record_type="ribs"
    )
    
    CHUNK_SIZE = 30
    anycast_ases = list(read_json("../anycast_prefixes/output/anycast_asn_to_prefix.json").keys())
    print("Total length of Anycast ASes: " + str(len(anycast_ases)))
    # for next_index in range(CHUNK_SIZE, len(anycast_ases) + CHUNK_SIZE, CHUNK_SIZE):
    next_index = int(next_index)
    prev_index = next_index - CHUNK_SIZE
    print("Current chunk: " + str((prev_index, next_index)))
    anycast_ases_chunk = anycast_ases[prev_index:next_index]
    as_filter = ""
    for idx, asn in enumerate(anycast_ases_chunk):
        if idx == len(anycast_ases_chunk) - 1: as_filter += str(asn)
        else: as_filter += str(asn) + "|"

    stream.parse_filter_string("path _(" + as_filter + ")$")
    routing_tables_location = 'input/'
    write_from_stream_to_file(routing_tables_location, stream, date, next_index)

main("2023-11-01", sys.argv[1])
