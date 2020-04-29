
var locale = window.navigator.userLanguage || window.navigator.language;
var eventsTable;
moment.locale(locale);
String.prototype.capitalize = function() {
  return this.charAt(0).toUpperCase() + this.slice(1)
}

window.onload = function(){

  		eventsTable = new Tabulator("#eventstable", {
  			layout:"fitColumns",
  			//ajaxURL: '/api/events/',
            ajaxSorting:true,
            ajaxFiltering:true,
  			resizableColumns:false,

            persistence:{
                sort: true, //persist column sorting
                filter: true, //persist filter sorting
                page: false, // /!\ page persistence does not work with remote pagination
            },

            // Activate grouping only if we sort by start date
            dataSorting : function(sorters){
                // If eventsTable is not ready to be used: exit
                if(eventsTable == undefined)
                    return 0;
                if(sorters[0]['field'] == 'title')
                    eventsTable.setGroupBy(false);
                else if (sorters[0]['field'] == 'start')
                    eventsTable.setGroupBy(function(data){
                        return moment(data.start).format('dddd D MMMM YYYY').capitalize();
                    });
                else
                    eventsTable.setGroupBy(sorters[0]['field']);
            },
            pagination : 'remote',
            paginationSize : 10,
            pageLoaded :  updatePageURL,

            initialSort: [ {column:"start", dir:"asc"}],
            initialFilter: [{field:"end", type:">=", value:"now" }],
  			columns:[
      			{title:"Titre", field:"title", sorter:"string"},
                {title:"Date", field:"start", sorter:"string"},
  			],
  			    rowFormatter: eventRowFormatter,
            groupHeader:function(value, count, data, group){
                return value;
            },
            locale: true,
            locale:true,
            langs:{
                "fr":{
                    "ajax":{
                        "loading":"Chargement", //ajax loader text
                        "error":"Erreur", //ajax error text
                    },
                    "pagination":{
                        "page_size":"Evénements par page", //label for the page size select element
                        "first":"Début", //text for the first page button
                        "first_title":"Première Page", //tooltip text for the first page button
                        "last":"Fin",
                        "last_title":"Dernière Page",
                        "prev":"Précédente",
                        "prev_title":"Page Précédente",
                        "next":"Suivante",
                        "next_title":"Page Suivante",
                    }
                }
            },
  		});

        document.querySelectorAll('.tabulator-paginator button').forEach(function(button){
                    button.addEventListener('click', gotoEvents);
                });

        // Try to extract and set page
        var page = document.location.toString().split('#p')[1];
        eventsTable.modules.ajax.setUrl('/api/events/');
        if(! isNaN(page) ){
            eventsTable.setMaxPage(page); // We extends max page to avoid an error
            eventsTable.setPage(page);
        }
        else{
            eventsTable.setPage(1);
            console.log('No page defined');
        }

        refreshFilterDisplay();
};

function eventRowFormatter(row){
    try {
        var element = row.getElement();
        var data    = row.getData();
        var width   = element.offsetWidth;
        var html    = "";

        //clear current row data
        element.childNodes.forEach(function(e){ e.style.display="none"});

        //define a table layout structure and set width of row
        divRow = document.createElement("a");
        divRow.className = "row tabulator-cell";
        divRow.setAttribute("role","gridcell");
        divRow.setAttribute("href", data.view_uri);
        divRow.style.width = (width - 18) + "px";

        //add row data on right hand side
        html += `<div class="activities section">`;
        for (const activity of data.activity_types)
                    html += `<span class="activity ${activity['short']} type"></span>`;
        html += `</div>`;

        html += `<div class="section">
                    <img src="${data.photo_uri}" class="photo"/>
                 </div>`;

        var status_string = ''
        if(!data.is_confirmed) status_string = `<span class="event-status">${data.status}</span>`

        html += `<div class="section">
                     <h4>
                     ${status_string}
                     ${escapeHTML(data.title)}
                     </h4>
                     <div class="date">
                         <img src="/static/img/icon/ionicon/md-calendar.svg" class="icon"/>
                         ${localInterval(data.start, data.end)}
                     </div>

                     <div class="leader">
                        Par ${escapeHTML(data.leaders.map(displayLeader).join(' et '))}
                     </div>
                     <div class="slots">
                        ${slots(data.num_slots - data.free_slots)}
                        ${slots(data.free_slots, 'free_slot')}
                     </div>
                 </div>
                 <div class="breaker"></div>`;
        divRow.innerHTML = html;

        //append newly formatted contents to the row
        element.append(divRow);
    }
    catch(error){
      console.error(error);
    }
}

function localInterval(start, end){
    var startDate = localDate(start);
    var endDate = localDate(end);

    if( startDate == endDate)
        return startDate;
    return `${startDate} au ${endDate}`;
}

function localDate(date){
    return moment(date).format('ddd D MMM YY');
}

function slots(nb, css){
    if(css == undefined)
        css = '';
    if( ! Number.isInteger(nb) || nb < 0)
        return '';
    var slot = `<img src="/static/img/icon/ionicon/md-contact.svg" class="icon ${css}"/>`;
    return (new Array(nb)).fill( slot ).join('');
}
function displayLeader(user){
    return user.name;
}


function selectActivity(activity_id, element){


    // Toggle filter
    currentActivityFilter=eventsTable.getFilters().filter(function(i ){ return i['field'] == "activity_type" });
    console.log(currentActivityFilter.length);

    // Display all activities
    if (false === activity_id && currentActivityFilter.length != 0)
        eventsTable.removeFilter(currentActivityFilter);


    if (false !== activity_id){
        filter={field:"activity_type", type:"=", value: activity_id};
        if( currentActivityFilter.length ==0)
            eventsTable.addFilter( [filter]);
        else{
            eventsTable.removeFilter(currentActivityFilter);
            eventsTable.addFilter( [filter]);
        }
    }

    refreshFilterDisplay();
}

function togglePastActivities(element){

    if ( ! element.checked){
        eventsTable.addFilter( [{field:"end", type:">=", value:"now" }]);
    }else{
        endfilter=eventsTable.getFilters().filter(function(i ){ return i['field'] == "end" });
        eventsTable.removeFilter(endfilter);
    }

}

function toggleConfirmedOnly(confirmedOnly){

    if (confirmedOnly){
        eventsTable.addFilter( [{field:"status", type: "!=", value:  'Cancelled'  }]);
    }else{
        statusFilter=eventsTable.getFilters().filter(function(i ){ return i['field'] == "status" });
        eventsTable.removeFilter(statusFilter);
    }

}

function refreshFilterDisplay(){
    var filters = eventsTable.getFilters();
    // Unselect all activity filter buttons
    document.getElementById('select_all').checked = true;

    // Select activity filter button which appears in tabulator filter
    // and redresh checkboxes status
    for (filter of filters) {
        if (filter['field'] == 'activity_type')
            document.getElementById('select_'+filter['value']).checked = true;
    }


    var showCancelled = filters.filter(function(filter){ return filter['field'] == "status" }).length == 0 ;
    document.getElementById('cancelledcheckbox').checked = showCancelled;

    var showPast = filters.filter(function(filter){ return filter['field'] == "end" }).length == 0 ;
    document.getElementById('pastcheckbox').checked = showPast;
}

// Put age number in browser URL
function updatePageURL(){
    var page = eventsTable.getPage();
    var location = document.location.toString().split('#');
    document.location = `${location[0]}#p${page}` ;
}

function gotoEvents(event){
    console.log(event);
    // if we are not on top during a load, do not mess with page position
    if(window.scrollY > 50 && event.type !== 'click')
        return 0;

    var position = document.querySelector('#eventlist').getBoundingClientRect().top +  window.scrollY - 60;
    window.scrollTo(    {
            top: position,
            behavior: 'smooth'
        });
}
