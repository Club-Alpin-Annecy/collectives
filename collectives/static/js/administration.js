
function actionFormatter(cell, formatterParams, onRendered){
  return '<form style="display:inline; padding:0" action="'+ cell.getValue() +'" method="'+formatterParams['method']+'" ><input type="hidden" name="csrf_token" value="' + csrf_token + '"/></form><input type="image" src="/static/img/icon/ionicon/md-'+formatterParams['icon']+'.svg" style="margin: 0;height: 1.2em; width: 1.2em"  alt="'+formatterParams['alt']+'" title="'+formatterParams['alt']+'"/>';
}
function onclickTriggerInsideForm(e, cell){
  cell._cell.element.querySelector('form').submit();
}

window.onload = function(){
    var table = new Tabulator("#users-table",
        {
          ajaxURL: '/api/users/',
          layout:"fitColumns",
          columns:[
            {field:"avatar_uri", formatter: 'image', formatterParams:{height: '1em'}},
            {title:"Email", field:"mail", headerFilter:"input", widthGrow:3},
            {title:"Admin", field:"isadmin",  formatter:"tick", widthGrow:1},
            {title:"Enable", field:"enabled",  formatter:"tickCross", widthGrow:1},
            {field:"roles_uri",   formatter:actionFormatter, formatterParams:{'icon': 'ribbon', 'method': 'GET', 'alt': 'Roles'},   cellClick: onclickTriggerInsideForm},
            {field:"manage_uri",  formatter:actionFormatter, formatterParams:{'icon': 'create', 'method': 'GET', 'alt': 'Edition'}, cellClick: onclickTriggerInsideForm},
            {field:"delete_uri",  formatter:actionFormatter, formatterParams:{'icon': 'trash', 'method': 'POST', 'alt': 'Delete'},  cellClick: onclickTriggerInsideForm},
    ],});
    console.log("Fin du chargement du tableau");
}
