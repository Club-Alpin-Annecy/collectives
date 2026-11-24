
const onSelectAutocomplete = function (id, value) {
    document.getElementById('user-search-resultid').value = id;
}

function actionFormatter(csrfToken) {
    return function (cell, formatterParams, onRendered) {
        if (cell.getValue() == "") return '';
        return `<form style="display:inline; padding:0" action="${cell.getValue()}" method="${formatterParams['method']}" >` +
            `<input style="display:none" name="csrf_token" type+"hidden" value="${csrfToken}">` +
            '</form>' +
            `<input type="image" src="/static/img/icon/ionicon/${formatterParams['icon']}.svg" style="margin: 0;height: 1.2em; width: 1.2em"  alt="${formatterParams['alt']}" title="${formatterParams['alt']}"/>`;
    };
}

function levelFormatter(badgeLevels) {
    return function (cell, formatterParams, onRendered) {
        const level = cell.getValue();
        const badgeId = EnumBadgeIdsKeys[cell.getData().badge_id];
        if (badgeId in badgeLevels) {
            var thisBadgeLevels = badgeLevels[badgeId]

            for (const activityId of [cell.getData().activity_type?.id, null]) {
                if (activityId in thisBadgeLevels && level in thisBadgeLevels[activityId]) {
                    // Level names are user-defined: insert them as text, not HTML
                    return document.createTextNode(thisBadgeLevels[activityId][level].name);
                }
            }
        }

        return level;
    };
}

function onclickTriggerInsideForm(e, cell) {
    cell._cell.element.querySelector('form').submit();
}

function profileUrl(cell) {
    return cell.getData().user.profile_uri;
}
function grantorUrl(cell) {
    return cell.getData().grantor.leader_profile_uri;
}

// Value of the activity filter selecting badges without activity,
// see ActivityTypeSelectionForm.NO_ACTIVITY
const NO_ACTIVITY = 0;

function loadBadgesTable(ajaxUrl, ajaxParams, csrfToken, showType, showLevel, showGrantor, badgeLevels) {
    var table = new Tabulator("#badges-table",
        {
            ajaxURL: ajaxUrl,
            ajaxParams: ajaxParams,
            ajaxFiltering: true,
            ajaxSorting: true,
            layout: "fitColumns",
            pagination: "remote",
            paginationSize: 50,

            columns: [
                { field: "user.avatar_uri", formatter: 'image', formatterParams: { height: '1em' } },
                { title: "Nom", field: "user.full_name", headerFilter: "input", widthGrow: 3, formatter: "link", formatterParams: { url: profileUrl } },
                { title: "Activité", field: "activity_type.name", headerFilter: "select", headerFilterParams: { values: makeOptions({ [NO_ACTIVITY]: "Pas d'activité", ...EnumActivityType }) }, widthGrow: 3 },
                { title: "Badge", field: "name", headerFilter: "select", headerFilterParams: { values: makeOptions(EnumBadgeIds) }, widthGrow: 3, visible: showType },
                { title: "Expiration", field: "expiration_date", headerFilter: "input", widthGrow: 3 },
                { title: "Niveau", field: "level", headerFilter: "input", widthGrow: 2, visible: showLevel, formatter: levelFormatter(badgeLevels) },
                { title: "Attribué par", field: "grantor.full_name", headerFilter: "input", widthGrow: 3, formatter: "link", formatterParams: { url: grantorUrl }, visible: showGrantor },
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
            // map Tabulator pagination params to what our server expects
            paginationDataSent: {"page": "page", "size": "size"},
            paginationDataReceived: {"last_page": "last_page", "data": "data"},
        });

    // Export the badges matching the current filters of the table
    document.getElementById('badges-export').addEventListener('click', function (event) {
        event.preventDefault();
        const params = table.modules.ajax.serializeParams({ filters: table.getFilters(true) });
        document.location = this.href + '?' + params;
    });
}

function makeOptions(dict) {
    Object.assign(dict, {"":""});
    return dict;
}