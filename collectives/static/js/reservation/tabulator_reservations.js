      //initialize table
      let table = new Tabulator("#reservations-table", {
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
          location = row._row.data.reservationURL
      },
        columns:[
          {
            title:"collect_date",
            headerFilter:"input",
            field:"collect_date",
          },
          {
            title:"return_date",
            headerFilter:"input",
            field:"return_date",
          },
          {
            title:"userLicence",
            headerFilter:"input",
            field:"userLicence",
          },
          {
            title:"Etat",
            headerFilter:"input",
            field:"statusName",
          },

        ],
      });