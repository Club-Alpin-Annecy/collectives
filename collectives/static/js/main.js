var Collectives = {
    
};

var closeDropdown = function closeDropdown(item) {
    item.classList.remove('menu-dropdown-active');
    item.querySelector('.menu-dropdown-trigger').setAttribute('aria-expanded', 'false');
}

var initDropdowns = function initDropdowns() {
    var dropdowns = document.querySelectorAll('.menu-dropdown');
    dropdowns.forEach(function(item) {
        var trigger = item.querySelector('.menu-dropdown-trigger');
        if (!trigger) {
            return;
        }
        trigger.addEventListener('click', function(e) {
            var isOpen = item.classList.toggle('menu-dropdown-active');
            trigger.setAttribute('aria-expanded', isOpen ? 'true' : 'false');
        });
        item.addEventListener('keydown', function(e) {
            if (e.key === 'Escape' && item.classList.contains('menu-dropdown-active')) {
                closeDropdown(item);
                trigger.focus();
            }
        });
        // Close the menu when the focus or a click goes elsewhere
        item.addEventListener('focusout', function(e) {
            if (e.relatedTarget && !item.contains(e.relatedTarget)) {
                closeDropdown(item);
            }
        });
        document.addEventListener('click', function(e) {
            if (!item.contains(e.target)) {
                closeDropdown(item);
            }
        });
    })
}

var FOCUSABLE_SELECTOR = 'a[href], button, input:not([type=hidden]), select, textarea';

var openDialog = function openDialog(dialog, opener) {
    dialog.opener = opener;
    dialog.style.display = 'block';
    dialog.querySelector(FOCUSABLE_SELECTOR).focus();
}

var closeDialog = function closeDialog(dialog) {
    dialog.style.display = 'none';
    if (dialog.opener) {
        dialog.opener.focus();
    }
}

// Dialogs are the ".messages" panels: flashed messages, shown on load, and
// confirmation panels opened by a "data-dialog-open" button.
var initDialogs = function initDialogs() {
    document.querySelectorAll('.messages').forEach(function(dialog) {
        dialog.querySelectorAll('.close, .veil, [data-dialog-close]').forEach(function(closer) {
            closer.addEventListener('click', function(e) {
                closeDialog(dialog);
            });
        });
        dialog.addEventListener('keydown', function(e) {
            if (e.key === 'Escape') {
                closeDialog(dialog);
                return;
            }
            if (e.key !== 'Tab') {
                return;
            }
            // Keep the keyboard focus inside the dialog
            var focusables = dialog.querySelectorAll(FOCUSABLE_SELECTOR);
            var first = focusables[0];
            var last = focusables[focusables.length - 1];
            if (e.shiftKey && document.activeElement === first) {
                e.preventDefault();
                last.focus();
            } else if (!e.shiftKey && document.activeElement === last) {
                e.preventDefault();
                first.focus();
            }
        });
        if (dialog.style.display !== 'none') {
            openDialog(dialog, null);
        }
    });
    document.querySelectorAll('[data-dialog-open]').forEach(function(opener) {
        opener.addEventListener('click', function(e) {
            openDialog(document.getElementById(opener.dataset.dialogOpen), opener);
        });
    });
}

var initAll = function initAll() {
    initDropdowns();
    initDialogs();
}

Collectives.initAll  = initAll;

window.Collectives = Object.assign(window.Collectives, Collectives)


window.addEventListener('load', function(e) {
    // Initialize everything once Content is loaded
    Collectives.initAll();
});