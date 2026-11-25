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

// Buttons showing or hiding the content of the password field they control
var initPasswordReveal = function initPasswordReveal() {
    document.querySelectorAll('.password-reveal').forEach(function(button) {
        button.addEventListener('click', function() {
            var input = document.getElementById(button.getAttribute('aria-controls'));
            var reveal = input.type === 'password';
            input.type = reveal ? 'text' : 'password';
            button.setAttribute('aria-pressed', reveal ? 'true' : 'false');
        });
    });
}

// The tab title is the main heading of the page, followed by the site name
var initPageTitle = function initPageTitle() {
    var heading = document.querySelector('main h1') || document.querySelector('main .heading-1, main .heading-2');
    if (heading && heading.textContent.trim()) {
        document.title = heading.textContent.trim().replace(/\s+/g, ' ') + ' – ' + document.title.trim();
    }
}

// An icon without alternative text only illustrates the label next to it:
// hide it from screen readers, which would otherwise read its file name.
// Images carrying information have their own alt.
var initDecorativeIcons = function initDecorativeIcons() {
    document.querySelectorAll('img.icon:not([alt]), img.legacy-icon:not([alt])').forEach(function(icon) {
        icon.setAttribute('aria-hidden', 'true');
    });
}

var initAll = function initAll() {
    initPageTitle();
    initDecorativeIcons();
    initDropdowns();
    initDialogs();
    initPasswordReveal();
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
