import AlertManager from "../utils/AlertManager.js";

// Abstract class for Create/Edit Forms
export default class GroupForm {

    constructor() {

        // DOM Elements
        this.$form = $('#room-group-form')
        this.$group_name = $('#id_name')
        this.$member_ids_input = $('#id_member_ids')
        this.$coordinator_ids_input = $('#id_coordinator_ids')
        this.$name_search = $('#id_user_name_search')
        this.$search_results_table = $('#select-user')
        this.$display_selected_users_table = $('#display-selected-users')

        // Default message elements
        this.default_table_row = `<tr></tr><td colSpan="100%">Type either a first or last name to find users</td></tr>`
        this.no_matching_results_row = `<tr></tr><td colSpan="100%">No matches</td></tr>`
        this.empty_selected_users_msg =`<tr></tr><td colSpan="100%">Your selected users will be displayed here.</td></tr>`

        // User tracking list
        this.selected_members = this.initializeMap()

        this.$validate_form_input = $('#validate_group_url')

        this.addListeners();
    }

    initializeMap() {
        return new Map()
    }

    addListeners() {
        this.$name_search.on('input', () => {
            this.onType();
        });
        this.addCheckBoxListeners()
        this.addRemoveUserListeners()

        this.addSubmitAnywaysListener()
        this.addSubmitListener()
    }

    addSubmitListener() {
        this.$form.on('submit', (e) => {
            e.preventDefault();

            if (this.selected_members.size === 0) {
                const alertContainer = document.getElementById("group-message")
                AlertManager.stopEvent("Please add at least one user to the room group before submitting.", e, this.$name_search, alertContainer)
                return
            }

            const url = this.$validate_form_input.val();
            this.validateFormContent(url).then((issuedWarning) => {
                if (!issuedWarning) {
                    this.prepareAndSubmitForm();
                }
            })

        })
    }

    prepareAndSubmitForm() {
        const member_ids = [...this.selected_members.keys()]

        const coordinator_ids = []
        for (const [id, user] of this.selected_members) {
            if (user.is_coordinator) {
                coordinator_ids.push(id)
            }
        }

        this.$member_ids_input.val(member_ids.join(','));
        this.$coordinator_ids_input.val(coordinator_ids.join(','));


        // need to remove the old submit listener (validation check)
        this.$form.off('submit')
        this.$form.submit()
    }

    addSubmitAnywaysListener() {
        $('#submit-anyways-btn').on('click', () => {
            this.prepareAndSubmitForm()
        })
    }

    // Abstract class must be implemented by child classes
    async validateFormContent(url) {
        throw Error("Subclass must implement this method")
    }

    issueNameWarning(data) {
        const alertContainer = document.getElementById("group-message")
        AlertManager.showAlert(
            `A room group with this name already exists. <br>
             Name: <a href="${data.view_url}" target="_blank">${this.$group_name.val()}</a>, Members: ${data.group_members_string}
            `, alertContainer
        )
    }

    addCheckBoxListeners() {
        this.$search_results_table.on('change', '.add-user', (e) => {
            const $checkBox = $(e.currentTarget);
            const id = $checkBox.data('id');

            if ($checkBox.is(':checked')) {
                this.addMemberToMap(this.selected_members, id, $checkBox.data('firstname'), $checkBox.data('lastname')
                );
            } else {
                this.removeUserFromMap(id)
            }

            this.refreshUserList();
        });

        this.$display_selected_users_table.on('change', '.set-coordinator', (e) => {
            const $checkBox = $(e.currentTarget);
            const id = $checkBox.data('id');
            this.changeCoordinatorFlag(this.selected_members, id, $checkBox.is(':checked'))

            this.refreshUserList();
        });
    }

    addRemoveUserListeners() {
        this.$display_selected_users_table.on('click', '.remove-btn', (e) => {
            const $btn = $(e.currentTarget);
            const id = $btn.data('id')
            this.removeUserFromMap(id)

            this.refreshUserList();

            const checkbox = $(`#add-user-${id}`)

            if (checkbox.length > 0) {
                checkbox.prop('checked', false);
            }

        })
    }

    onType() {
        const url = this.$name_search.data('url');
        const name_q = this.$name_search.val().toLowerCase();

        if (name_q === '') {
            this.$search_results_table.html(this.default_table_row)
            return
        }

        $.ajax({
            method: 'GET',
            url: url,
            data: {
                'name_q': name_q,
            },
            success: (res) => {
                this.onSuccess(res.data)
            },

        })
    }

    onSuccess(users) {
        if (users.length === 0) {
            this.$search_results_table.html(this.no_matching_results_row)
            return
        }

        let content = ''
        for (const user of users) {

            const id = user.id

            let checked = ""

            if (this.selected_members.has(id)) {
                checked = "checked"
            }

            content += `
                    <tr>
                        <td> ${user.first_name} </td>
                        <td> ${user.last_name} </td>
                        <td class="p-0 text-center align-middle" style="height: 50px;">
                            <div class="d-flex justify-content-center align-items-center w-100 h-100" style="min-height: 45px;">
                                <input class="form-check-input form-check-input-lg add-user" 
                                       type="checkbox" 
                                       id="add-user-${user.id}" 
                                       ${checked}
                                       data-id="${user.id}" 
                                       data-firstname="${user.first_name}" 
                                       data-lastname="${user.last_name}">
                           </div>
                        </td>
                    </tr>
            
            `
        }
        this.$search_results_table.html(content);
    }

    refreshUserList() {

        if (this.selected_members.size === 0) {
            this.$display_selected_users_table.html(this.empty_selected_users_msg)
            return
        }

        let userArray = Array.from(this.selected_members)
        // If there is a coordinator, make this appear first; only 1 [for now]
        userArray.sort((a, b) => {
            return (b[1].is_coordinator - a[1].is_coordinator) ||
                a[1].first_name.localeCompare(b[1].first_name) ||
                a[1].last_name.localeCompare(b[1].last_name)
        })

        let htmlBuffer = userArray.map(([id, user]) => {
            let checked = ""

            if (user.is_coordinator) {
                checked = "checked"
            }
            return `<tr>
                        <td data-id="${id}">${user.first_name} ${user.last_name}</td>
                        <td class="p-0 text-center align-middle" style="height: 50px;">
                            <div class="d-flex justify-content-center align-items-center w-100 h-100" style="min-height: 45px;">
                                <input class="form-check-input form-check-input-lg set-coordinator" 
                                       type="checkbox" 
                                       id="set-user-${id}" 
                                       ${checked}
                                       data-id="${id}">
                           </div>
                        </td>
                        <td><button class="btn btn-danger btn-sm remove-btn" data-id="${id}">Remove</button></td>
                    </tr>`;
        });

        this.$display_selected_users_table.html(`${htmlBuffer.join('')}`)

    }

    addMemberToMap(map, id, first_name, last_name, is_coordinator=false) {
        if (typeof id === "string") {
            id = parseInt(id)
        }

        if (Number.isNaN(id)) {
            // fails silently
            return
        }

        map.set(
            id,
            {
                "first_name": first_name,
                "last_name": last_name,
                "is_coordinator": is_coordinator
            }
        )
    }

    removeUserFromMap(user_id) {
        this.selected_members.delete(user_id)
    }

    changeCoordinatorFlag(map, new_coordinator_id, flag) {
        const member = this.selected_members.get(new_coordinator_id)
        if (member) {
            member.is_coordinator = flag
        }
    }
}
