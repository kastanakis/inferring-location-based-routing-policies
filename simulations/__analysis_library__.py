import csv
import json
import numpy as np
import matplotlib.pyplot as plt
from ast import literal_eval as make_tuple
from pprint import pprint as pprint
########################################################################
########################## INPUT #######################################
# Read the input datasets
def read_input(simulations, ground_truth, as2rel_mapping):
    # Initialize two dicts
    sims_dict_best = dict()
    sims_dict_candidate = dict()
    sims_dict_strong_candidate = dict()
    # Unbox the as2rel dataset
    as2rel_dict = read_topology(as2rel_mapping)
    # Unbox the simulations dataset
    with open(simulations, 'r') as jsonfile:
        for line in jsonfile:
            simulation = json.loads(line)  # read the json file per line

            # Create a tuple for the AS-pair, this will be used as key later
            best_path = simulation['best_path']
            candidate_paths = simulation['candidate_paths']
            origin_as = int(best_path[-1])
            vp = int(best_path[0])
            key = str((origin_as, vp))
            sims_dict_best[key] = best_path
            sims_dict_candidate[key] = candidate_paths
            # Add in a dictionary the candidate paths which have the same path length and AS-relationship with the best path
            sims_dict_strong_candidate[key] = []
            for candidate in candidate_paths:
                if len(candidate) == len(best_path) and path2rel(best_path, as2rel_dict) == path2rel(candidate, as2rel_dict):
                    sims_dict_strong_candidate[key].append(candidate)
    
    unique_paths = dict()
    geoaware_unique_paths = dict()
    full_json = read_json(ground_truth)
    for prefix in full_json:
        paths = full_json[prefix]
        for path_idx in paths:
            path = path_idx.split(" ")
            path = list(map(int, path))
            origin_as = int(path[-1])
            vp = int(path[0])
            key = str((origin_as, vp))
            if key not in unique_paths:
                unique_paths[key] = list()
                geoaware_unique_paths[key] = list()
            if path not in unique_paths[key]:
                unique_paths[key].append(path)
            for geolocation_info in paths[path_idx]:
                if geolocation_info['vp_ip'] not in geoaware_unique_paths[key]:
                    geoaware_unique_paths[key].append(geolocation_info['vp_ip'])

    return (sims_dict_best, sims_dict_strong_candidate, sims_dict_candidate, unique_paths, geoaware_unique_paths, as2rel_dict)

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

# Writes content to a json file
def write_json(jsonfilename, content):
    with open(jsonfilename, 'w+') as fp:
        json.dump(content, fp, indent=4)
        
# Reads content from a json file
def read_json(jsonfilename):
    with open(jsonfilename, 'r') as jsonfile:
        return json.load(jsonfile)

########################### END ########################################
########################################################################

########################################################################
######################## EVALUATION ####################################
# Returns true if the list a is nested
def is_nested_list(a):
    return any(isinstance(i, list) for i in a)

# Single path match
def is_a_path_match(path1, path2):
    if path1 == path2 and path1 is not None:
        return 1
    return 0

# Translates a list of ASn paths to a list of relationship paths
def paths2rel(paths, as2rel_dict):
    rel_path_list_of_lists = list()
    for path in paths:
        rel_path = path2rel(path, as2rel_dict)
        rel_path_list_of_lists.append(rel_path)
    return rel_path_list_of_lists

# # Translates an ASn path to a relationship path
def path2rel(patth, rels_dict):
    rel_path = list()
    path = patth[:]  # We need a shallow copy for this process
    # While we still have asns in the path (at least two), this means we still have >1 relationships
    while(len(path) > 1):
        # Extract the first ASn and get its rel with the second
        head = path[0]
        path.remove(head)
        second = path[0]
        if(head in rels_dict.keys()):
            vp_rels = rels_dict[head]
        else:
            return []  # if we don't find the relationship just return [] for error checking
        for rel in vp_rels:
            if(rel[0] == second):
                rel_path.append(rel[1])
                break
    return rel_path

# Exact path match internal
def exact_path_match_candidate_path_vs_true_path_list(candidate_path, true_paths):
    # ...check whether it exists in the ground truth paths...
    for true_path in true_paths:
        if(is_a_path_match(candidate_path, true_path)):
            # increase both the exact paths counter and the total paths counter
            return(1, 1)
        # ...if not, continue with the rest of the candidate paths...
        else:
            continue
    # If we reached this point in the code, this means that none of the candidates is in the ground truth.
    return (0, 1)  # increase only the total paths counter

# Exact path match
def exact_path_match(sims_dict, truth_dict):
    # Do the exact path match comparison
    exact_paths_counter = 0
    total_paths_counter = 0
    for as_pairs in sims_dict:
        if(is_nested_list(sims_dict[as_pairs])):
            # For each simulated path...
            for candidate_path in sims_dict[as_pairs]:
                (epc, tpc) = exact_path_match_candidate_path_vs_true_path_list(
                    candidate_path, truth_dict[as_pairs])
                # If at least one path returns 1, then break the loop, since we found the best candidate
                if epc == 1:
                    break
        else:
            candidate_path = sims_dict[as_pairs]
            (epc, tpc) = exact_path_match_candidate_path_vs_true_path_list(
                candidate_path, truth_dict[as_pairs])
        # Increase the respective counters with the returned values from the above function
        exact_paths_counter += epc
        total_paths_counter += tpc

    exact_path_match_ratio = exact_paths_counter / total_paths_counter
    return exact_path_match_ratio

# Vantage point first hop match internal
def first_hop_path_match_candidate_path_vs_true_path_list(candidate_path, true_paths):
    for true_path in true_paths:
        # If you find that the first hop is the same in the sim path with a true path then return 1, 1
        if((len(true_path) >= 2 and len(candidate_path) >= 2) and is_a_path_match(candidate_path[1], true_path[1])):
            return(1, 1)
    # If we didnt find a match then return 0, 1
    return(0, 1)

# Vantage point first hop match
def first_hop_path_match(sims_dict, truth_dict):
    # Do the first hop match comparison
    first_hop_paths_counter = 0
    total_paths_counter = 0
    for as_pairs in sims_dict:
        if(is_nested_list(sims_dict[as_pairs])):
            # For each simulated path...
            for candidate_path in sims_dict[as_pairs]:
                (epc, tpc) = first_hop_path_match_candidate_path_vs_true_path_list(
                    candidate_path, truth_dict[as_pairs])
                # If at least one path returns 1, then break the loop, since we found the best candidate
                if epc == 1:
                    break
        else:
            candidate_path = sims_dict[as_pairs]
            (epc, tpc) = first_hop_path_match_candidate_path_vs_true_path_list(
                candidate_path, truth_dict[as_pairs])
        # Increase the respective counters with the returned values from the above function
        first_hop_paths_counter += epc
        total_paths_counter += tpc

    first_hop_path_match_ratio = first_hop_paths_counter / total_paths_counter
    return first_hop_path_match_ratio

# ASn to Relationship path match
def rel_hit_match(sims_dict, truth_dict, as2rel_dict):
    rel_hit_match_counter = 0
    total_paths_counter = 0
    for as_pairs in sims_dict:
        if(is_nested_list(sims_dict[as_pairs])):
            # For each simulated path...
            for candidate_path in sims_dict[as_pairs]:
                (epc, tpc) = exact_path_match_candidate_path_vs_true_path_list(
                    path2rel(candidate_path, as2rel_dict), paths2rel(truth_dict[as_pairs], as2rel_dict))
                # If at least one path returns 1, then break the loop, since we found the best candidate
                if epc == 1:
                    break
        else:
            candidate_path = sims_dict[as_pairs]
            (epc, tpc) = exact_path_match_candidate_path_vs_true_path_list(
                path2rel(candidate_path, as2rel_dict), paths2rel(truth_dict[as_pairs], as2rel_dict))
        # Increase the respective counters with the returned values from the above function
        rel_hit_match_counter += epc
        total_paths_counter += tpc

    rel_hit_match_ratio = rel_hit_match_counter / total_paths_counter
    return rel_hit_match_ratio

# Path length match internal
def path_length_match_candidate_path_vs_true_path_list(candidate_path, true_paths):
    for true_path in true_paths:
        # If you find that the path length is the same in the sim path with a true path then return 1, 1
        if(is_a_path_match(len(candidate_path), len(true_path))):
            return(1, 1)
    # If we didnt find a match then return 0, 1
    return(0, 1)

# Path length match
def path_length_match(sims_dict, truth_dict):
    path_length_match_counter = 0
    total_paths_counter = 0
    for as_pairs in sims_dict:
        if(is_nested_list(sims_dict[as_pairs])):
            # For each simulated path...
            for candidate_path in sims_dict[as_pairs]:
                (epc, tpc) = path_length_match_candidate_path_vs_true_path_list(
                    candidate_path, truth_dict[as_pairs])
                # If at least one path returns 1, then break the loop, since we found the best candidate
                if epc == 1:
                    break
        else:
            candidate_path = sims_dict[as_pairs]
            (epc, tpc) = path_length_match_candidate_path_vs_true_path_list(
                candidate_path, truth_dict[as_pairs])
        # Increase the respective counters with the returned values from the above function
        path_length_match_counter += epc
        total_paths_counter += tpc

    path_length_match_ratio = path_length_match_counter / total_paths_counter
    return path_length_match_ratio

# Jaccard Similarity Internal
def jaccard_similarity_internal(candidate_path, true_path):
    s1 = set(candidate_path)
    s2 = set(true_path)
    return float(len(s1.intersection(s2)) / len(s1.union(s2)))

# Jaccard Similarity
def jaccard_similarity(sims_dict, truth_dict):
    best_score_aggregator = 0
    total_paths_counter = 0
    for as_pair_sims in sims_dict:
        best_score_over_candidate_paths = 0
        if(is_nested_list(sims_dict[as_pair_sims])):
            for candidate_path in sims_dict[as_pair_sims]:
                best_score = 0
                for path in truth_dict[as_pair_sims]:
                    current_score = jaccard_similarity_internal(
                        candidate_path, path)
                    if current_score > best_score:
                        best_score = current_score
                if(best_score > best_score_over_candidate_paths):
                    best_score_over_candidate_paths = best_score
        else:
            best_score = 0
            candidate_path = sims_dict[as_pair_sims]
            for path in truth_dict[as_pair_sims]:
                current_score = jaccard_similarity_internal(
                    candidate_path, path)
                if current_score > best_score:
                    best_score = current_score
            if(best_score > best_score_over_candidate_paths):
                best_score_over_candidate_paths = best_score
        best_score_aggregator += best_score_over_candidate_paths
        total_paths_counter += 1
    jaccard_similarity_score = best_score_aggregator / total_paths_counter
    return jaccard_similarity_score
########################### END ########################################
########################################################################


########################################################################
###################### EXTRA ANALYSIS ##################################
# Create a line with the best paths, candidate paths and ground truth paths
def collect_exact_path_misses(sims_dict_best, sims_dict_strong_candidate, sims_dict_candidate, truth_dict):
    objects_list = list()
    # For all sim entries ... 
    for as_pair in sims_dict_best:  
        # ... do the exact path match comparison ...
        best_path = sims_dict_best[as_pair]
        (epc, tpc) = exact_path_match_candidate_path_vs_true_path_list(best_path, truth_dict[as_pair])

        # ... and log only exact path misses!
        if(epc == 0):
            if (truth_dict[as_pair] == []):
                continue
            object = dict()
            object["best_path"] = best_path
            object["candidate_paths"] = sims_dict_strong_candidate[as_pair]
            object["all_valid_paths"] = sims_dict_candidate[as_pair]
            object["ground_truth_paths"] = truth_dict[as_pair]

            objects_list.append(object)
    return objects_list

# Returns the first index for which: best path != ground truth path
def find_index_of_first_broken_link(sims_path, true_path):
    for idx, i in enumerate(sims_path):
        if sims_path[idx] != true_path[idx]:
            return idx
    return -1
########################### END ########################################
########################################################################