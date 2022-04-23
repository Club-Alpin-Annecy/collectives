let table_taken = new Tabulator("#equipment-type-taken-table", {
      layout:"fitColumns",      //fit columns to width of table
      responsiveLayout:"hide",  //hide columns that dont fit on the table
      tooltips:true,            //show tool tips on cells
      addRowPos:"top",          //when adding a new row, add it to the top of the table
      history:true,             //allow undo and redo actions on the table
      movableColumns:true,      //allow column order to be changed
      resizableRows:true,       //allow row order to be changed
      initialSort:[             //set the initial sort order of the data
          {column:"name", dir:"asc"},
     ],
      columns:[                 //define the table columns
        //{title:"id", field:"id", formatter:"number"},
        {title:"Photo", field:"pathImg", formatter:"image", formatterParams:{height: '7em'}},
        {title:"Type", field:"name"},
        {title:"Quantité", field:"quantity", editor:"number",
          editorParams:{
            min:1, max:20, step:1,
            elementAttributes:{ maxlength:"2" },
          },
          validator:["integer","max:50", "min:1"]
        },
        {title:"Supprimer", headerSort:false,
          formatter : function() {
            return "<input type='image' src='/static/img/icon/ionicon/md-trash.svg' style='margin: 0;height: 1.2em; width: 1.2em' title='Ajouter'/>"
          },
          cellClick : function(e,cell) {
            cell.getRow().delete();
          }
        }
      ],
        //create columns from data field names
    });