from matplotlib import pyplot as plt
import numpy as np
import json
import os
from pprint import pprint as pprint
# MIN_PEERING_COVERAGE = 1.0
# MIN_PREFIX_COVERAGE = 100 

# Reads content from a json file
def read_json(jsonfilename):
    with open(jsonfilename, 'r') as jsonfile:
        return json.load(jsonfile)

# Writes content to a json file
def write_json(jsonfilename, content):
    with open(jsonfilename, 'w+') as fp:
        json.dump(content, fp, indent=4)

# Finds all json files in a dir
def find_json_files(directory):
    json_files = [f for f in os.listdir(directory) if f.endswith('.json')]
    return json_files

sensitivity_results = dict()
for MIN_PEERING_COVERAGE in np.arange(0.1,1.1,0.1):
    for MIN_PREFIX_COVERAGE in range(10, 110, 10):
        print((MIN_PEERING_COVERAGE, MIN_PREFIX_COVERAGE))
        single_country_neighbors_per_as = dict()
        for file in find_json_files("./presence_of_neighbors/"):
            asn = file.split("presence_of_")[1].split("_neighbors.json")[0]
            presence_of_neighbors = read_json("./presence_of_neighbors/" + file)
            prefix_visibility_ratio_by_single_country_neighbors = dict()
            for prefix in presence_of_neighbors:
                single_country_neighbors = set()
                total_neighbors = set()
                for i, route in enumerate(presence_of_neighbors[prefix]):
                    neighbor = route["neighbor"]
                    if route["peering_locations"] is None: 
                        peering_coverage = 0 
                    else: 
                        peering_country, peering_coverage = max(route["peering_locations"].items(), key=lambda x: x[1])
                    ipv4_coverage = 0 if route["ipv4_coverage"] is None else route["ipv4_coverage"]
                    ipv6_coverage = 0 if route["ipv6_coverage"] is None else route["ipv6_coverage"]
                    
                    # A neighbor can either own prefixes and peer in multiple locations, or own prefixes but not peer, or peer but not own prefixes.
                    # We need to distinguish these three categories.
                    # First skip the entries which we cannot geolocate
                    if ipv4_coverage == 0 and ipv6_coverage == 0 and peering_coverage == 0: continue
                    # Then distinguish the use case between the following three categories
                    if ipv4_coverage == 0 and ipv6_coverage == 0:
                        if peering_coverage >= MIN_PEERING_COVERAGE:
                            single_country_neighbors.add(neighbor)
                    elif peering_coverage == 0:
                        if ipv4_coverage >= MIN_PREFIX_COVERAGE or ipv6_coverage >= MIN_PREFIX_COVERAGE:
                            single_country_neighbors.add(neighbor)
                    elif (ipv4_coverage >= MIN_PREFIX_COVERAGE or ipv6_coverage >= MIN_PREFIX_COVERAGE) and peering_coverage >= MIN_PEERING_COVERAGE:
                        ipv4_country = route["ipv4_country"]
                        ipv6_country = route["ipv6_country"]
                        if ipv4_country and ipv6_country and ipv4_country == ipv6_country == peering_country:
                            single_country_neighbors.add(neighbor)
                        elif not ipv4_country and ipv6_country == peering_country:
                            single_country_neighbors.add(neighbor)
                        elif not ipv6_country and ipv4_country == peering_country:
                            single_country_neighbors.add(neighbor)

                    total_neighbors.add(neighbor)
                
                prefix_visibility_ratio_by_single_country_neighbors[prefix] = len(single_country_neighbors)/len(total_neighbors)
            
            average_value = sum(prefix_visibility_ratio_by_single_country_neighbors.values()) / len(prefix_visibility_ratio_by_single_country_neighbors)
            single_country_neighbors_per_as[asn] = average_value
        sensitivity_results[str((MIN_PEERING_COVERAGE*100, MIN_PREFIX_COVERAGE))] = single_country_neighbors_per_as
write_json("sensitivity_analysis/sensitivity_analysis.json", sensitivity_results)

triplets = list()
for entry in sensitivity_results:
    x = int(float(entry.strip("()").split(", ")[0]))
    y = int(entry.strip("()").split(", ")[1])
    average = sum(sensitivity_results[entry].values()) / len(sensitivity_results[entry])
    triplets.append((x, y, average))

# Extracting unique values for rows and columns
rows = sorted(set(item[0] for item in triplets))
cols = sorted(set(item[1] for item in triplets))
print(rows)
print(cols)
# Creating a 2D array filled with zeros
num_rows = len(rows)
num_cols = len(cols)
matrix = [[0.0] * num_cols for _ in range(num_rows)]

# Populating the 2D array with the given values
for item in triplets:
    row_index = rows.index(item[0])
    col_index = cols.index(item[1])
    matrix[row_index][col_index] = item[2]

# Convert the list of lists into a NumPy array for better visualization
heatmap_data = np.array(matrix)

# Create a heatmap
fig, ax = plt.subplots()
FONT_SIZE = 13

im = plt.imshow(heatmap_data, cmap='rainbow', interpolation='nearest', aspect='auto')
# Add a colorbar to the right of the heatmap
cbar = plt.colorbar(im)
cbar.set_label('% of ASes who belong to a single country', fontsize=FONT_SIZE)
# Reverse the y-axis
plt.gca().invert_yaxis()
# Set axis labels based on the row and column indices
plt.xticks(np.arange(len(cols)), cols, fontsize=FONT_SIZE)
plt.yticks(np.arange(len(rows))[::-1], rows[::-1], fontsize=FONT_SIZE)
# Add actual values in the colored cells
for i in range(len(rows)):
    for j in range(len(cols)):
        text = plt.text(j, i, f'{heatmap_data[i, j]:.2f}', ha='center', va='center', color='black', fontsize=FONT_SIZE - 3)
# Add axis titles
plt.xlabel('Peering Coverage', fontsize=FONT_SIZE)
plt.ylabel('Prefix Coverage', fontsize=FONT_SIZE)

plt.tight_layout()
fig.savefig("sensitivity_analysis/sensitivity_analysis.png")

