var editCheck = function(row) {
  return true;
}


  //initialize table
  let table = new Tabulator("#equipment-model-table", {
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
    cellEdited: (cell)=> {
      let id = cell.getRow().getData().id
      let manufacturer = cell.getRow().getData().manufacturer
      let name = cell.getRow().getData().name
      axios.defaults.headers.common['X-CSRF-TOKEN'] = token_csrf;
      axios.post('/api/modelEdit/'+id+'/'+name+'/'+manufacturer)

    },
    columns:[                 //define the table columns
      //{title:"id", field:"id", formatter:"number"},
      {title:"Nom", headerFilter:"input",field:"name", editor: 'input', editable: editCheck},
      {title:"Fabricant", headerFilter:"input",field:"manufacturer", editor: 'input' },
      {title:"Supprimer", formatter:"buttonCross", headerSort:false, cellClick:function(e, cell){
          if(confirm('Attention vous allez supprimer tous les équipements liés à ce modèle ?')) {

              let id = cell.getRow().getData().id

              axios.defaults.headers.common['X-CSRF-TOKEN'] = token_csrf;

              axios.post('/api/modelDelete/'+id)
              .then((response)=>{
                cell.getTable().replaceData();

              })

          }
        }
      },
    ],
     //create columns from data field names
  });