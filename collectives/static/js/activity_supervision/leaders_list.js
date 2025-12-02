
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
            `<input type="image" src="/static/img/icon/ionicon/md-${formatterParams['icon']}.svg" style="margin: 0;height: 1.2em; width: 1.2em"  alt="${formatterParams['alt']}" title="${formatterParams['alt']}"/>`;
    };
}

function submitDeleteForm(e, cell) {
    cell._cell.element.querySelector('form').submit();
}

function profileUrl(cell) {
    return cell.getData().user.leader_profile_uri || cell.getData().user.profile_uri;
}

function loadLeadersTable(ajaxUrl, csrfToken) {
    new Tabulator("#leaders-table",
        {
            ajaxURL: ajaxUrl,
            ajaxFiltering: true,
            ajaxSorting: true,
            layout: "fitColumns",
            groupBy:"user.full_name",
            pagination:"remote",
            paginationSize: 50,

            columns: [
                { field: "user.avatar_uri", formatter: 'image', formatterParams: { height: '1em' } },
                { title: "Nom", field: "user.full_name", headerFilter: "input", widthGrow: 3, formatter: "link", formatterParams: { url: profileUrl } },
                { title: "Activité", field: "activity_type.name", headerFilter: "select", headerFilterParams:{values: makeOptions(EnumActivityType)}, widthGrow: 3 },
                { title: "Rôle", field: "name", headerFilter: "select", headerFilterParams:{values: makeOptions(EnumRoleIds, ActivityRequiredRoles)}, widthGrow: 3},
                { field: "delete_uri", formatter: actionFormatter(csrfToken), formatterParams: { 'icon': 'trash', 'method': 'POST', 'alt': 'Delete' }, cellClick: submitDeleteForm, headerSort: false },
            ],

            langs: {
                "fr-fr": {
                    "ajax": {
                        "loading": "Chargement", //ajax loader text
                        "error": "Erreur", //ajax error text
                    },
                }
            },
            paginationDataSent: {"page": "page", "size": "size"},
            paginationDataReceived: {"last_page": "last_page", "data": "data"},
        });
}


function makeOptions(dict, subset){
    if (subset) {
        const subsetDict = {};
        for (const key in subset) {
            opt = subset[key];
            if (opt in dict) {
                subsetDict[opt] = dict[opt];
            }
        }
        dict = subsetDict;
    }
    Object.assign(dict, {"":""});
    return dict;
}