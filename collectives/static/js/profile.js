var locale = window.navigator.userLanguage || window.navigator.language;
var eventstable;
moment.locale(locale);

window.onload = function(){
    var common_options = {
        layout:"fitColumns",
        ajaxURL: ajaxURL, // URL is defined in template

        paginationSize : 10,
        initialSort: [ {column:"start", dir:"asc"}],
        initialFilter: [
            {field:"end", type:">", value:  getServerLocalTime()},
        ],
        responsiveLayout:true,
        paginationSize: [50,100,200],
        columns:[
            {title: "Type",     field:"event_types", formatter: typesFormatter, maxWidth:100, variableHeight: true, headerFilter:"select",
                    headerFilterParams:{values: addEmpty(EnumEventType)}, headerFilterFunc: multiEnumFilter, responsive: 3, minWidth: 35   },
            {title: "Activité",     field:"activity_types", formatter: typesFormatter, maxWidth:100, variableHeight: true, headerFilter:"select",
                    headerFilterParams:{values: addEmpty(EnumActivityType)}, headerFilterFunc: multiEnumFilter, responsive: 1, minWidth: 35   },
            {title: "Tags",         field:"tags",           formatter: tagsFormatter,  maxWidth:100, variableHeight:true, headerFilter:"select",
                    headerFilterParams:{values: addEmpty(EnumEventTag)},     headerFilterFunc: multiEnumFilter, responsive: 2, minWidth: 35   },
            {title: "État",         field:"status",         sorter:"string",           headerFilter:"select",  formatterParams:{'enum': EnumEventStatus},
                    headerFilterParams:{values: addEmpty(EnumEventStatus)}, formatter: enumFormatter, minWidth: 60},
            { title:"Statut", field:"registration.status", headerFilter:"select", headerFilterParams:{values: addEmpty(EnumRegistrationStatus)},
                formatter: enumFormatter, formatterParams:{'enum': EnumRegistrationStatus}, responsive:1, minWidth: 120 },
            {title: "Titre",        field:"title",          sorter:"string",           headerFilter:"input", formatter:"textarea", widthGrow: 2.5, responsive:0, minWidth: 200},
            {title: "Date",         field:"start",          sorter:"string",           formatter:"datetime",
                    formatterParams:{   outputFormat:"D/M/YY", invalidPlaceholder:"(invalid date)"}, responsive:1, minWidth: 60},
            {title: "Insc.", field:"occupied_slots", maxWidth:80, responsive:4, minWidth: 80},
            {title: "Encadrant",    field:"leaders",        formatter: leadersFormatter, headerFilter:true, 
                    headerFilterFunc: leaderFilter, variableHeight: true, widthGrow: 2, responsive:3, minWidth: 60 },
            
        ],
        rowClick: function(e, row){ document.location= row.getData().view_uri},
    };


    var is_user_profile = ajaxURL.match(/^\/api\/user/);

    if(is_user_profile) {
        common_options = Object.assign(common_options),
            {
            groupBy: function(data){
                //data - the data object for the row being grouped
                return EnumRegistrationStatus[data.registration.status];
            }}
        }

    var eventstable= new Tabulator("#eventstable",
                    Object.assign(common_options, {   initialFilter: [
                                {field:"end", type:">", value:getServerLocalTime() },
                            ]}));
    var pasteventstable= new Tabulator("#pasteventstable",
                    Object.assign(common_options, {   initialFilter: [
                                {field:"end", type:"<", value:getServerLocalTime()  }],
                                initialSort: [ {column:"start", dir:"desc"}],
                            }));

    if(is_user_profile){

        var waitingtable= new Tabulator("#waitingtable",
        Object.assign(common_options, {   initialFilter: [
                    {field:"end", type:">", value:getServerLocalTime() },
                ]}));

        eventstable.hideColumn("registration.status")
        eventstable.addFilter("registration.status", "=", EnumRegistrationStatusKeys["Active"]);

        waitingtable.hideColumn("registration.status")
        waitingtable.addFilter("registration.status", "=", EnumRegistrationStatusKeys["Waiting"]);

        pasteventstable.addFilter("registration.status", "!=", EnumRegistrationStatusKeys["Waiting"]);
    }

}

function leadersFormatter(cell, formatterParams, onRendered){
    var names = cell.getValue().map((leader) => leader['name']);
    return names.join('<br/>');
}

function leaderFilter(value, data){
    var regex = new RegExp(value, "i");
    return regex.test( data.map(leader => leader['name']).join(' ') );
}

function typesFormatter(cell, formatterParams, onRendered){
    var names = cell.getValue().map((activity) => `<span class="activity ${activity['short']} s30px"></span>`);
    return names.join(' ');
}

function tagsFormatter(cell, formatterParams, onRendered){
    var names = cell.getValue().map((tag) => `<span class="activity s30px ${tag['short']} type" title="${tag['name']}"></span> `);
    return names.join(' ');
}

function multiEnumFilter(value, data){
    if(value == 0)
        return true;
    return data.map(item => item.id).includes(parseInt(value));
}
function enumFormatter(cell, formatterParams, onRendered){
    return formatterParams['enum'][cell.getValue()];
}
function addEmpty(dict){
    var copy={};
    copy['']="";
    Object.assign(copy, dict);
    return copy;
}
