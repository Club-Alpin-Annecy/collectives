
var cellClicked = false;

function actionFormatter(cell, formatterParams, onRendered) {
    if (cell.getValue()) {
        return '<form style="display:inline; padding:0" action="' + cell.getValue() + '" method="' + formatterParams['method'] + '" ></form><input type="image" src="/static/img/icon/ionicon/md-' + formatterParams['icon'] + '.svg" style="margin: 0;height: 1.2em; width: 1.2em"  alt="' + formatterParams['alt'] + '" title="' + formatterParams['alt'] + '"/>';
    }
    return '';
}

function onclickTriggerInsideForm(e, cell) {
    if (!cell.getValue()) return;
    cellClicked = true;
    cell._cell.element.querySelector('form').submit();
}

function tableColumns(finalized) {
    var columns = [
        { title: "Date", field: (finalized ? "finalization_time" : "creation_time"), widthGrow: 1, headerFilter: true },
        { title: "Événement", field: "event_title", widthGrow: 2, headerFilter: true },
        { title: "Objet", field: "item_title", widthGrow: 2, headerFilter: true },
        { title: "Tarif", field: "price_title", widthGrow: 2, headerFilter: true },
        { title: "Prix", field: (finalized ? "amount_paid" : "amount_charged"), widthGrow: 1 },
        { title: "Type", field: "payment_type", widthGrow: 1, headerFilter: true },
    ];

    if (finalized) {
        columns.push(
            { title: "Justificatif", field: "receipt_uri", formatter: actionFormatter, formatterParams: { 'icon': 'ribbon', 'method': 'GET', 'alt': 'Justificatif' }, cellClick: onclickTriggerInsideForm, headerSort: false }
        );
    }
    return columns;
}

function createMyPaymentsTable(id, url, finalized) {
    new Tabulator(id,
        {
            ajaxURL: url,
            layout: "fitColumns",
            columns: tableColumns(finalized),

            rowClick: function (e, row) {
                if (cellClicked) return;
                document.location.href = row.getData().details_uri;
            },

            locale: true,
            langs: {
                "fr": {
                    "ajax": {
                        "loading": "Chargement", //ajax loader text
                        "error": "Erreur", //ajax error text
                    },
                }
            }
        });
}

