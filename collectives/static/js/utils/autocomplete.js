
/**
 * Default values for setupAutoComplete() optional settings
 */
function autoCompleteDefaultSettings() {
    return {
        minChars: 2,  // Minimum number of characters to start loading results
        maxResults: 8, // Maximum number of results to load
        itemClass: "autocomplete-suggestion", // CSS class of loaded results containers 
        // Function rendering the HTML for a given result
        itemInnerHTML: function (item, itemValue) { return `<span>${escapeHTML(itemValue)}</span>`; }
    }
}

/**
 * Setups autocomplete for a text field
 * @param {string} field The HTML element
 * @param {string} baseUrl The API url providing the results. Search term will be passed to the 'q' parameter, maxResults to the 'l' parameter
 * @param {function} itemValue Function extracting the value associated to an item from the API call result
 * @param {function} onSelect Function called when user select a suggestion result. Function will be passed item id and value.
 * @param {dict} settings  Optional settings -- see autoCompleteDefaultSettings
 */
function setupAutoComplete(
    field,
    baseUrl,
    itemValue,
    onSelect,
    settings = {}
) {
    if (!field) { return null; }
    settings = Object.assign(autoCompleteDefaultSettings(itemValue), settings);

    // Functor performing the API query with 'term' then calling 'then'
    const loadResults = function (term, then) {
        var url = new URL(baseUrl, document.baseURI);
        url.searchParams.set("q", term);
        url.searchParams.set("l", settings.maxResults);
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
    const onSelectInternal = function (e, term, item) {
        onSelect(item.getAttribute('data-id'), item.getAttribute('data-val'));
    }

    const renderItem = function (item) {
        var val = itemValue(item);
        var innerHTML = settings.itemInnerHTML(item, val);
        if (item.is_active === false){
            var style = "text-decoration-line: line-through; color: grey; font-style: italic;"
            var misc = `(expiré)`
        }
        else {
            var style = ""; 
            var misc = "";
        }
        return `<div class="${settings.itemClass}" data-val='${escapeHTML(val)}' data-id="${item.id}" style="${style}">${innerHTML} ${misc}</div>`
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

/**
 * Wrapper around setupAutoComplete for user name searches.
 * Displays the license number alongside the name in suggestions to disambiguate
 * users with similar names. The selected value remains the full name only.
 * @param {string} field The HTML element
 * @param {string} baseUrl The API url providing the results
 * @param {function} onSelect Function called when user selects a suggestion. Passed item id and full name.
 * @param {dict} settings Optional settings -- see autoCompleteDefaultSettings
 */
function setupUserAutoComplete(field, baseUrl, onSelect, settings = {}) {
    return setupAutoComplete(
        field,
        baseUrl,
        function (item) { return item.full_name; },
        onSelect,
        Object.assign({
            itemInnerHTML: function (item, val) {
                var license = item.license ? ` <small style="color: grey;">(${escapeHTML(item.license)})</small>` : '';
                return `<span>${escapeHTML(val)}${license}</span>`;
            }
        }, settings)
    );
}

window.setupUserAutoComplete = setupUserAutoComplete;



// Formats "parent event" autocomplete options
function formatParentEvent(id, title, start_date)
{
    const truncated = title.length > 30 ? title.substring(0, 30) + '…' : title;
    const dateString = moment(start_date).format('DD/MM/YYYY');
    return `#${id} ${truncated} (${dateString})`;
}