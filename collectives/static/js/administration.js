
function actionFormatter(cell, formatterParams, onRendered){
  return '<form style="display:inline; padding:0" action="'+ cell.getValue() +'" method="'+formatterParams['method']+'" ></form><input type="image" src="/static/img/icon/ionicon/md-'+formatterParams['icon']+'.svg" style="margin: 0;height: 1.2em; width: 1.2em"  alt="'+formatterParams['alt']+'" title="'+formatterParams['alt']+'"/>';
}

function onclickTriggerInsideForm(e, cell){
  cell._cell.element.querySelector('form').submit();
}

function roleFormatter(cell, formatterParams, onRendered){
    cell.getElement().style.width="100px";
    cell.getElement().style.height="auto";
    cell.getElement().style['white-space']="normal";
    cell.getElement().style.height="auto";
    
    return cell.getValue().map(displayRole).join(' ');
}

function displayRole(role){
    return `<span class=\"activity ${role['activity_type.short'] || 'none'} s30px\" title=\"${role['name']} ${role['activity_type.name'] || ''}\">
                <span class=\"activity role${role['role_id']} s30px\" ></span>
            </span>`;
}

var table;
window.onload = function(){
    table = new Tabulator("#users-table",
        {
          ajaxURL: '/api/users/',
          ajaxSorting:true,
          ajaxFiltering:true,
          layout:"fitColumns",

          pagination : 'remote',
          paginationSize : 50,

          columns:[
            {field:"avatar_uri", formatter: 'image', formatterParams:{height: '1em'}},
            {title:"Actif", field:"enabled",  formatter:"tickCross", widthGrow:1},
            {title:"Email", field:"mail", headerFilter:"input", widthGrow:3, formatter:"link", formatterParams:{urlField:"profile_uri"}},
            {title:"Prénom", field:"first_name", headerFilter:"input", widthGrow:3, formatter:"link", formatterParams:{urlField:"profile_uri"}},
            {title:"Nom", field:"last_name", headerFilter:"input", widthGrow:3, formatter:"link", formatterParams:{urlField:"profile_uri"}},
            {title:"Roles", field:"roles", headerFilter: "select", headerFilterParams: {values:filters}, formatter:roleFormatter, headerSort:false,  widthGrow:2},
            {field:"roles_uri",   formatter:actionFormatter, formatterParams:{'icon': 'ribbon', 'method': 'GET', 'alt': 'Roles'},   cellClick: onclickTriggerInsideForm, headerSort:false},
            {field:"manage_uri",  formatter:actionFormatter, formatterParams:{'icon': 'create', 'method': 'GET', 'alt': 'Edition'}, cellClick: onclickTriggerInsideForm, headerSort:false},
            {field:"delete_uri",  formatter:actionFormatter, formatterParams:{'icon': 'trash', 'method': 'POST', 'alt': 'Delete'},  cellClick: onclickTriggerInsideForm, headerSort:false},
            ],

            locale:true,
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
}

var export_table;
function exportXLSX(){
    var filters = table.getFilters(true);
    
    //if there is no filter on role, we refuse the export.
    if( ! filters.map(function(i){return i['field']}).includes('roles') ){
        alert('Il faut sélectionner un role pour l\'exporter.');
        return false;
    }
        
    
    export_table = new Tabulator("#export-table", {
            ajaxURL: '/api/users/?filter_role=true',
            ajaxSorting:true,
            ajaxFiltering:true,
            pagination : 'remote',
            paginationSize : 9999999,
            columns:[
              {title:"Licence", field:"license",},
              {title:"Prénom", field:"first_name",},
              {title:"Nom", field:"last_name",},
              {title:"Email", field:"mail",},
              {title:"Téléphone", field:"phone",},
              {title:"Role", field:"role",},
              {title:"Activité", field:"activity",},
            ],
            initialFilter: table.getFilters(true),
            ajaxResponse:function(url, params, response){
               //url - the URL of the request
               //params - the parameters passed with the request
               //response - the JSON object returned in the body of the response.
               // This function aims to duplicate rows when user has several roles.
               newResponse = {'last_page': response['last_page'], 'data': []}
               for (user in response['data']) 
                    for (role in response['data'][user]['roles']){
                        user_data = Object.assign({}, response['data'][user]);
                        user_data['role'] = user_data['roles'][role]['name'];
                        user_data['activity'] = user_data['roles'][role]['activity_type.name'];
                        newResponse['data'].push(user_data);
                    }
              
               return newResponse; 
           },
            pageLoaded: function(){
                export_table.download("xlsx", "Listing.xlsx", {sheetName:"Liste"});
            }
        }
    ); 
}
