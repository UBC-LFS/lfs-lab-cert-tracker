$(document).ready(function() {

  // Enable a pop-up window
  $('#update-all-btn').on('click', function() {
    $('#select-all-modal').modal('show');
  });

});

// Update the number of clicked rooms
function updateInfo(list) {
  const updateAllNum = Object.keys(list).length;

  if (updateAllNum >= 0) {
    $('#update-all-num-1').html(updateAllNum);
    $('#update-all-num-2').html(updateAllNum);
  }

  if (updateAllNum == 0) {
    // Disable the Update All button
    $('#update-all-btn').prop('disabled', true);
    $('#select-all-checkbox').prop('checked', false)
  } else if (updateAllNum > 0) {
    // Enable the Update All button
    $('#update-all-btn').prop('disabled', false);

    // Display a list of clicked rooms in the pop-up window
    items = '';
    for (const [key, value] of Object.entries(list)) {
      items += '<li id="room_' + key + '"><input type="hidden" name="rooms[]" value="' + key + '" />' + value['building'] + ' ' + value['floor'] + ' - Room ' + value['room_number'] + '</li>';
    }
    $('#update-all-list').html(items);
  }
}
