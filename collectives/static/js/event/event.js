
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
