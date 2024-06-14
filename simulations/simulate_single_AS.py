import os
import sys
import time
import copy
import json
import uuid
import random
from tqdm import tqdm
import concurrent.futures
from pprint import pprint
from itertools import repeat
from ast import literal_eval as make_tuple

RANDOM_SAMPLE = 5000

# Load the topology using the CAIDA dataset
def load_topo(topology_date, simulator_version_folder):
    TOPOLOGY_FILE_FORMAT = '../as_graph/{}.as-rel2.txt'
    sys.path.insert(1, simulator_version_folder)
    from BGPtopology import BGPtopology
    Topo = BGPtopology()
    Topo.load_topology_from_csv(TOPOLOGY_FILE_FORMAT.format(topology_date), type="CAIDA")
    return Topo

# Reads content of json file and returns
def read_json(jsonfilename):
    with open(jsonfilename, 'r') as jsonfile:
        return json.load(jsonfile)

# Extract origin ASn and dest ASn from BGPStream paths
def get_ground_truth_paths(ground_truth_filename):
    unique_paths = set()
    full_json = read_json(ground_truth_filename)
    for prefix in full_json:
        paths = full_json[prefix]
        for path in paths:
            unique_paths.add(path)
    return list(unique_paths)

# Loads the topology, announces a unique prefix from an origin, selects the best paths from a vantage point
def simulate(path, Topo):
    # Extract src, dest ASns
    path = path.split(" ")
    origin_as, dest_as = (int(path[-1]), int(path[0]))

    # Create a unique prefix to avoid MOAS
    prefix = str(uuid.uuid4()) + "______add_originAS_to_avoid_MOAS_" + str(origin_as)
    
    # Announce prefix from origin ASns
    Topo.add_prefix(origin_as, prefix)

    # Get path from dest ASn (vantage point) to origin ASn
    node = Topo.get_node(dest_as)
    if node is None:
        return None
    simulated_path = node.get_path(prefix)
    if simulated_path is None:
        return None
    
    # Shallow copy of the path for storing purposes
    simulated_path_copy = copy.copy(simulated_path)
    # We add the vantage point in the beginning of the path
    simulated_path_copy.insert(0, dest_as)
    # This will be a single list...
    best_path = simulated_path_copy
    
    # Collect all candidate best paths
    all_best_paths = node.get_all_paths(prefix)
    if(all_best_paths is None):
        return None
    all_best_paths_fixed = list()
    for path in all_best_paths:
        simulated_path_copy = copy.copy(path)
        simulated_path_copy.insert(0, dest_as)
        all_best_paths_fixed.append(simulated_path_copy)
    
    # Store the necessary results in a dict entry
    value_to_be_written = {"best_path": best_path, "candidate_paths": all_best_paths_fixed}
    # Return the single-best simulated path and all-possible simulated paths 
    return value_to_be_written


def main(caida_dataset_date, ground_truth_filename, simulator_version_folder, output_filename):
    # Read the origin, vp tuples from the ground truth dataset
    ground_truth_paths = random.sample(get_ground_truth_paths(ground_truth_filename), RANDOM_SAMPLE)
    # Load the respective topology
    Topo = load_topo(caida_dataset_date, simulator_version_folder)
    # # Simulate in parallel and write results to file as soon as simulation jobs finish
    with concurrent.futures.ProcessPoolExecutor() as executor, open(output_filename, 'w+') as fp:
        # executor.map is ideal when we want to parallelize a for loop logic (i.e., one sim for every src, dst tuple)
        results = list(tqdm(executor.map(simulate, ground_truth_paths, repeat(Topo)), total=len(ground_truth_paths), desc="Simulating"))
        # Write the results into a file
        for result in results:
            if result: 
                json.dump(result, fp)
                fp.write('\n')
            

if __name__ == "__main__":
    # The date that the CAIDA dataset was collected
    caida_dataset_date = 20231101
    # The ASn of the target anycast network
    anycast_asn = '13335'
    # The ground truth dataset --JSON dictionary with origin, vp tuples as keys and a list of AS paths as values
    ground_truth_filename = '../routing_tables/output/' + anycast_asn + '_routing_presence_origin_bgpstream.json'
    # The simulator folder 
    simulator_version_folder = "input/__simulator_sigmetrics_2019__v1/"
    # The output filename of the simulated paths
    output_filename = "output/__simulator_sigmetrics_2019__v1/" + anycast_asn + "__simulated_paths_" + str(RANDOM_SAMPLE) + ".json"
    # Execute the simulations and measure time
    main(caida_dataset_date, ground_truth_filename, simulator_version_folder, output_filename)
