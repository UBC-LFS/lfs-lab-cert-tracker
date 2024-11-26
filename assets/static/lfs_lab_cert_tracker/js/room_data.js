$(document).ready(function() {
  const hrefs = window.location.href.split('?t=');

  if (hrefs.length === 2) {
    const table = hrefs[1].split('&next=');
    if (table.length > 0 && table[0] !== 'basic_info') {
      main(table[0] + '-table-0');
    }
  }

  $('.table-trigger').on('click', function() {
    tableID = $(this).data('table');
    main(tableID);
  });
});

function main(tableID) {
  const itemPerPage = 10;
  let currPage = 1;
  let rows = document.getElementById(tableID).getElementsByTagName('tbody')[0].rows;

  $('#display-total-' + tableID).html(rows.length);
  paginate(rows, currPage, tableID, itemPerPage);


  // Pagination

  $('#first-btn-' + tableID).on('click', function() {
    currPage = 1
    paginate(rows, currPage, tableID, itemPerPage);
    $('#display-total-' + tableID).html(rows.length);
  });

  $('#prev-btn-' + tableID).on('click', function() {
    currPage -= 1;
    paginate(rows, currPage, tableID, itemPerPage);
    $('#display-total-' + tableID).html(rows.length);
  });

  $('#next-btn-' + tableID).on('click', function() {
    currPage += 1;
    paginate(rows, currPage, tableID, itemPerPage);
    $('#display-total-' + tableID).html(rows.length);
  });

  $('#last-btn-' + tableID).on('click', function() {
    currPage = Math.ceil(rows.length / itemPerPage);
    paginate(rows, currPage, tableID, itemPerPage);
    $('#display-total-' + tableID).html(rows.length);
  });


  $('#pagination-' + tableID).on('click', '.page-item', function() {
    currPage = parseInt($(this).text());
    paginate(rows, currPage, tableID, itemPerPage);
    $('#display-total-' + tableID).html(rows.length);
  });


  // Search filter
  $('#search-' + tableID).on('keyup', function() {
    rows = filter($(this).data('table'), $(this).val().toLowerCase(), tableID, itemPerPage);
    $('#display-total-' + tableID).html(rows.length);
  });
}

function paginate(rows, num, tableID, itemPerPage) {
  const totalRows = rows.length;
  const pageCount = Math.ceil(totalRows / itemPerPage);

  const prevRange = (num - 1) * itemPerPage;
  const currRange = num * itemPerPage;

  let btns = ''
  for (let i = 1; i <= pageCount; i++) {
    if (i >= num - 3 && i <= num + 3) {
      btns += '<button class="page-item" type="button">' + i + '</button>';
    } else {
      btns += '<button class="page-item" type="button" style="display:none;">' + i + '</button>';
    }
  }
  $('#pagination-' + tableID).html(btns);

  // Make an active page item
  $('#pagination-' + tableID).find('.page-item').each(function() {
    $(this).removeClass('active');
    const currValue = parseInt($(this).text());
    if (currValue === num) {
      $(this).addClass('active');
    }
  });

  const firstBtn = $('#first-btn-' + tableID);
  const prevBtn = $('#prev-btn-' + tableID);
  const nextBtn = $('#next-btn-' + tableID);
  const lastBtn = $('#last-btn-' + tableID);

  if (num === 1) {
    disableButton(firstBtn);
    disableButton(prevBtn);
  } else {
    enableButton(firstBtn);
    enableButton(prevBtn);
  }

  if (pageCount === num) {
    disableButton(nextBtn);
    disableButton(lastBtn);
  } else {
    enableButton(nextBtn);
    enableButton(lastBtn);
  }

  // Show and hide table rows
  for (let i = 0; i < totalRows; i++) {
    if (i >= prevRange && i < currRange) {
      $(rows[i]).toggle(true);
    } else {
      $(rows[i]).toggle(false);
    }
  }
}

function enableButton(btn) {
  btn.removeClass('disabled');
  btn.removeAttr('disabled');
}

function disableButton(btn) {
  btn.addClass('disabled');
  btn.attr('disabled', true);
}

function filter(tableID, value, tableID, itemPerPage) {
  const tbody = document.getElementById(tableID).getElementsByTagName('tbody')[0];
  const filteredRows = [];
  for (const row of tbody.rows) {
    if (row.children.length > 2) {
      let isFiltered = false;
      if (row.children[1].innerHTML.toLowerCase().indexOf(value) > -1) {
        isFiltered = true;
        filteredRows.push(row);
      }
      $(row).toggle(isFiltered);
    }
  }

  if (filteredRows.length === 0) {
    if (tbody.rows[tbody.rows.length - 1].children.length > 2) {
      $('#' + tableID + ' tbody').append('<tr class="no-found-message text-sm"><td colspan="100%">No users found</td></tr>');
    }
  } else {
    $('#' + tableID + ' tbody tr.no-found-message').remove();
  }

  paginate(filteredRows, 1, tableID, itemPerPage);
  return filteredRows;
}
