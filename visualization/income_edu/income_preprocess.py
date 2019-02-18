import csv
import json
from math import ceil
import random

DATADIR = "/Users/adona/data/census/cps/"

### Helper functions

def load_csv_data(filepath, fields = "All"):
    print("Loading data from: " + filepath + "..")
    print("Loading fields: " + str(fields))
            
    with open(filepath, "r") as f:
        r = csv.DictReader(f)
        data = []
        nrows = 0
        for row in r:
            if(fields == 'All'):
                data.append(row)
            else:
                data.append({field: row[field] for field in fields})
            nrows += 1
            if (nrows % 10000 == 0):
                print("Record #: " + str(nrows))
        print("Finished loading file: " + filepath)
        print("# of records: " + str(len(data)))
    
    return data

def save_data_to_csv(data, filepath, fields = "All"):
    print("Saving data to: "+ filepath + "..")
    if fields == "All":
        fields = list(data[0].keys())
    print("Saving fields: " + str(fields))
    print("# of records to write: " + str(len(data)))

    with open(filepath, "w") as f:
        writer = csv.DictWriter(f, fieldnames=fields)
        writer.writeheader()
        nrows = 0
        for row in data:
            if (fields == "All"):
                writer.writerow(row)
            else: 
                writer.writerow({field: row[field] for field in fields})
            nrows += 1
            if (nrows % 10000 == 0):
                print("Record #: " + str(nrows))

    print("Data save finished.")

def load_JSON(filepath):
    print("Loading: " + filepath + "..")
    with open(filepath, "r") as f:
        data = json.loads(f.read())
    return data

def save_JSON(data, filepath):
    print("Saving: " + filepath + "..")
    with open(filepath, "w") as f:
        f.write(json.dumps(data, indent=2))


### Load the data
print("Loading data..")
filepath_data = DATADIR + "raw/asec16.csv"
# Variables on education, work, and income
fields = ["WORKLY", "CLASSWLY", "FULLPART", "WKSWORK2", "INCWAGE", "OCCLY", "EDUC", "ASECWT"]
data = load_csv_data(filepath_data, fields=fields) # 185,487


### Filter the data: 
print("Filtering data..")
# Only keep people who..
# .. worked last year
data = [p for p in data if p["WORKLY"] == "2"] # 92,157
# .. for wages (not self-employed)
data = [p for p in data if p["CLASSWLY"] in ["22", "25", "27", "28"]] # 83,432
# .. full time (at least 35h/week)
data = [p for p in data if p["FULLPART"] == "1"] # 67,155
# .. the entire year (at least 50 weeks)
data = [p for p in data if p["WKSWORK2"] == "6"] # 57,443


### Annotate data with occupation categories
# Load the occupation dictionary
# The dictionary is structured hierarchically by category: 
# {
#     "Management" : {
#         "10" : "Chief executives",
#         "20" : "General and operations managers",
#         "30" : "Legislators",
# ... 
print("Annotating data with occupation categories..")
filepath_occupations_dictionary = DATADIR + "dictionaries/occ_hierarchical.json"
occupations_dictionary = load_JSON(filepath_occupations_dictionary)

# Reorganize data structure to make it easier to work with:
# 1. Allocate category codes
# 2. Create flat categories and occupations dictionaries
# 3. Create a occupation -> category map
categories = {}
occupations = {}
occupation_to_category_map = {}
for (idx, category_description) in enumerate(occupations_dictionary.keys()):
  category_code = str(idx)
  categories[category_code] = category_description
  for occupation_code in occupations_dictionary[category_description]:
    occupation_description = occupations_dictionary[category_description][occupation_code]
    occupations[occupation_code] = occupation_description
    occupation_to_category_map[occupation_code] = category_code

# Annotate dataset with occupation categories
for p in data:
  p["CATLY"] = occupation_to_category_map[p["OCCLY"]]


### Remap the education field to lower granularity codes
print("Remapping the education field to lower granularity codes..")
# Define new education levels
educ_new_descriptions = ["None", "Some Primary / Secondary", "Some Highschool", 
              "Highschool Diploma", "Some College", "Associate's Degree", 
              "Bachelor's Degree", "Master's Degree", "Professional Degree", "Doctorate degree"]
# Map the old education codes to new ones
educ_old_code_groups = [ # Groups of old education codes which map to the same new, lower granularity, education code
  ["2"], # None
  ["10", "20", "30"], # Some primary/secondary
  ["40", "50", "60", "71"], # Some highschool - no degree
  ["73"], # Highschool diploma
  ["81"], # Some college - no degree
  ["91", "92"], # Associate's degree
  ["111"], # Batchelor's
  ["123"], # Master's
  ["124"], # Professional
  ["125"]] # Doctorate
educ_map = {}
for (idx, code_group) in enumerate(educ_old_code_groups):
  new_code = str(idx)
  for old_code in code_group:
    educ_map[old_code] = new_code
# Remap the data
for p in data:
  p["EDUC2"] = educ_map[p["EDUC"]]
education_levels = {str(idx):description for (idx, description) in enumerate(educ_new_descriptions)}


### Save data and dictionary
print("Saving the data and data dictionary..")

# Subsample the dataset (according to the weights ASECWT):
# 1. Normalize the weights to integers in [1,100]
for p in data:
  p["ASECWT"] = float(p["ASECWT"])   # Convert weights to float
max_w = max([p["ASECWT"] for p in data])
max_w_norm = 100
for p in data:
  p["ASECWT_norm"] = ceil(p["ASECWT"] / max_w * max_w_norm)  # Normalize

# 2. Construct an unweighted "expanded dataset" containing 
# norm_weight number of copies of each datapoint
# and subsample it on the fly
n_expanded = sum([p["ASECWT_norm"] for p in data])
n_target = 10000
subsampling_factor = n_target / n_expanded
subsampled_data = []
randseed = 109787
random.seed(randseed)
for p in data:
  norm_weight = p["ASECWT_norm"]
  for i in range(norm_weight): # for each copy
      if (random.random() < subsampling_factor): # subsample
          subsampled_data.append(p)

# Save the subsampled dataset
fields = ["EDUC2", "INCWAGE", "OCCLY", "CATLY"]
save_data_to_csv(subsampled_data, "asec16_employed_fulltime_10k.csv", fields)

# Save the data dictionary
data_dictionary = {
  "EDUC2": education_levels, 
  "OCCLY": occupations,
  "CATLY": categories
}
save_JSON(data_dictionary, "asec16_data_dictionary.json")

print("Done!")
