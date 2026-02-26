var locale = window.navigator.userLanguage || window.navigator.language;
var eventstable;
moment.locale(locale);

window.onload = function () {

    var is_user_profile = ajaxURL.match(/^\/api\/user/);

    var common_options = {
        layout: "fitColumns",
        // allow rows to grow in height when cell content wraps or contains line breaks
        variableRowHeight: true,
        resizableRows:true, 
        ajaxURL: ajaxURL, // URL is defined in template
        ajaxFiltering: true,
        ajaxSorting: true,
        pagination: true,
        pagination: "remote",
        paginationSize: 10,
        paginationSizeSelector: [10, 25, 50, 100],
        responsiveLayout: true,
        columns: [
            {
                title: "Type", field: "event_type", formatter: typesFormatter, maxWidth: 100, variableHeight: true, headerFilter: "select",
                headerFilterParams: { values: addEmpty(EnumEventType) }, responsive: 3, minWidth: 35, headerSort: false
            },
            {
                title: "Activité", field: "activity_types", formatter: typesFormatter, maxWidth: 100, variableHeight: true, headerFilter: "select",
                headerFilterParams: { values: addEmpty(EnumActivityType) }, responsive: 1, minWidth: 35, headerSort: false
            },
            {
                title: "Tags", field: "tags", formatter: tagsFormatter, maxWidth: 100, variableHeight: true, headerFilter: "select",
                headerFilterParams: { values: addEmpty(EnumEventTag) }, responsive: 3, minWidth: 35, headerSort: false
            },
            //            { title: "État", field: "status", sorter: "string", headerFilter: "select", formatterParams: { 'enum': EnumEventStatus },
            //                headerFilterParams: { values: addEmpty(EnumEventStatus) }, formatter: enumFormatter, minWidth: 60, responsive: 2 },
            {
                title: "Statut", field: "registration.status", headerFilter: "select", headerFilterParams: { values: registrationStatusOptions() }, visible: is_user_profile,
                formatter: enumFormatter, formatterParams: { 'enum': EnumRegistrationStatus }, responsive: 1, minWidth: 60
            },
            { title: "Titre", field: "title", sorter: "string", headerFilter: "input", formatter: titleFormatter, widthGrow: 2.5, responsive: 0, minWidth: 200 },
            {
                title: "Date", field: "start", sorter: "string", formatter: "datetime",
                formatterParams: { outputFormat: "D/M/YY", invalidPlaceholder: "(invalid date)" }, responsive: 2, minWidth: 60
            },
            { title: "Insc.", field: "occupied_slots", maxWidth: 80, responsive: 4, minWidth: 80, headerSort: false, visible: !is_user_profile },
            {
                title: "Encadrant", field: "leaders", formatter: leadersFormatter, headerSort: false, headerFilter: true,
                headerFilterFunc: leaderFilter, variableHeight: true, widthGrow: 2, responsive: 3, minWidth: 60
            },
        ],
        rowClick: function (e, row) { document.location = row.getData().view_uri },

        locale: true,
        langs: {
            "fr-fr": {
                "ajax": {
                    "loading": "Chargement", //ajax loader text
                    "error": "Erreur", //ajax error text
                },
                "pagination": {
                    "page_size": "Sorties par page", //label for the page size select element
                    "first": "Début", //text for the first page button
                    "first_title": "Première Page", //tooltip text for the first page button
                    "last": "Fin",
                    "last_title": "Dernière Page",
                    "prev": "Précédente",
                    "prev_title": "Page Précédente",
                    "next": "Suivante",
                    "next_title": "Page Suivante",
                }
            }
        },
    };

    var eventstable = new Tabulator("#eventstable",
        Object.assign({}, common_options, {
            initialFilter: [
                { field: "end", type: ">", value: getServerLocalTime() },
            ]
        })
    );
    var pasteventstable = new Tabulator("#pasteventstable",
        Object.assign({}, common_options, {
            initialFilter: [
                { field: "end", type: "<", value: getServerLocalTime() }
            ],
            initialSort: [{ column: "start", dir: "desc" }],
        })
    );

    if (is_user_profile) {
        eventstable.addFilter("registration.status", "in", [EnumRegistrationStatusKeys["Active"], EnumRegistrationStatusKeys["PaymentPending"], EnumRegistrationStatusKeys["Waiting"]]);
        pasteventstable.addFilter("registration.status", "!=", EnumRegistrationStatusKeys["Waiting"]);
    }

    pasteventstable.addFilter("status", "=", EnumEventStatusKeys["Confirmed"]);
}

function leadersFormatter(cell, formatterParams, onRendered) {
    var names = cell.getValue().map((leader) => leader['full_name']);
    return names.join('<br/>');
}

function leaderFilter(value, data) {
    var regex = new RegExp(value, "i");
    return regex.test(data.map(leader => leader['name']).join(' '));
}

function titleFormatter(cell, formatterParams, onRendered) {
    cell.getElement().style.whiteSpace = "pre-wrap";

    badges = "";
    eventStatus = cell.getData().status;
    if (eventStatus != EnumEventStatusKeys["Confirmed"]) {
        badges += ` <span class="event-status-badge event-status-${eventStatus}" title="${EnumEventStatus[eventStatus]}">${EnumEventStatus[eventStatus]} </span> `;
    }

    return cell.getValue() + badges;
}

function typesFormatter(cell, formatterParams, onRendered) {

    function formatFunc(activity) {
        if (activity['kind'] == 'Service') {
            return `<img src="/static/caf/icon/benevolat.svg" width="30px" title="${activity['name']}"/>`;
        } else {
            return `<img src="/static/caf/icon/${activity['short']}.svg" width="30px" title="${activity['name']}"/>`;
        }
    }

    var val = cell.getValue()
    if (Array.isArray(val))
        return val.map(formatFunc).join(' ');
    return formatFunc(val);
}

function tagsFormatter(cell, formatterParams, onRendered) {
    var names = cell.getValue().map((tag) => `<img src="/static/caf/icon/${tag['short']}.svg" width="30px"/>`);
    return names.join(' ');
}
function enumFormatter(cell, formatterParams, onRendered) {
    return formatterParams['enum'][cell.getValue()];
}

function addEmpty(dict) {
    var copy = {};
    copy[''] = "";
    Object.assign(copy, dict);
    return copy;
}

function registrationStatusOptions() {
    var copy = addEmpty(EnumRegistrationStatus);
    delete copy[EnumRegistrationStatusKeys['ToBeDeleted']];
    return copy;
}