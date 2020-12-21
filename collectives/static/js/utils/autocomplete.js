

/**
 * Setups automcomplete for a text field
 * @param {string} field The HTML element
 * @param {string} baseUrl The API url providing the results. Search term will be passed to the 'q' parameter
 * @param {function} itemValue Function extracting the value associated to an item from the API call result
 * @param {function} onSelect Function called when user select a suggestion result. Function will be passed item id and value.
 * @param {dict} settings  Optional settings
 */
function setupAutoComplete(
    field, 
    baseUrl,
    itemValue,
    onSelect,
    settings =
    {
        minChars : 2,
        itemClass : "autocomplete-suggestion",
        itemInnerHTML : function(item) { return `<span>${itemValue(item)}</span>`; } 
    }
)
{
    if(!field) { return null ; }

    // Functor performing the API query with 'term' then calling 'then'
    const loadResults  = function(term, then) {
        var url = new URL(baseUrl, document.baseURI);
        url.searchParams.set("q", term);
        var xhr = new XMLHttpRequest();
        xhr.open('GET', url);
        xhr.setRequestHeader('Content-Type', 'application/json');
        xhr.onload = function () {
            if (xhr.status === 200) {
                then(JSON.parse(xhr.responseText));
            }
        };
        xhr.send();
    };

    //  Functor calling 'onSelect' with id and value from the select item
    const onSelectInternal = function(e, term, item)
    {
        onSelect(item.getAttribute('data-id'), item.getAttribute('data-val'));
    }

    const renderItem =  function(item)
    {
        var val = itemValue(item);
        var innerHTML = settings.itemInnerHTML(item);
        return `<div class="${settings.itemClass}" data-val="${val}" data-id="${item.id}">${innerHTML}</div>`
    };

    return new window.autoComplete({
        selector: field,
        minChars: settings.minChars,
        source: loadResults,
        renderItem: renderItem,
        onSelect: onSelectInternal
    });
}

window.setupAutoComplete = setupAutoComplete;