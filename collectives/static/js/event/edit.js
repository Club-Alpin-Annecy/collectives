
var locale = window.navigator.userLanguage || window.navigator.language;
moment.locale(locale);


// Fonction to copy start date into end date in case of one day event
function copyStartDate() {
    if (!document.querySelector('input[name=end]').value)
        document.querySelector('input[name=end]').value = document.querySelector('input[name=start]').value;
}

function makeEditorToolbar() {
    return [
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
            title: "Image",
        },
        {
            name: "table",
            action: EasyMDE.drawTable,
            className: "fa fa-table",
            title: "Tableau",
        },
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
            action: function(){
                easymde.toTextArea();
                document.getElementById("form_edit_event").onsubmit=null;
            },
            className: "fa fa-power-off",
            title: "Désactiver Wysiwyg",
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
    var easymde = new EasyMDE(getEditorOptions(elementId));
    easymde.options.promptTexts = { "link": "Adresse du lien", "image": "Adresse de l'image" };
    return easymde;
}

function validateDateTime(element, canBeEmpty){
    if (element.value == "") {
        if(canBeEmpty) {
            element.setCustomValidity('');
        } else {
            element.setCustomValidity('Doit être défini');
        }
        return canBeEmpty;
    }

    if (!moment(element.value).isValid()){
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
    if(hasDateError) return false;

    // Start of event is before the end 
    if( moment(start.value) > moment(end.value) ){
        starts_before_ends.style.display = "inline";
        start.setCustomValidity('Doit être avant la fin');
        end.setCustomValidity('Doit être après le début');
   
        hasDateError = true;
    }

    var hasRegistrationOpen = registration_open_time.value != "";
    var hasRegistrationClose = registration_close_time.value != "";
    if(hasRegistrationClose || hasRegistrationOpen){
        // If a registration bound is defined, check the other one definition
        if(hasRegistrationOpen && hasRegistrationClose){
            // End of registration is before opening of registrations
            if(moment(registration_close_time.value) < moment(registration_open_time.value) ){
                opens_before_closes.style.display = "inline";
                registration_close_time.setCustomValidity("Doit être après l'ouverture");
                registration_open_time.setCustomValidity("Doit être avant la fermeture");
                
                hasDateError = true;
            }
        } else { 
            halfregistration.style.display = "inline";
            if(!hasRegistrationClose)
                registration_close_time.setCustomValidity('Doit être défini');
            if(!hasRegistrationOpen)
                registration_open_time.setCustomValidity('Doit être défini');
        
            hasDateError = true;
        }
    }

    // If there are already errors, do not proceed further on
    if(hasDateError) return false;

    // End of registration is before start of event
    if(registration_close_time.value != "" && moment(registration_close_time.value) > moment(start.value) ) {
        closes_before_starts.style.display = "inline";
        registration_close_time.setCustomValidity("Doit être avant le début de l'événement");
        start.setCustomValidity('Doit être après fermeture des inscriptions');
        hasDateError = true;
    }

    return hasDateError;
}

function removeRequiredAttributes()
{
    Array.from(document.getElementsByTagName("input")).forEach(
        function(element) {
            element.removeAttribute("required");
            element.setCustomValidity("");
        }
    );
}

    