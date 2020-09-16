
function createMyPaymentsTable(id, url, finalized)
{
    new Tabulator(id,
        {
          ajaxURL:url,
          layout:"fitColumns",

          columns:[
            {title:"Date", field:(finalized ? "finalization_time" : "creation_time"), widthGrow:1, headerFilter:true},
            {title:"Événement", field:"event_title", widthGrow:2, headerFilter:true},
            {title:"Objet", field:"item_title", widthGrow:2, headerFilter:true},
            {title:"Tarif", field:"price_title", widthGrow:2, headerFilter:true},
            {title:"Prix", field:(finalized ? "amount_paid" : "amount_charged"), widthGrow:1},
            {title:"Type", field:"payment_type", widthGrow:1, headerFilter:true},
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
        }
    });
}

