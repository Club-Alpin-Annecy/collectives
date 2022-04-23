      //initialize table
      let table2 = new Tabulator("#returned-equipment-table", {
        ajaxURL:ajaxURLReturnedEquipment,
        layout:"fitColumns",      //fit columns to width of table
        resizableRows:true,
        responsiveLayout:"hide",  //hide columns that dont fit on the table
        tooltips:true,            //show tool tips on cells
        addRowPos:"top",          //when adding a new row, add it to the top of the table
        history:true,              //allow 7 rows per page of data
        movableColumns:true,      //allow column order to be changed
        resizableRows:true,       //allow row order to be changed
        initialSort:[             //set the initial sort order of the data
            {column:"name", dir:"asc"},
        ],
        columns:[
          {
            title:"Référence",
            headerFilter:"input",
            field:"reference"
          },
          {
            title:"Type d'équipement",
            headerFilter:"input",
            field:"typeName",
            formatter:"link",
            formatterParams:{
              urlField:"equipmentURL"
            }
          },
          {
            title:"Commentaire",
            field:"comment",
            editor:"textarea",
            editorParams:{
              elementAttributes:{
                  maxlength:"500", //set the maximum character length of the textarea element to 10 characters
              }
            }
          },
        ],
      });