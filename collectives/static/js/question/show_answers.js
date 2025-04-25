

function actionFormatter(csrfToken) {
    return function (cell, formatterParams, onRendered) {
        if(cell.getValue() == "") return '';
        return `<form style="display:inline; padding:0" action="${cell.getValue()}" method="${formatterParams['method']}" >` +
            `<input style="display:none" name="csrf_token" type+"hidden" value="${csrfToken}">` +
            '</form>' +
            `<input type="image" src="/static/img/icon/ionicon/md-${formatterParams['icon']}.svg" style="margin: 0;height: 1.2em; width: 1.2em"  alt="${formatterParams['alt']}" title="${formatterParams['alt']}"/>`;
    };
}

function submitDeleteForm(e, cell) {
    if (confirm("Voulez vous vraiment supperimer cette réponse ?")) {    
       cell._cell.element.querySelector('form').submit();
    }
}

function makeStatusFilter(){
    dict = EnumRegistrationStatus
    dict[EnumRegistrationStatusKeys["ToBeDeleted"]] = "Supprimée"

    Object.assign(dict, {"":""});
    return dict;
}

function createShowAnswersTable(url, csrfToken)
{
    table =  new Tabulator("#answers-table",
        {
          ajaxURL: url,
          layout:"fitColumns",
          groupBy:"question.title",
          headerSort:true,
          columns:[
            {title:"Auteur", field:"user.full_name", widthGrow:1, headerFilter:true},
            {title:"État", field:"registration_status", widthGrow:1, headerFilter:true, editor: "select", headerFilterParams:{values: makeStatusFilter()}},
            {title:"Réponse", field:"value", widthGrow:4, headerFilter:true, formatter:"textarea"},
            {field: "delete_uri", formatter: actionFormatter(csrfToken), formatterParams: { 'icon': 'trash', 'method': 'POST', 'alt': 'Delete' }, cellClick: submitDeleteForm, headerSort: false },
            {field:"question.title"}, // required for header, hidden
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

    table.hideColumn("question.title");
    return table;
}
