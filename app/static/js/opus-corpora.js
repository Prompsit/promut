$(document).ready(function () {

    $.ajax({
        url: '/data/get-session-data',
        method: 'GET',
        contentType: false,
        cache: false,
        processData: false,
        success: function (response) {
            if (response.pending_download) {
                const id = response.pending_download;
                const dataset = response.dataset;
                checkDownloadStatus(id, dataset);
            }
        },
        error: function (xhr, status, error) {
            console.error("Task id not saved")
        }
    });

    //const formData = new FormData();
    //formData.append("task_id", "");
    //formData.append("dataset", "");
    //$.ajax({
    //    url: '/data/set-session-data',
    //    method: 'POST',
    //    data: formData,
    //    contentType: false,
    //    cache: false,
    //    processData: false,
    //    success: function (response) {   
    //    },
    //    error: function (xhr, status, error) {
    //        console.error("Task id not saved")
    //    }
    //});

    let adjust_languages = (el) => {
        let other = $('.lang_sel_opus').not(el);
        let selected_lang = $(el).find('option:selected').val();
        $(other).find('option').prop('disabled', false)
        $(other).find(`option[value='${selected_lang}']`).prop('disabled', true);

        if ($(other).find('option:selected').val() == selected_lang) {
            $(other).find('option:selected').prop('selected', false);
        }
    }

    $('.source_lang_search').on('change', function () {
        adjust_languages(this);
    });

    adjust_languages($('.source_lang_search'));

    function checkDownloadStatus(id, dataset) {

        const formData = new FormData();
        formData.append("task_id", id)
        $.ajax({
            url: '/data/check-downloading',
            method: 'POST',
            data: formData,
            contentType: false,
            cache: false,
            processData: false,
            success: function (response) {

                if (response.finished) {
                    const formData = new FormData();
                    formData.append("task_id", "");
                    formData.append("dataset", "");


                    $('.selected-dataset-download').text('Download');
                    $('.selected-dataset-download').prop('disabled', false);
                    $('#download-info').addClass('d-none');
                    $('.download-btn').prop('disabled', false);
                    $(".already-in-library").prop('disabled', true);

                    console.log("Finished downloading")

                    $.ajax({
                        url: '/data/set-session-data',
                        method: 'POST',
                        data: formData,
                        contentType: false,
                        cache: false,
                        processData: false,
                        success: function (response) {

                            $('#submit-dataset-search').click();
                            reloadTableData();

                        },
                        error: function (xhr, status, error) {
                            console.error("Task id not saved")
                        }
                    });
                } else {
                    $('.selected-dataset-download').prop('disabled', true);
                    $('.selected-dataset-download').text('Downloading...');
                    $('.download-btn').prop('disabled', true);
                    $('.download-text').text(`Downloading ${dataset} and adding it to library. Please wait`);
                    $('#download-info').removeClass('d-none');


                    setTimeout(() => {
                        checkDownloadStatus(id, dataset);
                    }, 3000);
                }
            },
            error: function (xhr, status, error) {
                console.error("Task id not saved")
            }
        });
    }

    function removeDownloadInfo() {
        try {
            const $target = $('#download-info');

            if ($target.length === 0) {
                console.error('Element with id "download-info" not found');
                return;
            }

            $('html, body').animate({
                scrollTop: $target.offset().top
            }, 1000);
        } catch (error) {
            console.error('Error scrolling to download info:', error);
        }
        setTimeout(() => {
            $("#private-corpora .dataTable").dataTable().api().ajax.reload();
        }, 15000);
    }

    $('.search-opus-corpora-form').on('submit', function (event) {
        event.preventDefault();

        $(".search-opus-corpora-form fieldset").prop("disabled", true);
        $(".searching-corpora").addClass("d-none");

        let formData = new FormData();
        formData.append("source_lang", $(".source_lang_search option:selected").val());
        formData.append("target_lang", $(".target_lang_search option:selected").val());

        $(".searching-corpora").removeClass("d-none");

        $.ajax({
            url: $(this).attr("action"),
            method: 'POST',
            data: formData,
            contentType: false,
            cache: false,
            processData: false,
            beforeSend: () => {

                $('.datasets-response-table').html('<div class="dataset-loader">Loading...</div>');

            },
            success: function (response) {

                const container = $('.datasets-response-table');
                displayDataTable(container, response.datasets);

            },
            error: function (xhr, status, error) {
                $(".searching-corpora").addClass("d-none");
                $('.datasets-response-table').html(
                    `<div class="error">Error: ${error}</div>`
                );
            }
        });
    });

    function checkIfExists(name, src, trg) {
        const formData = new FormData();
        formData.append("corpus_name", name);
        formData.append("source_lang", src);
        formData.append("target_lang", trg);

        return $.ajax({
            url: '/data/check-opus-corpus',
            method: 'POST',
            data: formData,
            contentType: false,
            cache: false,
            processData: false
        }).promise();
    }


    async function displayDataTable(dataTableContainer, data) {
        dataTableContainer.html('');

        const table = $('<table id="dataTable" class="table table-bordered w-100">');

        const headers = ["Dataset", "Sentences", "Version", "Src tokens", "Trg tokens", "Download"];

        const headerRow = $('<tr>');
        headers.forEach(header => {
            headerRow.append(`<th>${header}</th>`);
        });
        table.append('<thead><tr></tr></thead><tbody></tbody>');
        table.find('thead').append(headerRow);

        table.addClass('loading');
        table.removeClass('loading');

        table.find('tbody').empty().append('<tr><td colspan="100%" class="loading-cell">Loading data...</td></tr>');

        const fields = ["corpus", "alignment_pairs", "version", "source_tokens", "target_tokens", "download"]
        const rows = await Promise.all(
            data.map(async (row, idx) => {
                const exists = await checkIfExists(row.corpus, row.source, row.target);

                const rowElement = $('<tr>');

                fields.forEach(header => {
                    if (header === "download") {
                        rowElement.append(exists.result === -1 ?
                            `<td><button class="download-btn already-in-library" data-id="${idx}" disabled>Already in library</button></td>` :
                            `<td><button class="download-btn" data-id="${idx}" >Download</button></td>`
                        );
                    } else {
                        rowElement.append(`<td>${row[header]}</td>`);
                    }
                });

                return rowElement;
            })
        );
        table.find('tbody').empty().append(rows);

        $(".dataset-loader").addClass("d-none");
        $(".searching-corpora").addClass("d-none");

        dataTableContainer.append(table)
        // Initialize DataTable
        const newTable = $('#dataTable').DataTable({
            filter: true,
            "searching": true,
            ordering: true,
            paging: true,
            autoWidth: true,
            stateSave: true,
            dom: 'lfrtip'
        });

        newTable.page('first')
        newTable.draw(false)

        function reloadTableData(round = 1) {
            console.log("RELOAD FUNCTION BEING CALLED")
            if (round >= 5) {
                return;
            }
            setTimeout(() => {
                $(".corpora-table").dataTable().api().ajax.reload();
                reloadTableData(round + 1)
            }, 10000);
        }



        $('#dataTable').on('click', '.download-btn', function (e) {
            e.stopPropagation();
            e.stopImmediatePropagation();
            e.preventDefault();

            var notyf = new Notyf();

            const button = $(this);
            const row = button.closest('tr');
            const rowData = newTable.row(row).data();

            let formData = new FormData();
            formData.append("corpus", rowData[0])
            formData.append("source_lang", $(".source_lang_search option:selected").val());
            formData.append("target_lang", $(".target_lang_search option:selected").val());

            // Disable button during download
            button.prop('disabled', true);
            button.text('Downloading...');
            button.addClass('selected-dataset-download')
            $('.download-btn').prop('disabled', true);

            $.ajax({
                url: '/data/download-opus-corpus',
                method: 'POST',
                data: formData,
                contentType: false,
                cache: false,
                processData: false,
                success: function (response) {

                    $('.already-in-library').prop('disabled', true);
                    notyf.success({ message: 'Dataset downloaded and added to your collection!', duration: 3500, position: { x: "middle", y: "top" } });
                    if (response) {
                        try {
                            const formData = new FormData();
                            formData.append('task_id', response.task_id);
                            formData.append("dataset", rowData[0]);
                            $.ajax({
                                url: '/data/set-session-data',
                                method: 'POST',
                                data: formData,
                                contentType: false,
                                cache: false,
                                processData: false,
                                success: function (res) {
                                    checkDownloadStatus(response.task_id, rowData[0]);
                                },
                                error: function (xhr, status, error) {
                                    console.error("Task id not saved")
                                }
                            });
                            $('#download-info').removeClass('d-none');
                            removeDownloadInfo();
                            $(".corpora-table").dataTable().api().ajax.reload();
                        } catch (error) {
                            console.log("Error, the code above doesnt execute")
                        }

                    }
                },
                error: function (xhr, status, error) {
                    notyf.error({ message: 'Something went wrong with the download.', duration: 3500, position: { x: "middle", y: "top" } });
                    console.error('Download failed:', error);
                    button.text('Error');
                    button.prop('disabled', false);
                    $('.download-btn').prop('disabled', false);
                    setTimeout(() => {
                        button.text('Download');
                    }, 2000);
                }
            });
        });


    }

})
