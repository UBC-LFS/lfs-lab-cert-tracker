$(document).ready(function() {
    // quickAddCerts()

    addAreaCheckboxListeners();
});

function addAreaCheckboxListeners() {
    // $(".areas-form").on('click', '.submit-btn', showCarryOver);
    $(".areas-form").on('change', '.add-area-checkbox', function (e) {
        console.log("Fired")
        const $addAreaCheckbox = $(e.currentTarget)
        syncLinkAreaCheckbox($addAreaCheckbox)
    });
}

function syncLinkAreaCheckbox($addAreaCheckbox) {
    const areaID = $addAreaCheckbox.val()
    const $linkAreaCheckbox = $(`#link-area-${areaID}`)
    if ($addAreaCheckbox.is(':checked')) {
        $linkAreaCheckbox.prop('disabled', false)
    } else {
        $linkAreaCheckbox.prop('checked', false)
        $linkAreaCheckbox.prop('disabled', true)
    }
}

function quickAddCerts() {
    $(".areas-form").on('click', '.submit-btn', showCarryOver);
}

function showCarryOver(e) {
    e.preventDefault();
    const $form = $(".areas-form");
    const $submitBtn = $(e.currentTarget);
    const $modal = $('#add-area-certs-modal');

    let areaNames = '';

    $('[name="areas[]"]').each(function(index, checkbox) {

        if ($(this).is(':checked')) {

            const areaName = $(this).closest('tr').find('td.area-name').text().trim();

            areaNames += `<li>${areaName}</li>`;
        }
    });
    $('#selected-area-names').html(areaNames)

    const handleClick = (e) => {
        const $btn = $(e.currentTarget);
        const type = $btn.data('type');

        if (type === 'cancel') {
            $modal.modal('hide');
        } else if (type === 'autoAdd') {
            $form.append(`<input type="hidden" name="add_lab_certs" value="True">`);
            $(".areas-form").off('click', '.submit-btn', showCarryOver);
            $submitBtn.click();
        } else if (type === 'continue') {
            $(".areas-form").off('click', '.submit-btn', showCarryOver);
            $submitBtn.click();
        }
    };

    const handleDismiss = () => {
        $modal.off('click', 'button', handleClick);
        $modal.off('hidden.bs.modal', handleDismiss);
    };

    $modal.modal('show');
    $modal.on('click', 'button', handleClick);
    $modal.on('hidden.bs.modal', handleDismiss);
}