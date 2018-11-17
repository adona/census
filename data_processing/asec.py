from ipums import *
import matplotlib.pyplot as plt
import numpy as np
from matplotlib.ticker import FormatStrFormatter
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
    int_vars += ["SPMNADULTS", "SPMNCHILD", "SPMNPERS"]
    int_vars += ["INCSS", "INCWELFR", "INCRETIR", "INCSSI", "INCINT", "INCUNEMP", "INCWKCOM", 
        "INCVET", "INCSURV", "INCDISAB", "INCDIVID", "INCRENT", "INCEDUC", "INCCHILD", "INCASIST", "INCOTHER"]
    float_vars = ["SPMLUNCH", "SPMCAPHOUS", "SPMWIC", "SPMHEAT", "SPMSNAP", "SPMEITC", "SPMMEDXPNS", "SPMCAPXPNS", "SPMCHSUP", 
    "SPMSTTAX", "SPMFEDTAXAC", "SPMFEDTAXBC","SPMFICA"]
    float_vars += ["ASECWT", "SPMTOTRES", "SPMTHRESH"]
    # Also convert the replicate weights
    for rw in ["REPWT", "REPWTP"]:
        float_vars += [rw+str(i) for i in range(1,161,1)]
    for int_var in int_vars:
        if int_var in data[0]: # If one of the variables we read
            for p in data:
                p[int_var] = int(p[int_var])
    for float_var in float_vars:
        if float_var in data[0]: # If one of the variables we read
            for p in data:
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

    explore_financial_impact_doubling_up(doubling_up)

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

def split_shared_resources_between_family_subunits(doubling_up):
    # In-kind benefits (such as housing subsidies) and expenses (such as state and federal taxes)
    # are only avaiable in the dataset as totals for the entire SPM family unit.
    # Where possible, split those benefits and expenses between family subunits. 
    # In some cases it will be possible to do that unambiguously, e.g.:
    #   - taxes are also recorded at person level
    #   - housing subsidies are always allocated to the householder family subunit
    #   - WIC benefits are only available to families with children <=5yo, so if there's only one 
    #       subunit which matches this requirement, the benefit can be allocated to that subunit
    # In other cases, it will not be possible to split those resources unambigously, so mark those 
    # households with household["ambigous"][resource] = True.
    # NOTE that SNAP benefits (food assistance) and medical expenses can never be split unambigously, 
    # so skip those.

    unit_resources = [resource for resource in list(in_kind_benefits.keys()) + list(expenses.keys()) if resource not in ["SPMSNAP", "SPMMEDXPNS"]]
    for hh in doubling_up:
        p0 = hh["persons"][0] # householder
        persons = [p for p in hh["persons"] if p["SPMFAMUNIT"] == p0["SPMFAMUNIT"]] # persons in the SPM unit
        hh["subunits"] = []
        for i in range(1, hh["n_subunits"]+1, 1): # for each subunit
            p_subunit = [p for p in persons if p["subunit"] == i] # persons in the subunit
            hh["subunits"].append({
                "persons": p_subunit,
                "resources": {resource: 0 for resource in unit_resources}
            })
        hh["ambiguous"] = {resource: False for resource in unit_resources}
        ### Taxes (EITC, State, Federal, FICA) for each subunit can be calculated from values for each person in the subunit 
        for subunit in hh["subunits"]:
            subunit["resources"]["SPMEITC"] = sum([float(p["EITCRED"]) for p in subunit["persons"] if p["AGE"]>=15]) # EITC
            subunit["resources"]["SPMSTTAX"] = sum([float(p["STATAXAC"]) for p in subunit["persons"] if p["AGE"]>=15]) # State
            subunit["resources"]["SPMFEDTAXBC_2"] = sum([float(p["FEDTAXAC"])+float(p["EITCRED"]) for p in subunit["persons"]  if p["AGE"]>=15]) # Federal
        # FICA (Social Security) has a few data issues (<<1% of datapoints seem to have inconsistent individual/total FICA)
        # Will need to mark those as "ambiguous"
        if abs(p0["SPMFICA"] - sum([float(p["FICA"]) for p in persons if p["AGE"]>=15]))<10:
            for subunit in hh["subunits"]:
                subunit["resources"]["SPMFICA"] = sum([float(p["FICA"]) for p in subunit["persons"] if p["AGE"]>=15])
        else:
            hh["ambiguous"]["SPMFICA"] = True
        ### Housing and Energy subsidies: Always allocate them to the householer's subunit
        s0 = hh["subunits"][p0["subunit"]-1] # householder's subunit
        s0["resources"]["SPMCAPHOUS"] = p0["SPMCAPHOUS"] # Housing
        s0["resources"]["SPMHEAT"] = p0["SPMHEAT"] # Energy
        ### Other benefits/expenses will have to be allocated manually in non-ambiguous situations
        # i.e. situations where only one subunit fulfills the condition for getting that benefit/expense.
        ### School lunch
        if p0["SPMLUNCH"]>0:
            subunit_school_lunch = [subunit for subunit in hh["subunits"] if  # Subunits with children 5-18yo
                len([p for p in subunit["persons"] if p["AGE"]>=5 and p["AGE"]<=18])>0]
            if len(subunit_school_lunch) == 1: # If only one candidate subunit
                subunit_school_lunch[0]["resources"]["SPMLUNCH"] = p0["SPMLUNCH"] # Allocate the benefit to this subunit
            else: # Otherwise it's ambiguous how to split this benefit
                hh["ambiguous"]["SPMLUNCH"] = True # 8% ambiguous (127 out of 1542)
        ### WIC
        if p0["SPMWIC"]>0:
            subunit_wic = [subunit for subunit in hh["subunits"] if  # Subunits where at least on person is getting WIC
                len([p for p in subunit["persons"] if p["GOTWIC"]=="2"])>0]
            if len(subunit_wic) == 1: # If only one subunit is getting WIC
                subunit_wic[0]["resources"]["SPMWIC"] = p0["SPMWIC"] # Allocate the benefit to this subunit
            else: # Otherwise it's ambiguous how to split this benefit
                hh["ambiguous"]["SPMWIC"] = True # 5% ambiguous (15 out of 294)
        ### Work + childcare expenses
        if p0["SPMCAPXPNS"]>0:
            # Check if the expenses split correctly between work and childcare
            if abs(p0["SPMCAPXPNS"] - float(p0["SPMWKXPNS"]) - float(p0["SPMCHXPNS"]))>10:
                hh["ambiguous"]["SPMCAPXPNS"] = True # 1% ambiguous (85 out of 6654)
            else:
                if float(p0["SPMCHXPNS"])>0: # If there are any childcare expenses
                    subunit_childcare = [subunit for subunit in hh["subunits"] if  # Subunits with at least ..
                        len([p for p in subunit["persons"] if p["WORKLY"]=="2"])>0 and # .. one working adult and 
                        len([p for p in subunit["persons"] if p["AGE"]<18])>0] # .. one child
                    if len(subunit_childcare) == 1: # If only one candidate subunit
                        subunit_childcare[0]["resources"]["SPMCAPXPNS"] = float(p0["SPMCHXPNS"]) # Allocate the expense to this subunit
                    else: # Otherwise it's ambiguous how to split this expense
                        hh["ambiguous"]["SPMCAPXPNS"] = True # (25 out of 308)
                if not hh["ambiguous"]["SPMCAPXPNS"]: # If the childcare expenses aren't ambiguous
                    # Also split the work expenses
                    for subunit in hh["subunits"]:
                        subunit["resources"]["SPMCAPXPNS"] += sum([float(p["WKXPNS"]) for p in subunit["persons"] if p["WKXPNS"] != "9999"])
        ### Child support
        # No info on who might be paying child support, so all households with child support are ambiguous
        if p0["SPMCHSUP"]>0:
            hh["ambiguous"]["SPMCHSUP"] = True # 100% (111 out of 111)

    # Sanity check that subunit resources sum up to total unit resources
    for hh in doubling_up:
        for resource in unit_resources:
            if not hh["ambiguous"][resource]:
                total_resource = sum([subunit["resources"][resource] for subunit in hh["subunits"]])
                assert(abs(total_resource - hh["persons"][0][resource])<10)

    # Check how many households I marked as "ambiguous"
    n_ambiguous = len([hh for hh in doubling_up if sum(hh["ambiguous"].values())>0])
    perc_ambiguous = n_ambiguous / len(doubling_up) * 100
    print(f"{perc_ambiguous :.1f}% households marked as ambiguous ({n_ambiguous} out of {len(doubling_up)})") # 4.8% (360 out of 7502)

def explore_financial_impact_doubling_up(doubling_up):
    # Explore hypothesis that doubling up and sharing resources has a positive financial impact 
    # and helps get some families above the poverty line that would otherwise be in poverty.
    # The analysis is based on a rough estimate only due to the difficulty of splitting shared benefits/expenses
    # between family subunits. Some of these (such as WIC benefits available only to families with young children)
    # can be unambiguously allocated to family subunits in most cases. However, some resources cannot be 
    # split between subunits, most notably a) SNAP benefits (food stamps) (median value per household ~$2300) and 
    # b) medical expenses (median value per household $4300). This analysis thus does NOT take SNAP and medical expenses
    # into account in its calculations of poverty levels (departure from standard estimates), as well as discards
    # approximately 5% other households where the resources cannot be ambiguously allocated to subunits.
    
    # Split shared resources between family subunits
    split_shared_resources_between_family_subunits(doubling_up)

    # Filter out ambiguous cases (~5% of households)
    doubling_up = [hh for hh in doubling_up if sum(hh["ambiguous"].values())==0]

    # Calculate resources and poverty level EXCLUDING a) SNAP benefits and b) medical expenses
    for hh in doubling_up:
        p0 = hh["persons"][0]
        # Run calculations for entire SPM unit...
        hh["SPMTOTRES_partial"] = p0["SPMTOTRES"] - (p0["SPMSNAP"]-p0["SPMMEDXPNS"]) # Exclude SNAP benefits and medical expenses
        hh["spm_perc_partial"] = hh["SPMTOTRES_partial"] / p0["SPMTHRESH"] * 100
        # ... as well as each individual subunit 
        for subunit in hh["subunits"]:
            subunit_resources_partial = 0
            # Add incomes
            for p in subunit["persons"]:
                if p["AGE"] >= 15:
                    for income in income_sources:
                        subunit_resources_partial += p[income]
            # Add benefits (except SNAP)
            for benefit in set(in_kind_benefits) - set(["SPMSNAP"]):
                subunit_resources_partial += subunit["resources"][benefit]
            # Substract expenses (except medical)
            for expense in set(expenses) - set(["SPMMEDXPNS"]):
                subunit_resources_partial -= subunit["resources"][expense]
            subunit["SPMTOTRES_partial"] = subunit_resources_partial
            # Also calculate the subunit threshhold
            adults = [p for p in subunit["persons"] if p["AGE"]>=18 or p["RELATE"] in ["101", "201"]]
            nadults = len(adults)
            nchild = len(subunit["persons"]) - nadults
            subunit["SPMTHRESH"] = p0["SPMTHRESH"] / SPM_family_scaling(p0["SPMNADULTS"], p0["SPMNCHILD"]) * SPM_family_scaling(nadults, nchild)
            subunit["spm_perc_partial"] = subunit["SPMTOTRES_partial"] / subunit["SPMTHRESH"] * 100

    # 3. Visualize: Poverty level of doubled-up families vs. individual family subunits

    # First, compute normalized weights that approximate the total # of households in the US the data represents
    us_population = 323.4*(10**6)
    ndata = weighted_len(data, "ASECWT") # total # of persons the ASEC dataset represents
    norm = us_population / ndata # roughly 1.5 — normalization factor to convert ASEC estimates to US population estimates
    for hh in doubling_up:
        hh["ASECWTH_norm"] = norm * hh["ASECWTH"]

    # Extract poverty level estimates for doubled up households and individual subunits
    doubling_up_poverty = [hh["spm_perc_partial"] for hh in doubling_up]
    weights_doubling_up = [hh["ASECWTH_norm"]/10**6 for hh in doubling_up] # measures in millions of households

    subunits_poverty = []
    weights_subunits = []
    for hh in doubling_up:
        hh_subunits = [subunit["spm_perc_partial"] for subunit in hh["subunits"]]
        subunits_poverty += hh_subunits
        weights_subunits += [hh["ASECWTH_norm"]/10**6] * len(hh_subunits) # measured in millions of households

    # Visualize!
    fig, ax = plt.subplots()
    bins = range(0,1001,100)
    ax.hist(subunits_poverty, bins=bins, weights=weights_subunits)
    ax.hist(doubling_up_poverty, bins=bins, weights=weights_doubling_up)
    ax.set_xlabel("Percentage of poverty line")
    ax.xaxis.set_major_formatter(FormatStrFormatter('%d%%'))
    ax.set_ylabel("Number of US households (millions)")
    ax.legend(["Family sub-units living separately", "Families doubling up"])
    ax.set_title("Poverty level of families doubling up vs. family sub-units living separately")


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
    # (i.e. a spouse/cohabiting unmarried partner and/or children)
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

### SPM Units

# Poverty threshholds

def SPM_family_scaling(nadults, nchildren): # Family scaling factor
    if (nadults==1 and nchildren==0): # 1 adult
        scale = 1
    elif (nadults==2 and nchildren==0): # 2 adults
        scale = 1.41
    elif (nadults==1 and nchildren>0): # single parents
        scale = (1 + 0.8 + 0.5*(nchildren-1))**0.7
    else: # all other families
        scale = (nadults + 0.5*nchildren)**0.7
    return scale

def sanity_check_spmthresholds(data, households):
    ### Make sure I understand how SPMTHRESH is calculated:
    #      For each COUNTY and SPMMORT (tenure) there is a unique threshhold for a one-person SPM unit
    #      which then gets adjusted for family structure (scaling factor give by SPM_family_scaling)
    log("Sanity check that I understand how SPM thresholds are calculated..")

    # Check that for each COUNTY and SPMMORT (tenure) there is a unique threshhold once I undo the family scaling
    counties = sorted(list(set([p["COUNTY"] for p in data])))
    tenures = sorted(list(set([p["SPMMORT"] for p in data])))
    thresholds = {county:{tenure: None for tenure in tenures} for county in counties}
    for county in counties[1:]: # For each county
        for tenure in tenures: # For each tenure
            persons = [p for p in data if p["COUNTY"] == county and p["SPMMORT"] == tenure]
            # print(f"county: {county}, tenure: {tenure}, # persons: {len(persons)}")
            if(len(persons) > 0):
                threshs = [round(p["SPMTHRESH"] / SPM_family_scaling(p["SPMNADULTS"], p["SPMNCHILD"]), 2) for p in persons]
                threshs = list(set(threshs))
                assert(len(threshs) == 1) # If you reverse the family scaling factor, there is a unique threshhold
                thresholds[county][tenure] = threshs[0]

    # Sanity check that for all persons for which I know the COUNTY, my SPMTHRESH calculation agrees with the data
    for i,p in enumerate(data):
        if(p["COUNTY"] != "0"):
            my_thresh = thresholds[p["COUNTY"]][p["SPMMORT"]] * SPM_family_scaling(p["SPMNADULTS"], p["SPMNCHILD"])
            assert(abs(my_thresh - p["SPMTHRESH"])<1)

    # Sanity check that adults for the purpose of SPMNCHILD are defined as >=18yo OR the householder or their spouse
    adult_age = 18
    for i,hh in enumerate(households):
        p0 = hh["persons"][0]
        spmfam = [p for p in hh["persons"] if p["SPMFAMUNIT"] == p0["SPMFAMUNIT"]]
        npers = len(spmfam)
        adults = [p for p in spmfam if p["AGE"]>= adult_age or p["RELATE"] in ["101", "201"]]
        nadults = len(adults)
        nchild = npers - nadults
        if not ((npers == p0["SPMNPERS"]) and (p0["SPMNPERS"] == p0["SPMNADULTS"] + p0["SPMNCHILD"]) and (nadults == p0["SPMNADULTS"]) and (nchild == p0["SPMNCHILD"])):
            print(i)
            print_household_profile(p0["CPSID"])
            print()

# Family resources

income_sources = {
    "INCWAGE" : "Wage and salary income", 
    "INCBUS" : "Non-farm business income", 
    "INCFARM" : "Farm income", 
    "INCSS" : "Social Security income", 
    "INCWELFR" : "Welfare (public assistance) income", 
    "INCRETIR" : "Retirement income", 
    "INCSSI" : "Income from SSI", 
    "INCINT" : "Income from interest", 
    "INCUNEMP" : "Income from unemployment benefits", 
    "INCWKCOM" : "Income from worker's compensation", 
    "INCVET" : "Income from veteran's benefits", 
    "INCSURV" : "Income from survivor's benefits", 
    "INCDISAB" : "Income from disability benefits", 
    "INCDIVID" : "Income from dividends", 
    "INCRENT" : "Income from rent", 
    "INCEDUC" : "Income from educational assistance", 
    "INCCHILD" : "Income from child support", 
    "INCASIST" : "Income from assistance", 
    "INCOTHER" : "Income from other Source not specified"
}
in_kind_benefits = {
    "SPMLUNCH" : "SPM unit's school lunch value", 
    "SPMCAPHOUS" : "SPM unit's capped housing subsidy", 
    "SPMWIC" : "SPM unit's WIC value", 
    "SPMHEAT" : "SPM unit's energy subsidy", 
    "SPMSNAP" : "SPM unit's SNAP subsidy",
    "SPMEITC": 	"SPM unit's federal EITC",
}
expenses = {
    "SPMMEDXPNS" : "SPM unit's medical out-of-pocket and Medicare B subsidy", 
    "SPMCAPXPNS" : "SPM unit's capped work and child care expenses", 
    "SPMCHSUP" : "SPM unit's child support paid", 
    "SPMSTTAX" : "SPM unit's state tax", 
    "SPMFEDTAXBC_2": "SPM unit's federal tax (before EITC)",
    "SPMFICA" : "SPM unit's FICA and federal retirement"
}

def correct_fed_tax(data):
    for p in data:
        p["SPMFEDTAXBC_2"] = float(p["SPMFEDTAXAC"]) + float(p["SPMEITC"])

def sanity_check_family_resources(data, households):
    correct_fed_tax(data)
    log("Total family resource estimates that are off by >$10: ...")
    for hh in households:
        p0 = hh["persons"][0]
        persons = [p for p in hh["persons"] if p["SPMFAMUNIT"] == p0["SPMFAMUNIT"]]
        # Calculate total family resources
        # Add incomes for persons 15+ yo
        total_resources = 0
        for p in persons:
            if p["AGE"] >= 15:
                for income in income_sources:
                    total_resources += p[income]
        # Add family-wide benefits
        for benefit in in_kind_benefits:
            total_resources += p0[benefit]
        # Substract family-wide expenses
        for expense in expenses:
            total_resources -= p0[expense]
        if abs(total_resources - p0["SPMTOTRES"])>10:
            print(f"(CPSID: {hh['CPSID']}) {round(total_resources - p0['SPMTOTRES'],2)}")
    # Only 5 households have family resource estimates off by >$10, and they are all off by 
    # about $50. I can't figure out why, but I'm OK with that level of error


###########

filepath_data = DATADIR + "raw/asec16r2.csv"
filepath_dictionary = DATADIR + "dictionaries/asec16_dictionary_compact_extended_2.json"
data = load_and_preprocess_asec_data(filepath_data, filepath_dictionary)
explore_housing_family_doubling_up(data)

print("Here!")