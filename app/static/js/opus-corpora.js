$(document).ready(function () {



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
                $(".dataset-loader").addClass("d-none");
                $(".searching-corpora").addClass("d-none");
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


    function displayDataTable(dataTableContainer, data) {
        dataTableContainer.html('');

        const table = $('<table id="dataTable" class="table table-bordered w-100">');

        const headers = ["Dataset", "Sentences", "Version", "Src tokens", "Trg tokens", "Download"];

        const headerRow = $('<tr>');
        headers.forEach(header => {
            headerRow.append(`<th>${header}</th>`);
        });
        table.append('<thead><tr></tr></thead><tbody></tbody>');
        table.find('thead').append(headerRow);

        const fields = ["corpus", "alignment_pairs", "version", "source_tokens", "target_tokens", "download"]
        data.forEach((row, idx) => {
            const rowElement = $('<tr>');
            fields.forEach(header => {
                if (header === "download") {
                    rowElement.append(`<td><button class="download-btn" data-id="${idx}" >Download</button></td>`)
                } else {
                    rowElement.append(`<td>${row[header]}</td>`);

                }
            });
            table.find('tbody').append(rowElement);
        });

        dataTableContainer.append(table)
        // Initialize DataTable
        const newTable = $('#dataTable').DataTable({
            searching: true,
            ordering: true,
            paging: true,
            autoWidth: true,
            stateSave: true,
            dom: 'lrtip'
        });

        function reloadTableContent() {
            $(".tab-pane.active .dataTable").each(function (i, el) {
                console.log("")
                $(el).DataTable().ajax.reload();
            });
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
            $('.download-btn').prop('disabled', true);

            $.ajax({
                url: '/data/download-opus-corpus',
                method: 'POST',
                data: formData,
                contentType: false,
                cache: false,
                processData: false,
                success: function (response) {
                    button.text('Download');
                    button.prop('disabled', false);
                    $('.download-btn').prop('disabled', false);
                    notyf.success({ message: 'Dataset downloaded and added to your collection!', duration: 3500, position: { x: "middle", y: "top" } });

                    if (response) {
                        reloadTableContent();
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