
$(document).ready(function() {
    $('[data-toggle="tooltip"]').tooltip()

    const $userTable = $('#area-users-table')

    $userTable.on('post-body.bs.table', function() {
        $('[data-toggle="tooltip"]', this).tooltip();
    });

    $userTable.on('change', '.role-selector', function() {

        const $select = $(this)

        const selected_role = Number($select.val())
        const user_role = Number($select.data('roleId'))

        const user_id = $select.data('userId')

        const $btn = $(`#btn-${user_id}`)

        if ($btn.length === 0) {
            return
        }

        const isOriginalRole = selected_role === user_role

        $btn.prop('disabled', isOriginalRole)

        $btn.tooltip(
            isOriginalRole ? "enable" : "disable"
        )

    })
})
