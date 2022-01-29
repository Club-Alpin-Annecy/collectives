var configurationTable;
var logsTable;


window.onload = function(){
    logsTable = new Tabulator("#logs-table",
        {
          data: files,
          layout:"fitColumns",

          pagination : 'local',
          paginationSize : 10,
          paginationSizeSelector:[5, 10 ,20, 50],
          initialSort:[{column: 'end', dir: 'desc'}],

          columns:[
            {field:"link",  formatter:"link",  title:"Nom", formatterParams:{labelField :"name"}},
            {field:"size", title:"Taille", formatter: sizeFormatter},
            {field:"start", formatter: 'datetime', title:"Date de début", formatterParams:{inputFormat:"X", outputFormat:"MM/DD/YYYY HH:mm:ss"}},
            {field:"end", formatter: 'datetime', title:"Date de fin", formatterParams:{inputFormat:"X", outputFormat:"MM/DD/YYYY HH:mm:ss"}},
         ],
    });
}


function sizeFormatter(cell){
    value = cell.getValue();
    units = [' B', ' kB', ' MB', ' GB', ' TB', 'PB', 'EB', 'ZB', 'YB'];
    while(value > 1024){
        value = value /1024;
        units.shift();
    }
    return Math.round(value*10)/10+ units[0];
}