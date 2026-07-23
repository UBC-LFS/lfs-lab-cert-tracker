$(document).ready(function() {

    const $deactivateGroupModal = $('#room-groups-deactivate-modal');

    $('.deactivate-group-btn').on('click', function() {
        showModal($deactivateGroupModal, $(this), "deactivate")
    })

    const $activateGroupModal = $('#room-groups-activate-modal');

    $('.activate-group-btn').on('click', function() {
        showModal($activateGroupModal, $(this), "activate")
    })
});

function showModal($modal, $btn, action) {
    const data = $btn.data();
    const id = data.id;
    const name = data.name;
    const groupMembersString = data.groupMembers;

    $modal.find(`#${action}-group-id`).text(id);
    $modal.find(`#${action}-group-name`).text(name);
    $modal.find('#group-members-string').text(groupMembersString);

    $modal.find('input[name="group"]').val(id);

}