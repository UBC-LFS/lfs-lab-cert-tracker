$(document).ready(function() {
  let updateAllList = {};

  // Enable a pop-up window
  $('#update-all-btn').on('click', function() {
    $('#select-all-modal').modal('show');
  });

  $('#selected-rooms .room-checkbox').on('click', function() {
    const id = $(this).val();

    if ($(this).is(':checked')) {
      $(this).prop('checked', true);
      updateAllList[id] = {
        'user': $(this).data('user'),
        'building': $(this).data('building'),
        'floor': $(this).data('floor'),
        'number': $(this).data('number')
      };
    } else {
      $(this).prop('checked', false)
      delete updateAllList[id];
    }
    updateInfo(updateAllList);
  });

  $('#select-all-checkbox').on('click', function() {
    for (const tr of $('#selected-rooms > tbody > tr')) {
      $self = $(tr).find('input.room-checkbox');
      if ($(this).is(':checked')) {

        // New rooms are checked
        if ($self.data('is_new') === true) {
          $self.prop('checked', true);
          updateAllList[$self.val()] = {
            'user': $self.data('user'),
            'building': $self.data('building'),
            'floor': $self.data('floor'),
            'number': $self.data('number')
          };
        }
      } else {
        $self.prop('checked', false);
        delete updateAllList[$self.val()];
      }
    }
    updateInfo(updateAllList);
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
      items += '<li id="room_' + key + '"><input type="hidden" name="rooms[]" value="' + key + '" /><span class="text-primary">' + value['user'] + '</span>: ' + value['building'] + ' ' + value['floor'] + ' - Room ' + value['number'] + '</li>';
    }
    $('#update-all-list').html(items);
  }
}
