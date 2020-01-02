var locale = window.navigator.userLanguage || window.navigator.language;
var eventstable;
moment.locale(locale);

window.onload = function(){
    var common_options = {
        layout:"fitDataFill",
        ajaxURL: ajaxURL, // URL is defined in template

        paginationSize : 10,
        initialSort: [ {column:"start", dir:"asc"}],
        initialFilter: [
            {field:"end", type:">", value:  getServerLocalTime()}
        ],
        columns:[
            {title: "Type",         field:"activity_types", formatter: typesFormatter     },
            {title: "Titre",        field:"title",          sorter:"string"                 },
            {title: "Date",         field:"start",          sorter:"string",             formatter:"datetime",
                    formatterParams:{   outputFormat:"dddd D MMMM YYYY", invalidPlaceholder:"(invalid date)",}  },
            {title: "Participants", field: "occupied_slots" },
            {title: "Encadrant",    field:"leaders",        formatter: leadersFormatter     }
        ],
        rowClick: function(e, row){ document.location= row.getData().view_uri},
    };


    var eventstable= new Tabulator("#eventstable",
                    Object.assign(common_options, {   initialFilter: [
                                {field:"end", type:">", value:getServerLocalTime() }
                            ]}));
    var pasteventstable= new Tabulator("#pasteventstable",
                    Object.assign(common_options, {   initialFilter: [
                                {field:"end", type:"<", value:getServerLocalTime()  }
                            ]}));
}

function leadersFormatter(cell, formatterParams, onRendered){
    var names = cell.getValue().map((leader) => leader['name']);
    return names.join('<br/>');
}

function typesFormatter(cell, formatterParams, onRendered){
    var names = cell.getValue().map((activity) => `<span class="activity ${activity['short']} s30px"></span>`);
    return names.join(' ');
}
