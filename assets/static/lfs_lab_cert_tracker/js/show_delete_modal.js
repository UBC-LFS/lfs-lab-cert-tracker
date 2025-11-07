$(document).ready(function() {

    const $deleteRoomModal = $('#rooms-model-delete-modal');

    $('.delete-room-btn').on('click', function() {
        showModal($deleteRoomModal, $(this))
    })
});

function showModal($modal, $btn) {
    const data = $btn.data();
    const id = data.id;
    const name = data.name;
    const numReqs = data.numReqs;

    if (parseInt(numReqs) === 0) {
        $modal.find(".alert-primary").removeClass('d-none');
        $modal.find('.alert-danger').addClass('d-none');
    } else {
        $modal.find('#delete-room-num-requests').text(numReqs);
        $modal.find(".alert-primary").addClass('d-none');
        $modal.find('.alert-danger').removeClass('d-none');
    }

    $modal.find('#delete-room-id').text(id);
    $modal.find('#delete-room-name').text(name);
    $modal.find('input[name="room"]').val(id);

}