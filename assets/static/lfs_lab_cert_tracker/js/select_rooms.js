$(document).ready(function() {
  let data = {
    'building': {'id': '', 'name': '', 'code': ''},
    'floor': {'id': '', 'name': ''},
    'rooms': {}
  };

  if (sessionStorage.getItem('key-request-data')) {
    data = JSON.parse(sessionStorage.getItem('key-request-data'));
  }

  // Send a post data
  $('#select-rooms-continue').on('click', function() {
    const rooms = [];
    for (let [k, v] of Object.entries(data['rooms'])) {
      rooms.push(v['id']);
    }
    $.ajax({
      method: 'POST',
      url: $(this).data('post-url'),
      data: {
        'rooms[]': rooms,
        'next': $(this).data('next-url'), 'csrfmiddlewaretoken': $(this).data('token')
      },
      dataType: 'json',
      success: function(res) {
        window.location.href = res.next;
      }
    });
  });


  // Check if a selected building exists
  if (data['building']['id']) {
    $('#select-building option[value="' + data['building']['id'] + '"]').attr('selected', 'selected');
    displayFloorOptions(rooms, data['building']['id']);
  }

  // Check if a selected floor exists
  if (data['floor']['id']) {
    $('#select-floor option[value="' + data['floor']['id'] + '"]').attr('selected', 'selected');
    displayRooms(rooms, data['building']['id'], data['floor']['id']);
  }

  // Check if selected rooms exist
  if (Object.keys(data['rooms']).length > 0) {
    checkRooms(data['rooms']);
    updateHTMLForSelectedRooms(data['rooms']);
  }

  /*
   * Click Event - Select Actions
   */

  // Select a building
  $('#select-building').on('change', function() {
    $('#select-floor option:not(:first)').remove();
    $('#select-room').html('<tr><td colspan="100%">Select a Building and a Floor to see a list of rooms</td></tr>');

    const id = this.value;
    if (id && rooms[id]) {
      selectOption('building', id);
      displayFloorOptions(rooms, id);

      data['building']['id'] = id;
      data['building']['name'] = $(this).find(':selected').attr('name');
      data['building']['code'] = $(this).find(':selected').attr('code');
      sessionStorage.setItem('key-request-data', JSON.stringify(data));
    } else {
      sessionStorage.removeItem('key-request-data');
    }
  });

  // Select a floor
  $('#select-floor').on('change', function() {
    $('#select-room').html('<tr><td colspan="100%">Select a Building and a Floor to see a list of rooms</td></tr>');

    const buildingID = data['building']['id'];
    const id = this.value;

    if (buildingID && id && rooms[buildingID][id]) {
      selectOption('floor', id);
      displayRooms(rooms, buildingID, id);
      checkRooms(data['rooms']);

      data['floor']['id'] = id;
      data['floor']['name'] = $(this).find(':selected').attr('name');
      sessionStorage.setItem('key-request-data', JSON.stringify(data));
    } else {
      data['floor'] = {'id': '', 'name': ''};
      sessionStorage.setItem('key-request-data', JSON.stringify(data));
    }
  });

  // Select rooms in the list
  $('#select-room').on('change', 'input', function() {
    const buildingCode = data['building']['code'];
    const floorName = data['floor']['name'];
    const id = this.value;
    const number = $(this).data('number');

    if (buildingCode && floorName && id && number) {
      if (Object.keys(data['rooms']).includes('room_' + id)) {
        deleteSelectedRooms(data, 'room_' + id);
      } else {
        appendSelectedRooms(data, buildingCode, floorName, id, number);
      }
    }
  });

  // Delete a room in the selected rooms
  $('#display-selected-rooms').on('click', '.selected-rooms .room', function() {
    deleteSelectedRooms(data, $(this).data('room'));
  });

  $('#display-selected-rooms').on('click', '.delete-all', function() {
    if (Object.keys(data['rooms']).length > 0) {
      for (let room of Object.keys(data['rooms'])) {
        $('#' + room).prop('checked', false).removeAttr('checked');
      }
      if (sessionStorage.getItem('key-request-data')) {
        sessionStorage.removeItem('key-request-data');
      }
      data = {
        'building': {'id': '', 'name': '', 'code': ''},
        'floor': {'id': '', 'name': ''},
        'rooms': {}
      };
      $('#display-selected-rooms').html('<p class="text-center text-secondary">Your selected rooms will be displayed here.</p>');
      window.location.reload();
    }
  });

});


/*
 * Helper functions
 */


// Select a building
function selectBuilding(buildingID) {
  $('#select-building option').each(function() {
    $(this).removeAttr('selected');
  });

  if (buildingID) {
    $('#select-building option[value="' + buildingID + '"]').attr('selected', 'selected');
  }
}

// Select an option for a building and a floor
function selectOption(item, id) {
  $('#select-'+ item +' option').each(function() {
    $(this).removeAttr('selected');
  });

  if (id) {
    $('#select-' + item + ' option[value="' + id + '"]').attr('selected', 'selected');
  }
}

// Display floor options
function displayFloorOptions(rooms, buildingID) {
  if (rooms && buildingID) {
    for (let floorID of Object.keys(rooms[buildingID])) {
      const floor = rooms[buildingID][floorID];
      $('#select-floor').append('<option value="' + floor['id'] + '" name="' + floor['name'] + '">' + floor['name'] + '</option>');
    }
  }
}

// Display rooms
function displayRooms(rooms, buildingID, floorID) {
  if (rooms && buildingID && floorID && rooms[buildingID][floorID]) {
    $('#select-room').html('');
    for (let room of rooms[buildingID][floorID]['numbers']) {
      if (room['is_active']) {
        $('#select-room').append('<tr><td><input id="room_' + room['id'] + '" type="checkbox" name="room[]" value="' + room['id'] + '" data-number="' + room['number'] + '" /></td><td>' + room['number'] + '</td><td class="text-left">' + createList(room['areas']) + '</td><td class="text-left">' + createList(room['trainings']) + '</td></tr>');
      }
    }
  }
}

// Check rooms
function checkRooms(rooms) {
  for (let room of Object.keys(rooms)) {
    $('#' + room).attr('checked', 'checked');
  }
}

// Append selected rooms and update html
function appendSelectedRooms(data, buildingCode, floorName, roomID, roomNumber) {
  $('#room_' + roomID).attr('checked', 'checked');
  data['rooms']['room_' + roomID] = { 'id': roomID, 'number': roomNumber, 'building': buildingCode, 'floor': floorName };
  sessionStorage.setItem('key-request-data', JSON.stringify(data));
  updateHTMLForSelectedRooms(data['rooms']);
}

// Delete a room in the selected rooms
function deleteSelectedRooms(data, room) {
  delete data['rooms'][room];
  $('#' + room).prop('checked', false).removeAttr('checked');

  if (Object.keys(data['rooms']).length === 0) {
    $('#display-selected-rooms').html('<p class="text-center text-secondary">Your selected rooms will be displayed here.</p>');
  } else {
    updateHTMLForSelectedRooms(data['rooms']);
  }
  sessionStorage.setItem('key-request-data', JSON.stringify(data));
}

// Update html in the selected rooms
function updateHTMLForSelectedRooms(rooms) {
  if (Object.keys(rooms).length > 0) {
    let content = '<table class="table selected-rooms">';
    let count = 1;
    for (let [id, item] of Object.entries(rooms)) {
      content += '<tr><td>' + count + '</td><td>' + item['building'] + ' - ' + item['floor'] + '</td><td>Room ' + item['number'] + '</td><td><button class="btn btn-xs btn-danger room" type="button" data-room="' + id + '">Del</button></td></tr>';
      count++;
    }
    content += '</table><button class="btn btn-danger delete-all" type="button">Delete All</button>';
    $('#display-selected-rooms').html(content);
  }
}

function createList(items) {
  let list = '<ul class="list-minus-20">';
  for (let item of items) {
    list += '<li>' + item['name'] + '</li>';
  }
  list += '</ul>';
  return list;
}
