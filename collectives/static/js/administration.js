
function actionFormatter(cell, formatterParams, onRendered){
  return '<form style="display:inline; padding:0" action="'+ cell.getValue() +'" method="'+formatterParams['method']+'" ><input type="image" src="/static/img/icon/ionicon/md-'+formatterParams['icon']+'.svg" style="margin: 0;height: 1.2em; width: 1.2em" onclick="submit()"/></form>';
}

window.onload = function(){
    var table = new Tabulator("#users-table",
        {
          ajaxURL: '/api/users/',
          layout:"fitColumns",
          columns:[
            {field: 'avatar', formatter: 'image', formatterParams:{height: '1em'}},
            {title:"Email", field:"mail", headerFilter:"input", widthGrow:3},
            {title:"Admin", field:"isadmin",  formatter:"tick", widthGrow:1},
            {title:"Enable", field:"enabled",  formatter:"tickCross", widthGrow:1},
<<<<<<< HEAD
            { field:"manage",  formatter:actionFormatter, formatterParams:{'icon': 'create', 'method': 'GET'}},
            { field:"delete",  formatter:actionFormatter, formatterParams:{'icon': 'trash', 'method': 'POST'}},
=======
            {title:"Roles", field:"roles_uri",  formatter:"link", formatterParams:{label:"Gérer"}, widthGrow:1},
>>>>>>> master
    ],});
    console.log("Fin du chargement du tableau");
}
