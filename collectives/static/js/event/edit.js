// Fonction to copy start date into end date in case of one day event
function copyStartDate() {
    if (!document.querySelector('input[name=end]').value)
        document.querySelector('input[name=end]').value = document.querySelector('input[name=start]').value;
}

function makeEditorToolbar() {
    return [
        {
            name: "bold",
            action: SimpleMDE.toggleBold,
            className: "fa fa-bold",
            title: "Gras",
        },
        {
            name: "italic",
            action: SimpleMDE.toggleItalic,
            className: "fa fa-italic",
            title: "Italique",
        },
        {
            name: "strikethrough",
            action: SimpleMDE.toggleStrikethrough,
            className: "fa fa-strikethrough",
            title: "Barré",
        },
        {
            name: "heading",
            action: SimpleMDE.toggleHeadingSmaller,
            className: "fa fa-header",
            title: "Titre",
        },
        "|",
        {
            name: "list-ul",
            action: SimpleMDE.toggleUnorderedList,
            className: "fa fa-list-ul",
            title: "Liste",
        },
        {
            name: "list-ol",
            action: SimpleMDE.toggleOrderedList,
            className: "fa fa-list-ol",
            title: "Liste numérotée",
        },
        "|",
        {
            name: "link",
            action: SimpleMDE.drawLink,
            className: "fa fa-link",
            title: "Lien hypertexte",
        },
        {
            name: "image",
            action: SimpleMDE.drawImage,
            className: "fa fa-picture-o",
            title: "Image",
        },
        {
            name: "table",
            action: SimpleMDE.drawTable,
            className: "fa fa-table",
            title: "Tableau",
        },
        "|",
        {
            name: "preview",
            action: SimpleMDE.togglePreview,
            className: "fa fa-eye no-disable",
            title: "Aperçu",
        },
        {
            name: "side-by-side",
            action: SimpleMDE.toggleSideBySide,
            className: "fa fa-columns no-disable no-mobile",
            title: "Aperçu temps-réel",
        },
        {
            name: "fullscreen",
            action: SimpleMDE.toggleFullScreen,
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

    ]

}

function getEditorOptions(elementId) {
    return {
        element: document.getElementById(elementId),
        blockStyles: { italic: "_" },
        spellChecker: false,
        status: false,
        promptURLs: true,
        toolbar: makeEditorToolbar()
    };
}

function makeEditor(elementId)
{
    var simplemde = new SimpleMDE(getEditorOptions(elementId));
    simplemde.options.promptTexts = { "link": "Adresse du lien", "image": "Adresse de l'image" };
    return simplemde;
}
