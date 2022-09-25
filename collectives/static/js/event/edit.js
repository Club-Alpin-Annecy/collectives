
var locale = window.navigator.userLanguage || window.navigator.language;
moment.locale(locale);


// Fonction to copy start date into end date in case of one day event
function copyStartDate() {
    if (!document.querySelector('input[name=end]').value)
        document.querySelector('input[name=end]').value = document.querySelector('input[name=start]').value;
}

function getActivityIds() {
    var multiActivity = document.getElementById("multi_activities_mode").checked;
    var ids;
    if (multiActivity) {
        ids = Array.from(document.querySelectorAll(`#multi_activity_types option:checked`), e => e.value);
    } else {
        ids = [document.getElementById("single_activity_type").value];
    }
    return ids;
}

function listUploadedFiles(baseUrlString) {

    // Add list of activity ids to query string
    url = new URL(baseUrlString, document.baseURI)
    params = new URLSearchParams(url);
    getActivityIds().forEach(id => params.append('activity_ids', id));
    url.search = params.toString();

    // Reload tabulator data
    var table = Tabulator.prototype.findTable("#uploaded-files-table")[0];
    table.setData(url.toString());

    // Show modal dialog 
    const modal = document.querySelector('.container_bg_modal');
    openModal(modal);
}

function makeEditorToolbar(options) {
    toolbar = [
        {
            name: "bold",
            action: EasyMDE.toggleBold,
            className: "fa fa-bold",
            title: "Gras",
        },
        {
            name: "italic",
            action: EasyMDE.toggleItalic,
            className: "fa fa-italic",
            title: "Italique",
        },
        {
            name: "strikethrough",
            action: EasyMDE.toggleStrikethrough,
            className: "fa fa-strikethrough",
            title: "Barré",
        },
        {
            name: "heading",
            action: EasyMDE.toggleHeadingSmaller,
            className: "fa fa-header",
            title: "Titre",
        },
        "|",
        {
            name: "list-ul",
            action: EasyMDE.toggleUnorderedList,
            className: "fa fa-list-ul",
            title: "Liste",
        },
        {
            name: "list-ol",
            action: EasyMDE.toggleOrderedList,
            className: "fa fa-list-ol",
            title: "Liste numérotée",
        },
        {
            name: "table",
            action: EasyMDE.drawTable,
            className: "fa fa-table",
            title: "Tableau",
        },
        "|",
        {
            name: "link",
            action: EasyMDE.drawLink,
            className: "fa fa-link",
            title: "Lien hypertexte",
        },
        {
            name: "image",
            action: EasyMDE.drawImage,
            className: "fa fa-picture-o",
            title: "Image en ligne",
        }
    ]
    if (options.uploadImage) {
        toolbar.push(
            {
                name: "upload-image",
                action: EasyMDE.drawUploadedImage,
                className: "fa fa-upload",
                title: "Télécharger un document",
            }
        );
    }
    if (options.listUploadedFilesEndpoint) {
        toolbar.push(
            {
                name: "list-uploaded-files",
                action: function () {
                    listUploadedFiles(options.listUploadedFilesEndpoint);
                },
                className: "fa fas fa-folder-open",
                title: "Documents téléchargés",
            }
        );
    }
    toolbar.push(
        "|",
        {
            name: "preview",
            action: EasyMDE.togglePreview,
            className: "fa fa-eye no-disable",
            title: "Aperçu",
        },
        {
            name: "side-by-side",
            action: EasyMDE.toggleSideBySide,
            className: "fa fa-columns no-disable no-mobile",
            title: "Aperçu temps-réel",
        },
        {
            name: "fullscreen",
            action: EasyMDE.toggleFullScreen,
            className: "fa fa-arrows-alt no-disable no-mobile",
            title: "Plein écran",
        },
        "|",
        {
            name: "guide",
            action: "https://docs.framasoft.org/fr/mattermost/help/messaging/formatting-text.html",
            className: "fa fa-question-circle",
            title: "Aide",
        },
        "|",
        {
            name: "nowysiwyg",
            action: function () {
                easymde.toTextArea();
                document.getElementById("form_edit_event").onsubmit = null;
            },
            className: "fa fa-power-off",
            title: "Désactiver Wysiwyg",
        }
    );

    return toolbar;

}

function getEditorOptions(elementId) {
    return {
        element: document.getElementById(elementId),
        blockStyles: { italic: "_" },
        spellChecker: false,
        promptURLs: true,
        uploadImage: true,
        status: ['upload-image'],

        imageAccept: "image/png, image/jpeg, image/gif, application/pdf, application/vnd.oasis.opendocument.spreadsheet, application/vnd.oasis.opendocument.text, application/vnd.openxmlformats-officedocument.wordprocessingml.document, application/vnd.openxmlformats-officedocument.spreadsheetml.sheet, text/xml, application/gpx+xml",
        imageCSRFName: "X-CSRFToken",
        imageCSRFHeader: true,
        imagePathAbsolute: true,
        imageTexts: {
            sbInit: 'Vous pouvez insérer des documents en les collant ou les déposant dans la zone de texte.',
            sbOnDragEnter: 'Déposez le document pour le télécharger.',
            sbOnDrop: 'Téléchargement de "#images_names#" en cours...',
            sbProgress: 'Téléchargement de "#file_name#": #progress#%',
            sbOnUploaded: 'Téléchargement de "#image_name#" terminé',
            sizeUnits: ' B, KB, MB',
        },
        errorMessages: {
            noFileGiven: 'Aucun fichier choisi.',
            typeNotAllowed: 'Ce type de document n\'est pas autorisé.',
            fileTooLarge: 'Le fichier "#image_name#" est trop volumineux (#image_size#) ou le nombre de fichiers maximum par événement a été atteint.\n' +
                'La taille maximum autorisée est #image_max_size#.',
            importError: 'Une erreur est survenue lors du téléchargement de "#image_name#".',
        },
        sideBySideFullscreen: false
    };
}

function makeEditor(elementId, options = {}) {
    var allOptions = Object.assign({}, getEditorOptions(elementId), options);
    allOptions.toolbar = makeEditorToolbar(allOptions)

    var easymde = new EasyMDE(allOptions);
    easymde.options.promptTexts = { "link": "Adresse du lien", "image": "Adresse de l'image" };
    return easymde;
}

function validateDateTime(element, canBeEmpty) {
    if (element.value == "") {
        if (canBeEmpty) {
            element.setCustomValidity('');
        } else {
            element.setCustomValidity('Doit être défini');
        }
        return canBeEmpty;
    }

    if (!moment(element.value).isValid()) {
        element.setCustomValidity('Doit être une date');
        return false;
    }
    element.setCustomValidity('');
    return true;
}

function checkDateOrder() {
    const start = document.getElementById('start');
    const end = document.getElementById('end');
    const registration_open_time = document.getElementById('registration_open_time');
    const registration_close_time = document.getElementById('registration_close_time');

    // Hide all previous error messages
    const starts_before_ends = document.getElementById("starts_before_ends_error");
    const halfregistration = document.getElementById("halfregistration");
    const closes_before_starts = document.getElementById("closes_before_starts_error");
    const opens_before_closes = document.getElementById("opens_before_closes_error");
    halfregistration.style.display = "none";
    starts_before_ends.style.display = "none";
    closes_before_starts.style.display = "none";
    opens_before_closes.style.display = "none";


    var hasDateError = false;
    // Make sure validateDateTime is called for each field, even if errors have already
    // benn encountered, in order to properly reset custom validity message
    hasDateError = hasDateError || !validateDateTime(start, false);
    hasDateError = hasDateError || !validateDateTime(end, false);
    hasDateError = hasDateError || !validateDateTime(registration_open_time, true);
    hasDateError = hasDateError || !validateDateTime(registration_close_time, true);

    // Don't check order if some dates are invalid
    if (hasDateError) return false;

    // Start of event is before the end 
    if (moment(start.value) > moment(end.value)) {
        starts_before_ends.style.display = "inline";
        start.setCustomValidity('Doit être avant la fin');
        end.setCustomValidity('Doit être après le début');

        hasDateError = true;
    }

    var hasRegistrationOpen = registration_open_time.value != "";
    var hasRegistrationClose = registration_close_time.value != "";
    if (hasRegistrationClose || hasRegistrationOpen) {
        // If a registration bound is defined, check the other one definition
        if (hasRegistrationOpen && hasRegistrationClose) {
            // End of registration is before opening of registrations
            if (moment(registration_close_time.value) < moment(registration_open_time.value)) {
                opens_before_closes.style.display = "inline";
                registration_close_time.setCustomValidity("Doit être après l'ouverture");
                registration_open_time.setCustomValidity("Doit être avant la fermeture");

                hasDateError = true;
            }
        } else {
            halfregistration.style.display = "inline";
            if (!hasRegistrationClose)
                registration_close_time.setCustomValidity('Doit être défini');
            if (!hasRegistrationOpen)
                registration_open_time.setCustomValidity('Doit être défini');

            hasDateError = true;
        }
    }

    // If there are already errors, do not proceed further on
    if (hasDateError) return false;

    // End of registration is before start of event
    if (registration_close_time.value != "" && moment(registration_close_time.value) > moment(start.value)) {
        closes_before_starts.style.display = "inline";
        registration_close_time.setCustomValidity("Doit être avant le début de l'événement");
        start.setCustomValidity('Doit être après fermeture des inscriptions');
        hasDateError = true;
    }

    return hasDateError;
}

function removeRequiredAttributes() {
    Array.from(document.getElementsByTagName("input")).forEach(
        function (element) {
            element.removeAttribute("required");
            element.setCustomValidity("");
        }
    );
}

function insertLink(editor, name, url, asImage) {

    if (!editor.codemirror) {
        return;
    }

    cm = editor.codemirror

    let absoluteUrl = new URL(url, document.baseURI);

    alt = cm.getSelection()
    if (!alt) {
        alt = name;
    }

    text = `[${alt}](${absoluteUrl.href})`
    if (asImage) text = '!' + text;

    cm.replaceSelection(text);

    const modal = document.querySelector('.container_bg_modal');
    closeModal(modal);

}

function iconFormatter(cell, formatterParams, onRendered) {
    if (cell.getValue()) {
        return `<i class="fa ${formatterParams['icon']}" alt="${formatterParams['alt']}"></i>`;
    }
    return '';
}


function createUploadedFilesTable(editor, csrf_token) {
    function insertFileAsLink(e, cell) {
        url = cell.getValue();
        name = cell.getRow().getData().name
        insertLink(editor, name, url, false);
    }

    function insertFileAsImage(e, cell) {
        url = cell.getValue();
        name = cell.getRow().getData().name
        insertLink(editor, name, url, true);
    }

    function sortFiles(a, b, aRow, bRow, column, dir, sorterParams) {
        if (aRow.getData().activity_name == bRow.getData().activity_name) {
            return a.localeCompare(b);
        }

        // Ensures that files with no activity are always on top
        var nullOrder = dir == "asc" ? 1 : -1;
        if (aRow.getData().activity_name == null) return -nullOrder;
        if (bRow.getData().activity_name == null) return nullOrder;
        return aRow.getData().activity_name.localeCompare(bRow.getData().activity_name);
    }

    function deleteFile(e, cell) {
        if (cell.getValue() == null) {
            alert("Vous ne pouvez pas supprimer ce fichier");
            return;
        }

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

    return new Tabulator("#uploaded-files-table",
        {
            layout: "fitColumns",

            nestedFieldSeparator: false,
            columns: [
                {
                    title: "Fichier", widthGrow: 3, field: "name", formatter: "link", formatterParams: { urlField: "url" }, sorter: sortFiles
                },
                { title: "Taille", widthGrow: 1, field: "size", formatter: sizeFormatter },
                { title: "Date", widthGrow: 1, field: "date", formatter: "datetime", formatterParams: { outputFormat: "DD/MM/YYYY" } },
                { field: "url", width: "24", align: "center", formatter: iconFormatter, formatterParams: { 'icon': 'fa-link', 'alt': 'Insérer comme lien' }, cellClick: insertFileAsLink, headerSort: false },
                { field: "thumbnail_url", width: "24", align: "center", formatter: iconFormatter, formatterParams: { 'icon': 'fa-image', 'alt': 'Insérer comme image' }, cellClick: insertFileAsImage, headerSort: false },
                { field: "delete_url", width: "24", align: "center", formatter: iconFormatter, formatterParams: { 'icon': 'fa-trash link-danger', 'alt': 'Supprimer' }, cellClick: deleteFile, headerSort: false }
            ],

            groupBy: "activity_name",
            initialSort: [{ column: "name", dir: "asc" }],

            locale: true,
            langs: {
                "fr": {
                    "ajax": {
                        "loading": "Chargement", //ajax loader text
                        "error": "Erreur", //ajax error text
                    },
                }
            },
            groupHeader: function (value, count, data, group) {
                return value == null ? "Cet événement" : value;
            },
        });
}


