from ipums import *
import matplotlib.pyplot as plt
import numpy as np
plt.ion()


DATADIR = "/Users/adona/data/census/cps/"
data_dictionary_compact = {} # Gets read in at the same time as the data in the load_timeuse_data_json function
def get_description(field, code):
    return data_dictionary_compact[field][code]

def load_and_preprocess_asec_data(filepath_data, filepath_dictionary):
    # Load the data and data dictionary
    global data_dictionary_compact
    data_dictionary_compact = load_JSON(filepath_dictionary)
    data = load_csv_data(filepath_data) # 185,487

    # Preprocess the data
    # Filter out people who weren't in the rotation to be give a CPS interview ("ASEC oversampling")
    # and thus cannot be connected to longitudinal CPS data / timeuse data
    log("Filtering out persons without a CPS ID, whose records cannot be connected to longitudinal data..")
    data = [p for p in data if p["CPSIDP"]!="0"] # 117,990 
    
    # Convert int and float variables
    log("Converting int and float variables.. ")
    int_vars = ["INCTOT", "AGE", "UHRSWORKT"]
    float_vars = ["ASECWT", "SPMTOTRES", "SPMTHRESH"]
    # If replicate weights are included in the dataset, convert them as well
    for rw in ["REPWT", "REPWTP"]:
        if(rw+"1" in data[0]):
            float_vars += [rw+str(i) for i in range(1,161,1)]
    for p in data: 
        for int_var in int_vars:
            p[int_var] = int(p[int_var])
        for float_var in float_vars:
            p[float_var] = float(p[float_var])
    
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

###

filepath_data = DATADIR + "raw/asec16r.csv"
filepath_dictionary = DATADIR + "dictionaries/asec16_dictionary_compact_extended.json"
data = load_and_preprocess_asec_data(filepath_data, filepath_dictionary)
explore_variable_work_schedule(data)
