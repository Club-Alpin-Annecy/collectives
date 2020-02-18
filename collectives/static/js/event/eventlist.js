
var locale = window.navigator.userLanguage || window.navigator.language;
var eventsTable;
moment.locale(locale);
String.prototype.capitalize = function() {
  return this.charAt(0).toUpperCase() + this.slice(1)
}

window.onload = function(){

  		eventsTable = new Tabulator("#eventstable", {
  			layout:"fitColumns",
  			ajaxURL: '/api/events/',
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
                if(sorters[0]['field'] != 'title')
                    eventsTable.setGroupBy(sorters[0]['field']);
                else
                    eventsTable.setGroupBy(false);
            },

            pagination : 'remote',
            paginationSize : 10,
            pageLoaded :  updatePageURL,

            initialSort: [ {column:"start", dir:"asc"}],
            initialFilter: [
                {field:"end", type:"=", value:  moment().format('YYYY-MM-DDTHH:mm:ss')  }
            ],
  			columns:[
      			{title:"Titre", field:"title", sorter:"string"},
                {title:"Date", field:"start", sorter:"string"},
  			],
  			    rowFormatter: eventRowFormatter,
            groupHeader:function(value, count, data, group){
                return moment(new Date(value)).format('dddd D MMMM YYYY').capitalize();
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

        // Try to extract and set page
        var page = document.location.toString().split('#p')[1];
        if(! isNaN(page) ){
            eventsTable.setMaxPage(page); // We extends max page to avoid an error
            eventsTable.setPage(page);
        }
        else
            console.log('No page defined')


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
    return moment(new Date(date)).format('ddd D MMM YY');
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


function toggleActivity(activity_id, element){
    filter={field:"activity_type", type:"=", value: activity_id};

    // Toggle filter
    currentActivityFilter=eventsTable.getFilters().filter(function(i ){ return i['field'] == "activity_type" });


    if (currentActivityFilter.length ==0)
        eventsTable.addFilter( [filter]);
    else if (currentActivityFilter[0]['value'] == activity_id)
        eventsTable.removeFilter(currentActivityFilter);
    else{
        eventsTable.removeFilter(currentActivityFilter);
        eventsTable.addFilter( [filter]);
    }

    refreshFilterDisplay();
}

function togglePastActivities(element){

    if ( ! element.checked){
        eventsTable.addFilter( [{field:"end", type:">=", value:getServerLocalTime() }]);
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
    for ( button of document.querySelectorAll('#eventlist #filters .activity') )
        button.classList.add('unselected');

    // Select activity filter button which appears in tabulator filter
    for (filter of filters)
        if (filter['field'] == 'activity_type')
            document.querySelector('#eventlist #filters .'+filter['value']).classList.remove('unselected');

    var onlyConfirmed = filters.filter(function(filter){ return filter['field'] == "status" && filter['value'] == 0 }).length == 0 ;
    document.getElementById('cancelledcheckbox').checked = onlyConfirmed;

    var onlyFuture = filters.filter(function(filter){ return filter['field'] == "end" }).length != 0 ;
    document.getElementById('pastcheckbox').checked = ! onlyFuture;
}

// Put age number in browser URL
function updatePageURL(){
    var page = eventsTable.getPage();
    var location = document.location.toString().split('#');
    document.location = `${location[0]}#p${page}` ;
}

function gotoEvents(event){
    // if we are not on top, do not mess with page position
    if(window.scrollY > 50)
        return 0;

    var position = document.querySelector('#eventlist').getBoundingClientRect().top +  window.scrollY - 60;
    window.scrollTo(    {
            top: position,
            behavior: 'smooth'
        });
}
