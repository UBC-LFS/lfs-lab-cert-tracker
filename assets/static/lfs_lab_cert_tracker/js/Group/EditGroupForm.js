import GroupForm from "./GroupForm.js";

class EditGroupForm extends GroupForm {

    constructor() {
        super()
        // Group ID
        this.group_id = $('#group_id').val()

    }

    initializeMap() {
        const $groupJSONContent = $('#group_members_json')

        const groupMap = new Map()

        if ($groupJSONContent.length === 0) {
            return groupMap
        }

        const groupMembers = JSON.parse($groupJSONContent.text())

        for (const member of groupMembers) {
            this.addMemberToMap(groupMap, member.id, member.first_name, member.last_name, member.is_coordinator)
        }

        return groupMap
    }

    // Edit form only cares about checking for invalid name;
    async validateFormContent(url) {
        let issue_warning = false
        await $.ajax({
            method: 'GET',
            url: url,
            data: {
                'name': this.$group_name.val(),
                'group_id': this.group_id
            },
            success: (res) => {
                if (res.has_duplicate) {
                    issue_warning = true

                    if (res.match_type === 'name') {
                        this.issueNameWarning(res.data)
                    }

                }
            },

        })
        return issue_warning
    }
}

$(document).ready(function() {
    new EditGroupForm()
});
