


function createEventConditionsTable(id) {

    function genFieldId(rowIndex, fieldName) {
        return `${id}-${rowIndex}-${fieldName}`
    }

    function hiddenField(rowIndex, fieldName, value) {
        var fieldId = genFieldId(rowIndex, fieldName);
        return `<input type="hidden" id="${fieldId}" name="${fieldId}" value="${value}">`
    }

    function deleteRow(e, cell) {
        cell.getRow().delete();

        if (cell.getTable().getData().length == 0) {
            var field = document.getElementById(id);
            field.classList.add('display-none');
        }
    }

    function hiddenFieldsFormatter(cell, formatterParams, onRendered) {
        const row = cell.getRow();
        const rowIndex = row.getIndex();
        const eventId = cell.getRow().getData().event_id
        return hiddenField(rowIndex, "event_id", row.getData().event_id)
            + hiddenField(rowIndex, "condition_id", row.getData().condition_id);
    }
    
    function isLeaderFormatter(cell, formatterParams, onRendered) {
        const row = cell.getRow();
        const rowIndex = row.getIndex();

        selectId = genFieldId(rowIndex, "is_leader");
        selectOptions = [
            ["", "Encadrant ou Participant"],
            [0, "Participant"],
            [1, "Encadrant"],
        ];

        selectStr = `<select style="width:auto; margin-bottom:auto" name="${selectId}" id="${selectId}">`;
        selectOptions.forEach((option) => {
            selected = option[0] === row.getData().is_leader ? "selected" : "";
            selectStr += `<option value="${option[0]}" ${selected}>${option[1]}</option>`;
        });
        selectStr += `</select>`;

        return selectStr;
    }

    return new Tabulator("#" + id,
        {
            layout: "fitColumns",

            columns: [
                {
                    title: "Evénement", field: "event_name", formatter: "link", formatterParams: { urlField: "event_url" }
                },
                { title: "En tant que", field: "is_leader", align: "center", formatter: isLeaderFormatter, headerSort: false },
                { field: "delete", width: "24", align: "center", formatter: "buttonCross", cellClick: deleteRow, headerSort: false },
                { field: "event_id",  formatter: hiddenFieldsFormatter, visible: false, headerSort: false }
            ],
        });

}

function setupEventConditionsEditor(fieldId, existing) {
    if (existing.length == 0) {
        var field = document.getElementById(fieldId);
        field.classList.add('display-none');
    }

    var table = createEventConditionsTable(fieldId);
    table.setData(existing);

    
    return table;
}

function addEventCondition(table, fieldId, val, isLeaderSelectId) {
    val = JSON.parse(val);

    var isLeaderSelect = document.getElementById(isLeaderSelectId);

    var rowCount = table.getRows().length;
    var index = rowCount == 0 ? 0 : (table.getRows()[rowCount-1].getIndex() + 1);

    table.addData(
        [
            {
                "id": index,
                "condition_id": "",
                "event_id": val.id,
                "event_name": val.title,
                "event_url": val.view_uri,
                "is_leader": isLeaderSelect.value === "" ? "" : parseInt(isLeaderSelect.value)
            }
        ]
    );

    if(index == 0) {
       var field = document.getElementById(fieldId);
      field.classList.remove('display-none');
    }
}


function createRoleConditionsTable(id) {

    function genFieldId(rowIndex, fieldName) {
        return `${id}-${rowIndex}-${fieldName}`
    }

    function hiddenField(rowIndex, fieldName, value) {
        var fieldId = genFieldId(rowIndex, fieldName);
        return `<input type="hidden" id="${fieldId}" name="${fieldId}" value="${value}">`
    }

    function deleteRow(e, cell) {
        cell.getRow().delete();

        if (cell.getTable().getData().length == 0) {
            var field = document.getElementById(id);
            field.classList.add('display-none');
        }
    }

    function hiddenFieldsFormatter(cell, formatterParams, onRendered) {
        const row = cell.getRow();
        const rowIndex = row.getIndex();
        const eventId = cell.getRow().getData().event_id
        return hiddenField(rowIndex, "role_id", row.getData().role_id)
            + hiddenField(rowIndex, "activity_id", row.getData().activity_id)
            + hiddenField(rowIndex, "condition_id", row.getData().condition_id);
    }

    return new Tabulator("#" + id,
        {
            layout: "fitColumns",

            columns: [
                {title: "Rôle", field: "role_name", formatter: "text"},
                {title: "Activité", field: "activity_name", formatter: "text"},
                { field: "delete", width: "24", align: "center", formatter: "buttonCross", cellClick: deleteRow, headerSort: false },
                { field: "role_id",  formatter: hiddenFieldsFormatter, visible: false, headerSort: false }
            ],
        });

}

function setupRoleConditionsEditor(fieldId, existing) {
    if (existing.length == 0) {
        var field = document.getElementById(fieldId);
        field.classList.add('display-none');
    }

    var table = createRoleConditionsTable(fieldId);
    table.setData(existing);
    return table;
}

function addRoleCondition(fieldId, roleSelectId, activitySelectId) {
    var roleSelect = document.getElementById(roleSelectId);
    var activitySelect = document.getElementById(activitySelectId);
    
    var role_id = roleSelect.value;
    var role_name = roleSelect.options[roleSelect.selectedIndex].text;
    
    var activity_id = activitySelect.value;
    var activity_name = activitySelect.options[activitySelect.selectedIndex].text;
    
    var table = Tabulator.prototype.findTable("#"+fieldId)[0];
    var rowCount = table.getRows().length;
    var index = rowCount == 0 ? 0 : (table.getRows()[rowCount-1].getIndex() + 1);

    table.addData(
        [
            {
                "id": index,
                "condition_id": "",
                "role_id": role_id,
                "role_name": role_name,
                "activity_id": activity_id,
                "activity_name": activity_name,
            }
        ]
    );

    if(index == 0) {
       var field = document.getElementById(fieldId);
       field.classList.remove('display-none');
    }
}