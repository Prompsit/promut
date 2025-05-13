$(document).ready(function () {

    let adjust_languages = (el) => {
        let other = $('.lang_sel_model').not(el);
        let selected_lang = $(el).find('option:selected').val();
        $(other).find('option').prop('disabled', false)
        $(other).find(`option[value='${selected_lang}']`).prop('disabled', true);

        if ($(other).find('option:selected').val() == selected_lang) {
            $(other).find('option:selected').prop('selected', false);
        }
    }

    $('.source_lang_model').on('change', function () {
        adjust_languages(this);
    });

    adjust_languages($('.source_lang_model'));


    $('.search-opus-models-form').on('submit', function (event) {
        event.preventDefault();

        $(".search-opus-models-form fieldset").prop("disabled", true);
        $(".searching-models").addClass("d-none");

        let formData = new FormData();
        formData.append("source_lang", $(".source_lang_model option:selected").val());
        formData.append("target_lang", $(".target_lang_model option:selected").val());

        $(".searching-models").removeClass("d-none");

        $.ajax({
            url: $(this).attr("action"),
            method: 'POST',
            data: formData,
            contentType: false,
            cache: false,
            processData: false,
            beforeSend: () => {

                $('.models-response-table').html('<div class="dataset-loader">Loading...</div>');

            },
            success: function (response) {

                const container = $('.models-response-table');
                displayDataTable(container, response);

            },
            error: function (xhr, status, error) {
                $(".searching-models").addClass("d-none");
                $('.models-response-table').html(
                    `<div class="error">Error: ${error}</div>`
                );
            }
        });
    });

    function checkIfExists() {
        const formData = new FormData();
        formData.append("source_lang", $(".source_lang_model option:selected").val());
        formData.append("target_lang", $(".target_lang_model option:selected").val());

        return $.ajax({
            url: '/library/check-model',
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

        const headers = ["Model", "BLEU score", "Size", "Language pair", "Download"];

        const headerRow = $('<tr>');
        headers.forEach(header => {
            headerRow.append(`<th>${header}</th>`);
        });
        table.append('<thead><tr></tr></thead><tbody></tbody>');
        table.find('thead').append(headerRow);

        table.addClass('loading');
        table.removeClass('loading');

        table.find('tbody').empty().append('<tr><td colspan="100%" class="loading-cell">Loading data...</td></tr>');

        const fields = ["model", "score", "size", "langpair", "download"]
        const rows = await Promise.all(
            [data].map(async (row, idx) => {
                const exists = await checkIfExists();

                const rowElement = $('<tr>');

                fields.forEach(header => {
                    if (header === "download") {
                        rowElement.append(exists.result === -1 ?
                            `<td><button class="download-btn already-in-library" data-id="${idx}" disabled>Already in library</button></td>` :
                            `<td><button class="download-btn" data-id="${idx}" >Download</button></td>`
                        );

                    }
                    else if (header === "size") {
                        rowElement.append(`<td>${row["size"] ? Intl.NumberFormat("en", {
                            notation: "compact",
                        }).format(row["size"]) : ""}</td>`);
                    }
                    else {
                        rowElement.append(`<td>${row[header]}</td>`);
                    }
                });

                return rowElement;
            })
        );
        table.find('tbody').empty().append(rows);

        $(".dataset-loader").addClass("d-none");
        $(".searching-models").addClass("d-none");

        dataTableContainer.append(table)
        // Initialize DataTable
        const newTable = $('#dataTable').DataTable({
            filter: true,
            "searching": true,
            ordering: true,
            paging: true,
            autoWidth: true,
            stateSave: true,
            dom: 'lrtip'
        });

        newTable.page('first')
        newTable.draw(false)

        // Dataset download on btn click
        $('#dataTable').on('click', '.download-btn', function (e) {
            e.stopPropagation();
            e.stopImmediatePropagation();
            e.preventDefault();

            var notyf = new Notyf();

            const button = $(this);

            $(".model-download-block").removeClass('d-none');

            let formData = new FormData();
            formData.append("source_lang", $(".source_lang_model option:selected").val());
            formData.append("target_lang", $(".target_lang_model option:selected").val());
            // Disable button during download
            button.prop('disabled', true);
            button.text('Downloading...');
            button.addClass('selected-dataset-download')
            $('.download-btn').prop('disabled', true);

            $.ajax({
                url: '/library/download-model',
                method: 'POST',
                data: formData,
                contentType: false,
                cache: false,
                processData: false,
                success: function (response) {
                    button.text("Already in library")
                    $('.already-in-library').prop('disabled', true);
                    notyf.success({ message: 'Model downloaded and added to collection!', duration: 3500, position: { x: "middle", y: "top" } });
                    $(".model-download-block").addClass('d-none');
                    setTimeout(function () {
                        location.reload();
                    }, 3000);
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
                    $(".model-download-block").addClass('d-none');
                }
            });
        });


    }

})
