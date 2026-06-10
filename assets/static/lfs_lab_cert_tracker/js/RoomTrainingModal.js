import TableModal from "./utils/TableModal.js";

const userHistoryModal = new TableModal({
    buttonSelector: '.view-training-btn',
    modalSelector: '#training-modal',
    tableBodySelector: null,
    paginationSelector: '#pagination-room-training',
    summarySelector: '#training-summary',
    url: 'trainingUrl',

    initPageArg: () => {
        return 'room_page'
    },

    resetModal: () => {

        $('#nav-room-training-tab').trigger('click')


    },

    getSelectorsFromRenderKey: (renderKey) => {
        const valMap = {}
        if (renderKey === "room") {

            valMap.$tableBody = `#room-training-table`
            valMap.$summary = `#room-training-summary`
            valMap.$pagination = `#pagination-room-training`
            valMap.page_arg = "room_page"
            valMap.columns = [{
                index: 0,
                getValue: (entry) => entry.id,
            },
                {
                    index: 1,
                    getValue: (entry) => entry.name,
                },

            ]


        } else if (renderKey === "area") {
            valMap.$tableBody = `#area-training-table`
            valMap.$summary = `#area-training-summary`
            valMap.$pagination = `#pagination-area-training`
            valMap.page_arg = "area_page"
            valMap.columns = [
                {
                    index: 0,
                    getValue: (entry) => entry.id,
                },
                {
                    index: 1,
                    getValue: (entry) => entry.name,
                },
                {
                    index: 2,
                    getValue: (entry) => entry.area_name
                }

            ]

        }
        return valMap
    },

    columns: []
});



