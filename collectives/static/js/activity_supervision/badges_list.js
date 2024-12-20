
const onSelectAutocomplete = function (id, value) {
    document.getElementById('user-search-resultid').value = id;
    document.getElementById('user-search-form').submit();
}

function actionFormatter(csrfToken) {
    return function (cell, formatterParams, onRendered) {
        if(cell.getValue() == "") return '';
        return `<form style="display:inline; padding:0" action="${cell.getValue()}" method="${formatterParams['method']}" >` +
            `<input style="display:none" name="csrf_token" type+"hidden" value="${csrfToken}">` +
            '</form>' +
            `<input type="image" src="/static/img/icon/ionicon/${formatterParams['icon']}.svg" style="margin: 0;height: 1.2em; width: 1.2em"  alt="${formatterParams['alt']}" title="${formatterParams['alt']}"/>`;
    };
}

function onclickTriggerInsideForm(e, cell) {
    cell._cell.element.querySelector('form').submit();
}

function profileUrl(cell) {
    return cell.getData().user.profile_uri;
}

function loadBadgesTable(ajaxUrl, ajaxParams, csrfToken) {
    var table = new Tabulator("#badges-table",
        {
            ajaxURL: ajaxUrl,
            ajaxParams: ajaxParams,
            layout: "fitColumns",
            pagination:"local",
            paginationSize: 50,

            columns: [
                { field: "user.avatar_uri", formatter: 'image', formatterParams: { height: '1em' } },
                { title: "Nom", field: "user.full_name", headerFilter: "input", widthGrow: 3, formatter: "link", formatterParams: { url: profileUrl } },
                { title: "Activité", field: "activity_type.name", headerFilter: "input", widthGrow: 3 },
                { title: "Badge", field: "type", headerFilter: "input", widthGrow: 3, visible: false },
                { title: "Expiration", field: "expiration_date", headerFilter: "input", widthGrow: 3},
                { title: "Niveau", field: "level", headerFilter: "input", widthGrow: 2, visible: true},
                { field: "delete_uri", formatter: actionFormatter(csrfToken), formatterParams: { 'icon': 'md-trash', 'method': 'POST', 'alt': 'Delete' }, cellClick: onclickTriggerInsideForm, headerSort: false },
                { field: "renew_uri", formatter: actionFormatter(csrfToken), formatterParams: { 'icon': 'refresh', 'method': 'POST', 'alt': 'Renouveler' }, cellClick: onclickTriggerInsideForm, headerSort: false },            
            ],

            langs: {
                "fr-fr": {
                    "ajax": {
                        "loading": "Chargement", //ajax loader text
                        "error": "Erreur", //ajax error text
                    },
                }
            },
        }); 
        
        if(level)
            table.showColumn('level');
        if(badge)
            table.showColumn('type');
}
