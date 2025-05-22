/* Helper functions for 'Add Training to Room' and 'Delete Training from Room' */

$(document).ready(function() {
  const itemPerPage = 20;
  let currPage = 1;
  let rows = document.getElementById('table-rooms').getElementsByTagName('tbody')[0].rows;
  let updateAllList = {};

  $('#display-total-rooms').html(rows.length);
  paginate(rows, currPage, itemPerPage);

  // Pagination

  $('#first-btn-rooms').on('click', function() {
    currPage = 1
    paginate(rows, currPage, itemPerPage);
    $('#display-total-rooms').html(rows.length);
  });

  $('#prev-btn-rooms').on('click', function() {
    currPage -= 1;
    paginate(rows, currPage, itemPerPage);
    $('#display-total-rooms').html(rows.length);
  });

  $('#next-btn-rooms').on('click', function() {
    currPage += 1;
    paginate(rows, currPage, itemPerPage);
    $('#display-total-rooms').html(rows.length);
  });

  $('#last-btn-rooms').on('click', function() {
    currPage = Math.ceil(rows.length / itemPerPage);
    paginate(rows, currPage, itemPerPage);
    $('#display-total-rooms').html(rows.length);
  });

  $('#pagination-rooms').on('click', '.page-item', function() {
    currPage = parseInt($(this).text());
    paginate(rows, currPage, itemPerPage);
    $('#display-total-rooms').html(rows.length);
  });

  $('#table-rooms .room-checkbox').on('click', function() {
    const id = $(this).val();

    if ($(this).is(':checked')) {
      $(this).prop('checked', true);
      updateAllList[id] = {
        'building': $(this).data('building'),
        'floor': $(this).data('floor'),
        'room_number': $(this).data('room_number')
      };
    } else {
      $(this).prop('checked', false)
      delete updateAllList[id];
    }
    updateInfo(updateAllList);
  });

  $('#select-all-checkbox').on('click', function() {
    for (const tr of $('#table-rooms > tbody > tr')) {
      $self = $(tr).find('input.room-checkbox');
      if ($(this).is(':checked')) {

        // New rooms are checked
        if ($self.data('is_new') === true) {
          $self.prop('checked', true);
          updateAllList[$self.val()] = {
            'building': $self.data('building'),
            'floor': $self.data('floor'),
            'room_number': $self.data('room_number')
          };
        }

      } else {
        $self.prop('checked', false);
        delete updateAllList[$self.val()];
      }
    }
    updateInfo(updateAllList);
  });

  // Filter
  $('#select-building').on('change', function() {
    rows = filter(this.value, $('#select-floor').val(),  $('#select-room').val(), itemPerPage);
    $('#display-total-rooms').html(rows.length);
  });

  $('#select-floor').on('change', function() {
    rows = filter($('#select-building').val(), this.value,  $('#select-room').val(), itemPerPage);
    $('#display-total-rooms').html(rows.length);
  });

  $('#select-room').on('change', function() {
    rows = filter($('#select-building').val(), $('#select-floor').val(),  this.value, itemPerPage);
    $('#display-total-rooms').html(rows.length);
  });
});

function paginate(rows, num, itemPerPage) {
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

  $('#pagination-rooms').html(btns);

  // Make an active page item
  $('#pagination-rooms').find('.page-item').each(function() {
    $(this).removeClass('active');
    const currValue = parseInt($(this).text());
    if (currValue === num) {
      $(this).addClass('active');
    }
  });

  const firstBtn = $('#first-btn-rooms');
  const prevBtn = $('#prev-btn-rooms');
  const nextBtn = $('#next-btn-rooms');
  const lastBtn = $('#last-btn-rooms');

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

function filter(building, floor, room, itemPerPage) {
  const tbody = document.getElementById('table-rooms').getElementsByTagName('tbody')[0];
  let filteredRows = [];
  let count = 0;

  if (building) count++;
  if (floor) count++;
  if (room) count++;

  let searching = [];
  let c = 0;
  for (const row of tbody.rows) {
    if (row.children.length === 7) {
      let temp = 0;
      if (building && row.children[1].innerHTML.indexOf(building) > -1) temp++;
      if (floor && row.children[2].innerHTML.indexOf(floor) > -1) temp++;
      if (room && row.children[3].innerHTML.indexOf(room) > -1) temp++;
      searching.splice(c, 0, temp);
    }
    c++;
  }

  c = 0;
  for (const row of tbody.rows) {
    if (row.children.length === 7) {
      let isFiltered = false;
      if (searching[c] === count) {
        isFiltered = true;
        filteredRows.push(row);
      }
      $(row).toggle(isFiltered);
    }
    c++;
  }

  if (filteredRows.length === 0) {
    if (tbody.rows[tbody.rows.length - 1].children.length === 7) {
      $('#table-rooms' + ' tbody').append('<tr class="no-found-message text-sm"><td colspan="100%">No users found</td></tr>');
    }
  } else {
    $('#table-rooms' + ' tbody tr.no-found-message').remove();
  }

  paginate(filteredRows, 1, itemPerPage);
  return filteredRows;
}
