$(document).ready(function() {

	// Search filter
	$('.area-search-input').on('keyup', function() {
		const user = $(this).data('user');
    const value = $(this).val().toLowerCase();

    const $filtered  = $('#area-list-' + user +' tbody tr').filter(function() {
			const isMatched = $(this).text().toLowerCase().indexOf(value) > -1;
			$(this).toggle(isMatched);
      return isMatched;
    });

		if ($filtered.length == 0) {
			$('#area-list-' + user + ' tbody').append('<tr class="no-found-message text-sm"><td colspan="3">No areas found</td></tr>');
		} else {
			$('#area-list-' + user + ' tbody tr.no-found-message').remove();
		}

  });

	// Enable Is PI input
	$('form .custom-table .area-input').on('change', function() {
		const path = '#role-input-area' + $(this).data('area') + '-user' +  $(this).data('user');

		if ( $(path).attr('disabled') === 'disabled' ) {
			$(path).prop('disabled', false);
		} else {
			$(path).prop('disabled', true);
		}
	});

	// Add
	$('form .btn-submit').on('click', function(e) {
		e.preventDefault();

		$(this).val('Wait! Saving...');
		$(this).prop('disabled', true);

		const userId = $(this).data('user');
		const formData = $('#area-list-form-' + userId).serializeArray();

		$.ajax({
			method: 'POST',
			url: $(this).data('url'),
			data: formDataToJson(JSON.stringify(formData)),
			dataType: 'json',
			success: function(res) {
				let message = '<div class="alert alert-STATUS alert-dismissible fade show" role="alert">' +
												res.message +
												'<button type="button" class="close" data-dismiss="alert" aria-label="Close"><span aria-hidden="true">&times;</span></button>' +
											'</div>';

				if (res.status === 'success') message = message.replace('STATUS', 'success');
				if (res.status === 'warning') message = message.replace('STATUS', 'warning');
				else message = message.replace('STATUS', 'danger');

				$('#user-areas-message').html(message);
				sessionStorage.setItem( 'assign-user-areas', JSON.stringify({ 'status': res.satus, 'message': message }) );
				location.reload();
			},
			error: function(err) {
				const message = '<div class="alert alert-danger alert-dismissible fade show" role="alert">' +
													'An error occurred. ' + err.statusText + ' (' + err.status + '). Please contact administrator for assistance.' +
													'<button type="button" class="close" data-dismiss="alert" aria-label="Close"><span aria-hidden="true">&times;</span></button>' +
												'</div>';
				$('#user-area-modal-' + userId + '-error').html(message);
		 }
		});
	});

	if ( sessionStorage.getItem('assign-user-areas') ) {
    const data = JSON.parse( sessionStorage.getItem('assign-user-areas') );
    $('#user-areas-message').append(data.message);
    sessionStorage.removeItem('assign-user-areas');
  }

});

function formDataToJson(form_data) {
	const data = JSON.parse(form_data);
	const len = data.length;

  let json = {};
	json[ data[0]['name'] ] = data[0]['value'];
	json[ data[len-1]['name'] ] = data[len-1]['value'];
	let areas = [];
  for (let i = 1; i < len - 1; i++) {
		console.log(data[i]['name']);
		if (data[i+1]['name'] === 'role') {
			areas.push([data[i]['value'], 1]);
			i += 1;
		} else {
			areas.push([data[i]['value'], 0]);
		}
  }
	json['areas[]'] = areas;
	console.log(json);
  return json;
}
