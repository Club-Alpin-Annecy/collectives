

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
            {title:"État", field:"status", widthGrow:1, headerFilter:true,  editor:"select", editorParams:{values: EnumPaymentStatus}, headerFilterParams:{values: EnumPaymentStatus}},
            {title:"Date", field:"creation_time", widthGrow:1.2, headerFilter:dateFilterEditor, headerFilterFunc:dateFilterFunction,  formatter:"datetime", formatterParams: { outputFormat:"DD/MM/YYYY" }},
            {title:"Objet", field:"item.title", widthGrow:2, headerFilter:true},
            {title:"Tarif", field:"price.title", widthGrow:2, headerFilter:true},
            {title:"Payé", field:"amount_paid", widthGrow:1},
            {title:"Type", field:"payment_type", widthGrow:1, headerFilter:true, editor:"select", editorParams:{values: EnumPaymentType}, headerFilterParams:{values: EnumPaymentType}},
            {title:"Adhérent", field:"buyer_name", widthGrow:2, headerFilter:true},
            {title:"Inscription", field:"registration_status", widthGrow:1, headerFilter:true,  editor:"select", editorParams:{values: EnumRegistrationStatus}, headerFilterParams:{values: EnumRegistrationStatus}},
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
    table.addColumn({title:"Collective", field:"item.event.title", widthGrow:2, headerFilter:true}, true, "name");
    table.addColumn({
            title:"Activité",
            field:"item.event.activity_types_names",
            widthGrow:1.5,
            headerFilter:true,
            editor:"select",
            editorParams:{values: EnumActivityType},
            headerFilterParams:{values: EnumActivityType}
        }, true, "name");
    return table;
}

function exportAsExcell(e)
{
    var params = table.modules.ajax.serializeParams({'filters':table.getFilters(true)});
    var url = e.href + "?" + params;
    document.location = url;
    return false;
}

//custom header filter
var dateFilterEditor = function(cell, onRendered, success, cancel, editorParams){

	var container = document.createElement('span');
    start = document.createElement('input');
    start.type = 'date';
    end = document.createElement('input');
    end.type = 'date';

    function buildDate(){
        success({
            start:start.value,
            end:end.value,
        });
    }

    start.addEventListener("change", buildDate);
    end.addEventListener("change", buildDate);


    container.append(start);
    container.append(document.createElement('br'));
    container.append(end);
	return container;
}

//custom filter function
function dateFilterFunction(headerValue, rowValue, rowData, filterParams){
    //headerValue - the value of the header filter element
    //rowValue - the value of the column in this row
    //rowData - the data for the row being filtered
    //filterParams - params object passed to the headerFilterFuncParams property
   console.log(headerValue);
   	var format = filterParams.format || "DD/MM/YYYY";
   	var start = Date.parse(headerValue.start);
   	var end = Date.parse(headerValue.end);
   	var value = Date.parse(rowValue)
    console.log(start);
    console.log(end);
    console.log(rowValue);
   	if(rowValue){
   		if(!isNaN(start)){
   			if(!isNaN(end)){
                console.log("SE");
   				return value >= start && value <= end;
   			}else{
                console.log("S");
   				return value >= start;
   			}
   		}else{
   			if(!isNaN(end)){
                console.log("E");
   				return value <= end;
   			}
   		}
   	}

    return true; //must return a boolean, true if it passes the filter.
}
