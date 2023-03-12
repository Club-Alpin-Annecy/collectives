
function escapeHTML(str) {
    return str
      .replace(/&/g, '&amp;')
      .replace(/</g, '&lt;')
      .replace(/>/g, '&gt;')
      .replace(/\"/g, '&quot;')
      .replace(/\'/g, '&#39;')
      .replace(/\//g, '&#x2F;')
}


function sizeFormatter(cell) {
    value = cell.getValue();
    units = [' B', ' kB', ' MB', ' GB', ' TB', 'PB', 'EB', 'ZB', 'YB'];
    while (value > 1024) {
        value = value / 1024;
        units.shift();
    }
    return Math.round(value * 10) / 10 + units[0];
}

