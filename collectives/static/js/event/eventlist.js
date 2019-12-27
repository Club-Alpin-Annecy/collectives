
var locale = window.navigator.userLanguage || window.navigator.language;
moment.locale(locale);
String.prototype.capitalize = function() {
  return this.charAt(0).toUpperCase() + this.slice(1)
}

window.onload = function(){

  		var eventstable = new Tabulator("#eventstable", {
  			layout:"fitColumns",
  			ajaxURL: '/api/events/',
  			resizableColumns:false,
            groupBy:"start",
            pagination : 'remote',
            paginationSize : 10,
            //initialSort:[ {column:"start", dir:"asc"}],
  			columns:[
      			{title:"Titre", field:"title", sorter:"string"},
                {title:"Date", field:"start", sorter:"string"},
  			],
            rowClick: function(e, row){ document.location= row.getData().view_uri},
  			rowFormatter: eventRowFormatter,
            groupHeader:function(value, count, data, group){
                return moment(new Date(value)).format('dddd D MMMM YYYY').capitalize();
            },
  		})
};

function eventRowFormatter(row){
    var element = row.getElement();
    var data    = row.getData();
    var width   = element.offsetWidth;
    var html    = "";

    //clear current row data
    element.childNodes.forEach(function(e){ e.style.display="none"});

    //define a table layout structure and set width of row
    divRow = document.createElement("div");
    divRow.className = "row tabulator-cell";
    divRow.setAttribute("role","gridcell");
    divRow.style.width = (width - 18) + "px";

    //add row data on right hand side
    html += `<div class="activities section">`;
    for (const activity of data.activity_types)
                html += `<span class="activity ${activity['short']} type"></span>`;
    html += `</div>`;

    html += `<div class="section">
                <img src="${data.photo_uri}" class="photo"/>
             </div>`;

    html += `<div class="section">
                 <h4>${data.title}</h4>
                 <div class="date">
                     <img src="/static/img/icon/ionicon/md-calendar.svg" class="icon"/>
                     ${localInterval(data.start, data.end)}
                 </div>

                 <div class="leader">
                    Par ${data.leaders.map(displayLeader).join('et')}
                 </div>
                 <div class="slots">
                    ${slots(data.num_slots - data.free_slots)}
                    ${slots(data.free_slots, 'free_slot')}
                 </div>
             </div>
             <div class="breaker"></div>`;
    divRow.innerHTML = html;

    //append newly formatted contents to the row
    element.append(divRow);
}

function localInterval(start, end){
    if( start == end)
        return localDate(new Date(start));
    return `${localDate(new Date(start))} au ${localDate(new Date(end))}`;
}

function localDate(date){
    return moment(date).format('ddd D MMM YY');
}
function slots(nb, css){
    if(css == undefined)
        css = '';
    var slot = `<img src="/static/img/icon/ionicon/md-contact.svg" class="icon ${css}"/>`;
    return (new Array(nb)).fill( slot ).join('');
}
function displayLeader(user){
    return user.name;
}
