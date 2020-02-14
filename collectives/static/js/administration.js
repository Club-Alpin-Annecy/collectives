
function actionFormatter(cell, formatterParams, onRendered){
  return '<form style="display:inline; padding:0" action="'+ cell.getValue() +'" method="'+formatterParams['method']+'" ></form><input type="image" src="/static/img/icon/ionicon/md-'+formatterParams['icon']+'.svg" style="margin: 0;height: 1.2em; width: 1.2em"  alt="'+formatterParams['alt']+'" title="'+formatterParams['alt']+'"/>';
}
function onclickTriggerInsideForm(e, cell){
  cell._cell.element.querySelector('form').submit();
}

window.onload = function(){
    var table = new Tabulator("#users-table",
        {
          ajaxURL: '/api/users/',
          ajaxSorting:true,
          ajaxFiltering:true,
          layout:"fitColumns",

          pagination : 'remote',
          paginationSize : 50,

          columns:[
            {field:"avatar_uri", formatter: 'image', formatterParams:{height: '1em'}},
            {title:"Email", field:"mail", headerFilter:"input", widthGrow:3, formatter:"link", formatterParams:{urlField:"profile_uri"}},
            {title:"Prénom", field:"first_name", headerFilter:"input", widthGrow:3, formatter:"link", formatterParams:{urlField:"profile_uri"}},
            {title:"Nom", field:"last_name", headerFilter:"input", widthGrow:3, formatter:"link", formatterParams:{urlField:"profile_uri"}},
            {title:"Admin", field:"isadmin",  formatter:"tick", widthGrow:1},
            {title:"Enable", field:"enabled",  formatter:"tickCross", widthGrow:1},
            {field:"roles_uri",   formatter:actionFormatter, formatterParams:{'icon': 'ribbon', 'method': 'GET', 'alt': 'Roles'},   cellClick: onclickTriggerInsideForm, headerSort:false},
            {field:"manage_uri",  formatter:actionFormatter, formatterParams:{'icon': 'create', 'method': 'GET', 'alt': 'Edition'}, cellClick: onclickTriggerInsideForm, headerSort:false},
            {field:"delete_uri",  formatter:actionFormatter, formatterParams:{'icon': 'trash', 'method': 'POST', 'alt': 'Delete'},  cellClick: onclickTriggerInsideForm, headerSort:false},
            ],
            langs:{
                "fr":{
                    "ajax":{
                        "loading":"Chargement", //ajax loader text
                        "error":"Erreur", //ajax error text
                    },
                    "pagination":{
                        "page_size":"Evénements par page", //label for the page size select element
                        "first":"Début", //text for the first page button
                        "first_title":"Première Page", //tooltip text for the first page button
                        "last":"Fin",
                        "last_title":"Dernière Page",
                        "prev":"Précédente",
                        "prev_title":"Page Précédente",
                        "next":"Suivante",
                        "next_title":"Page Suivante",
                    }
                }
            },
});
    console.log("Fin du chargement du tableau");
}
