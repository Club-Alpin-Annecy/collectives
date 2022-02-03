var paymentItemTable;
document.addEventListener("DOMContentLoaded", function(){
    paymentItemTable = new Tabulator("#payment_item_table", {
        layout:"fitColumns",
        ajaxURL: `/api/event/${event_id}/prices`,
        nestedFieldSeparator: false,
        groupBy: "item.title",

        
        columns:[
            {title:"Titre", field:"item.title",  widthGrow:2, formatter: 'textarea'},
            {title:"Intitulé", field:"title", formatter: 'textarea'},
            {title:"Prix", field:"amount"},
            {title:"Début", field:"start_date", align:"center"},
            {title:"Fin", field:"end_date", align:"center"},
            {title:"Que<br/> Encadrant", field:"leader_only", formatter: 'tick', align:"center"},
            {title:"Nombre<br/> max", field:"max_uses", align:"center"},
            {title:"Type de<br/> licence", field:"license_types", align:"center", formatter: licenseFormatter}
        ],

        locale: 'fr-fr',
        langs:{
            "fr-fr":{
                "ajax":{
                    "loading":"Chargement", //ajax loader text
                    "error":"Erreur", //ajax error text
                },
            }
        },
    });
});


function licenseFormatter(cell, formatterParams, onRendered){
    text = cell.getValue();
    for (i in LicenseCategories){
        text = text.replace(i, `<acronym title="${LicenseCategories[i]}">${i}</acronym>`);
    }
    return `<div style="white-space: pre-wrap;" >${text}</div>`;
}