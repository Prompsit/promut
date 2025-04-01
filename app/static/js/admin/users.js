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
                        $(template).find(".delete-user").removeClass("d-none");

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
        var notyf = new Notyf();

        const notifications = { delete: "Deletion successful", admin: "Changed role to admin successfully", expert: "Changed role to expert successfully", normal: "Changed role to normal successfully", researcher: "Changed role to reasearcher successfully" }

        const errors = { delete: "error while deleting.", admin: "Could not change role to admin. Please thy again.", expert: "Could not change role to expert. Please thy again.", normal: "Could not change role to normal. Please thy again.", researcher: "Could not change role to researcher. Please thy again." }

        try {
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
                        users_table.ajax.reload();
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

    $('.multiple-user-actions').on('click', 'button', async function () {
        const action = $(this).attr('id');
        const selectedUsers = [...$('tr.selected td:first-child')].map(el => el.innerText);
        await processUsers(selectedUsers, action);
    });

    $(document).on('click', '.user-actions-dropdown .actions-container button', async function (event) {
        event.preventDefault();
        event.stopPropagation();
        const action = $(this).attr('id');
        const user = $(this).closest("tr").find("td:first-child")[0].innerText;

        try {
            await processUsers([user], action);
        } catch (error) {
            console.error('Error processing users:', error);
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
