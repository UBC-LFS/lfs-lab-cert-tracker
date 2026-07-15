$(document).ready(function() {

    const $deleteGroupModal = $('#room-groups-delete-modal');

    $('.delete-group-btn').on('click', function() {
        showModal($deleteGroupModal, $(this))
    })
});

function showModal($modal, $btn) {
    const data = $btn.data();
    const id = data.id;
    const name = data.name;
    const groupMembersString = data.groupMembers;

    $modal.find('#delete-group-id').text(id);
    $modal.find('#delete-group-name').text(name);
    $modal.find('#group-members-string').text(groupMembersString);

    $modal.find('input[name="group"]').val(id);

}