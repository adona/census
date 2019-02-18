const MAX_WAGE = 200000;
const CHART_MARGIN = 50, 
  X_AXIS_SHIFT = 20,
  Y_AXIS_SHIFT = 10;

var data, data_subsample,
  occupations, categories, education_levels, 
  edu_ticks, edu_scale, edu_labels, wage_scale,
  draw_data, data_selected, data_mouseover;

// Read the data
var url_data = "https://storage.googleapis.com/iron-flash-216615-dev/asec16_employed_fulltime_10k.csv", 
  url_dictionary = "https://storage.googleapis.com/iron-flash-216615-dev/asec16_data_dictionary.json";
d3.csv(url_data, function(d) { // Load the data
  data = d; // Save to global variable (for easier debugging)
  preprocess_data();

  d3.json(url_dictionary, function(data_dictionary) { // Load the data dictionary
    occupations = data_dictionary["OCCLY"];
    categories = data_dictionary["CATLY"]
    education_levels = data_dictionary["EDUC2"];

    initialize_visualization();
  });
});

function preprocess_data() {
  for(var i = 0; i<data.length; i++) {
    person = data[i];
    person["ID"] = i; // Add unique IDs
    person["EDUC2"] = +person["EDUC2"]; // Convert vars to int
    person["INCWAGE"] = +person["INCWAGE"];
    person["INCWAGE"] = Math.min(person["INCWAGE"], MAX_WAGE) // Top-code wages
    person["edu_perturbation"] = 0.15*randn_bm()  // Pre-compute a perturbation factor
      // which will later be used to better visualize points that overlap along the edu axis.
      // Pre-computting it in advance for both efficiency reasons, and so that the perturbations 
      // are the same between redraws.
  }
  // Create data subsample for when showing the entire dataset is too slow
  data_subsample = data.filter(p => Math.random() < 0.3);
}

function initialize_visualization() {
  set_visualization_height();
  create_categories_list();
  draw_chart_background();
  data_selected = data_subsample;
  draw_data(data_selected, "selected");
  window.onresize = resize_visualization;
}

function resize_visualization() {
  set_visualization_height();
  set_categories_list_height();
  draw_chart_background();
  draw_data(data_selected, 'selected');
}

function set_visualization_height() {
  var window_height = $(window).height(),
    header_height = $("#header").outerHeight(true),
    visualization_container = $("#visualization-container"),
    container_margin = visualization_container.outerHeight(true) - visualization_container.height(),
    new_container_height = window_height - header_height - container_margin;
  visualization_container.height(new_container_height);
}

function create_categories_list() {
  // Convert categories dictionary to list for easier data binding
  var categories_list = []
  for (var code in categories)
    categories_list.push({
      "code": code,
      "description": categories[code]
    });
  // Sort alphabetically
  categories_list.sort((a, b) => (a["description"] > b["description"]) ? 1 : -1)

  var categories_list_div = d3.select("#categories-list");

  // Add "All occupations" category
  categories_list_div
    .append("div")
      .attr("class", "category all")
      .attr("code", "all")
      .attr("state", "selected")
    .append("div")
      .attr("class", "category-label")
      .text("All Occupations")
      .on("click", d => process_occp_list_interaction("selected", "all"))
      .on("mouseover", d => process_occp_list_interaction("mouseover", "all"))
      .on("mouseout", d => process_occp_list_interaction("mouseout"));

  // Add a scroll container
  var scroll_container = categories_list_div
    .append("div")
      .attr("id", "scroll-container");

  // Add individual categories
  var category_divs = scroll_container
    .selectAll("category")
      .data(categories_list, category => category["code"]);
  category_divs = category_divs.enter()
    .append("div")
      .attr("class", "category")
      .attr("code", category => category["code"])
      .attr("state", "")
    .append("div")
      .attr("class", "category-label")
      .text(category => category["description"])  
      .on("click", d => process_occp_list_interaction("selected", d["code"]))
      .on("mouseover", d => process_occp_list_interaction("mouseover", d["code"]))
      .on("mouseout", d => process_occp_list_interaction("mouseout"));

    set_categories_list_height();
}

function set_categories_list_height() {
  // Manually set the scroll-container height relative to its parent container so that scroll works correctly
  var scroll_container_height = $("#categories-list").innerHeight() - $(".category.all").outerHeight(true);
  d3.select("#scroll-container")
    .attr("style", "height: "+ scroll_container_height + "px");
}

function draw_chart_background() {
  var chart_div = d3.select("#chart");

  // If this is a re-draw (e.g. window resize), first remove the existing chart
  chart_div.selectAll("*").remove();	

  // Create a new SVG canvas
  var chart_width = chart_div.node().offsetWidth,
    chart_height = chart_div.node().offsetHeight;
  var svg = chart_div.append("svg")
    .attr("width", chart_width)
    .attr("height", chart_height);

  // Create the axes
  // Manually space the ticks on the edu axis, with larger gaps between edu stages (e.g. between highschol and college)
  edu_ticks = [1, 2, 3, 4, 6, 7, 8, 10, 11, 12];
  edu_labels = [];
  for (var code in education_levels)
    edu_labels.push(education_levels[code]);

  var edu_extent = [0.5, 12.5],
    wage_extent = [0, MAX_WAGE];

  edu_scale = d3.scaleLinear()
    .domain(edu_extent)
    .range([CHART_MARGIN + X_AXIS_SHIFT, chart_width - CHART_MARGIN]);
  wage_scale = d3.scaleLinear()
    .domain(wage_extent)
    .range([chart_height - CHART_MARGIN - Y_AXIS_SHIFT, CHART_MARGIN]);

  var edu_axis = d3.axisBottom()
    .scale(edu_scale)
    .tickValues(edu_ticks)
    .tickFormat((d,i) => edu_labels[i]);
  var wage_axis = d3.axisLeft()
    .scale(wage_scale)
    .ticks(5, "$,s");

  svg.append("g")
    .attr("class", "x axis")
    .attr("transform", "translate(0," + (chart_height-CHART_MARGIN) + ")")
    .call(edu_axis);
  svg.append("g")
    .attr("class", "y axis")
    .attr("transform", "translate(" + CHART_MARGIN + ",0)")
    .call(wage_axis);

  customize_edu_tick_labels(chart_height);

  // Add y-axis title
  chart_div.append("div")
    .attr("class", "y-label")
    .text("Annual Wage")
    .attr("style", "width: 40px; text-align: right; transform: translate(1px,15px);");			
}

function customize_edu_tick_labels(chart_height) {
  // Delete the auto-generated tick labels from the SVG
  d3.selectAll("g.x.axis g.tick text").remove();

  // Create new labels, as individual divs in the #chart container
  x_labels = d3.select("#chart")
    .selectAll('.x-label')
      .data(edu_labels);
  x_labels = x_labels.enter()
    .append("div")
    .attr("class", "x-label")
    .text(x => x);

  // Adjust their width based on the distance between ticks
  var min_label_width = 55,
    tick_distance = 0.9*(edu_scale(2)-edu_scale(1)),
    label_width;

  if (tick_distance >= min_label_width) { 
    // If window is large enough, show the labels horizontally, of width tick_distance
    label_width = tick_distance;
    x_labels.attr("style", function(x, i) {
      var label_style = "width: " + label_width + "px; ";
      // And translate them to be centered on the tickmarks. 
      var x_pos = edu_scale(edu_ticks[i]) - label_width/2,
        y_pos = chart_height - CHART_MARGIN + 15;
      label_style += "transform: translate(" + x_pos + "px," + y_pos + "px);";
      return 	label_style;
    });
  } else {
    // If the window is too small for the ticks to be horizontal, make them diagonal
    // Of width min_label_width
    label_width = min_label_width;
    x_labels.attr("style", function(x, i) {
      var label_style = "width: " + label_width + "px; ";
      // Text aligned right
      label_style += "text-align: right; "
      // Translated so that the top-left corner is aligned with the tickmarks
      var x_pos = edu_scale(edu_ticks[i]) - label_width - 5,
        y_pos = chart_height - CHART_MARGIN + 13;
      label_style += "transform: translate(" + x_pos + "px," + y_pos + "px) ";
      // And rotated 45 degrees
      label_style += "rotate(-60deg); transform-origin: right top;";
      return 	label_style;
    });
  }
}

function draw_data(data_to_draw, data_state) {
  // At any given time, the chart will show either:
  //  1. one "selected" dataset, or 
  //  2. one "mouseover" dataset, and one "background" (previously "selected") dataset
  // The draw_data function updates one of those datasets 
  // (as indicated by data_state in {"selected", "mouseover", "background"})
  // fading in any new datapoints, and fading out any old points not in data_to_draw.

  // NOTES:
  //  1. If a point is in both "mouseover" and "background" datasets, it will be drawn twice
  //  2. Points fading out slowly can cause race conditions. e.g. A user could mouseover, out, and back over the same
  // dataset in quick succession, in which case the d3 data binding for the 2nd mouseover 
  // would see that the datapoints already exist from the 1st mouseover, and not create new ones, 
  // soon after which the datapoints would finish fading out and dissapear. To handle this situation,
  // datapoints are labeled with attribute "out" when they start fading out, and if the user returns 
  // to a dataset with those points while they're still fading out, new copies are made of them.

  var circles = d3.select("svg")
    .selectAll("[state="+data_state+"]:not([out])") // Datapoints with this data_state which are not currently fading out
      .data(data_to_draw, person=>person["ID"]);

  circles.enter()
    .append('circle')
      .attr('state', data_state)
      .attr('cx', person => edu_scale(edu_ticks[person["EDUC2"]] + person["edu_perturbation"]))
      .attr('cy', person => wage_scale(person["INCWAGE"]))
      .attr('r', 2.25)
      .on("mouseover", circleMouseOver)
      .on("mouseout", circleMouseOut)
      .style("opacity", 0)
      .transition() // Fade in new datapoints
        .style("opacity", 1)
        .ease(d3.easeCubicOut)
        .duration(300);

  circles.exit()
    .attr("out", "true")
    .transition() // Fade out exiting datapoints
      .style("opacity", 0)
      .ease(d3.easeCubicIn)
      .duration(300)
      .remove();
        
  function circleMouseOver(d) { 
    // Make the current cirle slightly larger
    d3.select(this).attr("r", 4);

    // Create the infobox
    var occp_description = occupations[d["OCCLY"]];
    var wage = d["INCWAGE"];
    // First make sure the old infobox was removed 
    // (it should on mouseout, but sometimes it fails to due to a race condition)
    d3.select("#infobox").remove();
    // Then create the new one
    var infobox = d3.select("#chart")
      .append("div")
      .attr("id", "infobox");
    infobox.append("span")
      .attr("style", "font-weight: 700;")
      .text("Occupation");
    infobox.append("span")
      .text(occp_description)
    infobox.append("span")
      .text(" ("+d3.format("$,")(wage) + ")");
    infobox
      .style("opacity", 0)
      .transition()
      .delay(10)
      .style("opacity", 1);
  }

  function circleMouseOut(d) {	
    // Remove the infobox
    d3.select("#infobox").remove();

    // Return circle radius to normal
    d3.select(this).attr("r", 2.25);
  }
}

function process_occp_list_interaction(interaction, code) {
  switch(interaction) {
    case "selected":
      // 1. Update the occupation list
      d3.select("#categories-list [state=selected]").attr("state", ""); // Clear previous selection 
      d3.select("#categories-list [state=mouseover]").attr("state", "selected"); // Change current mouseover to selection

      // 2. Update the data
      draw_data([], "background"); // Remove previous selection (currently in the background)
      d3.selectAll("circle[state=mouseover]").attr("state", "selected"); // Change current mouseover to selection

      data_selected = data_mouseover;
      data_mouseover = [];
      break;

    case "mouseover":
      // 1. Update the occupation list
      var mouseover_div = d3.select("#categories-list .category[code='" + code + "']");
      if(mouseover_div.attr("state") == "selected") return; // If element is already selected, ignore mouseover
      mouseover_div.attr("state", "mouseover"); // Else, set new mouseover

      // 2. Update the data
      d3.selectAll("circle[state=selected]").attr("state", "background"); // Fade currently selected data into the background
      data_mouseover = filter_data(code);
      draw_data(data_mouseover, "mouseover"); // Add new mouseover data
      break;

    case "mouseout":
      // 1. Update the occupation list
      d3.select("#categories-list [state=mouseover]").attr("state", ""); // Clear current mouseover

      // 2. Update the data
      draw_data([], "mouseover"); // Remove current mouseover
      d3.selectAll("circle[state=background]").attr("state", "selected");  // Bring selected data back from the background

      data_mouseover = [];
      break;
  }
}

function filter_data(code) {
  if (code == "all")
    return data_subsample
  else 
    return data.filter(p => p["CATLY"] == code); 
}

// Standard Normal variate using Box-Muller transform.
function randn_bm() {
  var u = 0, v = 0;
  while(u === 0) u = Math.random(); //Converting [0,1) to (0,1)
  while(v === 0) v = Math.random();
  return Math.sqrt( -2.0 * Math.log( u ) ) * Math.cos( 2.0 * Math.PI * v );
}
