$('.edit-btn').on('click', function() {
    const url = $(this).data('url');
    const pk = $(this).data('pk');
    $.get(url, function(html) {
        $('#edit-user-id').val(pk)
        $('#user-edit-modal-body').html(html);
        $('#user-edit-modal').modal('show');
    });
});