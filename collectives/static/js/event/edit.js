function severalDays(e){
  var field = document.getElementById('datetimepickerend');
  if(e.checked)
    field.style.display="inline";
  else
    field.style.display="none";
  copyStartDate();
}

// Fonction to copy start date into end date in case of one day event
function copyStartDate(){
  if( ! document.querySelector('input[name=several]').checked)
      document.querySelector('input[name=end]').value = document.querySelector('input[name=start]').value;
}

window.onload = function() {
      severalDays(document.querySelector('input[name=several]')) ;
}
