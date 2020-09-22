
const renderItem = function (item) {
    let icon;
    if (item.type === 'user') {
        icon = '<i class="fab fa-github"></i>';
    }
    return `<div class="autocomplete-suggestion" data-val="${item.full_name}" data-id="${item.id}"><span>${item.full_name}</span></div>`
};

const onSelect = function (e, term, item) {
    document.getElementById('user-search-resultid').value = item.getAttribute('data-id');
    document.getElementById('user-search-form').submit();
}

const loadResults = function (term, then) {
    var xhr = new XMLHttpRequest();
    xhr.open('GET', '/api/users/autocomplete/?q=' + encodeURIComponent(term));
    xhr.setRequestHeader('Content-Type', 'application/json');
    xhr.onload = function () {
        if (xhr.status === 200) {
            then(JSON.parse(xhr.responseText));
        }
    };
    xhr.send();
}

const autocompleteSearch = function () {
    const searchInput = document.getElementById('user-search');

    if (searchInput) {
        new window.autoComplete({
            selector: searchInput,
            minChars: 2,
            source: function (term, suggest) {
                loadResults(term,
                    function (data) {
                        const matches = []
                        data.forEach((user) => {
                            matches.push({ full_name: user.full_name, id: user.id });
                        });
                        suggest(matches)
                    });
            },
            renderItem: renderItem,
            onSelect: onSelect
        });
    }
    return searchInput;
};

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

document.addEventListener('DOMContentLoaded', function () {
    autocompleteSearch();
})


