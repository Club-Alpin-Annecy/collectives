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
            title:"Supprimer",
            formatter:"buttonCross",
            headerSort:false,
            cellClick:function(e, cell){
              if(confirm('Voulez-vous vraiment retirer cet équipement de cet réservation ???????')) {

                  let id = cell.getRow().getData().id

                  axios.defaults.headers.common['X-CSRF-TOKEN'] = token_csrf;
                  axios.post('/api/remove_reservation_equipment/'+id+'/'+reservation_id)
                  .then((response)=>{
                    console.log(response)
                    window.location.reload()
                  })

              }
            }
          },
        ],
      });