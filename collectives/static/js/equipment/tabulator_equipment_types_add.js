function actionFormatter(cell, formatterParams, onRendered){
  return '<form style="display:inline; padding:0" action="'+ cell.getValue() +'" method="'+formatterParams['method']+'" ></form><input type="image" src="/static/img/icon/ionicon/md-'+formatterParams['icon']+'.svg" style="margin: 0;height: 1.2em; width: 1.2em"  alt="'+formatterParams['alt']+'" title="'+formatterParams['alt']+'"/>';
}

function onclickTriggerInsideForm(e, cell){
  cell._cell.element.querySelector('form').submit();
}

function cellInTable(tab, value){
  for(row of tab.getData()) {
    if(row.id == value) { console.log("true"); return true }
  }
  return false;
}
//initialize table
let table = new Tabulator("#equipment-type-table", {
      ajaxURL:ajaxURL,
      layout:"fitColumns",      //fit columns to width of table
      responsiveLayout:"hide",  //hide columns that dont fit on the table
      tooltips:true,            //show tool tips on cells
      addRowPos:"top",          //when adding a new row, add it to the top of the table
      history:true,             //allow undo and redo actions on the table
      pagination:"local",       //paginate the data
      paginationSize:4,         //allow 7 rows per page of data
      movableColumns:true,      //allow column order to be changed
      resizableRows:true,       //allow row order to be changed
      initialSort:[             //set the initial sort order of the data
          {column:"name", dir:"asc"},
      ],
      columns:[                 //define the table columns
        //{title:"id", field:"id", formatter:"number"},
        {title:"Photo", field:"pathImg", formatter:"image", formatterParams:{height: '7em'}},
        {title:"Type", headerFilter:"input",field:"name"},
        {title:"Quantité", field:"quantity", editor:"number",
          editorParams:{
            min:0, max:50, step:1,
            elementAttributes:{maxlength:"2"},
          },
          validator:["integer","max:50"]
        },
        {title:"Ajouter au panier", headerSort:false,
          formatter : actionFormatter, formatterParams:{'icon': 'add-circle-outline', 'method': 'POST', 'alt': 'Ajouter'},
          cellClick : function(e,cell) {
            let row = cell.getRow();
            let qty = row.getData().quantity;
            if(!cellInTable(table_taken, row.getData().id)) {
              if(qty < 1 || !qty) table.updateRow(row.getIndex(), {quantity:1});
              table_taken.addData(row.getData());
            }
          }
        }
      ],
        //create columns from data field names
    });