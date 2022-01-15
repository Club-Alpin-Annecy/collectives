      //initialize table
      let table = new Tabulator("#equipment-table", {
        ajaxURL:ajaxURL,
        layout:"fitColumns",      //fit columns to width of table
        responsiveLayout:"hide",  //hide columns that dont fit on the table
        tooltips:true,            //show tool tips on cells
        addRowPos:"top",          //when adding a new row, add it to the top of the table
        history:true,             //allow undo and redo actions on the table
        pagination:"local",       //paginate the data
        paginationSize:7,         //allow 7 rows per page of data
        movableColumns:true,      //allow column order to be changed
        resizableRows:true,       //allow row order to be changed
        initialSort:[             //set the initial sort order of the data
            {column:"name", dir:"asc"},
        ],
        rowClick: function (e, row) {
          location = row._row.data.equipmentURL
      },
        columns:[              //define the table columns
          //{title:"id", field:"id", formatter:"number"},
          {
            title:"Type",
            headerFilter:"input",
            field:"typeName",
            formatter:"link",
            formatterParams:{
              urlField:"urlEquipmentTypeDetail"
            }
          },
          {
            title:"Modèle",
            headerFilter:"input",
            field:"modelName",
            formatter:"link",
            formatterParams:{
              urlField:"urlEquipmentTypeDetail"
            }
          },
          {
            title:"Reference",
            headerFilter:"input",
            field:"reference",
            formatter:"link",
            formatterParams:{
              urlField:"equipmentURL"
            }
          },
          {
            title:"Etat",
            field:"statusName",
            headerFilter: "select",
	          headerFilterParams:{
              "Libre":"Libre",
              "Loué":"Loué",
              "Révision en cours": "Révision en cours",
              "Invalide": "Invalide"
            }
          },

        ],
         //create columns from data field names
      });