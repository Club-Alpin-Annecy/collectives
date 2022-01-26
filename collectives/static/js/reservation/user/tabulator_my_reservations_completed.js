      //initialize table
      let tableHistoricalReservations = new Tabulator("#historical-reservation-table", {
        ajaxURL:ajaxURLHistoricalReservation,
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
          location = row._row.data.reservationURLUser
      },
        columns:[
          {
            title:"Date de collecte",
            headerFilter:"input",
            field:"collect_date",
            formatter:"datetime", formatterParams:{
              outputFormat:"DD/MM/YYYY"
            },
          },
          {
            title:"Date de retour",
            headerFilter:"input",
            field:"return_date",
            formatter:"datetime", formatterParams:{
              outputFormat:"DD/MM/YYYY"
            },
          },
          {
            title:"Licence",
            headerFilter:"input",
            field:"userLicence",
          },
          {
            title:"État",
            headerFilter:"input",
            field:"statusName",
          },

        ],
      });