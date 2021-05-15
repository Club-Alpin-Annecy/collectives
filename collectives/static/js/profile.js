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
        columns:[
            {title: "Activité",     field:"activity_types", formatter: typesFormatter, maxWidth:100, variableHeight: true, headerFilter:true,
                    editor:"select", headerFilterParams:{values: addEmpty(EnumActivityType)}, headerFilterFunc: multiEnumFilter   },
            {title: "Tags",         field:"tags",           formatter: tagsFormatter,  maxWidth:100, variableHeight:true, headerFilter:true,
                    editor:"select", headerFilterParams:{values: addEmpty(EnumEventTag)},     headerFilterFunc: multiEnumFilter   },
            {title: "État",         field:"status",         sorter:"string",           headerFilter:true,
                    editor:"select", headerFilterParams:{values: Object.values(addEmpty(EnumEventStatus))}},
            {title: "Titre",        field:"title",          sorter:"string",           headerFilter:"input", formatter:"textarea", widthGrow: 3},
            {title: "Date",         field:"start",          sorter:"string",           formatter:"datetime",
                    formatterParams:{   outputFormat:"D MMMM YY", invalidPlaceholder:"(invalid date)",}},
            {title: "Insc.", field:"occupied_slots", maxWidth:80,},
            {title: "Encadrant",    field:"leaders",        formatter: leadersFormatter, headerFilter:true, headerFilterFunc: leaderFilter, variableHeight: true, widthGrow: 2 }
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
    console.log(value); console.log(data);
    return data.map(item => item.id).includes(parseInt(value));
}

function addEmpty(dict){
    Object.assign(dict, {"":""});
    return dict;
}
