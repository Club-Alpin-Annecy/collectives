
var unregister_message = `L'inscription a un évènement vous engage à y participer.

Une désinscription inopinée peut fortement contrarier l'organisation de l'encadrant bénévole, voire le pousser à annuler une collective pour laquelle il aura investi de son temps pour l'organiser.

Si lors de votre inscription des arrhes ont été demandés par l’encadrant, ils ne vous seront pas remboursés.

Merci de contacter l'encadrant pour prévenir et justifier votre désinscription.

Confirmez-vous la désinscription ?`;


const renderItem = function (item) {
    let icon;
    if (item.type === 'user') {
        icon = '<i class="fab fa-github"></i>';
    }
    return `<div class="autocomplete-suggestion" data-val="${item.full_name}" data-id="${item.id}"><span>${item.full_name}</span></div>`
};

const onSelect = function (e, term, item) {
    document.getElementById('user-search-resultid').value = item.getAttribute('data-id');
    document.getElementById('user-search-form').submit();
}

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

// Function to load into clipboard the Content
// of an input (#id).
function copy(id){
    var input = document.getElementById(id);
    input.select();
    input.setSelectionRange(0, 99999); /*For mobile devices*/
    document.execCommand("copy");
}

document.addEventListener('DOMContentLoaded', function () {
    autocompleteSearch();
})