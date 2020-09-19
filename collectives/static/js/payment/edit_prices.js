
function updateNewItemTitleVisibility()
{
    var itemSelect = document.getElementById("existing_item");
    var selectedId = itemSelect.options[itemSelect.selectedIndex].value;
    var showNewItem = selectedId == 0;

    var newItemField = document.getElementById("new-item-title");
    newItemField.style.visibility = showNewItem ? "visible" : "hidden";
    newItemField.style.height = showNewItem ? "auto" : 0;
}

function dateInputsFallback(tail)
{
  // Some browsers do not support HTML5 date pickers yet
  // Use tail instead for those cases
  // See https://stackoverflow.com/questions/18020950/how-to-make-input-type-date-supported-on-all-browsers-any-alternatives
  var dateInputs = document.querySelectorAll("input[type='date']");
  dateInputs.forEach( function(dateInput) {
    if (dateInput && dateInput.type != 'date') {
      tail.DateTime("input[type=date]", {
        weekStart: 1,
        timeFormat: false
      });
    }
  });
}