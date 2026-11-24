var Collectives = {
    
};

var initDropdowns = function initDropdowns() {
    var dropdowns = document.querySelectorAll('.menu-dropdown');
    dropdowns.forEach(function(item) {
        var trigger = item.querySelector('.menu-dropdown-trigger');
        if (trigger) {
            trigger.addEventListener('click', function(e) {
                item.classList.toggle('menu-dropdown-active')
            });
        }
    })
}

var initAll = function initAll() {
    initDropdowns();
}

Collectives.initAll  = initAll;

window.Collectives = Object.assign(window.Collectives, Collectives)


window.addEventListener('load', function(e) {
    // Initialize everything once Content is loaded
    Collectives.initAll();
});

/**
 * Scroll back to the top of the page, or of targetElement when given, when the
 * user changes page with the paginator of a Tabulator table.
 *
 * Listens to the paginator clicks rather than to Tabulator's pageLoaded, which
 * also fires on the initial load and on every filter or sort change.
 */
var bindScrollToTopOnPageChange = function bindScrollToTopOnPageChange(table, targetElement) {
    table.element.addEventListener('click', function (e) {
        if (!e.target.closest('.tabulator-page')) {
            return;
        }
        if (targetElement) {
            targetElement.scrollIntoView({ behavior: 'smooth' });
        } else {
            window.scrollTo({ top: 0, behavior: 'smooth' });
        }
    });
};
