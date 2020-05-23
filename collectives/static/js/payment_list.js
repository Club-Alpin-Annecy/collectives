
function detailsFormatter(cell, formatterParams, onRendered){
  return `<a href="${cell.getValue()}">Détails</a>`;
}

var table;
window.onload = function(){
    table = new Tabulator("#payments-table",
        {
          ajaxURL: `/api/payments/${getEventId()}/list`,
          layout:"fitColumns",

          columns:[
            {title:"État", field:"status", widthGrow:1},
            {title:"Objet", field:"item_title", widthGrow:2},
            {title:"Tarif", field:"price_title", widthGrow:2},
            {title:"Prix", field:"amount_charged", widthGrow:1},
            {title:"Type", field:"payment_type", widthGrow:1},
            {title:"Adhérent", field:"creditor_name", widthGrow:2},
            {title:"Inscription", field:"registration_status", widthGrow:1},
            {field:"details_uri",   formatter:detailsFormatter, formatterParams:{}, headerSort:false}
            ],

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

