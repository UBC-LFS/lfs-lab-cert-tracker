import GroupForm from "./GroupForm.js";

class CreateGroupForm extends GroupForm {

    constructor() {
        super()
    }

    initializeMap() {
        return new Map();
    }

    // Edit form only cares about checking for invalid name;
    async validateFormContent(url) {
        const ids_list = [...this.selected_members.keys()]
        let issue_warning = false
        await $.ajax({
            method: 'GET',
            url: url,
            data: {
                'name': this.$group_name.val(),
                'members[]': ids_list,
            },
            success: (res) => {
                if (res.has_duplicate) {
                    issue_warning = true

                    if (res.match_type === 'name') {
                        this.issueNameWarning(res.data)
                    } else if (res.match_type === 'composition') {
                        this.issueCompositionWarning(res.data)
                    }

                }
            },

        })
        return issue_warning
    }

    issueCompositionWarning(data) {
        const modalEl = document.getElementById('duplicate-group-modal')
        const list = modalEl.querySelector("ul")

        let items = ""
        for (const name of data.group_names) {
            items += `<li>${name}</li>`
        }

        let userArray = Array.from(this.selected_members)

        let member_names_array = userArray.map(([id, user]) => {
            return user.first_name + " " + user.last_name
        });

        const member_string = member_names_array.join(", ")

        $('#num-duplicates').text(data.num_matches)
        $('#group-member-names').text(member_string)
        $('#view_groups_link').attr('href', data.view_url)

        list.innerHTML = items

        const modal = new bootstrap.Modal(modalEl)
        modal.show()
    }
}

$(document).ready(function() {
    new CreateGroupForm()

});
