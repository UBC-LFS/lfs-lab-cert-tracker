$(document).ready(function() {

  // Enable a pop-up window
  $('#delete-all-btn').on('click', function() {
    $('#select-all-modal').modal('show');
  });
});


// Update the number of clicked rooms
function updateInfo(list) {
  const updateAllNum = Object.keys(list).length;

  if (updateAllNum >= 0) {
    $('#delete-all-num-1').html(updateAllNum);
    $('#delete-all-num-2').html(updateAllNum);
  }

  if (updateAllNum == 0) {
    // Disable the Update All button
    $('#delete-all-btn').prop('disabled', true);
    $('#select-all-checkbox').prop('checked', false)
  } else if (updateAllNum > 0) {
    // Enable the Update All button
    $('#delete-all-btn').prop('disabled', false);

    // Display a list of clicked rooms in the pop-up window
    items = '';
    for (const [key, value] of Object.entries(list)) {
      items += '<li id="room_' + key + '"><input type="hidden" name="rooms[]" value="' + key + '" />' + value['building'] + ' ' + value['floor'] + ' - Room ' + value['room_number'] + '</li>';
    }
    $('#delete-all-list').html(items);
  }
}
