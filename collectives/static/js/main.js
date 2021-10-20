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