import pandas as pd
import json

# Reading the UNSD dataset
df = pd.read_csv('input/UNSD.csv', sep=';', keep_default_na=False)

# Grouping ISO-alpha2 codes per sub-region name
grouped_data = df.set_index('ISO-alpha2 Code')['Sub-region Name'].to_dict()

# Writing the result
# writes content to json file
with open("output/region_per_country.json", 'w+') as fp:
    json.dump(grouped_data, fp, indent=4)