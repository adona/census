# Developed in Python 3.x
import json
import csv

DATADIR = "/Users/adona/data/census/timeuse/"
RELEVANT_FIELDS_HOUSEHOLD = ["HH_SIZE", "FAMINCOME"]
RELEVANT_FIELDS_PERSON = ["DAY", "AGE", "SEX", "RACE", "MARST", "HH_NUMOWNKIDS", 
  "LIVING_WITH", "EDUC", "EMPSTAT", "FULLPART", "OCC"]
RELEVANT_FIELDS_ACTIVITY = ["ACTIVITY3", "CATEGORY", "START"]

def add_household_fields(households):
  for household in households:
    respondent = household["persons"][0]
    for field in RELEVANT_FIELDS_HOUSEHOLD:
      respondent[field] = household[field]

def add_living_with_field(households, data_dictionary):
  for household in households:
    respondent = household["persons"][0]
    # Collect information about other members in the household
    partner = None
    parents = []
    ages = {
      "children": [],
      "grandchildren": []
    }
    n_relationship = {
      "siblings": 0,
      "other_relatives": 0,
      "housemates": 0
    }
    other_hh_members = household["persons"][1:]
    for other_hh_member in other_hh_members:
      relationship = data_dictionary["RELATE"][other_hh_member["RELATE"]]
      age = int(other_hh_member["AGE"])
      if relationship in ["Spouse", "Unmarried partner"]:
        partner = relationship
      elif relationship == "Child":
        ages["children"].append(age)
      elif relationship == "Grandchild":
        ages["grandchildren"].append(age)
      elif relationship == "Parent":
        parent_sex = data_dictionary["SEX"][other_hh_member["SEX"]]
        parents.append("mother" if parent_sex == "Female" else "father")
      elif relationship == "Sibling":
        n_relationship["siblings"] += 1
      elif relationship == "Other relative":
        n_relationship["other_relatives"] += 1
      elif relationship == "Housemate":
        n_relationship["housemates"] += 1
    # Put together a living_with variable, adding fields only where there was relevant info
    living_with = {}
    if partner != None:
      living_with["partner"] = partner
    for relationship in ages:
      if len(ages[relationship]) > 0:
        living_with[relationship] = ages[relationship]
    if len(parents) > 0:
      living_with["parents"] = parents
    for relationship in n_relationship:
      if n_relationship[relationship] > 0:
        living_with[relationship] = n_relationship[relationship]
    # Add the living_with variable to the respondent
    respondent["LIVING_WITH"] = living_with
    
def get_respondents(households):
  return [household["persons"][0] for household in households]

def convert_fields_to_descriptions(persons, data_dictionary):
  for field in RELEVANT_FIELDS_PERSON + RELEVANT_FIELDS_HOUSEHOLD:
    if field in data_dictionary:
      if data_dictionary[field] == "int":
        for person in persons:
          person[field] = int(person[field])
      elif data_dictionary[field] == "string":
        break # Nothing to do
      else: # categorical
        for person in persons:
          code = person[field]
          person[field] = data_dictionary[field][code]        

def recode_activity_field(persons, filepath_activity_map, filepath_activities_by_category):
  activity_map = load_csv(filepath_activity_map)

  # Extract new activities, organized by category, and save to file
  categories = [entry["new_category"] for entry in activity_map]
  categories = deduplicate_list(categories)
  activities_by_category = []
  for category in categories:
    category_activities = [entry["new_activity"] for entry in activity_map if entry["new_category"] == category]
    category_activities = deduplicate_list(category_activities)
    activities_by_category.append({
      "category": category,
      "activities": category_activities
    })
  save_JSON(activities_by_category, filepath_activities_by_category)

  # Create map of old_activity -> new_activity
  activity_map_dict = {}
  for entry in activity_map:
    code = int(entry["code"])
    activity_map_dict[code] = {
      "new_activity": entry["new_activity"],
      "new_category": entry["new_category"]
    }
  activity_map = activity_map_dict

  # Recode activity field
  for person in persons:
    for activity in person["activities"]:
      code = int(activity["ACTIVITY"])
      activity["ACTIVITY3"] = activity_map[code]["new_activity"]
      activity["CATEGORY"] = activity_map[code]["new_category"]    

def extract_relevant_fields_only(persons):
  persons_relevant = []
  for p in persons:
    p_relevant = {field:p[field] for field in RELEVANT_FIELDS_PERSON + RELEVANT_FIELDS_HOUSEHOLD}
    p_relevant["activities"] = [
      {field:activity[field] for field in RELEVANT_FIELDS_ACTIVITY}
        for activity in p["activities"]]
    persons_relevant.append(p_relevant)
  return persons_relevant

### Helper functions

def deduplicate_list(list_in):
  # Deduplicate list while maintaining order based on when elements were first encountered
  # (alternative to list(set(list_in)) which does not maintain order).
  unique_entries = set()
  list_out = []
  for entry in list_in:
    if entry not in unique_entries:
      unique_entries.add(entry)
      list_out.append(entry)
  return list_out


def load_JSON(filepath):
    print("Loading: " + filepath + "..")
    with open(filepath, "r") as f:
      data = json.loads(f.read())
    return data

def save_JSON(data, filepath):
    print("Saving: " + filepath + "..")
    with open(filepath, "w") as f:
      f.write(json.dumps(data))

def load_csv(filepath):
    print("Loading: " + filepath + "..")            
    with open(filepath, "r") as f:
      r = csv.DictReader(f)
      data = [row for row in r]
    return data

###

filepath_in = DATADIR + "raw/atus16.json"
filepath_dictionary = DATADIR + "dictionaries/atus16_dictionary2.json"
filepath_activity_map = DATADIR + "dictionaries/activities_map3.csv"
filepath_activities_by_category = DATADIR + "dictionaries/activities_by_category3.json"

households = load_JSON(filepath_in)
data_dictionary = load_JSON(filepath_dictionary)
add_household_fields(households)
add_living_with_field(households, data_dictionary)
persons = get_respondents(households)
convert_fields_to_descriptions(persons, data_dictionary)
recode_activity_field(persons, filepath_activity_map, filepath_activities_by_category)

persons = extract_relevant_fields_only(persons)

filepath_out = "atus16.json"
save_JSON(persons, filepath_out)
