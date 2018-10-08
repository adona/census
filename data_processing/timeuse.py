from ipums import *

RECTYPES = {
    "1": "household",
    "2": "person",
    "3": "activity",
    "4": "who",
    "5": "eldercare"
}

data_dictionary_compact = {} # Gets read in at the same time as the data in the load_timeuse_data_json function
def get_description(field, code):
    return data_dictionary_compact[field][code]

### Load

def convert_timeuse_data_to_json(filepath_data_raw, filepath_dictionary, filepath_data_json):
    ## Convert timeuse data from the IPUMS fixed-width format to JSON

    ### Example use:
    # datadir = "/Users/adona/data/census/timeuse/"
    # filepath_data_raw = datadir + "raw/atus16.dat"
    # filepath_dictionary = datadir + "dictionaries/atus16_dictionary_detailed.json"
    # filepath_data_json = datadir + "raw/atus16.json"
    # convert_timeuse_data_to_json(filepath_data_raw, filepath_dictionary, filepath_data_json)

    # The time use data is hierarchical:
    #   Household
    #       |_ Person
    #           |_ Activity
    #               |_ Who (who else was with the person during this activity)
    # Each household has one or more persons in it, 
    # each person who has completed a time diary (one person per household) has multiple activities
    # and each activity may have one or more "who" entries for other persons there during the activity.

    # The raw IPUMS data files are encoded as "fixed-width text files".
    #   - each line represents a record of type household, person, activity, or who
    #   - the first character of the line specifies the record type (see RECTYPES dictionary above)
    #   - the rest of the line contains all the data fields for that record, 
    #       encoded with fixed width, and concatenated.
    #       The field names, lenghts, and start and end positions are specified in a data dictionary.

    # Example raw file:
        # 1201301011300040000001020135595 ...                                       <- household #1
        # | serial # | ...      |year| ... 
        # 2201301011300040201301001010011899905.66203400022020202060501 ...         <- person #1
        #                 |person #|  ...               |age|sex| ...
        # 32013010113000402013010101999904800480010000000000004:00:0012:00:0099 ... <- activity #1
        #                                                    |start||end|
        # 42013010113000402 ...                                                     <- who #1
        # 32013010113000402 ...                                                     <- activity #2
        # ... 

    # Example data dictionary:
        # {
        #   "household": [
        #     {
        #       "name": "SERIAL",
        #       "rectype": "1",
        #       "len": 7,
        #       "start": 16,
        #       "end": 22,
        #       "field_type": "string"
        #     },
        #     ... 
        #   ],
        #   "person": [
        #     {
        #     "name": "AGE",
        #     "rectype": "2",
        #     ...

    log("Converting timeuse data from the IPUMS fixed-width format to JSON.. ")

    data_dictionary_detailed = load_JSON(filepath_dictionary)

    log("Loading the raw data from.. ")
    log(filepath_data_raw)
    data = []
    with open(filepath_data_raw, "r") as f:
        line_nr = 0
        while True:
            line = f.readline().strip() # Read the next line
            if len(line) == 0: # If reached EOF, stop
                break

            # Identify what type of record it is (household, person, activity, who, etc):
            rectype = RECTYPES[line[0]]

            if rectype == "household":
                household = parse_fixedwidth_datafile_line(line, data_dictionary_detailed, RECTYPES) # Parse the household information
                data.append(household) # Append the household to the data
                household["persons"] = [] # Prepare to parse the persons in the household

            elif rectype == "person":
                person = parse_fixedwidth_datafile_line(line, data_dictionary_detailed, RECTYPES) # Parse the person information
                household["persons"].append(person) # Append the person to its household
                person["activities"] = [] # Prepare to parse the person's activities

            elif rectype == "activity":
                activity = parse_fixedwidth_datafile_line(line, data_dictionary_detailed, RECTYPES) # Parse the activity information
                person["activities"].append(activity) # Append the activity to its person
                activity["who"] = [] # Prepare to parse who else was with the person during the activity
            
            elif rectype == "who":
                who = parse_fixedwidth_datafile_line(line, data_dictionary_detailed, RECTYPES) # Parse who else was with the person during the activity
                activity["who"].append(who) # Append it to the activity
            
            elif rectype == "eldercare":
                continue # Ignoring this for now

            line_nr += 1    
            if(line_nr % 10000 == 0):
                print("# records read: " + str(line_nr))

    log("Data load and conversion complete.")
    save_JSON(data, filepath_data_json)

def load_timeuse_data_json(filepath_data, filepath_dictionary):
    global data_dictionary_compact
    data_dictionary_compact = load_JSON(filepath_dictionary)
    data = load_JSON(filepath_data)    
    return data

### Pre-process

def preprocess_timeuse_data(data, filepath_dictionary, filepath_activity_map, flatten="none"):
    log("Preprocessing timeuse data.. ")
    data = convert_weights_to_float(data)
    data = annotate_data_with_poverty_info(data)
    data = remap_activity_field(data, filepath_activity_map, filepath_dictionary)
    data = annotate_data_with_aggregate_activity_times(data, "ACTIVITY2")
    if(flatten == "partial"):
        data = partially_flatten_timeuse_data(data)
    elif(flatten == "full"):
        data = flatten_timeuse_data(data)
    return data

def convert_weights_to_float(data):
    log("Converting weights to float..")
    weight_fields = ["WT06"]
    # If replicate weights are included in the dataset, prepare to convert them as well
    if("RWT06_1" in data[0]["persons"][0]): 
        weight_fields = weight_fields + list(map(lambda i: "RWT06_"+str(i+1), range(160)))
    for hh in data:
        for p in hh["persons"]:
            for weight_field in weight_fields:
                p[weight_field] = float(p[weight_field])
    return data

def get_poverty_info(household):
    # Official poverty guidelines for 2016
    # https://www.peoplekeep.com/blog/2016-federal-poverty-level-fpl-guidelines
    # Alaska and Hawaii are treated separately because the costs of living are significantly higher
    POVERTY_LINE_2016 = {
        "02": [14840, 20020, 25200, 30380, 35560, 40740, 45920, 51120, 56320, 61520, 66720, 71920], # Alaska
        "15": [13670, 18430, 23190, 27950, 32710, 37470, 42230, 47010, 51790, 56570, 61350, 66130],  # Hawaii
        "elsewhere": [11880, 16020, 20160, 24300, 28440, 32580, 36730, 40890, 45050, 49210, 53370, 57530]
    }

    # Get the poverty line for this household based on its location (state) and size
    state = household["STATEFIP"]
    hh_size = int(household["HH_SIZE_CPS8"])
    if state in POVERTY_LINE_2016.keys():
        pov_threshhold = POVERTY_LINE_2016[state][hh_size-1]
    else: 
        pov_threshhold = POVERTY_LINE_2016["elsewhere"][hh_size-1]

    # Get the household income. The income is encoded as a range (eg. "$20,000 to $24,999") - 
    # extract the lower and upper boundaries and convert to int. 
    hh_income = data_dictionary_compact["FAMINCOME"][household["FAMINCOME"]]
    if hh_income in ["Refused", "Don't know", "Blank"]:
        return None

    hh_income = hh_income.split(" ")
    if hh_income[0] == "Less": # "Less than $5,000"
        hh_income_lower = 0
        hh_income_upper = parse_dollar_amt(hh_income[2])
    elif hh_income[2] == "over": # "$150,000 and over"
        hh_income_lower = hh_income_upper = parse_dollar_amt(hh_income[0])
    else:
        hh_income_lower = parse_dollar_amt(hh_income[0])
        hh_income_upper = parse_dollar_amt(hh_income[2])

    # Calculate the % of poverty line
    pov_percentage_lower = round(hh_income_lower/pov_threshhold*100, 1)
    pov_percentage_upper = round(hh_income_upper/pov_threshhold*100, 1)

    return {
        "pov_threshhold": pov_threshhold,
        "hh_income_lower": hh_income_lower,
        "hh_income_upper": hh_income_upper,
        "pov_percentage_lower": pov_percentage_lower,
        "pov_percentage_upper": pov_percentage_upper
    }

def annotate_data_with_poverty_info(data):
    log("Annotating household data with poverty info.. ")
    for hh in data:
        hh.update(get_poverty_info(hh))
    return data

def remap_activity_field(data, filepath_map, filepath_dictionary):
    log("Remapping the activity field.. ")
    with open(filepath_map, "r") as f:
        # Read the mapping from the file
        r = csv.DictReader(f)
        mapping = {}
        for row in r:
            # If the CSV/Sheets conversions have removed leading 0s, add them back
            for code_field in ["Code", "Code2"]:
                if(len(row[code_field]) == 5): row[code_field] = "0" + row[code_field]
            mapping[row["Code"]] = {
                "Code": row["Code2"],
                "Description": row["Description2"]
            }

    # Remap the data
    for hh in data: 
        activities = hh["persons"][0]["activities"]
        for a in activities:
            a["ACTIVITY2"] = mapping[a["ACTIVITY"]]["Code"]

    # Add the new field to the data_dictionary & re-save the dictionary
    data_dictionary_compact["ACTIVITY2"] = {entry["Code"]: entry["Description"] for entry in mapping.values()}
    save_JSON(data_dictionary_compact, filepath_dictionary)

    return data

def get_aggregate_activity_times(person, activity_field):
    # Initialize all possible activities to zero
    all_activities = {a:0 for a in data_dictionary_compact[activity_field].keys()}
    
    # Calculate how many minutes this person spent on each
    for activity in person["activities"]:
        activity_code = activity[activity_field]
        activity_duration = int(activity["DURATION"])

        # Increment activity counter
        all_activities[activity_code] += activity_duration

        # Activities are also grouped by category, at two levels of granularity, e.g.: 
            # 020000	Household Activities
            # 020100	  Housework
            # 020101	    Interior cleaning
        # Also incremenet the category counters
        if(activity_code[4:6] != "00"):
            all_activities[activity_code[0:4]+"00"] += activity_duration
        if(activity_code[2:4] != "00"):
            all_activities[activity_code[0:2]+"0000"] += activity_duration

    return all_activities

def annotate_data_with_aggregate_activity_times(data, activity_field):
    log("Annotating data with aggregate activity times.. ")
    for hh in data:
        p = hh["persons"][0]
        p["aggregate_activity_times"] = get_aggregate_activity_times(p, activity_field)
    return data

def partially_flatten_timeuse_data(data):
    log("Partially flattening timeuse data.. ")
    flat_data = []
    for household in data:
        flatp = {}        
        # Add all the household characteristics
        flatp.update({k:household[k] for k in household.keys() if k!="persons"})
        # Add person characteristics ONLY for the person being interviewed (person #0)
        flatp.update(household["persons"][0])
        flat_data.append(flatp)
    return flat_data

def flatten_timeuse_data(data):
    log("Flattening time use data.. ")
    flat_data = []
    for household in data:
        flatp = {}
        # Add all the household characteristics
        flatp.update({k:household[k] for k in household.keys() if k!="persons"})
        # Add person characteristics ONLY for the person being interviewed (person #0)
        person = household["persons"][0]
        flatp.update({k:person[k] for k in person.keys() if k!="activities"})
        # Add aggregate activity times for that person
        flatp.update(person["aggregate_activity_times"])
        flat_data.append(flatp)
    return flat_data

### Explore

def print_household_profile(household):
    log("Household #: " + household["CASEID"])
    log("# persons in household: " + household["HH_SIZE"] + " (" + 
        household["HH_NUMADULTS"] + " adults, " + household["HH_NUMKIDS"] + " kids)")

    person = household["persons"][0]
    log("Person interviewed: " + get_description("SEX", person["SEX"]) + ", " + get_description("RACE", person["RACE"]) +
        ", age " + person["AGE"]  + ", " + get_description("MARST", person["MARST"]) + ", ")
    log("Employment status: " + get_description("EMPSTAT", person["EMPSTAT"]) + " (" + person["OCC"] + ")")

    log("Their " + get_description("DAY", person["DAY"]) + ":")
    activities = person["activities"]
    for activity in activities:
        log(activity["START"] + "-" + activity["STOP"] + " (" + activity["DURATION"] + "min) \t" + 
            get_description("ACTIVITY", activity["ACTIVITY"]) + 
            " \t (" + get_description("WHERE", activity["WHERE"]) + ")")

    print("")
