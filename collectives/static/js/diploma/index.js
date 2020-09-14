
var locale = window.navigator.userLanguage || window.navigator.language;
var diplomaTable;
moment.locale(locale);

// page setup
window.onload = function(){

    eventsTable = new Tabulator("#diplomastable", {
        layout:"fitColumns",
        ajaxURL: '/api/diploma/',
        ajaxSorting:true,
        ajaxFiltering:true,

        pagination : 'remote',
        paginationSize : 50,
        paginationSizeSelector: [10, 25, 50, 100],

        columns:[
            {formatter:"link", formatterParams: {label: '👤', urlPrefix : '/profile/user/'}, field:"user.id", width:30, headerSort:false},
            {title:"Nom de famille", field:"user.last_name", sorter:"string", headerFilter:true},
            {title:"Prénom", field:"user.first_name", sorter:"string", headerFilter:true},
            {title:"Activité", field:"type.activity.name", sorter:"string", headerFilter:true, formatter:activityFormatter, headerSort:false},
            {title:"Titre", field:"type.title", sorter:"string", headerFilter:true},
            {title:"Obtention", field:"obtention", sorter:"date", formatter:"datetime", formatterParams:{ inputFormat:"YYYY-MM-DD",  outputFormat:"DD/MM/YYYY",}},
            {title:"Expiration", field:"expiration", sorter:"date", formatter:"datetime", formatterParams:{ inputFormat:"YYYY-MM-DD",  outputFormat:"DD/MM/YYYY",}},
            {title:"🗑", formatter:"buttonCross", field:"id", width:50, cellClick: deleteDiploma, headerSort:false},

        ],

        locale: 'fr-fr',
        langs:{
            "fr-fr":{
                "ajax":{
                    "loading":"Chargement", //ajax loader text
                    "error":"Erreur", //ajax error text
                },
                "pagination":{
                    "page_size":"Collectives par page", //label for the page size select element
                    "first":"Début", //text for the first page button
                    "first_title":"Première Page", //tooltip text for the first page button
                    "last":"Fin",
                    "last_title":"Dernière Page",
                    "prev":"Précédente",
                    "prev_title":"Page Précédente",
                    "next":"Suivante",
                    "next_title":"Page Suivante",
                },
                'headerFilters':{
                    "default":"Recherche 🔍",
                }
            }
        },
    });

    // Add autocomplete on user input
    autocompleteSearch();

};

// Formatting of activity column
function activityFormatter(cell, formatterParams, onRendered){
    data = cell.getRow().getData();
    return `<span class=\"activity ${data['type']['activity']['short'] || 'none'} s30px\" title=\"${cell.getValue() || 'none'}\">
            </span>`;
}

// Action when clink n delete cross
function deleteDiploma(e, cell){
    id = cell.getValue();
    form = document.getElementById('delete_form');
    form.action = form.action + id;
    form.submit();
}

// Action when click on the user icon.
function gotoUser(e, cell){
    document.location = "/profile/user/"+row.getData();
}

// autoComplete list creation
const renderItem = function (item) {
    let icon;
    if (item.type === 'user') {
        icon = '<i class="fab fa-github"></i>';
    }
    return `<div class="autocomplete-suggestion" data-val="${item.full_name}" data-id="${item.id}"><span>${item.full_name}</span></div>`
};

// Autocomplete activation function when user select an autocomplete option.
const onSelect = function (e, term, item) {
    document.getElementById('user_id').value = item.getAttribute('data-id');
}

// Autocomplete result retrieval function.
const loadResults = function (term, then) {
    var xhr = new XMLHttpRequest();
    xhr.open('GET', '/api/users/autocomplete/?q=' + encodeURIComponent(term));
    xhr.setRequestHeader('Content-Type', 'application/json');
    xhr.onload = function () {
        if (xhr.status === 200) {
            then(JSON.parse(xhr.responseText));
        }
    };
    xhr.send();
}

// Autocomple initialisation function
const autocompleteSearch = function () {
    const searchInput = document.getElementById('user-search');

    if (searchInput) {
        new window.autoComplete({
            selector: searchInput,
            minChars: 2,
            source: function (term, suggest) {
                loadResults(term,
                    function (data) {
                        const matches = []
                        data.forEach((user) => {
                            matches.push({ full_name: user.full_name, id: user.id });
                        });
                        suggest(matches)
                    });
            },
            renderItem: renderItem,
            onSelect: onSelect
        });
    }
    return searchInput;
};
