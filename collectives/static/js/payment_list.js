
var table;
window.onload = function(){
    table = new Tabulator("#payments-table",
        {
          ajaxURL: `/api/payments/${getEventId()}/list`,
          layout:"fitColumns",

          columns:[
            {title:"État", field:"status", widthGrow:1, headerFilter:true},
            {title:"Objet", field:"item_title", widthGrow:2, headerFilter:true},
            {title:"Tarif", field:"price_title", widthGrow:2, headerFilter:true},
            {title:"Payé", field:"amount_paid", widthGrow:1},
            {title:"Type", field:"payment_type", widthGrow:1, headerFilter:true},
            {title:"Adhérent", field:"creditor_name", widthGrow:2, headerFilter:true},
            {title:"Inscription", field:"registration_status", widthGrow:1, headerFilter:true},
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

