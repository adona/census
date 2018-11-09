from ipums import *
import matplotlib.pyplot as plt
import numpy as np
plt.ion()


DATADIR = "/Users/adona/data/census/cps/"
data_dictionary_compact = {} # Gets read in at the same time as the data in the load_timeuse_data_json function
def get_description(field, code):
    return data_dictionary_compact[field][code]

def load_and_preprocess_asec_data(filepath_data, filepath_dictionary, fields="All"):
    # Load the data and data dictionary
    global data_dictionary_compact
    data_dictionary_compact = load_JSON(filepath_dictionary)
    data = load_csv_data(filepath_data, fields=fields) # 185,487

    # Preprocess the data
    # Filter out people who weren't in the rotation to be give a CPS interview ("ASEC oversampling")
    # and thus cannot be connected to longitudinal CPS data / timeuse data
    log("Filtering out persons without a CPS ID, whose records cannot be connected to longitudinal data..")
    data = [p for p in data if p["CPSIDP"]!="0"] # 117,990 
    
    # Convert int and float variables
    log("Converting int and float variables.. ")
    int_vars = ["AGE", "UHRSWORKT", "UHRSWORKLY", "WKSWORK1", "PTWEEKS", "INCTOT", "INCWAGE", "INCBUS", "INCFARM"]
    int_vars += ["LINENO", "ASPOUSE", "PECOHAB", "PELNMOM", "PELNDAD"]
    float_vars = ["ASECWT", "SPMTOTRES", "SPMTHRESH"]
    # Also convert the replicate weights
    for rw in ["REPWT", "REPWTP"]:
        float_vars += [rw+str(i) for i in range(1,161,1)]
    for p in data: 
        for int_var in int_vars:
            if(int_var in p):
                p[int_var] = int(p[int_var])
        for float_var in float_vars:
           if(float_var in p):
               p[float_var] = float(p[float_var])
   
    # Annotate data with industry
    # Load hierarchical occupations dictionary
    filepath_occ = DATADIR + "dictionaries/occ_hierarchical.json"
    occ_hierarchical = load_JSON(filepath_occ)
    jobs_to_industries = {}
    for industry in occ_hierarchical:
        for job in occ_hierarchical[industry]:
            jobs_to_industries[job] = industry
    jobs_to_industries["0"] = "N/A (not applicable)"
    for p in data:
        p["INDLY"] = jobs_to_industries[p["OCCLY"]]


    # Annotate data with % of poverty line
    log("Annotating data with % of poverty line..")
    for p in data:
        p["spm_perc"] = p["SPMTOTRES"] / p["SPMTHRESH"] * 100

    return data

def explore_variable_work_schedule(data):    
    employed = [p for p in data if p["UHRSWORKT"]!=999] # 55,575
    hours_vary = [p for p in data if p["UHRSWORKT"]==997] # 3,879
    
    # Calculate % of all employees who report working variable hours
    perc = weighted_len(hours_vary, "ASECWT")/weighted_len(employed, "ASECWT")*100
    log("%" + "{:.1f}".format(perc) + " report working irregular # hours / week.")

    # Calculate % of employees who report working variable hours by poverty level
    perc_hours_vary = []
    se = []
    wbin = 100
    bins = list(range(0, 701, wbin))
    for bin_left in bins[:-1]:
        bin_right = bin_left + wbin
        employed_bin = [p for p in employed if p["spm_perc"] >= bin_left and p["spm_perc"] < bin_right]
        hours_vary_bin = [p for p in hours_vary if p["spm_perc"] >= bin_left and p["spm_perc"] < bin_right]        
        f = lambda wf: weighted_len(hours_vary_bin, wf)/weighted_len(employed_bin, wf)*100
        perc_bin, se_bin = compute_estimate_and_standard_error(f, "ASECWT", "REPWTP")
        perc_hours_vary.append(perc_bin)
        se.append(se_bin)

    # Visualize
    mid_bins = [x + wbin/2 for x in bins[:-1]]
    fig, ax = plt.subplots()
    ax.bar(mid_bins, perc_hours_vary, width=80, yerr=se)
    ax.set_xticks(bins)
    ax.set_xlabel("Percentage of poverty level")
    ax.set_title("Percentage of employees who report working irregular # hours / week, by poverty level")

    # Also look how the % varies across industries
    # Load hierarchical occupations dictionary
    filepath_occ = DATADIR + "dictionaries/occ_hierarchical.json"
    occ_hierarchical = load_JSON(filepath_occ)
    industries = list(occ_hierarchical.keys())[:-1] # Exclude military

    # Calculate % of employees who report working variable hours by poverty level
    perc_hours_vary = []
    se = []
    for industry in industries:
        occ_codes = occ_hierarchical[industry].keys()
        employed_industry = [p for p in employed if p["OCC"] in occ_codes]
        hours_vary_industry = [p for p in hours_vary if p["OCC"] in occ_codes]
        f = lambda wf: weighted_len(hours_vary_industry, wf)/weighted_len(employed_industry, wf)*100
        perc_bin, se_bin = compute_estimate_and_standard_error(f, "ASECWT", "REPWTP")
        perc_hours_vary.append(perc_bin)
        se.append(se_bin)

    # Visualize
    industries_short = ["Management", "Business", "Finance", "CS/Math", "Engineering", "Science", 
        "Community/Social", "Legal", "Education", "Entertainment", "Medical", "Healthcare Support", "Protective",
        "Food", "Cleaning", "Personal", "Retail", "Admin", "Agriculture", "Construction", "Extraction", 
        "Installation/Repairs", "Manufacturing", "Transportation"]
    industries_sorted = []
    for (i, industry) in enumerate(industries):
        industries_sorted.append({
            "industry": industry,
            "industry_short": industries_short[i],
            "perc_hours_vary": perc_hours_vary[i],
            "se": se[i]
        })
    industries_sorted = sorted(industries_sorted, key=lambda x: x["perc_hours_vary"], reverse=True)

    fig, ax = plt.subplots()
    nbars = len(industries_sorted)
    ax.barh(range(nbars), [x["perc_hours_vary"] for x in industries_sorted], xerr = [x["se"] for x in industries_sorted])
    ax.set_yticks(range(nbars))
    ax.set_yticklabels([x["industry_short"] for x in industries_sorted])
    ax.invert_yaxis()
    ax.set_title("Percentage of employees who report working irregular # hours / week, by industry")

def explore_poverty_demographics(data):
    # Who are the poor? 
    us_population = 323.4*(10**6)
    ndata = weighted_len(data, "ASECWT") # total # of persons the ASEC dataset represents
    adj = us_population / ndata # roughly 1.5 — adjustment factor to convert ASEC estimates to US population estimates
    adj_len = lambda x: adj * weighted_len(x, "ASECWT") # adjusted length of an array = # of US persons it represents

    poor = [p for p in data if p["spm_perc"] <= 100]
    npoor = adj_len(poor)
    perc_poor = npoor / us_population
    print(f"Roughly 1 in {1/perc_poor :.0f} Americans are poor. ({perc_poor :.1%})")
    print(f"Thats roughly {npoor/(10**6) :.1f} million people.")

    ### Segment the US poor population by whether or not they worked last year, 
    # and if not why not (retired, disabled, in school full time, etc)
    poor_segmented = {
        "children": [p for p in poor if int(p["AGE"])<15],
        # Adults who...
        # ... worked for at least part of last year
        "employed": [p for p in poor if p["WORKLY"] == "2"],
        # ... report wanting but not being able to find work
        "unemployed": [p for p in poor if p["WHYNWLY"] == "1"],
        # ... report not being able to work last year primarily because.. 
        "retired": [p for p in poor if p["WHYNWLY"] == "5"],
        "disabled": [p for p in poor if p["WHYNWLY"] == "2"],
        "school": [p for p in poor if p["WHYNWLY"] == "4"],
        "family": [p for p in poor if p["WHYNWLY"] == "3"],
        "other": [p for p in poor if p["WHYNWLY"] == "7"]
    }

    # Sanity check that I segmented the poor population exhaustively
    total = 0
    for segment in poor_segmented:
        perc = adj_len(poor_segmented[segment])/npoor
        total += perc
        print(f"{segment}: {perc :.1%}")
    print(f"Total: {total :.1%}")
    assert(abs(total - 1) < 10**-6)

    ### Look in more depth @ employed persons
    poor_employed = poor_segmented["employed"]
    npoor_employed = adj_len(poor_employed)

    # How long did they work? (hours/week and weeks/year)
    # Visualize
    n_weeks_worked = [p["WKSWORK1"]+random.normalvariate(0,1) for p in poor_employed]
    n_hours_worked = [p["UHRSWORKLY"]+random.normalvariate(0,1) for p in poor_employed]
    fig, ax = plt.subplots()
    ax.scatter(n_weeks_worked, n_hours_worked, s=2)
    ax.set_title("Time worked last year (hours/week and weeks/year)")
    ax.set_xlabel("# weeks/year")
    ax.set_ylabel("# hours/week")
    # Aggregate stats
    timeworked = {
        "allyear" : [p for p in poor_employed if p["WKSWORK1"] >= 50], # 55%
        "allyear_fulltime" : [p for p in poor_employed if p["WKSWORK1"] >= 50 and p["UHRSWORKLY"] >= 35], # 37%
        "allyear_parttime" : [p for p in poor_employed if p["WKSWORK1"] >= 50 and p["UHRSWORKLY"] < 35], # 18%
        "partyear" : [p for p in poor_employed if p["WKSWORK1"] < 50], # 45%
        "partyear_fulltime" : [p for p in poor_employed if p["WKSWORK1"] < 50 and p["UHRSWORKLY"] >= 35], # 21%
        "partyear_parttime" : [p for p in poor_employed if p["WKSWORK1"] < 50 and p["UHRSWORKLY"] < 35] # 24%
    }
    for segment in timeworked:
        perc = adj_len(timeworked[segment])/npoor_employed
        print(f"{segment}: {perc :.1%}")


    # How much $$ did they bring home?
    allyear_fulltime = timeworked["allyear_fulltime"]
    fig, ax = plt.subplots()
    bins = range(0,100000,1000)
    ax.hist([p["INCTOT"] for p in poor_employed], bins=bins, weights=[p["ASECWT"] for p in poor_employed])
    ax.hist([p["INCTOT"] for p in allyear_fulltime], bins=bins, weights=[p["ASECWT"] for p in allyear_fulltime])
    ax.set_xlabel("Total annual income")
    ax.set_title("Total annual income for employed persons under the poverty line")
    ax.legend(["All employed", "Employed entire year, full time"])

    print(f'People in poverty who worked the entire year full time, brought home a median of ${weighted_median(allyear_fulltime, "INCTOT", "ASECWT") :,.0f}.')

    # What industries were they in?
    jobs = weighted_counter(poor_employed, "INDLY", "ASECWT")
    for job in jobs:
        job["adj_count"] = adj * job["count"]
        print(f'{job["key"]}: ({job["perc"] :.1f}% = {job["adj_count"] :,.0f} persons)')

    fig, ax = plt.subplots()
    nbars = len(jobs)
    ax.barh(range(nbars), [x["perc"] for x in jobs])
    ax.set_yticks(range(nbars))
    ax.set_yticklabels([x["key"] for x in jobs])
    ax.invert_yaxis()

def explore_housing_family_doubling_up(data):
    # Bundle persons into households, and annotate the households with family subunits
    # A family subunit consists of a person + their spouse/unmarried partner (if any) + DEPENDENT children (if any)
    # Dependent children are defined as <21 years old who do NOT have their own family sub-unit
    # (spouse/unmarried partner or own children).
    households = bundle_persons_into_households(data)
    annotate_households_with_family_subunits(households)

    # Households with more than one family subunit are doubling up
    # E.g. A nuclear family + the householder's elderly parent.
    doubling_up = [hh for hh in households if hh["n_subunits"] > 1] # 7,502 households 

    # Compute what % of all households are doubling up
    n_doubling_up = weighted_len(doubling_up, "ASECWTH")
    n_households = weighted_len(households, "ASECWTH")
    perc_doubling_up = n_doubling_up / n_households * 100
    print(f"{perc_doubling_up :.2f}% households are doubling up.") # 15.09%

    # Visualize % of households doubling up by poverty level
    wbin = 100
    bins = list(range(0, 1001, wbin))
    perc_doubling_up_bin = []
    se = []
    for bin_left in bins[:-1]:
        bin_right = bin_left + wbin
        all_households_bin = [hh for hh in households if hh["spm_perc"] >= bin_left and hh["spm_perc"] < bin_right]
        doubling_up_bin = [hh for hh in doubling_up if hh["spm_perc"] >= bin_left and hh["spm_perc"] < bin_right]        
        f = lambda wf: weighted_len(doubling_up_bin, wf)/weighted_len(all_households_bin, wf)*100
        perc_bin, se_bin = compute_estimate_and_standard_error(f, "ASECWTH", "REPWT")
        perc_doubling_up_bin.append(perc_bin)
        se.append(se_bin)

    mid_bins = [x + wbin/2 for x in bins[:-1]]
    fig, ax = plt.subplots()
    ax.bar(mid_bins, perc_doubling_up_bin, width=80, yerr=se)
    ax.set_xticks(bins)
    ax.set_xlabel("Percentage of poverty level")
    ax.set_title('Percentage of households in which family members are "doubling up", by poverty level')
    # TODO: Switch to fractions (3x poverty line) instead of %s (300% poverty line)

    print("Here!")

def bundle_persons_into_households(data):
    # Create a dictionary of households, indexed by CPSID
    cpsids = list(set([p["CPSID"] for p in data]))
    households = {cpsid: {"persons": []} for cpsid in cpsids}
    for p in data:
        hh = households[p["CPSID"]]
        hh["persons"].append(p)
    # Convert to list (so I can compute weighted statistics over it)
    households_list = []
    for cpsid in cpsids:
        hh = households[cpsid]
        hh["CPSID"] = cpsid
        households_list.append(hh)
    households = households_list
    # Annotate households with relevant info 
    for hh in households:
        p0 = hh["persons"][0] # householder
        hh["spm_perc"] = p0["spm_perc"] # poverty info
        hh["SPMTHRESH"] = p0["SPMTHRESH"]
        hh["ASECWTH"] = float(p0["ASECWTH"]) # weights
        for i in range(1, 161, 1): # including replicate weights
            hh["REPWT"+str(i)] = float(p0["REPWT"+str(i)])
    return households

def annotate_households_with_family_subunits(households):
    # Split SPM family units into family sub-units consisting only of:
    # a person + their spouse/unmarried partner (if any) + DEPENDENT children (if any)
    # NOTE: Dependent children are defined as <21 years old who do NOT have their own family sub-unit
    # (spouse/unmarried partner or own children).
    # So mother+father+16yo is one unit, mother+father+16yo child+1yo grandchild is two units and the 
    # 16yo is considered an independent adult rather than a dependent child.
    for hh in households:
        p0 = hh["persons"][0] # householder
        p_spm = [p for p in hh["persons"] if p["SPMFAMUNIT"] == p0["SPMFAMUNIT"]] # persons in the SPM unit
        p_spm = sorted(p_spm, key=lambda p: p["AGE"], reverse=True) # sort decreasing by age
        for p in p_spm: # to begin with, nobody is assigned to any subunit
            p["subunit"] = -1
        n_subunits = 0
        for p in p_spm: # for each person in the SPM unit (in decreasing age order)
            if is_independent_adult(p, hh): # independent adult
                partner = get_partner(p, hh)
                if(partner != None) and (partner["subunit"] != -1):
                    p["subunit"] = partner["subunit"] # same subunit as partner
                else: # new subunit!
                    n_subunits += 1
                    p["subunit"] = n_subunits
            else: # children
                parents = get_parents(p, hh)
                if len(parents) > 0:
                    p["subunit"] = parents[0]["subunit"] # same subunit as parent
        # Anybody at this point with subunit -1 are "dependents" who haven't been allocated to a subunit yet
        # because they don't have a parent in the house.
        # If the householder is one of them (e.g. a 18yo living with friends), allocate them to their own subunit.
        if p0["subunit"] == -1:
            n_subunits += 1
            p0["subunit"] = n_subunits
        # Everybody else, allocate to the householder's subunit
        # These will be e.g. grandchildren living with their grandparents
        for p in p_spm:
            if p["subunit"] == -1:
                p["subunit"] = p0["subunit"]
        hh["n_subunits"] = n_subunits
    return households

### Family relationships

def get_parents(p, hh):
    parents = [p2 for p2 in hh["persons"] if p2["LINENO"] in [p["PELNMOM"], p["PELNDAD"]]]
    return parents

def get_partner(p, hh):
    partner = [p2 for p2 in hh["persons"] if p2["LINENO"] in [p["ASPOUSE"], p["PECOHAB"]]]
    if len(partner)>0:
        return partner[0]
    else: 
        return None

def get_children(p, hh):
    children = [p2 for p2 in hh["persons"] if p["LINENO"] in [p2["PELNMOM"], p2["PELNDAD"]]]
    return children

def is_independent_adult(p, hh):
    # An independent adult is a person who is either 21+ years old OR has own primary family
    # (i.e. a spouse/unmarried partner and/or children)
    return (p["AGE"] >= 21) or (get_partner(p, hh) != None) or (len(get_children(p, hh))>0)

def print_household_profile(cpsid):
    hh = [p for p in data if p["CPSID"] == cpsid]
    for (i, p) in enumerate(hh):
        print(f'{i}. {get_description("RELATE",p["RELATE"])} - {p["AGE"]}; ' + 
            f'{get_description("SEX",p["SEX"])}; ' + 
            f'{get_description("MARST",p["MARST"])}; ' + 
            f'{get_description("EMPSTAT",p["EMPSTAT"])}; ' + 
            f'{get_description("FTYPE",p["FTYPE"])}; ' + 
            f'{get_description("FAMREL",p["FAMREL"])}')
    # print("")

### 

filepath_data = DATADIR + "raw/asec16r2.csv"
filepath_dictionary = DATADIR + "dictionaries/asec16_dictionary_compact_extended_2.json"
data = load_and_preprocess_asec_data(filepath_data, filepath_dictionary)
explore_housing_family_doubling_up(data)

print("Here!")
