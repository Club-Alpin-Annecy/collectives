// Fonction to copy start date into end date in case of one day event
function copyStartDate(){
    if (!document.querySelector('input[name=end]').value)
        document.querySelector('input[name=end]').value = document.querySelector('input[name=start]').value;
}

