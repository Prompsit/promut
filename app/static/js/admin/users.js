$(document).ready(function () {
    let users_table = $(".users-table").DataTable({
        processing: true,
        serverSide: true,
        responsive: true,
        ajax: {
            url: "users_feed",
            method: "post"
        },
        columnDefs: [
            { targets: 0, responsivePriority: 1 },
            {
                targets: 4,
                className: "notes-row",
                render: function (data, type, row) {
                    const template = document.importNode(document.getElementById('notes-template').content, true);

                    if (row[4]) {
                        $(template).find('.notes-content').html(row[4]);
                        $(template).find('.notes-link').attr('href', 'user/' + row[0]);
                        $(template).find('.notes-link').removeClass('d-none');
                    }

                    const ghost = document.createElement('div');
                    ghost.appendChild(template);
                    return ghost.innerHTML;
                }
            },
            {
                targets: 5,
                responsivePriority: 1,
                className: "actions",
                searchable: false,
                sortable: false,
                render: function (data, type, row) {
                    let template = document.importNode(document.querySelector("#users-table-actions-template").content, true);

                    $(template).find(".edit-user").attr("href", "user/" + row[0]);

                    if ($("#current_user").val() != row[0]) {
                        $(template).find(".delete-user").attr("href", `delete_user?id=${row[0]}`);
                        $(template).find(".delete-user").removeClass("d-none");

                        $(template).find(".become-admin").attr("href", "become/admin/" + row[0]);
                        $(template).find(".become-expert").attr("href", "become/expert/" + row[0]);
                        $(template).find(".become-normal").attr("href", "become/beginner/" + row[0]);
                        $(template).find(".become-researcher").attr("href", "become/researcher/" + row[0]);
                        $(template).find('.become-btn').removeClass('d-none');
                        if (row[6]) { // is admin
                            $(template).find(".become-admin").addClass("d-none");
                        } else if (row[7]) { // is expert
                            $(template).find(".become-expert").addClass("d-none");
                        } else if (row[8]) { // is researcher
                            $(template).find(".become-researcher").addClass("d-none");
                        } else {
                            $(template).find(".become-normal").addClass("d-none");
                        }
                    }

                    let ghost = document.createElement('div');
                    ghost.appendChild(template);
                    return ghost.innerHTML;
                }
            }
        ]
    });

    users_table.on('click', 'tbody tr td:first-child', function (e) {
        const row = e.currentTarget.closest("tr");
        const cells = $(row).find('td:contains("Admin")');

        console.log(cells, cells.length)

        if (!cells.length) {
            row.classList.toggle('selected');
        }

        const actionsContainer = $('.multiple-user-actions-container');

        let template = document.importNode(document.querySelector("#multiple-users-actions-template").content, true);

        let ghost = document.createElement('div');
        ghost.appendChild(template);

        if (users_table.rows('.selected').data().length > 1) {
            actionsContainer.html(ghost.innerHTML);
        } else {
            actionsContainer.html("");
        }
    });

});
