
function createActivityDocumentsTable(url, csrf_token) {

    function deleteFile(e, cell) {
        if (!confirm("Voulez-vous vraiment supprimer ce fichier ?")) {
            return false;
        }

        var res = null;
        var req = new XMLHttpRequest();

        req.open('POST', cell.getValue(), true);
        req.setRequestHeader('x-csrf-token', csrf_token);
        req.onload = function () {
            cell.getTable().replaceData()
        };
        req.send();
    }

    function makeOptions(dict) {
        return [""].concat(Object.values(dict).sort());
    }

    return new Tabulator("#activity-documents-table",
        {
            ajaxURL: url,
            layout: "fitColumns",

            nestedFieldSeparator: false,
            columns: [
                {
                    title: "Fichier", headerFilter: "input", widthGrow: 3, field: "name", formatter: "link", formatterParams: { urlField: "url" }
                },
                {
                    title: "Activité", headerFilter: "select",
                    headerFilterParams: { values: makeOptions(EnumActivityType) },
                    widthGrow: 2, field: "activity_name"
                },
                { title: "Taille", widthGrow: 1, field: "size", formatter: sizeFormatter },
                { title: "Date", widthGrow: 1, field: "date", formatter: "datetime", formatterParams: { outputFormat: "DD/MM/YYYY" } },
                { field: "delete_url", width: "24", align: "center", formatter: "buttonCross", cellClick: deleteFile, headerSort: false }
            ],

            locale: true,
            langs: {
                "fr": {
                    "ajax": {
                        "loading": "Chargement", //ajax loader text
                        "error": "Erreur", //ajax error text
                    },
                }
            },
        });
}