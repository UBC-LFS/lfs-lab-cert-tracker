$(document).ready(function() {
  $('#welcome-modal').modal('show');

  $('#close-welcome-modal').on('click', function() {
    $('#welcome-modal').modal('hide');

    $.ajax({
      method: 'POST',
      url: $(this).data('url'),
      data: {
        read_welcome_message: true,
        csrfmiddlewaretoken: $(this).data('token')
      },
      dataType: 'json',
      success: function(res) {
        let message = '<div class="alert alert-success alert-dismissible fade show" role="alert">' +
            res.message +
            '<button type="button" class="close" data-dismiss="alert" aria-label="Close"><span aria-hidden="true">&times;</span></button>' +
          '</div>';

        $('#welcome-message-alert').html(message);
      },
      error: function(err) {
        const message = '<div class="alert alert-danger alert-dismissible fade show" role="alert">' +
                          'Error: ' + err.statusText + ' (' + err.status + '). ' +
                          '<button type="button" class="close" data-dismiss="alert" aria-label="Close"><span aria-hidden="true">&times;</span></button>' +
                        '</div>';
        $('#welcome-message-alert').html(message);
      }
    });
  });
});
