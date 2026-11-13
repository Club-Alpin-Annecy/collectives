
var unregister_message = `L'inscription a un événement vous engage à y participer.

Une désinscription inopinée peut fortement contrarier l'organisation de l'encadrant, voire le pousser à annuler une collective pour laquelle il aura investi de son temps pour l'organiser.

Si lors de votre inscription un paiement a été effectué ou des arrhes ont été demandés par l’encadrant, ils ne vous seront pas remboursés.

Merci de contacter l'encadrant pour prévenir et justifier votre désinscription.

Confirmez-vous la désinscription ?`;

var unregister_message_waiting = `Confirmez-vous la désinscription de la liste d'attente ?`;

const onSelectAutocomplete = function (id, val) {
    document.getElementById('user-search-resultid').value = id;
    document.getElementById('user-search-form').submit();
}

// Function to load into clipboard the Content
// of an input (#id).
function copyToClipboard(id){
    var input = document.getElementById(id);
    input.select();
    input.setSelectionRange(0, 99999); /*For mobile devices*/
    document.execCommand("copy");
}


function attendanceSelectAll(value){
    document.querySelectorAll(`#attendancelist select`).forEach(function(i){
                                                if(i.value=="0"){
                                                    i.value = value;
                                                    i.onchange();
                                                }
                                            });
}

function attendanceUpdate(select, origValue){
    if(select.value != origValue) {
        select.style.color='#eb691c'; 
        select.style.fontWeight='bold';
    } else {
        select.style.color=null; 
        select.style.fontWeight=null;
    }

    if(select.value == EnumRegistrationStatusKeys["Rejected"]) {
        document.getElementById('attendance-rejection-explanation').style.display = null;
    }
}

function showAllRegistration(button) {
    button.parentElement.querySelectorAll('.display-none').forEach(function(el){
        el.classList.remove('display-none');
    });
    button.style.display = 'none';
}
// Before registrations open, display a countdown and reload the page once at
// opening time, rather than having every member refresh it over and over.
function setupRegistrationCountdown() {
    const countdown = document.getElementById('registration-countdown');
    if (!countdown) return;

    // Remaining time comes from the server clock, not from the visitor's one
    const opening = Date.now() + Number(countdown.dataset.seconds) * 1000;
    const value = countdown.querySelector('.registration-countdown-value');
    const pad = (n) => String(n).padStart(2, '0');

    function update() {
        const remaining = Math.max(0, Math.ceil((opening - Date.now()) / 1000));
        const hours = Math.floor(remaining / 3600);
        const minutes = Math.floor((remaining % 3600) / 60);
        const seconds = remaining % 60;
        if (hours > 0) value.textContent = `${hours} h ${pad(minutes)} min`;
        else if (minutes > 0) value.textContent = `${minutes} min ${pad(seconds)} s`;
        else value.textContent = `${seconds} s`;
    }
    update();
    setInterval(update, 1000);

    // A random delay spreads the reloads of all waiting members over a few seconds
    const reloadTime = opening + 500 + Math.random() * 2500;
    const reload = () => window.location.reload();
    setTimeout(reload, reloadTime - Date.now());
    // Browsers delay timers of background tabs: check again when the tab is shown
    document.addEventListener('visibilitychange', () => {
        if (document.visibilityState === 'visible' && Date.now() >= reloadTime) reload();
    });
}

document.addEventListener('DOMContentLoaded', setupRegistrationCountdown);
