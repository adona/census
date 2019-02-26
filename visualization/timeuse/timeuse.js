const EDU_HIGHSCHOOL_OR_LESS = ["No education", "Some primary / secondary", "Some high school", "High school"];
const EDU_BACHELORS = "Bachelor's degree";
const EUD_MASTERS_PHD = ["Master's degree", "Professional degree", "Doctoral degree"];
const WEEKDAY = ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday"];
const WEEKEND = ["Saturday", "Sunday"];

const FILTER_GENDER = { "filter-id": "filter-gender", 
  "name": "Gender",
  "options":
    [{"id": "all", "label": "All", "condition": p => true},
     {"id": "men", "label": "Men", "condition": p => p["SEX"] == "Male"},
     {"id": "women", "label": "Women", "condition": p => p["SEX"] == "Female"}]};
const FILTER_AGE = { "filter-id": "filter-age",
  "name": "Age",
  "options":
     [{"id": "all", "label": "All", "condition": p => true},
      {"id": "15_24", "label": "15-24", "condition": p => p["AGE"] <= 24},
      {"id": "25-44", "label": "25-64", "condition": p => p["AGE"] >= 25 && p["AGE"] <=64},
      {"id": "65_plus", "label": "65+", "condition": p => p["AGE"] >= 65}]};
const FILTER_RACE = { "filter-id": "filter-race", 
  "name": "Race",
  "options":
     [{"id": "all", "label": "All", "condition": p => true},
      {"id": "white", "label": "White", "condition": p => p["RACE"] == "White"},
      {"id": "black", "label": "Black", "condition": p => p["RACE"] == "Black"},
      {"id": "other", "label": "Other", "condition": p => !(["White", "Black"].includes(p["RACE"]))}]};
const FILTER_KIDS = { "filter-id": "filter-kids", 
  "name": "Children",
  "options":
     [{"id": "all", "label": "All", "condition": p => true},
      {"id": "none", "label": "No", "condition": p => p["HH_NUMOWNKIDS"] == 0},
      {"id": "1_or_more", "label": "Yes", "condition": p => p["HH_NUMOWNKIDS"] > 0}]};
const FILTER_EDU = { "filter-id": "filter-edu", 
  "name": "Education",
  "options":
     [{"id": "all", "label": "All", "condition": p => true},
      {"id": "highschool", "label": "High school", "condition": p => EDU_HIGHSCHOOL_OR_LESS.includes(p["EDUC"])},
      {"id": "college", "label": "College", "condition": p => p["EDUC"] == EDU_BACHELORS}, 
      {"id": "masters_phd", "label": "Masters / Ph.D.", "condition": p => EUD_MASTERS_PHD.includes(p["EDUC"])}]};
const FILTER_EMPLOYMENT = { "filter-id": "filter-employement", 
  "name": "Employment",
  "options":
     [{"id": "all", "label": "All", "condition": p => true},
      {"id": "employed", "label": "Employed", "condition": p => p["EMPSTAT"] == "Employed"},
      {"id": "unemployed", "label": "Unemployed", "condition": p => p["EMPSTAT"] == "Unemployed"},
      {"id": "not_looking", "label": "Not Looking", "condition": p => p["EMPSTAT"] == "Not in labor force"}]};
const FILTER_DAY = { "filter-id": "filter-day", 
  "name": "Day of week",
  "options":
     [{"id": "all", "label": "All", "condition": p => true},
      {"id": "weekday", "label": "M-F", "condition": p => WEEKDAY.includes(p["DAY"])},
      {"id": "weekend", "label": "S-S", "condition": p => WEEKEND.includes(p["DAY"])}]};
const FILTER_MODELS = 
  [[FILTER_GENDER, FILTER_AGE, FILTER_RACE, FILTER_KIDS], 
   [FILTER_EDU, FILTER_EMPLOYMENT, FILTER_DAY]];
const FILTERS_BAR = d3.select("#filters-bar");

const SEARCHBOX_PLACEHOLDER = "e.g. Playing with children, volunteering.. ";

const N_RESULTS_DIV = d3.select("#n-results").remove().node();

const T_START = parse_time("04:00");
const TIME_EXTENT = d3.extent([T_START, add_one_day(T_START)]);   // Timelines run from 4am to 4am next day
const TIMELINE_TEMPLATE = d3.select(".timeline-container").remove().node();
const TIMELINE_MARGIN_BOTTOM = 20;
const ACTIVITY_RECT_HEIGHT = 20;
const ACTIVITY_RECT_HEIGHT_MOUSEOVER = 35;
const ACTIVITY_RECT_RADIUS = 3;
const ACTIVITY_COLORS = { // See most colors here: https://coolors.co/0d2c54-69306d-247ba0-70c1b3-ffb400
  "Sleep": "#EFEFEF", // Grey
  "Personal Care": "#EFEFEF", // Grey
  "Housework & Errands": "#247BA0", // Light Blue
  "Work": "#0D2C54", // Dark Blue
  "Education": "#69306D", // Purple
  "Caring for Others": "#70C1B3", // Green
  "Eating & drinking": "#F77046", // Orange
  "Leisure": "#FFB400", // Bright Yellow
  "Travel": "#999999", // Medium-grey
  "Missing data": "#FFFFFF" // White
};


var persons, activities_by_category;

var url_activities = "https://storage.googleapis.com/iron-flash-216615-dev/atus16_activities_by_category.json"
var url_data = "https://storage.googleapis.com/iron-flash-216615-dev/atus16.json.zip";

d3.json(url_activities, function(d) {
  activities_by_category = d; // Save to global variable (for easier debugging)  
  
  initialize_header();

  console.log("Loading data..");
  fetch(url_data)
    .then(response => response.blob())
    .then(blob => decompress_data(blob, function(d) {
      persons = d; // Save to global variable (for easier debugging)

      preprocess_data();

      d3.select("#loading-data").remove();
      d3.select("#header").node().appendChild(N_RESULTS_DIV);    

      filter_persons();
    }));
  });


function initialize_header() {
  initialize_filters();
  initialize_searchbox();

  // Add top-margin to main-area = height of the fixed header, so they don't overlap
  var header_height = d3.select("#header").node().getBoundingClientRect()["height"];
  d3.select("#timelines-list").attr("style", "margin-top: "+ (header_height) + "px;");
}

function initialize_filters() {
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
    .on("change", filter_persons);

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
    filtered_activities_by_category, filtered_activities, 
    idx_selected;

  function show_suggestions_box() {
    if (suggestions_box != null) return;
    var suggestion_box_top = searchbox.node().getBoundingClientRect()["height"];
    suggestions_box = searchbox.append("ul")
      .attr("class", "suggestions-box")
      .attr("style", "top: " + suggestion_box_top + "px;");
    filter_suggestions("");
  }
  
  function hide_suggestions_box() {
    if (suggestions_box == null) return;
    suggestions_box.remove();
    suggestions_box = null;
    idx_selected = null;
  }

  function filter_suggestions(query) {
    if (query == "") {
      filtered_activities_by_category = activities_by_category;
    } else {
      filtered_activities_by_category = [];
      for (var i=0; i<activities_by_category.length; i++) {
        var category = activities_by_category[i];
        var filtered_category_activities = category["activities"].filter(activity => 
          activity.toLowerCase().search(query.toLowerCase()) != -1);
        if (filtered_category_activities.length > 0)
          filtered_activities_by_category.push({
            "category": category["category"],
            "activities": filtered_category_activities
          });
      }
    }
    filtered_activities = [];
    for (var i=0; i<filtered_activities_by_category.length; i++)
      filtered_activities = filtered_activities.concat(filtered_activities_by_category[i]["activities"]);

    update_suggestions();
  }

  function update_suggestions() {
    suggestions_box.selectAll("*").remove();
    idx_selected = null;

    var category_divs = suggestions_box.selectAll("div")
      .data(filtered_activities_by_category)
      .enter()
        .append("div");

    category_divs
      .append("li")
      .attr("class", "suggestion-category")
      .text(category => category["category"]);
    
    category_divs
      .selectAll(".suggestion-activity")
      .data(category => category["activities"])
      .enter()
        .append("li")
        .attr("class", "suggestion-activity")
        .text(activity => activity);

    suggestions_box
      .selectAll(".suggestion-activity")
      .on("mouseover", (d, i) => update_selection(i))
      .on("mouseout", () => update_selection(null))
      .on("mousedown", completeSearch);
  }

  function update_selection_by_arrowpress(arrowPressed) {
    // Figure out which should be the next selected element
    if (arrowPressed == "ArrowDown")
      new_idx = idx_selected == null? 0 : idx_selected+1;
    else 
      new_idx = idx_selected == null? filtered_activities.length-1 : idx_selected-1;
    // Check that it's not out of bounds
    if ((new_idx < 0) || (new_idx >= filtered_activities.length))
      new_idx = null;
    // Update the selection
    update_selection(new_idx);
  }

  function update_selection(new_idx) {
    var lis = suggestions_box.selectAll(".suggestion-activity").nodes();
    if (idx_selected != null) 
      lis[idx_selected].classList.remove("selected");
    if(new_idx != null)
      lis[new_idx].classList.add("selected");
    idx_selected = new_idx;
  }

  function completeSearch() {
    if (idx_selected != null)
      input.node().value = filtered_activities[idx_selected];
    input.node().blur();
  }

  function onBlur() {
    hide_suggestions_box();
    filter_persons();
  }
}

function decompress_data(blob, callback) {
  console.log("Decompressing data..");
  zip.createReader(new zip.BlobReader(blob), function(reader) {
    reader.getEntries(function(entries) {
      entries[0].getData(new zip.TextWriter(), function(d) {
        d = JSON.parse(d);
        callback(d);
      });
    });
  });
}

function preprocess_data() {
  console.log("Preprocessing data..")
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

function filter_persons() {
  var checked_inputs = d3.selectAll(".filter-option input:checked"),
      checked_options = checked_inputs.select(function() { return this.parentNode; });
  var conditions = checked_options.data().map(option => option["condition"]);
  filtered_persons = persons;
  for (var i=0; i<conditions.length; i++)
    filtered_persons = filtered_persons.filter(conditions[i]);


  var activities_query = d3.select("#activities-searchbox input").node().value.toLowerCase();
  filtered_persons = filtered_persons.filter(person => {
    var has_activity = false;
    var activities = person["activities"];
    for (var i=0; i<activities.length; i++)
      if (activities[i]["ACTIVITY3"].toLowerCase().search(activities_query) != -1) {
        has_activity = true;
        break;
      }
    return has_activity;
  });

  d3.select("#n-results-placeholder").text(filtered_persons.length);

  visualize_filtered_persons();
}

function visualize_filtered_persons() {
  d3.selectAll(".timeline-container").remove();
  for (var i=0; i<Math.min(50, filtered_persons.length); i++)
    visualize_person(filtered_persons[i]);
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
    bbox = svg.node().getBoundingClientRect(),
    width = bbox["width"]-1,
    height = bbox["height"];

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
  var activity_rects = svg.selectAll(".activity")
    .data(person["activities"], activity => person["ID"] + "_" + activity["ACTNUM"]);
  activity_rects.enter()
    .append('rect')
    .attr("class", "activity")
    .attr("id", activity => "activity-" + person["ID"] + "-" + activity["ACTNUM"])
    .attr("x", activity => time_scale(activity["START"]))
    .attr("y", y0 - ACTIVITY_RECT_HEIGHT)
    .attr("width", activity => time_scale(activity["STOP"])-time_scale(activity["START"]))
    .attr("height", ACTIVITY_RECT_HEIGHT)
    .attr("rx", ACTIVITY_RECT_RADIUS)
    .attr("ry", ACTIVITY_RECT_RADIUS)
    .attr("style", activity => "fill: " + ACTIVITY_COLORS[activity["CATEGORY"]] + ";")
    .on("mouseover", activityMouseOver)
    .on("mouseout", activityMouseOut);

    // Mouseover event listeners
    var summary_div = timeline_container.select(".summary");
    function activityMouseOver(activity, i) {
      var y = time_scale(activity["STOP"]) + 5;
      timeline_container.select("#activity-" + person["ID"] + "-" + activity["ACTNUM"])
        .attr("y", y0 - ACTIVITY_RECT_HEIGHT_MOUSEOVER)
        .attr("height", ACTIVITY_RECT_HEIGHT_MOUSEOVER);
      // Remove the demographics summary
      summary_div.remove();
      // Add activity description
      timeline_container.select(".annotations")
        .append("div")
        .attr("class", "activity-label")
        .attr("id", "label-"  + person["ID"] + "-" + activity["ACTNUM"])
        .attr("style", "left: " + y + "px;")
        .text(activity["ACTIVITY3"]);
    }
    
    function activityMouseOut(activity, i) {
      timeline_container.select("#activity-" + person["ID"] + "-" + activity["ACTNUM"])
        .attr("y", y0 - ACTIVITY_RECT_HEIGHT)
        .attr("height", ACTIVITY_RECT_HEIGHT);
      // Remove activity description
      d3.select("#label-" + person["ID"] + "-" + activity["ACTNUM"]).remove();
      // Add back demographics summary
      timeline_container.select(".annotations").node().appendChild(summary_div.node());
    }
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
