

function actionFormatter(cell, formatterParams, onRendered) {
    if (cell.getValue()) {
        return `<form style="display:inline; padding:0" action="${cell.getValue()}" method="${formatterParams['method']}" ></form><input type="image" src="/static/img/icon/ionicon/md-${formatterParams['icon']}.svg" style="margin: 0;height: 1.2em; width: 1.2em"  alt="${formatterParams['alt']}" title="${formatterParams['alt']}"/>`;
    }
    return '';
}


function makeCellClickedCallback(state) {
    return function (e, cell) {
        // If the cell does not have a valid receipt link, ignore
        if (!cell.getValue()) return;
        // Disarm 'rowClick' event
        state.cellClicked = true;
        // Submit form
        cell._cell.element.querySelector('form').submit();
    };
}

function tableColumns(payment_status, state) {
    var date_field = '';
    var receipt_uri_field = '';
    var amount_field = '';
    switch (payment_status) {
        case 'Initiated':
            date_field = 'creation_time';
            amount_field = 'amount_charged';
            break;
        case 'Approved':
            date_field = 'finalization_time';
            amount_field = 'amount_paid';
            receipt_uri_field = 'receipt_uri';
            break;
        case 'Refunded':
            date_field = 'refund_time';
            amount_field = 'amount_paid';
            receipt_uri_field = 'refund_receipt_uri';
            break;
    }

    var columns = [
        { title: "Date", field: date_field, widthGrow: 1, headerFilter: true },
        { title: "Événement", field: "item.event.title", widthGrow: 2, headerFilter: true },
        { title: "Objet", field: "item.title", widthGrow: 2, headerFilter: true },
        { title: "Tarif", field: "price.title", widthGrow: 2, headerFilter: true },
        { title: "Prix", field: amount_field, widthGrow: 1 },
        { title: "Type", field: "payment_type", widthGrow: 1, headerFilter: true },
    ];

    if (receipt_uri_field) {
        columns.push(
            { title: "Justificatif", field: receipt_uri_field, formatter: actionFormatter, formatterParams: { 'icon': 'document', 'method': 'GET', 'alt': 'Justificatif' }, cellClick: makeCellClickedCallback(state), headerSort: false }
        );
    }
    return columns;
}

function createMyPaymentsTable(id, url, payment_status) {

    // Hack to prevent Tabulator rowClick() event from firing
    // once a cellClick() has been processed
    var state = {
        cellClicked: false
    };

    new Tabulator(id,
        {
            ajaxURL: url,
            layout: "fitColumns",
            columns: tableColumns(payment_status, state),

            rowClick: function (e, row) {
                if (state.cellClicked) return;
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

