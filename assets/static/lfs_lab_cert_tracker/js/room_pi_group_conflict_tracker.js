
$(document).ready(function() {
    // Load existing data if there is some
    const user_rows = $('.added-user')

    const user_tracker = new Map()



    user_rows.each(function(index, element) {
        const $row = $(element);

        const $userTd = $row.find('td.user')

        const name = $userTd.text()

        const $entitySpans = $row.find('span.badge')

        const user_id = String($userTd.data('userId'))

        const entities = new Set()

        $entitySpans.each(function(i, span) {
            entities.add($(span).text())
        });

        user_tracker.set(user_id, {
            'entities': entities,
            'name': name
        })
    })

    $('#pis-table-0').on('change', 'input.add-approver-checkbox', function() {
        const $row = $(this).closest('tr');
        const entity = "PI"
        const name = $row.find('td.userName').text()
        const userID = String($row.find('td.userID').text())
        const isChecked = $(this).is(':checked');

        processUser(user_tracker, userID, isChecked, entity, name)

        displaySelectedUsers(user_tracker)


    });

    $('#groups-table-0').on('change', 'input.add-approver-checkbox', function() {
        const $row = $(this).closest('tr');
        const entity = $row.find('td.group-name').text()
        const groupList = $row.find('td.group_members').find('li')

        const isChecked = $(this).is(':checked');

        groupList.each(function(i, li) {
            const $li = $(li)
            const user_id = String($li.data('userId'))
            const name = $li.text()

            processUser(user_tracker, user_id, isChecked, entity, name)
        });

        displaySelectedUsers(user_tracker)


    });

});

function getSingleEntityRow(user_id, name, entity) {
    return `<tr id="added-user-${user_id}" class="added-user">
            <td class="user" data-user-id="${user_id}">${name}</td>
            <td class="entity">
                <div class="text-success">
                    <span class="material-symbols-outlined align-middle" style="font-size: 1rem;">check_circle</span>
                    <strong>No conflict</strong>
                </div>
                <div>
                    <span data-entity="${entity}" class="badge badge-light border mr-1 mb-1">${entity}</span>
                </div>
            </td>
        </tr>
    `
}

function getMultiEntityRow(user_id, name, entity_list) {

    const entity_badges = entity_list.map(entity => {
        return `<span class="badge badge-light border mr-1 mb-1">${entity}</span>`;
    }).join('');

    return `<tr id="added-user-${user_id}" class="added-user">
            <td class="user" data-user-id="${user_id}">${name}</td>
            <td class="entity">
                <div class="text-danger mb-1">
                    <span class="material-symbols-outlined align-middle" style="font-size: 1rem;">close</span>
                    <strong>Conflict</strong>
                </div>
                <div>
                    ${entity_badges}
                </div>
            </td>
        </tr>
    `
}

function displaySelectedUsers(user_tracker) {
    const $conflict_table =  $('#display-selected-users')

    if (user_tracker.size === 0) {
        $conflict_table.html(`
        <tr>
            <td colspan="100%">Your selected users will be displayed here.</td>
        </tr>`)
        return
    }

    const sortedMap = new Map(
        [...user_tracker.entries()].sort((a, b) => a[1].name.localeCompare(b[1].name))
    );

    let html_content = ''
    sortedMap.forEach((user, user_id) => {
        if (user.entities.size === 1) {
            html_content += getSingleEntityRow(user_id, user.name, [...user.entities][0])
        } else {
            html_content += getMultiEntityRow(user_id, user.name, [...user.entities])
        }
    })

    $conflict_table.html(html_content)
}

function processUser(user_tracker, user_id, isChecked, entity, name) {
    if (user_tracker.has(user_id)) {
        let user = user_tracker.get(user_id)
        if (isChecked) {
            user.entities.add(entity)
        } else {
            user.entities.delete(entity)
            if (user.entities.size === 0) {
                user_tracker.delete(user_id)
            }
        }
    } else if (isChecked) {
        user_tracker.set(user_id, {
            'entities': new Set([entity]),
            'name': name
        })
    }
}