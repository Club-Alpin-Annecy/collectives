
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

    return '<ul>' + cell.getValue().map(displayRole).join(' ') + '</ul>';
}

function badgeFormatter(cell, formatterParams, onRendered){
    cell.getElement().style.width="100px";
    cell.getElement().style.height="auto";
    cell.getElement().style['white-space']="normal";
    cell.getElement().style.height="auto";

    return `<ul> ${cell.getValue().map(displayBadge).join(' ')} </ul>`;
}

function displayRole(role){
    return `<li>${role['name']} ${role.activity_type?.name || ''}</li>`
}

function displayBadge(badge){
    return `<li>${badge['name']} ${badge.activity_type?.name || ''}</li>`
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
          paginationSizeSelector:[50, 100, 200],

          columns:[
            {field:"avatar_uri", formatter: 'image', formatterParams:{height: '1em'}},
            {title:"Actif", field:"enabled",  formatter:"tickCross", widthGrow:1},
            {title:"Email", field:"mail", headerFilter:"input", widthGrow:3, formatter:"link", formatterParams:{urlField:"profile_uri"}},
            {title:"Prénom", field:"first_name", headerFilter:"input", widthGrow:3, formatter:"link", formatterParams:{urlField:"profile_uri"}},
            {title:"Nom", field:"last_name", headerFilter:"input", widthGrow:3, formatter:"link", formatterParams:{urlField:"profile_uri"}},
            {title:"Roles", field:"roles", headerFilter: "select", headerFilterParams: filters, formatter:roleFormatter, headerSort:false,  widthGrow:2},
            {title:"Badges", field:"badges", headerFilter: "select", headerFilterParams: filters_badge, formatter:badgeFormatter, headerSort:false,  widthGrow:4},
            {field:"roles_uri",   formatter:actionFormatter, formatterParams:{'icon': 'ribbon', 'method': 'GET', 'alt': 'Roles'},   cellClick: onclickTriggerInsideForm, headerSort:false},
            {field:"badges_uri",   formatter:actionFormatter, formatterParams:{'icon': 'pricetags-outline', 'method': 'GET', 'alt': 'Badges'},   cellClick: onclickTriggerInsideForm, headerSort:false},
            {field:"manage_uri",  formatter:actionFormatter, formatterParams:{'icon': 'create', 'method': 'GET', 'alt': 'Edition'}, cellClick: onclickTriggerInsideForm, headerSort:false},
            {field:"delete_uri",  formatter:actionFormatter, formatterParams:{'icon': 'trash', 'method': 'GET', 'alt': 'Delete'},  cellClick: onclickTriggerInsideForm, headerSort:false},
            ],

            locale:true,
            langs:{
                "fr-fr":{
                    "ajax":{
                        "loading":"Chargement", //ajax loader text
                        "error":"Erreur", //ajax error text
                    },
                    "pagination":{
                        "page_size":"Adhérents par page", //label for the page size select element
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

function exportXLXS(element){
    allFilters = table.getFilters(true);
    filter = allFilters.filter(function(f){ return f['field'] == 'roles' });

    if(filter[0]['value'] == undefined)
        alert('Vous devez sélectionner un filtre pour pouvoir exporter les rôles.');
    else
        document.location = element.href + filter[0]['value'];

    return false;
}

function doExport(){
    const data = new FormData();
    data.append('csrf_token', window.csrfToken);
    const allFilters = table.getFilters(true);
    allFilters.forEach((filter, index) => {
        data.append(`filters[${index}][field]`, filter.field);
        data.append(`filters[${index}][value]`, filter.value);
    });

    fetch('/administration/users/export', {
        method: 'POST',
        body: data,
    }).then(response => {
        if (!response.ok) {
            throw new Error('Erreur serveur');
        }
        const filename = response.headers.get('Content-Disposition')
            ?.split('filename=')[1]?.replace(/"/g, '') || 'export.xlsx';
        return response.blob().then(blob => ({ blob, filename }));
    }).then(({ blob, filename }) => {
        const url = window.URL.createObjectURL(blob);
        const link = document.createElement('a');
        link.href = url;
        link.download = filename;
        document.body.appendChild(link);
        link.click();
        document.body.removeChild(link);
        window.URL.revokeObjectURL(url);
    }).catch(error => {
        alert('Erreur lors de l\'export: ' + error.message);
    });
}

function exportSearchXLXS(){
    const allFilters = table.getFilters(true);

    if (allFilters.length === 0) {
        const modal = document.getElementById('export-confirm-modal');
        const message = document.getElementById('export-confirm-message');
        const btnCancel = document.getElementById('export-confirm-cancel');
        const btnProceed = document.getElementById('export-confirm-proceed');

        message.textContent = 'Aucun filtre actif. Tous les utilisateurs seront exportés. Continuer ?';
        modal.classList.add('display-flex');
        modal.classList.remove('display-none');

        const closeModalAndCleanup = () => {
            modal.classList.add('display-none');
            modal.classList.remove('display-flex');
            btnCancel.removeEventListener('click', handleCancel);
            btnProceed.removeEventListener('click', handleProceed);
        };

        const handleCancel = () => {
            closeModalAndCleanup();
        };

        const handleProceed = () => {
            closeModalAndCleanup();
            doExport();
        };

        btnCancel.addEventListener('click', handleCancel);
        btnProceed.addEventListener('click', handleProceed);
    } else {
        doExport();
    }

    return false;
}
