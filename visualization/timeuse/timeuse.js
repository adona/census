const EDU_HIGHSCHOOL_OR_LESS = ["No education", "Some primary / secondary", "Some high school", "High school"];
const EDU_BACHELORS = "Bachelor's degree";
const EUD_MASTERS_PHD = ["Master's degree", "Professional degree", "Doctoral degree"];
const WEEKDAY = ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday"];
const WEEKEND = ["Saturday", "Sunday"];

const FILTER_GENDER = { "filter-id": "filter-gender", 
  "name": "Gender",
  "options":
    [{"id": "all", "label": "All", "filter_condition": p => true},
     {"id": "men", "label": "Men", "filter_condition": p => p["SEX"] == "Male"},
     {"id": "women", "label": "Women", "filter_condition": p => p["SEX"] == "Female"}]};
const FILTER_AGE = { "filter-id": "filter-age",
  "name": "Age",
  "options":
     [{"id": "all", "label": "All", "filter_condition": p => true},
      {"id": "15_24", "label": "15-24", "filter_condition": p => p["AGE"] <= 24},
      {"id": "25-44", "label": "25-64", "filter_condition": p => p["AGE"] >= 25 && p["AGE"] <=64},
      {"id": "65_plus", "label": "65+", "filter_condition": p => p["AGE"] >= 65}]};
const FILTER_RACE = { "filter-id": "filter-race", 
  "name": "Race",
  "options":
     [{"id": "all", "label": "All", "filter_condition": p => true},
      {"id": "white", "label": "White", "filter_condition": p => p["RACE"] == "White"},
      {"id": "black", "label": "Black", "filter_condition": p => p["RACE"] == "Black"},
      {"id": "other", "label": "Other", "filter_condition": p => !(["White", "Black"].includes(p["RACE"]))}]};
const FILTER_KIDS = { "filter-id": "filter-kids", 
  "name": "Children",
  "options":
     [{"id": "all", "label": "All", "filter_condition": p => true},
      {"id": "none", "label": "No", "filter_condition": p => p["HH_NUMOWNKIDS"] == 0},
      {"id": "1_or_more", "label": "Yes", "filter_condition": p => p["HH_NUMOWNKIDS"] > 0}]};
const FILTER_EDU = { "filter-id": "filter-edu", 
  "name": "Education",
  "options":
     [{"id": "all", "label": "All", "filter_condition": p => true},
      {"id": "highschool", "label": "High school", "filter_condition": p => EDU_HIGHSCHOOL_OR_LESS.includes(p["EDUC"])},
      {"id": "college", "label": "College", "filter_condition": p => p["EDUC"] == EDU_BACHELORS}, 
      {"id": "masters_phd", "label": "Masters / Ph.D.", "filter_condition": p => EUD_MASTERS_PHD.includes(p["EDUC"])}]};
const FILTER_EMPLOYMENT = { "filter-id": "filter-employement", 
  "name": "Employment",
  "options":
     [{"id": "all", "label": "All", "filter_condition": p => true},
      {"id": "employed", "label": "Employed", "filter_condition": p => p["EMPSTAT"] == "Working"},
      {"id": "unemployed", "label": "Unemployed", "filter_condition": p => p["EMPSTAT"] == "Unemployed"},
      {"id": "not_looking", "label": "Not Looking", "filter_condition": p => p["EMPSTAT"] == "Not in labor force"}]};
const FILTER_DAY = { "filter-id": "filter-day", 
  "name": "Day of week",
  "options":
     [{"id": "all", "label": "All", "filter_condition": p => true},
      {"id": "weekday", "label": "M-F", "filter_condition": p => WEEKDAY.includes(p["DAY"])},
      {"id": "weekend", "label": "S-S", "filter_condition": p => WEEKEND.includes(p["DAY"])}]};
const FILTER_MODELS = 
  [[FILTER_GENDER, FILTER_AGE, FILTER_RACE, FILTER_KIDS], 
   [FILTER_EDU, FILTER_EMPLOYMENT, FILTER_DAY]];
const FILTERS_BAR = d3.select("#filters-bar");

const SEARCHBOX_PLACEHOLDER = "e.g. Playing with children, volunteering.. ";

const RESULTS_AND_LEGEND_DIV = d3.select("#results-and-legend").remove().node();
const RESULTS_PER_PAGE = 100;

const T_START = parse_time("04:00");
const T_STOP = add_one_day(T_START);
const TIME_EXTENT = [T_START, T_STOP];   // Timelines run from 4am to 4am next day
const TIMELINE_TEMPLATE = d3.select(".timeline-container").remove().node();
const TIMELINE_MARGIN_BOTTOM = 20;
const ACTIVITY_RECT_HEIGHT = 20;
const ACTIVITY_RECT_RADIUS = 3;
const ACTIVITY_COLORS = { // See most colors here: https://coolors.co/0d2c54-69306d-247ba0-70c1b3-ffb400
  "Sleep": "#EFEFEF", // Grey
  "Personal Care": "#EFEFEF", // Grey
  "Housework & Errands": "#247BA0", // Light Blue
  "Work": "#0D2C54", // Dark Blue
  "Education": "#69306D", // Purple
  "Caring for Others": "#70C1B3", // Green
  "Eating & Drinking": "#F77046", // Orange
  "Leisure": "#FFB400", // Bright Yellow
  "Travel": "#999999", // Medium-grey
  "Missing data": "#FFFFFF" // White
};
const HAS_LIGHT_ACTIVITY_COLOR = ["Sleep", "Personal Care", "Missing data"];

const PROFILE_CARD_TEMPLATE = d3.select(".profile-card").remove().node();

var persons, activities_by_category,
  active_filter_conditions, is_activity_match,
  filtered_persons, npersons_visible,
  activity_dropdown_is_visible = false;

var url_activities = "https://storage.googleapis.com/iron-flash-216615-dev/atus16_activities_by_category_final.json"
var url_data = "https://storage.googleapis.com/iron-flash-216615-dev/atus16_final.json.gz";

$.getJSON(url_activities)
  .done(function(d) {
    activities_by_category = d; // Save to global variable (for easier debugging)

    preprocess_activities();
    initialize_header();

    $.getJSON(url_data)
      .done(function(d) {
        persons = d; // Save to global variable (for easier debugging)

        preprocess_data();

        d3.select("#loading-data").remove();
        d3.select("#header-content").node().appendChild(RESULTS_AND_LEGEND_DIV);
        initialize_legend();
  
        filter_persons();
  
        $(window).on('scroll', function() {
          var scrollPercent = ($(window).scrollTop() / 
            ($(document).height() - $(window).height())) * 100;
          if (scrollPercent >= 80)
            add_next_results_page();
        });  
      });
  });

function preprocess_activities() {
  // Annotate each category and activity with:
  // - an "is_match" function where is_match(other_activity) is true iff other_activity belongs to that category / is equal to that activity
  // - a "filter_condition" function where filter_condition(person) is true iff that person's timeline contains at least one matching activity
  // These will be used for activity filtering, and highlighting the matches in the filtered results.
  activities_by_category.forEach(function(category) {
    var is_category_match = activity => activity["CATEGORY"] == category["category"];
    category["is_match"] = is_category_match;
    category["filter_condition"] = person => (person["activities"].filter(activity => is_category_match(activity)).length > 0);
    

    category["activities"] = 
      category["activities"].map(function(activity) {
        var is_activity_match = other_activity => other_activity["ACTIVITY3"] == activity;
        return {
          "activity": activity,
          "is_match": is_activity_match,
          "filter_condition": person => (person["activities"].filter(other_activity => is_activity_match(other_activity)).length > 0)
        };
      });
  });
  // Add an "All Activities" at the top (corresponding to no filtering)
  activities_by_category.unshift({
    "category": "All Activities",
    "is_match": activity => false,
    "filter_condition": person => true,
    "activities": []
  });
}

function initialize_header() {
  initialize_filters();
  initialize_searchbox();

  // Add top-margin to main-area = height of the fixed header, so they don't overlap
  var header_height = $("#header").height();
  d3.select("#timelines-list").attr("style", "margin-top: "+ (header_height+5) + "px;");
}

function initialize_filters() {
  active_filter_conditions = {};
  for(var row=0; row<FILTER_MODELS.length; row++) {
    var filters_row = FILTERS_BAR.append("div")
      .attr("class", "filters-row")
      .attr("row-number", row+1);
    for(var i=0; i<FILTER_MODELS[row].length; i++)
      create_filter(FILTER_MODELS[row][i], filters_row);
  }
}

function create_filter(filter_model, filters_row) {
  var filter_id = filter_model["filter-id"];
  active_filter_conditions[filter_id] = filter_model["options"][0]["filter_condition"];

  var filter = filters_row.append("form")
    .attr("class", "filter")
    .attr("id", filter_id);

  filter.append("div")
    .attr("class", "filter-name")
    .text(filter_model["name"]);

  var options_div = filter.append('div')
    .attr("class", "filter-options");

  var options = options_div.selectAll(".filter-option")
    .data(filter_model["options"], option => option["id"])
    .enter()
      .append("div")
      .attr("class", "filter-option");

  options.append("input")
    .attr("type", "radio")
    .attr("name", filter_id)
    .attr("id", option => filter_id+"-"+option["id"])
    .on("change", function() {
      var filter_condition = filter.select(".filter-option input:checked").data()[0]["filter_condition"];
      filter_persons(filter_id, filter_condition);
    });

  options.append("label")
    .attr("for", option => filter_id+"-"+option["id"])
    .text(option => option["label"]);

  filter.select("input").attr("checked", "checked");
}

function initialize_searchbox() {
  var searchbox = FILTERS_BAR.append("div")
    .attr("id", "activities-searchbox");

  searchbox.append("div")
    .attr("class", "filter-name")
    .text("Activity");

  active_filter_conditions["activities-searchbox"] = activities_by_category[0]["filter_condition"];
  is_activity_match = activities_by_category[0]["is_match"];

  var input = searchbox.append("input")
  .attr("type", "text")
  .attr("placeholder", SEARCHBOX_PLACEHOLDER)
  .on("focus", show_suggestions_box)
  .on("blur", onBlur)
  .on("keydown", () => {
    if (["ArrowDown", "ArrowUp"].includes(d3.event.key))
      d3.event.preventDefault();
  })
  .on("keyup", () => {
    var key = d3.event.key;
    switch(key) {
      case "ArrowDown":
      case "ArrowUp": 
        update_selection_by_arrowpress(key);
        break;
      case "Enter":
      case "Tab":
      case "Escape":
        completeSearch();
        break;
      default:
        filter_suggestions(input.node().value);
    }
  });
  
  var suggestions_box, 
    filtered_activities_by_category, 
    n_filtered_suggestions, idx_selected;

  function show_suggestions_box() {
    if (suggestions_box != null) return;
    var suggestion_box_top = $(searchbox.node()).height();
    suggestions_box = searchbox.append("ul")
      .attr("class", "suggestions-box")
      .attr("style", "top: " + suggestion_box_top + "px;");
    filter_suggestions("");
    activity_dropdown_is_visible = true;
  }
  
  function hide_suggestions_box() {
    if (suggestions_box == null) return;
    suggestions_box.remove();
    suggestions_box = null;
    idx_selected = null;
    activity_dropdown_is_visible = false;
  }

  function filter_suggestions(query) {
    query = query.toLowerCase();
    var is_match = suggestion => suggestion.toLowerCase().includes(query);

    filtered_activities_by_category = [];
    activities_by_category.forEach(function(category) {
      var filtered_category_activities = category["activities"].filter(activity => is_match(activity["activity"]));
      if ((filtered_category_activities.length > 0) || (is_match(category["category"]))) {
        var filtered_category = {};
        for (var field in category)
          if (field != "activities")
            filtered_category[field] = category[field];
        filtered_category["activities"] = filtered_category_activities;
        filtered_activities_by_category.push(filtered_category);
      }
    });

    update_suggestions();
  }

  function update_suggestions() {
    suggestions_box.selectAll("*").remove();
    idx_selected = null;

    var category_containers = suggestions_box.selectAll("div")
      .data(filtered_activities_by_category)
      .enter()
        .append("div");

    var category_divs = category_containers
      .append("li")
        .attr("class", "suggestion-category")
    category_divs
      .append("span")
        .text(category => category["category"]);
    category_divs
      .append("span")
        .attr("class", "match-count")
        // .text(category => " [" + category["n_filtered_persons"] + " - " + category["perc_filtered_persons"] + "%]");
        .text(category => " [" + category["perc_filtered_persons"] + "%]");
      
    var activity_divs = category_containers
      .selectAll(".suggestion-activity")
      .data(category => category["activities"])
      .enter()
        .append("li")
        .attr("class", "suggestion-activity");
    activity_divs
      .append("span")
        .text(activity => activity["activity"]);
    activity_divs
      .append("span")
        .attr("class", "match-count")
        // .text(activity => " [" + activity["n_filtered_persons"] + " - " + activity["perc_filtered_persons"] + "%]");
        .text(activity => " [" + activity["perc_filtered_persons"] + "%]");
    
    suggestions_box
      .selectAll("li")
      .on("mouseover", (d, i) => update_selection(i))
      .on("mouseout", () => update_selection(null))
      .on("mousedown", completeSearch);
    
    n_suggestions = suggestions_box.selectAll("li").nodes().length;
  }

  function update_selection_by_arrowpress(arrowPressed) {
    // Figure out which should be the next selected element
    if (arrowPressed == "ArrowDown")
      new_idx = idx_selected == null? 0 : idx_selected+1;
    else 
      new_idx = idx_selected == null? n_filtered_suggestions-1 : idx_selected-1;
    // Check that it's not out of bounds
    if ((new_idx < 0) || (new_idx >= n_filtered_suggestions))
      new_idx = null;
    // Update the selection
    update_selection(new_idx);
  }

  function update_selection(new_idx) {
    var lis = suggestions_box.selectAll("li").nodes();
    if (idx_selected != null) 
      lis[idx_selected].classList.remove("selected");
    if(new_idx != null)
      lis[new_idx].classList.add("selected");
    idx_selected = new_idx;
  }

  function completeSearch() {
    var selected_activity;
    if (idx_selected == null) {
      selected_activity = activities_by_category[0];  // All Activities
      input.node().value = "";
    } else {
      selected_activity = suggestions_box.select(".selected").data()[0];
      var input_text;
      if (selected_activity["category"] != null)
        input_text = selected_activity["category"] != "All Activities" ? selected_activity["category"] : "";
      else 
        input_text = selected_activity["activity"];
      input.node().value = input_text;
    }

    is_activity_match = selected_activity["is_match"];
    filter_condition = selected_activity["filter_condition"]
    filter_persons("activities-searchbox", filter_condition);
    
    input.node().blur();
  }

  function onBlur() {
    hide_suggestions_box();
  }
}

function initialize_legend() {
  var id = "legend";
  var parent_div = d3.select("#legend-text");
  var position = { left: $(parent_div.node()).width() + 18 };
  var arrow_direction = "left";
  var legend_tooltip = create_tooltip(id, parent_div, position, arrow_direction);
  var legend = legend_tooltip.select(".tooltip-body");

  legend
    .append("div")
    .attr("id", "legend-title")
    .text("Legend");

  var category_divs = legend.selectAll(".legend-category")
    .data(activities_by_category.slice(1, activities_by_category.length-1))
    .enter()
      .append("div")
      .attr("class", "legend-category");

  category_divs
    .append("div")
      .attr("class", "legend-color")
      .attr("style", category => "background: " + ACTIVITY_COLORS[category["category"]]);
  
  category_divs
    .append("div")
      .attr("class", "legend-description")
      .text(category => category["category"]);
  
  legend
    .append("div")
    .attr("id", "legend-close")
    .text("✖");

  var tooltip_top = -0.9*$(legend_tooltip.node()).height();
  legend_tooltip
    .attr("style", legend_tooltip.attr("style") + " top: " + tooltip_top + "px;");
  legend_tooltip.select(".tooltip-arrow")
    .attr("style", "top: " + (-tooltip_top) + "px; ");
  
  legend_tooltip.style("visibility", "hidden");
  var visible = false;
  d3.select("#show-legend")
    .on("click", function() {
      if (!visible)
        legend_tooltip.style("visibility", "visible");
      else
        legend_tooltip.style("visibility", "hidden");
      visible = ! visible;
    });
  d3.select("#legend-close")
    .on("click", function() {
      legend_tooltip.style("visibility", "hidden");
      visible = false;
    });
}

function preprocess_data() {
  for (var i=0; i<persons.length; i++) {
    person = persons[i];
    person["ID"] = i;
    preprocess_timeline(person);
  }
}

function preprocess_timeline(person) {
  var timeline = person["activities"];
  // Parse START & STOP times
  var next_day = false;
  for (var i = 0; i < timeline.length; i++) {
    var activity = timeline[i];
    activity["ACTNUM"] = i;
    var start = parse_time(activity["START"]),
      stop = i<timeline.length-1 ? parse_time(timeline[i+1]["START"]) : T_START;
    if (start > stop) { // Detect that we've just crossed midnight..
      next_day = true;
      stop = add_one_day(stop);
    } else if (next_day) { // .. and from then onward add a day to all times.
      start = add_one_day(start);
      stop = add_one_day(stop);
    }
    activity["START"] = start;
    activity["STOP"] = stop;
  }
}

function filter_persons(updated_filter_id, updated_filter_condition) {
  // Update the filters
  if (updated_filter_id != null)
    active_filter_conditions[updated_filter_id] = updated_filter_condition;

  // Filter
  filtered_persons = persons;
  // Filter through everything but the activity filter (for now)
  for (var filter_id in active_filter_conditions)
    if (filter_id != "activities-searchbox")
      filtered_persons = filtered_persons.filter(active_filter_conditions[filter_id]);
  // Annotate the activities with # of filtered persons matching each activity
  if (updated_filter_id != "activities-searchbox")
    annotate_activities_with_n_filtered_persons();
  // Now filter through the activity as well
  filtered_persons = filtered_persons.filter(active_filter_conditions["activities-searchbox"]);

  // Update the # of results
  d3.select("#n-results-placeholder").text(filtered_persons.length);

  // Visualize results!
  visualize_filtered_persons();
}

function annotate_activities_with_n_filtered_persons() {
  console.log("Annotating activities wtih n_filtered_persons");
  persons_matching_category = {};
  persons_matching_activity = {};
  activities_by_category.forEach(category => {
    persons_matching_category[category["category"]] = new Set();
    category["activities"].forEach(activity => persons_matching_activity[activity["activity"]] = new Set());
  });

  filtered_persons.forEach(person => {
    person["activities"].forEach(activity => {
      persons_matching_category[activity["CATEGORY"]].add(person["ID"]);
      persons_matching_activity[activity["ACTIVITY3"]].add(person["ID"]);
    })
  })

  var n_filtered_persons = filtered_persons.length;
  activities_by_category.forEach(category => {
    category["n_filtered_persons"] = persons_matching_category[category["category"]].size;
    category["perc_filtered_persons"] = Math.ceil(category["n_filtered_persons"]/n_filtered_persons*100);
    category["activities"].forEach(activity => {
      activity["n_filtered_persons"] = persons_matching_activity[activity["activity"]].size;
      activity["perc_filtered_persons"] = Math.ceil(activity["n_filtered_persons"]/n_filtered_persons*100);
    });
  });
  activities_by_category[0]["n_filtered_persons"] = filtered_persons.length;
  activities_by_category[0]["perc_filtered_persons"] = 100;
}

function visualize_filtered_persons() {
  d3.selectAll(".timeline-container").remove();
  npersons_visible = 0;
  add_next_results_page();
}

function add_next_results_page() {
  var new_npersons_visible = Math.min(npersons_visible + RESULTS_PER_PAGE, filtered_persons.length);
  for (var i=npersons_visible; i<new_npersons_visible; i++)
    visualize_person(filtered_persons[i]);
  npersons_visible = new_npersons_visible;
}

function visualize_person(person) {  
  // Instantiate the template for visualizing an individual person
  var timeline_container = TIMELINE_TEMPLATE.cloneNode(true);
  timeline_container.setAttribute("id", "timeline-"+person["ID"]);
  d3.select("#timelines-list").node().appendChild(timeline_container);
  timeline_container = d3.select(".timeline-container[id=timeline-"+person["ID"]+"]"); // Re-select as a D3 selection

  timeline_container
    .select(".demographics")
    .text(person["AGE"] + "yo " + person["RACE"] + " " + person["SEX"]);
  
  timeline_container
    .select(".day")
    .text(person["DAY"]);

  create_timeline(person, timeline_container);
}

function create_timeline(person, timeline_container) {
  var svg = timeline_container.select(".timeline"),
    width = $(svg.node()).width()-1,
    height = $(svg.node()).height();

  // Create the axis
  var time_scale = d3.scaleTime()
    .domain(TIME_EXTENT)
    .range([0, width]);
  var time_axis = d3.axisBottom()
    .scale(time_scale)
    .tickFormat(d3.timeFormat("%I %p"));
  var y0 = height - TIMELINE_MARGIN_BOTTOM;
  svg.append("g")
    .attr("class", "x axis")
    .attr("transform", "translate(0," + y0 + ")")
    .call(time_axis);

  // Create the activity rects
  var activity_rects = svg.selectAll(".activity-container")
    .data(person["activities"], activity => person["ID"] + "_" + activity["ACTNUM"]);
  activity_rects.enter()
    .append("g")
      .attr("class", "activity-container")
      .attr("id", activity => "activity-" + person["ID"] + "-" + activity["ACTNUM"])
    .append('rect')
      .attr("class", "activity")
      .attr("x", activity => time_scale(activity["START"]))
      .attr("y", y0 - ACTIVITY_RECT_HEIGHT)
      .attr("width", activity => time_scale(activity["STOP"])-time_scale(activity["START"]))
      .attr("height", ACTIVITY_RECT_HEIGHT)
      .attr("rx", ACTIVITY_RECT_RADIUS)
      .attr("ry", ACTIVITY_RECT_RADIUS)
      .attr("style", activity => "fill: " + ACTIVITY_COLORS[activity["CATEGORY"]] + ";")
      .on("mouseover", activityMouseOver)
      .on("mouseout", activityMouseOut);

  // If the results are filtered by activity, also highlight the matching activities
  matching_activities = person["activities"].filter(is_activity_match);
  svg.selectAll(".activity-container")
    .data(matching_activities, activity => person["ID"] + "_" + activity["ACTNUM"])
      .append("rect")
        .attr("class", "activity-highlight")
        .attr("x", activity => time_scale(activity["START"]))
        .attr("y", y0 + 3)
        .attr("width", activity => time_scale(activity["STOP"])-time_scale(activity["START"]))
        .attr("height", 5)
        .attr("rx", ACTIVITY_RECT_RADIUS)
        .attr("ry", ACTIVITY_RECT_RADIUS)    
        .attr("style", activity => "fill: " + ACTIVITY_COLORS[activity["CATEGORY"]] + ";")

  // Mouseover event listeners
  var annotations_div = timeline_container.select(".annotations");
  function activityMouseOver(activity, i) {
    add_activity_description(person, activity, timeline_container, time_scale);
    add_detailed_profile(person, timeline_container);
  }
  function activityMouseOut(activity, i) {
    remove_activity_description(person, activity);
    remove_detailed_profile(person);
  }
}

function create_tooltip(id, parent_div, position, arrow_direction) {
  var position_string = "";
  for (var direction in position)
    position_string += direction + ": " + position[direction] + "px; ";

  var tooltip = parent_div
    .append("div")
      .attr("class", "tooltip")
      .attr("id", id)
      .attr("style", position_string);
  tooltip
    .append("div")
      .attr("class", "tooltip-arrow")
      .attr("arrow-direction", arrow_direction);
  tooltip
    .append("div")
      .attr("class", "tooltip-body")
      .attr("arrow-direction", arrow_direction);
  return tooltip;
}

function add_activity_description(person, activity, timeline_container, time_scale) {
  if (activity_dropdown_is_visible) return;

  // Create tooltip
  var id = "activity-description-"  + person["ID"] + "-" + activity["ACTNUM"];
  var parent_div = timeline_container.select(".annotations");
  var activity_center = (time_scale(activity["START"]) + time_scale(activity["STOP"]))/2;
  var position = { "top": -3 };
  var arrow_direction ="down";
  var tooltip = create_tooltip(id, parent_div, position, arrow_direction);
  tooltip.classed("activity-description", true);

  // Set color to match activity
  var color = HAS_LIGHT_ACTIVITY_COLOR.includes(activity["CATEGORY"]) ? "black" : "white";
  var border = activity["CATEGORY"] == "Missing data" ? "border: solid lightgrey 1px; " : "border-width: 0px; ";
  var style = "background: " + ACTIVITY_COLORS[activity["CATEGORY"]] + "; " + 
    "color: " + color + "; " + border;
  var text = activity["ACTIVITY3"];
  tooltip.select(".tooltip-body")
    .attr("style", style)
    .text(text);
  tooltip.select(".tooltip-arrow")
    .attr("style", style);

  // Position horizontally (now that I know it's width) so that 
  // the arrow always points to the center of the activity, 
  // but the tooltip body relative to the arrow is dependent on when the activity is in the day.
  var tooltip_width = $(tooltip.node()).width();
  var activity_center_as_percentage = activity_center / time_scale(T_STOP);  
  var arrow_left = 5 + activity_center_as_percentage*(tooltip_width-25);
  var tooltip_left = activity_center - arrow_left - 5;
  tooltip
    .attr("style", "top: " + position["top"] + "px; " + "left: " + tooltip_left + "px; ");
  tooltip.select(".tooltip-arrow")
    .attr("style", style + "left: " + arrow_left + "px; ");

  // Detect collisions with either the demographics or day, and, if needed, set visibility: hidden;
  var demographics = timeline_container.select(".demographics");
  var day = timeline_container.select(".day");
  if (divs_overlap(tooltip.node(), demographics.node()))
    demographics.style("visibility", "hidden");
  if (divs_overlap(tooltip.node(), day.node()))
    day.style("visibility", "hidden");

}

function remove_activity_description(person, activity) {
  timeline_container = d3.select(".timeline-container[id=timeline-"+person["ID"]+"]");
  timeline_container.select(".activity-description").remove();
  timeline_container.select(".demographics").style("visibility", "visible");
  timeline_container.select(".day").style("visibility", "visible");
}

function add_detailed_profile(person, timeline_container) {
  if (activity_dropdown_is_visible) return;

  // Create the tooltip
  var id = "person-profile-"  + person["ID"];
  var parent_div = timeline_container.select(".annotations");
  var position = { "left": $(parent_div.node()).width() + 15 }; // Will set top once I know the height of the tooltip
  var arrow_direction = "left";
  var profile_tooltip = create_tooltip(id, parent_div, position, arrow_direction);
  profile_tooltip.classed("profile-tooltip", true);

  // Set up the profile card template
  var profile_card = profile_tooltip.select(".tooltip-body");
  profile_card.classed("profile-card", true);
  var template = PROFILE_CARD_TEMPLATE.cloneNode(true);
  $(profile_card.node()).append(template.childNodes);

  // Fill in the information
  var img_name = "user.png";
  profile_card.select(".icon")
    .attr("src", "img/"+img_name)
    .attr("alt", "Female default profile image icon");

  var simple_fields = ["AGE", "SEX", "RACE", "DAY", "MARST", "EDUC", "FAMINCOME"];
  for (var i=0; i<simple_fields.length; i++) {
    var field = simple_fields[i];
    profile_card.select("."+field).text(person[field]);  
  }
  add_living_with_information(person, profile_card);
  add_work_information(person, profile_card);

  // Position vertically (now that I know it's height) so that 
  // the arrow always points to the center of the timeline, 
  // but the tooltip body relative to the arrow is dependent on where the timeline is on the page.
  var tooltip_height = $(profile_tooltip.node()).height();
  var timeline_center = $(timeline_container.node()).height() - 32;
  var timeline_center_relative_document = $(timeline_container.node()).offset().top + timeline_center;
  var timeline_center_relative_window = timeline_center_relative_document - ($(window).scrollTop() + $("#header").height());
  var timeline_center_relative_window_as_percentage = timeline_center_relative_window/($(window).height() - $("#header").height());
  var arrow_top = 5 + timeline_center_relative_window_as_percentage*(tooltip_height-25);
  var tooltip_top = timeline_center - arrow_top - 5;
  profile_tooltip
    .attr("style", profile_tooltip.attr("style") + "top: " + tooltip_top + "px; ");
  profile_tooltip.select(".tooltip-arrow")
    .attr("style", "top: " + arrow_top + "px; ");

}

function add_living_with_information(person, profile_card) {
  var living_with_div = profile_card.select(".living-with");
  if (person["HH_SIZE"] == 1) {
    living_with_div.text("Living alone");
  }
  else {
    var living_with = person["LIVING_WITH"];
    var relations = Object.keys(living_with);
    var pronoun = person["SEX"] == "Female" ? "her" : "his";
    var lis = [];
    if (relations.includes("partner"))
      lis.push(pronoun + " " + living_with["partner"].toLowerCase());
    if (relations.includes("children")) {
      if (living_with["children"].length == 1)
        lis.push("one child (age " + living_with["children"][0] + ")");
      else 
        lis.push(living_with["children"].length + " children " + 
          "(ages " + list_to_string(living_with["children"]) + ")");
    }
    if (relations.includes("grandchildren")) {
      if (living_with["grandchildren"].length == 1)
        lis.push("one grandchild (age " + living_with["grandchildren"][0] + ")");
      else 
        lis.push(living_with["grandchildren"].length + " grandchildren " + 
          "(ages " + list_to_string(living_with["grandchildren"]) + ")");
    }
    if (relations.includes("parents")) {
      if (living_with["parents"].length == 1)
        lis.push(pronoun + " " + living_with["parents"][0]);
      else 
        lis.push(pronoun + " parents");
    }
    if (relations.includes("siblings"))
      if(living_with["siblings"] == 1)
        lis.push("one sibling");
      else  
        lis.push(living_with["siblings"] + " siblings");
    if (relations.includes("other_relatives"))
      if(living_with["other_relatives"] == 1)
        lis.push("one other relative");
      else  
        lis.push(living_with["other_relatives"] + " other relatives");
    if (relations.includes("housemates")) 
      if(living_with["housemates"] == 1)
        lis.push("one housemate");
      else  
        lis.push(living_with["housemates"] + " housemates");

    if (lis.length == 1) {
      living_with_div.text("Living with " + lis[0]);
    } else {
      living_with_div.append("span")
        .text("Living with:")
      var ul = living_with_div
        .append("ul")
        .selectAll("li")
          .data(lis)
          .enter()
            .append("li")
            .text(li => li);
    }
  }
}

function add_work_information(person, profile_card) {
  profile_card.select(".EMPSTAT").text(person["EMPSTAT"]);
  if (person["EMPSTAT"] == "Working") {
    profile_card.select(".FULLPART").text(person["FULLPART"].toLowerCase());
    profile_card.select(".OCC").text(person["OCC"]);
  } else {
    $(profile_card.select(".OCC").node()).parent().remove();
  }
}

function remove_detailed_profile(person) {
  d3.select("#person-profile-" + person["ID"]).remove();
}

/// Helper functions

function parse_time(time_str) {
  // Returns a Date object() with an arbitrary date (here Jan 1, 1900)
  // and the hh:mm set according to the time_str.
  // Implemented this way because the only capability needed is to represent
  // times over two consecutive days - which days exactly is not important.
  var hours = +time_str.substring(0, 2),
    minutes = +time_str.substring(3, 5);
  var date = new Date(0, 0, 1, hours, minutes, 0);
  return date;
}

function add_one_day(date) {
  return new Date(date.getTime() + 24*60*60*1000);
}

function list_to_string(list) {
  var string;
  switch (list.length) {
    case 0: 
      string = "";
      break;
    case 1:
      string = list[0];
      break;
    case 2: 
      string = list[0] + " and " + list[1];
      break;
    default:
      string = "";
      for (var i=0; i<list.length-1; i++)
        string += list[i] + ", "
      if (list.length > 1)
        string += "and ";
      string += list[list.length-1];
  }
  return string;
}

function divs_overlap(div1, div2) {
  div1 = $(div1);
  div2 = $(div2);

  var div1_x1 = div1.offset().left;
  var div1_y1 = div1.offset().top;
  var div1_w = div1.outerWidth(true);
  var div1_h = div1.outerHeight(true);
  var div1_x2 = div1_x1 + div1_w;
  var div1_y2 = div1_y1 + div1_h;

  var div2_x1 = div2.offset().left;
  var div2_y1 = div2.offset().top;
  var div2_w = div2.outerWidth(true);
  var div2_h = div2.outerHeight(true);
  var div2_x2 = div2_x1 + div2_w;
  var div2_y2 = div2_y1 + div2_h;
  
  return !(div1_y2 < div2_y1 || div1_y1 > div2_y2 || div1_x2 < div2_x1 || div1_x1 > div2_x2);
}
