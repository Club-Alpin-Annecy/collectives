var locale = window.navigator.userLanguage || window.navigator.language;
moment.locale(locale);

var retex_common_options = {
    layout: "fitColumns",
    variableRowHeight: true,
    resizableRows: true,
    ajaxFiltering: true,
    ajaxSorting: true,
    pagination: true,
    pagination: "remote",
    paginationSize: 10,
    paginationSizeSelector: [10, 25, 50, 100],
    responsiveLayout: true,
    initialSort: [{ column: "end", dir: "desc" }],
    columns: [
        {
            title: "Statut", field: "retex_status", formatter: retexStatusFormatter, headerSort: false, minWidth: 100
        },
        { title: "Titre", field: "title", sorter: "string", formatter: titleFormatter, widthGrow: 2.5, minWidth: 200 },
        {
            title: "Date", field: "start", sorter: "string", formatter: "datetime",
            formatterParams: { outputFormat: "D/M/YY", invalidPlaceholder: "(invalid date)" }, minWidth: 60
        },
        { title: "Activité", field: "activity_types", formatter: typesFormatter, maxWidth: 100, variableHeight: true, headerSort: false, minWidth: 35 },
        {
            title: "Encadrant", field: "leaders", formatter: leadersFormatter, headerSort: false, widthGrow: 2, minWidth: 60
        },
    ],
    rowClick: function (e, row) {
        var eventId = row.getData().id;
        document.location = "/retex/event/" + eventId + "/edit";
    },
    locale: true,
    langs: {
        "fr-fr": {
            "ajax": {
                "loading": "Chargement",
                "error": "Erreur",
            },
            "pagination": {
                "page_size": "Sorties par page",
                "first": "Début",
                "first_title": "Première Page",
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

function createRetexTable(elementId, ajaxURL) {
    return new Tabulator("#" + elementId, Object.assign({}, retex_common_options, {
        ajaxURL: ajaxURL,
    }));
}

function retexStatusFormatter(cell, formatterParams, onRendered) {
    var value = cell.getData().retex_status;
    if (value === null || value === undefined) {
        return '<span class="retex-status-todo">À faire</span>';
    }
    return `<span class="retex-status-badge retex-status-${value}">${EnumRetexStatus[value]}</span>`;
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

function leadersFormatter(cell, formatterParams, onRendered) {
    var names = cell.getValue().map((leader) => leader['full_name']);
    return names.join('<br/>');
}

function titleFormatter(cell, formatterParams, onRendered) {
    cell.getElement().style.whiteSpace = "pre-wrap";
    return cell.getValue();
}
