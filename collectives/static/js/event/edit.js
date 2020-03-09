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

function validateDateTime(element){
    if (element.value != "" && isNaN(new Date(element.value).getDay())){
        element.setCustomValidity('Doit être une date');
        return false;
    }
    element.setCustomValidity('');
    return true;
}

function checkDateOrder(){
    const start = document.getElementById('start');
    const end = document.getElementById('end');
    const registration_open_time = document.getElementById('registration_open_time');
    const registration_close_time = document.getElementById('registration_close_time');

    // Don't check order if a Date is not validated
    var validation =    validateDateTime(start) &&
                        validateDateTime(end) &&
                        validateDateTime(registration_open_time) &&
                        validateDateTime(registration_close_time);
    if( ! validation )
        return false;

    // If a registration bound is defined, check the other one definition
    const halfregistration = document.getElementById("halfregistration");
    if(     ( registration_open_time.value == "" && registration_close_time.value != "" )
        ||  ( registration_open_time.value != "" && registration_close_time.value == "" )){
        halfregistration.style.display = "inline";
        registration_close_time.setCustomValidity('Doit être défini');
        registration_open_time.setCustomValidity('Doit être défini');
        // Quit to avoid resetting pattern later
        return false;
    }
    else{
        halfregistration.style.display = "none";
        registration_close_time.setCustomValidity('');
        registration_open_time.setCustomValidity('');
    }


    // Start of event is before end of it
    const dateorder1 = document.getElementById("dateorder1");
    if( new Date(start.value) > new Date(end.value) ){
        dateorder1.style.display = "inline";
        start.setCustomValidity('Mauvais ordre des dates');
        end.setCustomValidity('Mauvais ordre des dates');
        // Quit to avoid resetting pattern later
        return false;
    }
    else{
        dateorder1.style.display = "none";
        start.setCustomValidity('');
        end.setCustomValidity('');
    }


    // End of registration is before start of event
    // Nothing if no value
    const dateorder2 = document.getElementById("dateorder2");
    if(registration_close_time.value != "" && new Date(registration_close_time.value) > new Date(start.value) ) {
        dateorder2.style.display = "inline";
        registration_close_time.setCustomValidity('Mauvais ordre des dates');
        start.setCustomValidity('Mauvais ordre des dates');
        // Quit to avoid resetting pattern later
        return false;
    }
    else{
        dateorder2.style.display = "none";
        registration_close_time.setCustomValidity('');
        start.setCustomValidity('');
    }

    // End of registration is before start of event
    // Nothing if no value
    const dateorder3 = document.getElementById("dateorder3");
    if(registration_open_time.value != "" && registration_close_time.value != "" && new Date(registration_close_time.value) < new Date(registration_open_time.value) ){
        dateorder3.style.display = "inline";
        registration_close_time.setCustomValidity('Mauvais ordre des dates');
        registration_open_time.setCustomValidity('Mauvais ordre des dates');
        // Quit to avoid resetting pattern later
        return false;
    }
    else{
        dateorder3.style.display = "none";
        registration_close_time.setCustomValidity('');
        registration_open_time.setCustomValidity('');
    }

    return true;
}
