
var locale = window.navigator.userLanguage || window.navigator.language;
var eventsTable;
moment.locale(locale);
String.prototype.capitalize = function() {
    return this.charAt(0).toUpperCase() + this.slice(1)
}

function buildEventsTable() {

    var newSession = true;
    var itemsPerPage = 25;
    try {
        var currentTime = new Date();
        var sessionTime = sessionStorage.getItem("eventlist-sessionDate");
        if (sessionTime) {
            var elapsedMilliseconds = currentTime - Date.parse(sessionTime)
            if(elapsedMilliseconds < 86400 * 1000)
            {
                // Last seen less that a day ago, keep session filters
                newSession = false;

                // Retrieve persisted items per page
                sessionPageSize = sessionStorage.getItem("eventlist-sessionPageSize");
                if(sessionPageSize) {
                    itemsPerPage = parseInt(sessionPageSize)
                }
            }
        }
        sessionStorage.setItem("eventlist-sessionDate", currentTime)
    } catch(error) {}

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
        paginationSize : itemsPerPage,
        paginationSizeSelector:[25, 50, 100],
        pageLoaded :  updatePageURL,

        initialSort: [ {column:"start", dir:"asc"}],
        columns:[
            {title:"Titre", field:"title", sorter:"string"},
            {title:"Date", field:"start", sorter:"string"},
            {title:"Encadrant", field:"leaders", headerSort:false},
        ],
        headerVisible:false,
        rowFormatter: eventRowFormatter,
        groupHeader:function(value, count, data, group){
            return value;
        },

        locale: 'fr-fr',
        langs:{
            "fr-fr":{
                "ajax":{
                    "loading":"Chargement", //ajax loader text
                    "error":"Erreur", //ajax error text
                },
                "pagination":{
                    "page_size":"Collectives par page", //label for the page size select element
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

    if(newSession) {
        // Don't keep stored filters about leader, date and title
        // between browser sessions
        removeFilter(eventsTable, 'leaders');
        removeFilter(eventsTable, 'start');
        removeFilter(eventsTable, 'end');
        removeFilter(eventsTable, 'title');

        document.querySelector('#datefilter').value = moment().format("MM/DD/YYYY");
    }

   document.querySelectorAll('.tabulator-paginator button').forEach(function(button){
       button.addEventListener('click', gotoEvents);
   });

   document.querySelectorAll('.tabulator-pages').forEach(function(buttons){
       buttons.addEventListener('click', gotoEvents);
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

   var tailOpts = {locale: "fr", dateFormat: "dd/mm/YYYY", timeFormat: false,};
   tail.DateTime(document.querySelector('#datefilter'), tailOpts);

   refreshFilterDisplay();
}

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
        divRow.className = "row tabulator-cell collectives-list--item";
        divRow.setAttribute("role","gridcell");
        divRow.setAttribute("href", data.view_uri);

        html += `<div class="section collectives-list--item--photo">
                    <img src="${data.photo_uri}"/>
                 </div>`;

        var status_string = getStatusString(data)
        var visibility_string = getVisibilityString(data)
        var availabilities_badge = getSlotsAvailableBadge(data)

        if(status_string+visibility_string+availabilities_badge != "")
            var keywords = `
                <div class="collectives-list--item--details-keywords">
                    ${visibility_string}
                    ${status_string}
                    ${availabilities_badge}
                </div>`;
        else 
            keywords = "";

        html_type =  `<span class="item aligned-flex-inline"> 
                            <img src="/static/caf/icon/${data['event_types'][0]['short']}.svg" width="30px"  title="${data['event_types'][0]['name']}"/> 
                            <span>${data['event_types'][0]['name']}</span>         
                    </span>`;

        html_tags =  data.tags.map(tag => `
                    <span class="item aligned-flex-inline"> 
                        <img src="/static/caf/icon/${tag['short']}.svg" width="30px" title="${tag['name']}"/> 
                        <span>${tag['name']}</span>
                    </span>`);
        html_tags = html_tags.join(' ');

        html_mobile_activities =  data.activity_types.slice(0, 3).map(activity => `
                        <span class="item inline-mobile aligned-flex-inline">
                            <img src="/static/caf/icon/${activity['short']}.svg" width="30px"/>
                            <span>${activity['name']}</span> 
                        </span>`).join(' ')

        html_activities =  data.activity_types.slice(0, 3).map(activity => `<img src="/static/caf/icon/${activity['short']}.svg" alt="${activity['name']}" title="${activity['name']}"/>`).join(' ')
        

        html += `<div class="section collectives-list--item--details">
                    
                    
                    <div class="collectives-list--item--details-heading">

                        <div class="no_mobile collectives-list--item--details-date">
                            ${escapeHTML(data.formated_datetime_range)}
                        </div>

                        ${keywords}
                    
                        <div>${escapeHTML(data.title)}</div>
                    </div>

                    <div class="collectives-list--item--details-bottom-left" >
                        <div class="heading-3 no_mobile collectives-list--item--details-activity-type" >
                            ${html_activities}
                        </div>

                        <div class="mobile collectives-list--item--details-date">
                            ${escapeHTML(data.formated_datetime_range)}
                        </div>
                        <div class="leader collectives-list--item--details-leader">
                        ${data.leaders.slice(0, 2).map(displayLeader).join('<br/>')}
                        ${data.leaders.length>3 ? '...' : ''}
                        </div>
                    </div>

                    <div class="collectives-list--item--details-bottom-right" >
                        <div class="collectives-list--item--details-tags"> ${html_mobile_activities} ${html_type} ${html_tags}</div>
                        <div class="collectives-list--item--details-slots">
                        <div class="aligned-flex">
                            <div class="collectives-list--item--details-slots-bar">
                                <div
                                    class="collectives-list--item--details-slots-bar-filler" 
                                    style="width: ${100-data.free_slots/data.num_slots*100}%">
                                </div>
                            </div>
                            <div collectives-list--item--details-slots-count> 
                                ${Math.max(0, data.num_slots-data.free_slots)}/${data.num_slots}
                            </div>
                        </div>
                    </div>
                 </div>`;
        divRow.innerHTML = html;

        //append newly formatted contents to the row
        element.append(divRow);
    }
    catch(error){
      console.error(error);
    }
}

function getSlotsAvailableBadge(event) {
    "returns 'Full' badge when no more available slots, and 'waiting list' when there are availabilities in waiting list (whatever is the number of already registered"
    if (event.status != EnumEventStatusKeys.Cancelled)
        if (event.has_free_waiting_slots && (!event.has_free_online_slots))
            return `<span class="event-status-badge event-status-waiting-list ">Liste d'attente</span>`
        else if (!event.has_free_slots && !event.has_free_waiting_slots)
            return `<span class="event-status-badge event-status-full ">Complet</span>`
        else
            return ``
    else
        return ``
}

function getStatusString(data) {
    " Compute status string based on event status"
    status_string = ''
    if(!data.is_confirmed) status_string = `<span class="event-status-badge event-status-${data.status} ">${EnumEventStatus[data.status]}</span>`
    return status_string
}

function getVisibilityString(data) {
    " Compute visibility string based on event visibility"
    if(data.visibility == EnumEventVisibilityKeys.Activity) return `<span class="event-status-badge event-status-private">Interne</span>`
    if(data.visibility == EnumEventVisibilityKeys.External) return `<span class="event-status-badge event-status-external">Grand public</span>`
    return ''
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
    return escapeHTML(user.name);
}

function selectFilter(type, id){
    var currentFilter=eventsTable.getFilters().filter(function(i){ return i['field'] == type });

    if (currentFilter.length != 0)
        eventsTable.removeFilter(currentFilter);

    var filter={field: type, type:"=", value: id};
    if (false !== id)
            eventsTable.addFilter( [filter]);

    refreshFilterDisplay();
}

function filterConfirmedOnly(confirmedOnly){

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
    document.getElementById('select_all_tags').checked = true;
    document.getElementById('select_all_event_types').checked = true;

    // Select activity filter button which appears in tabulator filter
    // and redresh checkboxes status
    for (filter of filters) {
        // If at least one filter is set, we display filters list
        if(filter['field'] != 'end' || filter['value'] != moment().format("DD/MM/YYYY"))
            document.getElementById('collectives-list-filters-toggle').checked = true;

        if (filter['field'] == 'activity_type')
            document.getElementById('select_activity_type_'+filter['value']).checked = true;
        if (filter['field'] == 'event_type')
            document.getElementById('select_event_type_'+filter['value']).checked = true;
        if (filter['field'] == 'tags')
            document.getElementById('select_tag_'+filter['value']).checked = true;
        if (filter['field'] == 'end') {
            document.querySelector('#datefilter').value = filter['value'];
        }
        if (filter['field'] == 'title') {
            return document.querySelector('#title').value = filter['value'];
        }
        if (filter['field'] == 'leaders') {
            return document.querySelector('#leader').value = filter['value'];
        }
    }


    var showCancelled = filters.filter(function(filter){ return filter['field'] == "status" }).length == 0 ;
    document.getElementById('cancelledcheckbox').checked = showCancelled;

}

// Put age number in browser URL
function updatePageURL(){
    var page = eventsTable.getPage();
    var location = document.location.toString().split('#');
    document.location = `${location[0]}#p${page}` ;

    // Persist page size in session
    var pageSize = eventsTable.getPageSize();
    sessionStorage.setItem("eventlist-sessionPageSize", pageSize);
}

function gotoEvents(event){
    // if we are not on top during a load, do not mess with page position
    if(window.scrollY > 50 && event.type !== 'click')
        return 0;

    var position = document.querySelector('#eventlist').getBoundingClientRect().top +  window.scrollY - 60;
    window.scrollTo(    {
        top: position,
        behavior: 'smooth'
    });
}


// Functions to set up autocomplete of leaders

function getLeaderHeaderFilter() {
    return document.querySelector('#leader');
}

function onSelectLeaderAutocomplete(id, val) {
    const searchInput = getLeaderHeaderFilter();
    searchInput.value = val;
}

function filterTable(field, value) {
    removeFilter(eventsTable,field);
    if (value != "")
        eventsTable.addFilter(field, "like", value);
}



function removeFilter(table, type){
    table.getFilters().forEach(function(filter){
        if(filter['field'] == type)
            table.removeFilter(filter['field'], filter['type'], filter['value'])
    })
}