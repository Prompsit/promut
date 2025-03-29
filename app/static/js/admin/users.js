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

    async function processUsers(users, action) {
        for (const user of users) {
            let formData = new FormData();
            formData.append("id", user)
            if (action != "delete") {
                formData.append("type", action)
            }
            $.ajax({
                url: `/admin/${action === "delete" ? "delete_user" : "become"}`,
                method: 'POST',
                data: formData,
                contentType: false,
                cache: false,
                processData: false,
                success: function (response) {
                    return;
                },
                error: function (xhr, status, error) {
                    console.error("Error deleting user", user)

                }
            });
        }

    }

    $('.multiple-user-actions').on('click', 'button', async function (event) {
        const action = $(this).attr('id');
        var notyf = new Notyf();
        const selectedUsers = [...$('tr.selected td:first-child')].map(el => el.innerText);
        try {
            await processUsers(selectedUsers, action);
            notyf.success({ message: 'User deletion successful!', duration: 3500, position: { x: "middle", y: "top" } });
        } catch (error) {
            notyf.error({ message: 'Something went wrong while deleting users.', duration: 3500, position: { x: "middle", y: "top" } });
            console.error('Deletion failed:', error);
            console.error('Failed to process users:', error);
        }

    });

    $("#multiple-users-btn").on('click', function () {
        $('.multiple-user-actions').toggle('d-none');
    })

    users_table.on('click', 'tbody tr td:first-child', function (e) {
        const row = e.currentTarget.closest("tr");
        const cells = $(row).find('td:contains("Admin")');

        if (!cells.length) {
            row.classList.toggle('selected');
        }
        if (users_table.rows('.selected').data().length > 1) {
            $("#multiple-users-btn").removeClass('d-none');
        } else {
            $("#multiple-users-btn").addClass('d-none');
        }
    });

});
