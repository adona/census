# Developed in Python 3.x
import json
import csv

DATADIR = "/Users/adona/data/census/timeuse/"
RELEVANT_FIELDS_HOUSEHOLD = ["HH_SIZE"]
RELEVANT_FIELDS_PERSON = ["DAY", "AGE", "SEX", "RACE", "MARST", "LIVING_WITH", "EDUC", "EMPSTAT", "FULLPART", "OCC"]
RELEVANT_FIELDS_ACTIVITY = ["ACTIVITY3", "CATEGORY", "START"]

def add_household_fields(households):
  for household in households:
    for field in RELEVANT_FIELDS_HOUSEHOLD:
      household["persons"][0][field] = household[field]

def add_living_with_field(households, data_dictionary):
  for household in households:
    respondent = household["persons"][0]
    respondent["LIVING_WITH"] = {}
    for other_hh_member in household["persons"][1:]:
      if other_hh_member["RELATE"] in ["020", "021"]:
        respondent["LIVING_WITH"]["partner"] = data_dictionary["RELATE"][other_hh_member["RELATE"]]
      elif other_hh_member["RELATE"] in ["022", "027", "040"]:
        if "children" not in respondent["LIVING_WITH"]:
          respondent["LIVING_WITH"]["children"] = []
        respondent["LIVING_WITH"]["children"].append(int(other_hh_member["AGE"]))
      elif other_hh_member["RELATE"] == "023":
        if "grandchildren" not in respondent["LIVING_WITH"]:
          respondent["LIVING_WITH"]["grandchildren"] = []
        respondent["LIVING_WITH"]["grandchildren"].append(int(other_hh_member["AGE"]))
      elif other_hh_member["RELATE"] == "024":
        if "parents" not in respondent["LIVING_WITH"]:
          respondent["LIVING_WITH"]["parents"] = []
        if other_hh_member["SEX"] == "01":
          respondent["LIVING_WITH"]["parents"].append("father")
        else:
          respondent["LIVING_WITH"]["parents"].append("mother")
      elif other_hh_member["RELATE"] == "025":
        if "siblings" not in respondent["LIVING_WITH"]:
          respondent["LIVING_WITH"]["siblings"] = 0
        respondent["LIVING_WITH"]["siblings"] += 1
      elif other_hh_member["RELATE"] == "026":
        if "other_relatives" not in respondent["LIVING_WITH"]:
          respondent["LIVING_WITH"]["other_relatives"] = 0
        respondent["LIVING_WITH"]["other_relatives"] += 1
      elif other_hh_member["RELATE"] in ["028", "029", "030"]:
        if "housemates" not in respondent["LIVING_WITH"]:
          respondent["LIVING_WITH"]["housemates"] = 0
        respondent["LIVING_WITH"]["housemates"] += 1

def get_respondents(households):
  return [household["persons"][0] for household in households]

def convert_fields_to_descriptions(persons, data_dictionary):
  for field in RELEVANT_FIELDS_PERSON + RELEVANT_FIELDS_HOUSEHOLD:
    if (field in data_dictionary):
      if (data_dictionary[field] != "int"): # if it's a categorical variable
        for person in persons:
          code = person[field]
          person[field] = data_dictionary[field][code]
      else:
        for person in persons:
          person[field] = int(person[field])

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
households = load_JSON(filepath_in)

filepath_dictionary = DATADIR + "dictionaries/atus16_dictionary2.json"
data_dictionary = load_JSON(filepath_dictionary)

add_household_fields(households)
add_living_with_field(households, data_dictionary)

persons = get_respondents(households)

convert_fields_to_descriptions(persons, data_dictionary)

filepath_activity_map = DATADIR + "dictionaries/activities_map3.csv"
filepath_activities_by_category = DATADIR + "dictionaries/activities_by_category3.json"
recode_activity_field(persons, filepath_activity_map, filepath_activities_by_category)

persons = extract_relevant_fields_only(persons)

filepath_out = "atus16.json"
save_JSON(persons, filepath_out)
