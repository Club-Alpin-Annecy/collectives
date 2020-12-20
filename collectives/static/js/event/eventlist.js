
function prepareEventClick(){
    if(document.querySelector("#eventstable .row") == null)
        return false;

    document.querySelector("#eventstable .row").addEventListener("click", handleEventClick);
    document.querySelector("#eventstable .row a").addEventListener("click", (e) => e.stopPropagation());
}

function handleEventClick(event) {
  const isTextSelected = window.getSelection().toString();
  if (!isTextSelected) {
    this.querySelector("a.main").click();
  }
}

function gotoEvents(event){
    // if we are not on top during a load, do not mess with page position
    if(window.scrollY > 50)
        return 0;

    var position = document.querySelector('#eventlist').getBoundingClientRect().top +  window.scrollY - 60;
    window.scrollTo(    {
        top: position,
        behavior: 'smooth'
    });
}

// Functions to set up autocomplete of leaders
function autocompleteLeaders()
{
    new window.autoComplete({
        selector: getLeaderHeaderFilter(),
        minChars: 2,
        source: sourceLeaderAutocomplete,
        renderItem: renderItemLeaderAutocomplete,
        onSelect: onSelectLeaderAutocomplete
    });
}

function getLeaderHeaderFilter() {
    return document.querySelector('input[type="text"][name="search"]');
}

function sourceLeaderAutocomplete(term, suggest) {
    loadResultsLeaderAutocomplete(term,
        function (data) {
            const matches = []
            data.forEach((user) => {
                matches.push({ full_name: user.full_name });
            });
            suggest(matches)
        });
}

function loadResultsLeaderAutocomplete(term, then) {
    var xhr = new XMLHttpRequest();
    xhr.open('GET', '/api/leaders/autocomplete/?q=' + encodeURIComponent(term));
    xhr.setRequestHeader('Content-Type', 'application/json');
    xhr.onload = function () {
        if (xhr.status === 200) {
            then(JSON.parse(xhr.responseText));
        }
    };
    xhr.send();
}
function renderItemLeaderAutocomplete (item) {
    let icon;
    if (item.type === 'user') {
        icon = '<i class="fab fa-github"></i>';
    }
    return `<div class="autocomplete-suggestion" data-val="${item.full_name}" data-id="${item.id}"><span>${item.full_name}</span></div>`
};

function onSelectLeaderAutocomplete(e, term, item) {
    const searchInput = getLeaderHeaderFilter();
    searchInput.value = item.getAttribute('data-val');
}
