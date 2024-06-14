from __analysis_library__ import *
import random
import geoip2.database
from geopy.distance import geodesic

def geolocate_per_ip_city_level(ip):
    with geoip2.database.Reader('../geolocation/maxmind/input/GeoLite2-City_20240119/GeoLite2-City.mmdb') as city_reader:
        response_city = city_reader.city(ip)
        return response_city.location.latitude, response_city.location.longitude

def geolocate_per_ip_country_level(ip):
    with geoip2.database.Reader('../geolocation/maxmind/input/GeoLite2-Country_20231103/GeoLite2-Country.mmdb') as country_reader:
        response_country = country_reader.country(ip)
        return response_country.country.iso_code

def resimulate_with_as_level_catchment_awareness(anycast_asn, sims_dict_candidate, geoaware_truth_dict, as2rel_dict, as_level_catchment_data):
    sims_dict_best_new = dict()
    sims_dict_candidate_new = dict()
    anycast_as_relationships = dict()
    for rel in as2rel_dict[int(anycast_asn)]:
        anycast_as_relationships[rel[0]] = rel[1]
    # For each origin, vp pair find a random IP of the source and geolocate to the country-level granularity
    for tuple in sims_dict_candidate:
        random_source_ip = random.choice(geoaware_truth_dict[tuple])
        src_presence = geolocate_per_ip_country_level(random_source_ip)
        # Then find all the unique penultimate ASes in the AS-path for that specific source AS country.
        # Utilize the AS-level catchment dataset for this
        unique_penultimate_ases_in_src_country = set()
        for prefix in as_level_catchment_data[anycast_asn]:
            for region in as_level_catchment_data[anycast_asn][prefix]:
                penultimate_ases = list()
                if src_presence in as_level_catchment_data[anycast_asn][prefix][region]:
                    penultimate_ases = as_level_catchment_data[anycast_asn][prefix][region][src_presence]
                unique_penultimate_ases_in_src_country.update(penultimate_ases)
        unique_penultimate_ases_in_src_country = list(unique_penultimate_ases_in_src_country)
        # Discard from all possible paths the ones in which the penultimate AS in the path doesnt exist in the respective country catchment
        all_possible_paths = sims_dict_candidate[tuple]
        sims_dict_candidate_new[tuple] = list()
        for possible_path in all_possible_paths:
            if possible_path[-2] in unique_penultimate_ases_in_src_country:
                sims_dict_candidate_new[tuple].append(possible_path)
        # If the returned list is empty, then fall back to the original simulations
        if not sims_dict_candidate_new[tuple]:
            sims_dict_candidate_new[tuple] = sims_dict_candidate[tuple]
        # Rerun the BGP selection process for the remaining candidate paths
        source_as_relationships = dict()
        vp = int(make_tuple(tuple)[1])
        for rel in as2rel_dict[vp]:
            source_as_relationships[rel[0]] = rel[1]
        best_path = sims_dict_candidate_new[tuple][0]
        for path in sims_dict_candidate_new[tuple]:
            if source_as_relationships[path[1]] < source_as_relationships[best_path[1]]:
                best_path = path
            elif source_as_relationships[path[1]] == source_as_relationships[best_path[1]]:
                if len(path) < len(best_path):
                    best_path = path   
        sims_dict_best_new[tuple] = best_path
    # Return the best path and all the valid paths that remained after the cutoff process 
    return sims_dict_best_new, sims_dict_candidate_new

def resimulate_with_pop_awareness(anycast_asn, sims_dict_candidate, geoaware_truth_dict, as2rel_dict, asn_per_pop, pop_per_asn):
    sims_dict_best_new = dict()
    sims_dict_candidate_new = dict()
    pops_per_anycast_asn = pop_per_asn[anycast_asn]
    anycast_as_relationships = dict()
    for rel in as2rel_dict[int(anycast_asn)]:
        anycast_as_relationships[rel[0]] = rel[1]
    # For each origin, vp pair find a random IP of the source and geolocate to lon, lat coordinates
    for tuple in sims_dict_candidate:
        random_source_ip = random.choice(geoaware_truth_dict[tuple])
        src_presence = geolocate_per_ip_city_level(random_source_ip)
        # Then find the closest pop from the ones in which the anycast AS exists utilizing the geodesic distance
        minimum_distance = 100000000000
        closest_pop = -1
        for pop in pops_per_anycast_asn:
            pop = str(pop)
            if asn_per_pop[pop]['as_members']:
                pop_presence = asn_per_pop[pop]['coord']
                distance = geodesic(src_presence, pop_presence).kilometers
                if distance < minimum_distance:
                    minimum_distance = distance
                    closest_pop = pop
        # From the closest pop extract all the as members
        possible_valid_asns = asn_per_pop[closest_pop]['as_members']
        # Now, keep only the asns which are connected with the anycast asn
        connected_asns_in_closest_pop = [asn for asn in possible_valid_asns if asn in anycast_as_relationships]
        # Discard from all possible paths the ones in which the penultimate AS in the path doesnt exist in the closest pop found earlier
        all_possible_paths = sims_dict_candidate[tuple]
        sims_dict_candidate_new[tuple] = list()
        for possible_path in all_possible_paths:
            if possible_path[-2] in connected_asns_in_closest_pop:
                sims_dict_candidate_new[tuple].append(possible_path)
        # If the returned list is empty, then fall back to the original simulations
        if not sims_dict_candidate_new[tuple]:
            sims_dict_candidate_new[tuple] = sims_dict_candidate[tuple]
        # Rerun the BGP selection process for the remaining candidate paths
        source_as_relationships = dict()
        vp = int(make_tuple(tuple)[1])
        for rel in as2rel_dict[vp]:
            source_as_relationships[rel[0]] = rel[1]
        best_path = sims_dict_candidate_new[tuple][0]
        for path in sims_dict_candidate_new[tuple]:
            if source_as_relationships[path[1]] < source_as_relationships[best_path[1]]:
                best_path = path
            elif source_as_relationships[path[1]] == source_as_relationships[best_path[1]]:
                if len(path) < len(best_path):
                    best_path = path   
        sims_dict_best_new[tuple] = best_path
    # Return the best path and all the valid paths that remained after the cutoff process 
    return sims_dict_best_new, sims_dict_candidate_new

def resimulate_without_as_rel_awareness(anycast_asn, sims_dict_candidate, as2rel_dict):
    sims_dict_best_new = dict()
    anycast_as_relationships = dict()
    for rel in as2rel_dict[int(anycast_asn)]:
        anycast_as_relationships[rel[0]] = rel[1]
    # For each origin, vp pair rerun the sim process without the GR clause
    for tuple in sims_dict_candidate:
        source_as_relationships = dict()
        vp = int(make_tuple(tuple)[1])
        for rel in as2rel_dict[vp]:
            source_as_relationships[rel[0]] = rel[1]
        best_path = sims_dict_candidate[tuple][0]
        for path in sims_dict_candidate[tuple]:
            if len(path) < len(best_path):
                best_path = path   
        sims_dict_best_new[tuple] = best_path
    return sims_dict_best_new, sims_dict_candidate

def plot_best_vs_candidate(filename, best_path_perf, candidate_paths_perf):
    print(best_path_perf)
    print(candidate_paths_perf)
    # Set plot characteristics
    FONT_SIZE = 13
    plt.rcParams.update({'font.size': FONT_SIZE})
    fig, ax = plt.subplots()
    ax.grid()
    width = 0.35
    x = np.arange(len(best_path_perf))

    # Plot data
    bp1 = plt.bar(x - width/2, best_path_perf, width, capsize=3,
                  edgecolor='black', label='Single Best Path')
    bp3 = plt.bar(x + width/2, candidate_paths_perf, width,
                  capsize=3, edgecolor='black', label='All Valid Paths')
    ax.set(xlabel='Metrics', ylabel='Prediction Ratio', ylim=[0.00, 1.00])
    ax.set_xticks(range(len(best_path_perf)))
    fig.tight_layout()
    ax.yaxis.set_major_locator(plt.MaxNLocator(10))
    ax.set_xticklabels(['Exact \nPath', 'AS-to-Rel \nPath',
                       'Path \nLength', 'Jaccard \nSimilarity'], ha='center')
    ax.legend(loc="lower right")
    
    # Save figure into png file
    fig.savefig(filename)

if __name__ == "__main__":
    # Input arguments and datasets
    version = 'v1'    
    date = '20231101'
    # The ASn of the target anycast network
    anycast_asn = '13335'
    # The ground truth dataset --JSON dictionary with origin, vp tuples as keys and a list of AS paths as values
    # ground_truth = '../routing_tables/output/' + anycast_asn + '_routing_presence_origin_bgpstream.json'
    # ground_truth = 'output/merged_routing_tables/all_observed_anycast_prefixes_and_one_random_as_path_per_prefix.json'
    ground_truth = 'output/merged_routing_tables/all_observed_anycast_prefixes_and_one_random_as_path_per_prefix_selective_announcements_only.json'
    # Simulations path
    simulations = "output/__simulator_sigmetrics_2019__v1/all_anycast_ASes_simulated_paths_selective_announcements_only.json"
    # Topology file
    as2rel_mapping = "../as_graph/" + date + ".as-rel2.txt"
    # PoP information
    asn_per_pop = read_json("../geolocation/peeringdb/output/asn_per_pop_map.json")
    pop_per_asn = read_json("../geolocation/peeringdb/output/pop_per_asn_map.json")
    # AS-level Catchment
    as_level_catchment_data = read_json("../anycast_catchment/output/as_level_anycast_catchment_per_region.json")
   
    # Read the ground truth files and the sims files and the AS-rel topology dataset
    (sims_dict_best, sims_dict_strong_candidate, sims_dict_candidate, truth_dict, geoaware_truth_dict,
     as2rel_dict) = read_input(simulations, ground_truth, as2rel_mapping)

    # # Resimulate the AS paths given PoP information and source IP geolocation information
    pop_aware_sims_dict_best, pop_aware_sims_dict_candidate = resimulate_with_pop_awareness(anycast_asn, sims_dict_candidate, geoaware_truth_dict, as2rel_dict, asn_per_pop, pop_per_asn)
    as_level_catchment_aware_sims_dict_best, as_level_catchment_aware_sims_dict_candidate = resimulate_with_as_level_catchment_awareness(anycast_asn, sims_dict_candidate, geoaware_truth_dict, as2rel_dict, as_level_catchment_data)
    no_gr_clause_best, no_gr_clause_all = resimulate_without_as_rel_awareness(anycast_asn, sims_dict_candidate, as2rel_dict)

    # Calculate the performance for the best path and candidate paths scenarios
    best_path_perf = [
        exact_path_match(sims_dict_best, truth_dict),
        rel_hit_match(sims_dict_best, truth_dict, as2rel_dict),
        path_length_match(sims_dict_best, truth_dict),
        jaccard_similarity(sims_dict_best, truth_dict),
    ]

    candidate_paths_perf = [
        exact_path_match(sims_dict_candidate, truth_dict),
        rel_hit_match(sims_dict_candidate, truth_dict, as2rel_dict),
        path_length_match(sims_dict_candidate, truth_dict),
        jaccard_similarity(sims_dict_candidate, truth_dict),
    ]

    # Plot the simulator's best path performance against the candidate paths performance and write misinferences to a file
    plot_best_vs_candidate("output/__simulator_sigmetrics_2019__v1/all_anycast_ASes_vanilla_model_performance_analysis_selective_announcements_only.png",
                           best_path_perf, candidate_paths_perf)
    
    # Calculate the performance for the best path and candidate paths scenarios
    pop_aware_best_path_perf = [
        exact_path_match(pop_aware_sims_dict_best, truth_dict),
        rel_hit_match(pop_aware_sims_dict_best, truth_dict, as2rel_dict),
        path_length_match(pop_aware_sims_dict_best, truth_dict),
        jaccard_similarity(pop_aware_sims_dict_best, truth_dict),
    ]

    pop_aware_candidate_paths_perf = [
        exact_path_match(pop_aware_sims_dict_candidate, truth_dict),
        rel_hit_match(pop_aware_sims_dict_candidate, truth_dict, as2rel_dict),
        path_length_match(pop_aware_sims_dict_candidate, truth_dict),
        jaccard_similarity(pop_aware_sims_dict_candidate, truth_dict),
    ]

    # Plot the simulator's best path performance against the candidate paths performance and write misinferences to a file
    plot_best_vs_candidate("output/__simulator_sigmetrics_2019__v1/all_anycast_ASes_pop_aware_model_performance_analysis_selective_announcements_only.png",
                           pop_aware_best_path_perf, pop_aware_candidate_paths_perf)

    # Calculate the performance for the best path and candidate paths scenarios
    as_level_catchment_aware_best_path_perf = [
        exact_path_match(as_level_catchment_aware_sims_dict_best, truth_dict),
        rel_hit_match(as_level_catchment_aware_sims_dict_best, truth_dict, as2rel_dict),
        path_length_match(as_level_catchment_aware_sims_dict_best, truth_dict),
        jaccard_similarity(as_level_catchment_aware_sims_dict_best, truth_dict),
    ]


    as_level_catchment_aware_candidate_paths_perf = [
        exact_path_match(as_level_catchment_aware_sims_dict_candidate, truth_dict),
        rel_hit_match(as_level_catchment_aware_sims_dict_candidate, truth_dict, as2rel_dict),
        path_length_match(as_level_catchment_aware_sims_dict_candidate, truth_dict),
        jaccard_similarity(as_level_catchment_aware_sims_dict_candidate, truth_dict),
    ]

    # Plot the simulator's best path performance against the candidate paths performance and write misinferences to a file
    plot_best_vs_candidate("output/__simulator_sigmetrics_2019__v1/all_anycast_ASes_as_level_catchment_aware_model_performance_analysis_selective_announcements_only.png",
                           as_level_catchment_aware_best_path_perf, as_level_catchment_aware_candidate_paths_perf)
    
    # Calculate the performance for the best path and candidate paths scenarios
    no_gr_best_path_perf = [
        exact_path_match(no_gr_clause_best, truth_dict),
        rel_hit_match(no_gr_clause_best, truth_dict, as2rel_dict),
        path_length_match(no_gr_clause_best, truth_dict),
        jaccard_similarity(no_gr_clause_best, truth_dict),
    ]


    no_gr_candidate_paths_perf = [
        exact_path_match(no_gr_clause_all, truth_dict),
        rel_hit_match(no_gr_clause_all, truth_dict, as2rel_dict),
        path_length_match(no_gr_clause_all, truth_dict),
        jaccard_similarity(no_gr_clause_all, truth_dict),
    ]

    # Plot the simulator's best path performance against the candidate paths performance and write misinferences to a file
    plot_best_vs_candidate("output/__simulator_sigmetrics_2019__v1/all_anycast_ASes_no_gr_model_performance_analysis_selective_announcements_only.png",
                           no_gr_best_path_perf, no_gr_candidate_paths_perf)

    