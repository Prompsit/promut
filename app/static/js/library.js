$(document).ready(function () {
    /* We hide certain columns if Datatables Responsive hid them */
    let hide_col = (col) => {
        if (col) $(col).addClass("d-none");
    }

    $.ajax({
        url: `/library/ping`,
        method: 'GET',
        contentType: false,
        cache: false,
        processData: false,
        success: function (response) {
            if (!response.is_up) {
                $(".opus-unavailable-models").removeClass("d-none");
                $(".opus-model-search-header").addClass("alert alert-secondary not-allowed");
                //  $(".opus-unavailable-datasets").removeClass("d-none");
                // $(".opus-search-header").addClass("alert alert-secondary not-allowed");
            }
        },
        error: function (xhr, status, error) {
            console.error("Error checking OPUS web", error)

        }
    });

    let hide_responsive = (columns) => {
        // Sometimes datatables returns "-" instead of a boolean, in that case
        // we return, since we don't know if it means that the column
        // is hidden or not
        for (let i = 0; i < columns.length; i++) if (columns[i] == "-") return;

        $(".corpus-header th").removeClass("d-none");
        $(".corpus-files-header th").removeClass("d-none");
        for (let i = 0; i < columns.length; i++) {
            if (!columns[i]) {
                $(".corpus-header").each(function () { hide_col($(this).find("th").eq(i)) })
                $(".corpus-files-header").each(function () { hide_col($(this).find("th").eq(i)) })
            }
        }
    }



    $('.corpora-table').each(function (i, el) {
        let public_mode = ($(el).attr("data-public") == "true");
        let used_mode = $(el).attr("data-used") == "true";
        let not_used_mode = $(el).attr("data-not-used") == "true";

        let corpora_table = $(el).DataTable({
            processing: true,
            serverSide: true,
            responsive: true,
            ajax: {
                url: "corpora_feed",
                method: "post",
                data: { public: public_mode, used: used_mode, not_used: not_used_mode }
            },
            drawCallback: function (settings) {
                let api = this.api()
                let rows = api.rows({ page: 'current' }).nodes();
                let row_data = api.rows({ page: 'current' }).data()
                let last_group = -1;
                rows.each(function (row, i) {
                    let data = row_data[i];
                    let corpus_data = data[7];

                    if (corpus_data.corpus_id != last_group) {
                        let template = document.importNode(document.querySelector("#corpus-header-template").content, true);
                        $(template).find(".corpus_name").html(corpus_data.corpus_name);
                        $(template).find(".corpus_name").attr("title", $(template).find(".corpus_name").attr("title") + " " + corpus_data.corpus_uploader);

                        if (corpus_data.corpus_description != "") {
                            $(template).find(".corpus_description").html(corpus_data.corpus_description);
                        } else {
                            $(template).find(".corpus-description-row").addClass("d-none");
                        }

                        $(template).find(".corpus_lang_src").html(corpus_data.corpus_source);
                        $(template).find(".corpus_lang_trg").html(corpus_data.corpus_target);

                        if (corpus_data.corpus_owner) {
                            if (corpus_data.corpus_public) {
                                $(template).find(".folder-shared").removeClass("d-none");
                            } else {
                                $(template).find(".folder-owner").removeClass("d-none");
                            }
                        } else {
                            $(template).find(".folder-grabbed").removeClass("d-none");
                        }

                        $(template).find(".export-btn").attr("href", corpus_data.corpus_export);
                        $(template).find(".corpus-preview").attr("href", corpus_data.corpus_preview);

                        if (public_mode) {
                            $(template).find(".grab-btn").attr("href", corpus_data.corpus_grab);
                            $(template).find(".grab-btn").removeClass("d-none");

                            if (corpus_data.opus_corpus && corpus_data.user_is_admin) {
                                $(template).find(".corpus-delete").attr("href", corpus_data.corpus_delete);
                                $(template).find(".corpus-delete").removeClass("d-none");
                            }
                        } else {
                            if (corpus_data.corpus_owner) {
                                if (corpus_data.corpus_public) {
                                    $(template).find(".corpus-stop-share").attr("href", corpus_data.corpus_share);
                                    $(template).find(".corpus-stop-share").removeClass("d-none");
                                } else {
                                    $(template).find(".corpus-share").attr("href", corpus_data.corpus_share);
                                    $(template).find(".corpus-share").removeClass("d-none");
                                }

                                $(template).find(".corpus-delete").attr("href", corpus_data.corpus_delete);
                                $(template).find(".corpus-delete").removeClass("d-none");
                            } else {
                                $(template).find(".corpus-ungrab").attr("href", corpus_data.corpus_ungrab);
                                $(template).find(".corpus-ungrab").removeClass("d-none");
                            }
                        }

                        $(row).before(template);
                        $('[data-toggle="tooltip"]').tooltip();

                        last_group = corpus_data.corpus_id;
                    }
                });
            },
            columnDefs: [
                {
                    targets: [0, 1, 2, 3, 4, 5, 6],
                    responsivePriority: 1
                },
                {
                    targets: 0,
                    responsivePriority: 1,
                    className: "border-right-0 align-middle text-center",
                    render: function (data, type, row) {
                        let corpus_data = row[7];
                        let template = document.importNode(document.querySelector("#preview-button-template").content, true);
                        $(template).find(".file-item-preview").attr("href", corpus_data.file_preview);
                        let ghost = document.createElement('div');
                        $(ghost).append(template);
                        return ghost.innerHTML;
                    }
                },
                {
                    targets: 1,
                    responsivePriority: 1,
                    className: "overflow",
                    render: function (data, type, row) {
                        let template = document.importNode(document.querySelector("#corpus-entry-template").content, true);
                        $(template).find(".file-name").html(data);

                        let ghost = document.createElement('div');
                        $(ghost).append(template);
                        return ghost.innerHTML;
                    }
                },
                {
                    targets: 6,
                    render: function (data, type, row) {
                        return (data != "") ? data : "—";
                    }
                }
            ]
        });

        corpora_table.on('responsive-resize', function (e, datatable, columns) {
            hide_responsive(columns);
        });

        corpora_table.on('draw', function () {
            hide_responsive(corpora_table.columns().responsiveHidden());
        });
    });

    $(".engines-table").each(function (i, el) {
        let public_mode = ($(el).attr("data-public") == "true");
        $(el).DataTable({
            processing: true,
            serverSide: true,
            responsive: true,
            ajax: {
                url: "engines_feed",
                method: "post",
                data: { public: public_mode },
            },
            columnDefs: [
                {
                    targets: 0,
                    responsivePriority: 1,
                    searchable: false,
                    sortable: false,
                    class: "text-center border-right-0",
                    render: function (data, type, row) {
                        let engine_data = row[8];
                        let template = document.importNode(document.querySelector("#engines-icon-template").content, true);

                        if (engine_data.opus_engine) {
                            $(template).find(".opus-engine").removeClass("d-none");
                        }

                        if (isAdmin === "True") {
                            $(template).find(".multiselect-checkbox").removeClass("d-none");
                        }
                        if (engine_data.engine_owner) {
                            $(template).find(".multiselect-checkbox").removeClass("d-none");
                        }

                        if (engine_data.engine_owner) {
                            if (engine_data.engine_public) {
                                $(template).find(".folder-shared").removeClass("d-none");
                            } else {
                                $(template).find(".folder-owner").removeClass("d-none");
                            }
                        } else {
                            $(template).find(".folder-grabbed").removeClass("d-none");
                        }


                        let ghost = document.createElement('div.actions-container');
                        $(ghost).append(template);

                        return ghost.innerHTML;
                    }
                },
                {
                    targets: [1, 2, 3, 4, 5, 6],
                    className: "overflow"
                },
                {
                    targets: 6,
                    render: function (data, type, row) {
                        const test_score = row[8].engine_test_score;
                        const id = row[8].engine_delete.replace("/library/delete/library_engines/", "");

                        return !row[8].opus_engine ? `<div class="bleu-container" id=${id}><div class="val-bleu">${data ? data.toFixed(2) : -1}<span>VAL.</span></div> <p class="separator">|</p> <div class="test-bleu">${test_score}<span>TEST</span></div></div>` : `<div class="bleu-container" id=${id}>${test_score !== -1 && test_score !== undefined ? `<div class="test-bleu">${test_score}<span>TEST</span></div>` : ""}</div>`
                    }
                },
                {
                    targets: 7,
                    responsivePriority: 1,
                    className: "actions",
                    searchable: false,
                    sortable: false,
                    render: function (data, type, row) {
                        let engine_data = row[8];
                        let template = document.importNode(document.querySelector("#engines-options-template").content, true);

                        $(template).find(".export-btn").attr("href", engine_data.engine_export);
                        $(template).find(".export-corpora-btn").attr("href", engine_data.engine_corpora_export);

                        $(template).find(".summary-btn").attr("href", engine_data.engine_summary);
                        $(template).find(".summary-btn").removeClass("d-none");


                        if (engine_data.engine_status === "opus") {
                            $(template).find(".export-btn").addClass("d-none");
                            $(template).find(".export-corpora-btn").addClass("d-none");
                            $(template).find(".summary-btn").addClass("d-none");
                        }

                        if (public_mode) {
                            if (engine_data.engine_status === "opus" && engine_data.user_is_admin) {
                                $(template).find(".delete-btn").attr("href", engine_data.engine_delete);
                                $(template).find(".delete-btn").removeClass("d-none");
                            }
                            $(template).find(".grab-btn").attr("href", engine_data.engine_grab);
                            $(template).find(".grab-btn").removeClass("d-none");
                        } else {
                            if (engine_data.engine_owner) {
                                if (engine_data.engine_public) {
                                    $(template).find(".stop-sharing-btn").attr("href", engine_data.engine_share);
                                    $(template).find(".stop-sharing-btn").removeClass("d-none");
                                } else {
                                    $(template).find(".share-btn").attr("href", engine_data.engine_share);
                                    $(template).find(".share-btn").removeClass("d-none");
                                }

                                $(template).find(".delete-btn").attr("href", engine_data.engine_delete);
                                $(template).find(".delete-btn").removeClass("d-none");
                            } else {
                                $(template).find(".remove-btn").attr("href", engine_data.engine_ungrab);
                                $(template).find(".remove-btn").removeClass("d-none");
                            }
                        }

                        let ghost = document.createElement('div');
                        ghost.appendChild(template);
                        return ghost.innerHTML;
                    }
                }
            ]
        });
    });

    let engines_table = $('.engines-table');

    $("#multiple-users-btn-engines").on('click', function () {
        $('.multiple-user-actions-engines').toggle('d-none');
    })

    engines_table.on('click', 'tbody tr td:first-child .multiselect-checkbox', function (e) {
        const row = e.currentTarget.closest("tr");

        const rows = $(engines_table).find('tr.selected');

        row.classList.toggle('selected');
        if (rows.length > 0) {
            $("#multiple-users-btn-engines").removeClass('d-none');
        } else {
            $("#multiple-users-btn-engines").addClass('d-none');
        }
    });


    async function processUsers(users, action) {
        var notyf = new Notyf();

        const notifications = { delete: "Deletion successful" }

        const errors = { delete: "Error while deleting." }

        try {
            for (const user of users) {
                let formData = new FormData();
                formData.append("id", user)
                formData.append("type", action);

                $.ajax({
                    url: `/library/delete-user`,
                    method: 'POST',
                    data: formData,
                    contentType: false,
                    cache: false,
                    processData: false,
                    success: function (response) {
                        window.location.reload(true);
                        return;
                    },
                    error: function (xhr, status, error) {
                        console.error("Error deleting user", user)

                    }
                });
            }
            notyf.success({ message: notifications[`${action}`], duration: 3500, position: { x: "middle", y: "top" } });

        } catch (error) {
            notyf.error({ message: errors[`${action}`], duration: 3500, position: { x: "middle", y: "top" } });
            console.error('Deletion failed:', error);
            console.error('Failed to process users:', error);
        }


    }

    $('.multiple-user-actions-engines').on('click', 'button', async function () {
        const selectedUsers = [...$('tr.selected .bleu-container')].map(el => el.id);

        $('.multiple-user-actions').toggle("d-none");
        await processUsers(selectedUsers, "delete");
    });




















    ///////////////////////////////////
    ///////////////////////////////////
    ///////////////////////////////////


    $(".details-table").DataTable({
        dom: "t",
        paging: false,
        columnDefs: [{
            targets: 4,
            sortable: false
        }]
    });

    setTimeout(function () {
        $('[href="#private-corpora"]').trigger('click');
        $('[href="#private-engines"]').trigger('click');
    }, 10);

    $('.upload-header').on('click', function (e) {
        e.preventDefault();
        $('.data-upload-form').toggleClass('collapsed');
        $('.header-collapse-icon').toggleClass('d-none');
        $('.header-collapsed-icon').toggleClass('d-none');
    })
    $('.opus-search-header').on('click', function (e) {
        e.preventDefault();
        $('.search-opus-corpora-container').toggleClass('collapsed');
        $('.header-collapse-icon-opus').toggleClass('d-none');
        $('.header-collapsed-icon-opus').toggleClass('d-none');
    })
    $('.opus-model-search-header').on('click', function (e) {
        e.preventDefault();
        $('.search-opus-models-container').toggleClass('collapsed');
        $('.header-collapse-icon-opus').toggleClass('d-none');
        $('.header-collapsed-icon-opus').toggleClass('d-none');
    })
    $('.datasets-header').on('click', function (e) {
        e.preventDefault();
        $('.corpora-nav-tabs-container').toggleClass('collapsed');
        $('.header-collapse-icon-datasets').toggleClass('d-none');
        $('.header-collapsed-icon-datasets').toggleClass('d-none');
    })
});
