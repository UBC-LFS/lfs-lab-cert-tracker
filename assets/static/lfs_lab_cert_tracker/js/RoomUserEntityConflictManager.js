import AlertManager from "./utils/AlertManager.js";

class RoomUserEntityConflictManager {

    constructor() {
        this.userTracker = new Map()
        this.checkForConflicts = this.checkForConflicts.bind(this)
        this.initPiForm();
        this.addListeners();

    }

    initPiForm() {
        $('#pis-table-0 tbody tr').each((index, row) => {
            const $row = $(row)
            const initChecked = $row.find('td input.init-checked').val()
            if (initChecked === "true") {
                const entity = "PI"
                const name = $row.find('td.userName').text()
                const userID = String($row.find('td.userID').text())
                this.processUser(userID, true, entity, name)

            }
        })
        $('#groups-table-0 tbody tr').each((index, row)=> {
            const $row = $(row)
            const initChecked = $row.find('td input.init-checked').val()
            if (initChecked === "true") {
                const entity = $row.find('td.group-name').text()
                const groupList = $row.find('td.group_members').find('li')
                this.editGroup(groupList, true, entity)
            }
        })

        this.displaySelectedUsers()
    }

    addListeners() {
        $(".pis-form").on('click', '.submit-btn', this.checkForConflicts)

        $('#pis-table-0').on('change', 'input.add-approver-checkbox', (e) => {
           this.processPIChanged($(e.currentTarget))
        });

        $('#groups-table-0').on('change', 'input.add-approver-checkbox', (e) => {
            this.processGroupChanged($(e.currentTarget))
        });

    }

    processGroupChanged($checkbox) {
        const $row = $checkbox.closest('tr');
        const entity = $row.find('td.group-name').text()
        const groupList = $row.find('td.group_members').find('li')

        const isChecked = $checkbox.is(':checked');

        this.editGroup(groupList, isChecked, entity)

        this.displaySelectedUsers()
    }

    editGroup(groupList, isChecked, entity) {
        groupList.each( (i, li) => {
            const $li = $(li)
            const user_id = String($li.data('userId'))
            const name = $li.text()

            this.processUser(user_id, isChecked, entity, name)
        });
    }

    processPIChanged($checkbox) {
        const $row = $checkbox.closest('tr');
        const entity = "PI"
        const name = $row.find('td.userName').text()
        const userID = String($row.find('td.userID').text())
        const isChecked = $checkbox.is(':checked');

        this.processUser(userID, isChecked, entity, name)

        this.displaySelectedUsers()
    }

    checkForConflicts(e) {
        e.preventDefault();

        const $submitBtn = $(e.currentTarget);

        const conflicts = []

        this.userTracker.forEach((entry) => {
            if (entry.entities.size > 1) {
                conflicts.push(`<li>${entry.name}: ${[...entry.entities].join(', ')}</li>`)
            }
        })

        const numConflicts = conflicts.length

        if (numConflicts > 0) {
            const allGroupsUrl = $('#all-approval-groups-link').val()
            const createGroupUrl = $('#create-new-approval-groups-link').val()

            let msg = "There "
            if (numConflicts === 1) {
                msg += "is 1 user "
            } else {
                msg += `are ${numConflicts} users `
            }

            msg +=  `with conflicts. Please review the following users:</p>
            <ul>
                ${conflicts.join('')}
            </ul>
            <p>Please go to the <a href="${allGroupsUrl}" target="_blank">All Approval Groups</a> page to modify the desired group, or go to the <a href="${createGroupUrl}" target="_blank">Create Approval Groups</a> page to create a new group.</p>
                `
            const alertContainer = document.getElementById("conflict-message")
            AlertManager.showAlert(msg, alertContainer)
        } else {
            $('.pis-form').off('click', '.submit-btn', this.checkForConflicts)
            $submitBtn.click()
        }
    }


    getSingleEntityRow(user_id, name, entity) {
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

    getMultiEntityRow(user_id, name, entity_list) {

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

    displaySelectedUsers() {
        const $conflict_table =  $('#display-selected-users')

        if (this.userTracker.size === 0) {
            $conflict_table.html(`
        <tr>
            <td colspan="100%">Your selected users will be displayed here.</td>
        </tr>`)
            return
        }

        const sortedMap = new Map(
            [...this.userTracker.entries()].sort((a, b) => a[1].name.localeCompare(b[1].name))
        );

        let html_content = ''
        sortedMap.forEach((user, user_id) => {
            if (user.entities.size === 1) {
                html_content += this.getSingleEntityRow(user_id, user.name, [...user.entities][0])
            } else {
                html_content += this.getMultiEntityRow(user_id, user.name, [...user.entities])
            }
        })

        $conflict_table.html(html_content)
    }

    processUser(user_id, isChecked, entity, name) {
        if (this.userTracker.has(user_id)) {
            let user = this.userTracker.get(user_id)
            if (isChecked) {
                user.entities.add(entity)
            } else {
                user.entities.delete(entity)
                if (user.entities.size === 0) {
                    this.userTracker.delete(user_id)
                }
            }
        } else if (isChecked) {
            this.userTracker.set(user_id, {
                'entities': new Set([entity]),
                'name': name
            })
        }
    }

}

$(document).ready(function() {
    // Load existing data if there is some

    new RoomUserEntityConflictManager();
});
