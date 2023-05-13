

function createPaymentsTable(url)
{
    return new Tabulator("#payments-table",
        {
          ajaxURL: url,
          layout:"fitColumns",

          ajaxFiltering: true,
          pagination: 'remote',
          paginationSize: 1,
          headerSort:false,
          paginationSize : 50,
          paginationSizeSelector:[ 50, 100, 200, 500],

          nestedFieldSeparator: false,
          columns:[
            {title:"État", field:"status", widthGrow:1, headerFilter:true,  editor:"select", editorParams:{values: addEmpty(EnumPaymentStatus)}, headerFilterParams:{values: addEmpty(EnumPaymentStatus)}},
            {title:"Date", field:"finalization_time", widthGrow:1.2, headerFilter:dateFilterEditor, formatter:"datetime", formatterParams: { outputFormat:"DD/MM/YYYY" }},
            {title:"Objet", field:"item.title", widthGrow:2, headerFilter:true},
            {title:"Tarif", field:"price.title", widthGrow:2, headerFilter:true},
            {title:"Payé", field:"amount_paid", widthGrow:1},
            {title:"Type", field:"payment_type", widthGrow:1, headerFilter:true, editor:"select", editorParams:{values: addEmpty(EnumPaymentType)}, headerFilterParams:{values: addEmpty(EnumPaymentType)}},
            {title:"Adhérent", field:"buyer_name", widthGrow:2, headerFilter:true},
            {title:"Inscription", field:"registration_status", widthGrow:1, headerFilter:true,  editor:"select", editorParams:{values: addEmpty(EnumRegistrationStatus)}, headerFilterParams:{values: addEmpty(EnumRegistrationStatus)}},
            {title:"Ref payline", field:"processor_order_ref", widthGrow:2, headerFilter:true},    
        ],

        rowClick:function(e, row){
            document.location.href = row.getData().details_uri;
        },

        locale:true,
        langs:{
            "fr":{
                "ajax":{
                    "loading":"Chargement", //ajax loader text
                    "error":"Erreur", //ajax error text
                },
            }
        },
});
}

function createAllPaymentsTable(url)
{
    var table = createPaymentsTable(url);
    table.addColumn({title:"Événement", field:"item.event.title", widthGrow:2, headerFilter:true}, true);
    table.addColumn({
            title:"Activité",
            field:"item.event.activity_type_names",
            widthGrow:1.5,
            headerFilter:true,
            editor:"select",
            headerFilterParams:{values: addEmpty(EnumActivityType)}
        }, true);
    table.addColumn({
            title:"Type",
            field:"item.event.event_type.name",
            widthGrow:1.5,
            headerFilter:true,
            editor:"select",
            headerFilterParams:{values: addEmpty(EnumEventType)}
        }, true);
    return table;
}

function exportAsExcel(e)
{
    var params = table.modules.ajax.serializeParams({'filters':table.getFilters(true)});
    var url = e.href + "?" + params;
    document.location = url;
    return false;
}

function addEmpty(dict){
    Object.assign(dict, {"":""});
    return dict;
}

function dateFilterEditor(cell, onRendered, success, cancel, editorParams){

	var container = document.createElement('span');
    start = document.createElement('input');
    start.type = 'datetime';
    start.style.width="100%";
    end = document.createElement('input');
    end.type = 'datetime';
    end.style.width="100%";

    function buildDate(){
        success({
            start:start.value,
            end:end.value,
        });
    }

    start.addEventListener("change", buildDate);
    end.addEventListener("change", buildDate);


    var tailOpts = {locale: "fr", timeFormat: false,};
    tail.DateTime(start, tailOpts);
    tail.DateTime(end, tailOpts);

    container.append(start);
    container.append(document.createElement('br'));
    container.append(end);
	return container;
}
