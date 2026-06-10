export default class TableModal {

    constructor(config) {
        this.config = config;

        this.$button = $(config.buttonSelector);
        this.$modal = $(config.modalSelector);

        this.$tableBody = $(config.tableBodySelector);

        this.$pagination = $(config.paginationSelector);
        this.$summary = $(config.summarySelector);

        this.$totalCount = $(config.totalCountSelector);
        this.columns = config.columns

        this.page_arg = 'page'
        if (this.config.initPageArg) {
            this.config.initPageArg()
        }

        this.currentUrl = null;

        this.addEventListeners();


    }

    addEventListeners() {
        this.$button.on('click', (e) => {

            this.currentUrl = $(e.currentTarget).data(this.config.url);
            this.loadPage(1);
        });

        this.$modal
            .on('shown.bs.modal', () => this.addNewTooltips())
            .on('hide.bs.modal', () => {
                document.activeElement.blur()
            })
            .on('hidden.bs.modal', () => {
                if (this.config.resetModal) {
                    this.config.resetModal()
                }
            })

    }
    loadPage(page = 1) {

        const url = `${this.currentUrl}?${this.page_arg}=${page}`

        $.ajax({
            url: url,
            method: 'GET',
            success: (res) => {
                if (res.status === 'success') {

                    for (const data of res.data) {
                        if (this.config.getSelectorsFromRenderKey) {

                            const valMap = this.config.getSelectorsFromRenderKey(data.key)
                            this.setGlobalVarsFromValMap(valMap)
                        }
                        this.render(data)

                    }
                    this.$modal.modal('show');
                    this.addNewTooltips();

                }
            }
        });
    }

    setGlobalVarsFromValMap(valMap) {
        if (valMap.$tableBody) {
            this.$tableBody = $(valMap.$tableBody)
        }
        if (valMap.$summary) {
            this.$summary = $(valMap.$summary)
        }
        if (valMap.$pagination) {
            this.$pagination = $(valMap.$pagination)
        }
        if (valMap.page_arg) {
            this.page_arg = valMap.page_arg
        }
        if (valMap.columns) {
            this.columns = valMap.columns
        }
    }

    render(data) {
        this.renderTable(data.data);

        this.renderPagination(data.num_pages, data.current_page, data.key);

    }


    renderTable(data) {
        this.$tableBody.html("");

        for (const item of data) {

            const row = this.$tableBody[0].insertRow(-1);

            for (const column of this.columns) {
                if (column.renderCell) {
                    column.renderCell(row, item, this);
                } else {
                    this.insertCell(
                        row,
                        column.index,
                        column.getValue(item),
                        column.width
                    );
                }
            }

            if (this.config.afterCreateRow) {
                this.config.afterCreateRow(row, item);
            }
        }

        if (data.length === 0) {
            const row = this.$tableBody[0].insertRow(-1);
            const emptyCell = document.createElement('td');
            emptyCell.colSpan = '100'
            emptyCell.textContent = "No training"
            row.appendChild(emptyCell)

        }
    }

    insertCell(row, index, text, width = 200) {
        const newCell = this.createCell(row, index);

        if (text) {
            const div = document.createElement('div');
            div.className = 'text-center mx-auto new-tooltip';
            div.title = text;
            // div.style.maxWidth = `${width}px`;
            div.style.display = 'block';
            div.setAttribute('data-bs-toggle', 'tooltip');
            div.textContent = text;
            newCell.appendChild(div);
        }
    }

    createCell(row, index) {
        const newCell = row.insertCell(index);
        newCell.style.verticalAlign = "middle";
        return newCell;
    }

    renderPagination(numPages, currentPage, page_key) {
        this.$summary.text(`Page ${currentPage} of ${numPages}`);

        this.$pagination.empty();

        if (numPages <= 1) return;

        const $nav = $('<ul class="pagination"></ul>');

        const prevPage = currentPage - 1;
        const nextPage = currentPage + 1;

        const noPrevPage = prevPage <= 0 ? 'disabled' : '';
        const noNextPage = nextPage > numPages ? 'disabled' : '';

        $nav.append(this.createPageItem(noPrevPage, 'First', 1, page_key));
        $nav.append(this.createPageItem(noPrevPage, "❮", prevPage, page_key));
        $nav.append(`<li class="page-item active"><span class="page-link">${currentPage}</span></li>`);
        $nav.append(this.createPageItem(noNextPage, "❯", nextPage, page_key));
        $nav.append(this.createPageItem(noNextPage, 'Last', numPages, page_key));

        this.$pagination.append($nav);
    }

    createPageItem(disabled, icon, page, page_key) {
        const $item = $(`
            <li class="page-item ${disabled}">
                <span class="page-link">${icon}</span>
            </li>
        `);

        if (!disabled) {

            const link = $item.find('.page-link');
            link.on('click', () => {
                this.page_arg = page_key === 'room' ? 'room_page' : 'area_page'
                this.loadPage(page)
            });
            link.css({ cursor: "pointer" });
        }

        return $item;
    }

    addNewTooltips() {
        for (const element of document.querySelectorAll('.new-tooltip')) {
            if (element.offsetWidth < element.scrollWidth) {
                new bootstrap.Tooltip(element);
                element.addEventListener("mouseenter", function () {
                    this.style.cursor = "pointer";
                });
            }
        }
    }



}

