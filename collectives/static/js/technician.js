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
    configurationTable = new Tabulator("#configuration-table",
        {
          ajaxURL: '/api/administration/configuration',
          layout:"fitColumns",

          pagination : 'local',
          paginationSize : 20,
          paginationSizeSelector:[10, 20, 50, 100, 200],

          columns:[
            {field:"name",  formatter:"link",  title:"Nom", headerFilter:true, formatterParams:{
                labelField :"name",
                urlPrefix:"https://doc.collectives.cafannecy.fr/configuration.html#config.",
                }},
            {field:"content", title:"Valeur", headerFilter: "input", formatter: "textarea", 
                    editor: true, cellEdited: updateConf, 
                    mutatorData :  (data) => data.replaceAll('\\n', '\n') 
                },
         ],

            locale:true,
            langs:{
                "fr-fr":{
                    "ajax":{
                        "loading":"Chargement", //ajax loader text
                        "error":"Erreur", //ajax error text
                    },
                    "pagination":{
                        "page_size":"Configuration par page", //label for the page size select element
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


// Check then upload the modified configuration item into server
// Checks are rudimentary.
function updateConf(cell){
    var data = cell.getRow().getData();
    console.log(data['content']);
    data['content'] = patchNewLine(data['content']);

    if(! isJsonString(data['content'])){
        alert('La valeur n\'est pas correcte: ce n\'est pas une chaine JSON. Veuillez la corriger');
        console.error("Wrong JSON:")
        console.error(data['content'])
        return false;
    }

    if(! confirm(`Vous allez mettre à jour ${data['name']}. Confirmez-vous?`)){
        return false;
    }

    xhr = new XMLHttpRequest();
    xhr.open('POST', '/api/administration/configuration');
    xhr.setRequestHeader('Content-Type', 'application/json');
    xhr.setRequestHeader('X-CSRFToken', csrf_token);
    xhr.onload = function() {
        if (xhr.status === 200) {
            cell.getTable().replaceData();
        }
        else {
            cell.getTable().replaceData();
            alert('Request failed.  Returned status of ' + xhr.status);
        }
    };
    xhr.send(JSON.stringify(data));
    
}

// Check if the string is a valid JSON dump
function isJsonString(str) {
    try {
        JSON.parse(str);
    } catch (e) {
        return false;
    }
    return true;
}

/* Function to convert newLines into \n in JSON strings.
It does not convert new line outside JSON strings */
function patchNewLine(dataString){
    var data = Array.from(dataString);

    // Status indicates if we are in a string
    var status = "";

    for (let i = 0; i < data.length; i++) {
        if (data[i] == "\n" && status != ""){ // Replace \n in string
            data[i] = "\\n"
        } else if (data[i] == status){        // Detect string closure
            status = "";
        } else if(['"', "'"]. includes(data[i]) && status == ""){ // Detect string opening
            status = data[i];
        }

    }

    return data.join("");
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