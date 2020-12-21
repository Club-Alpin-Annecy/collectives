
const onSelectAutocomplete = function (id, value) {
    document.getElementById('user-search-resultid').value = id;
    document.getElementById('user-search-form').submit();
}

function actionFormatter(csrfToken) {
    return function (cell, formatterParams, onRendered) {
        return `<form style="display:inline; padding:0" action="${cell.getValue()}" method="${formatterParams['method']}" >` +
            `<input style="display:none" name="csrf_token" type+"hidden" value="${csrfToken}">` +
            '</form>' +
            `<input type="image" src="/static/img/icon/ionicon/md-${formatterParams['icon']}.svg" style="margin: 0;height: 1.2em; width: 1.2em"  alt="${formatterParams['alt']}" title="${formatterParams['alt']}"/>`;
    };
}

function onclickTriggerInsideForm(e, cell) {
    cell._cell.element.querySelector('form').submit();
}

function profileUrl(cell) {
    return cell.getData().user.profile_uri;
}

function loadTraineesTable(ajaxUrl, csrfToken) {
    new Tabulator("#trainees-table",
        {
            ajaxURL: ajaxUrl,
            layout: "fitColumns",

            columns: [
                { field: "user.avatar_uri", formatter: 'image', formatterParams: { height: '1em' } },
                { title: "Prénom", field: "user.first_name", headerFilter: "input", widthGrow: 3, formatter: "link", formatterParams: { url: profileUrl } },
                { title: "Nom", field: "user.last_name", headerFilter: "input", widthGrow: 3, formatter: "link", formatterParams: { url: profileUrl } },
                { title: "Activité", field: "activity_type.name", headerFilter: "input", widthGrow: 3 },
                { field: "delete_uri", formatter: actionFormatter(csrfToken), formatterParams: { 'icon': 'trash', 'method': 'POST', 'alt': 'Delete' }, cellClick: onclickTriggerInsideForm, headerSort: false },
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
}


