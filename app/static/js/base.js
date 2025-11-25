$(document).ready(function () {

    function verifyUser() {
        $.ajax({
            url: "/auth/verify_user",
            method: "POST",
            data: {
                session_email: current_user_email
            },
            success: function (response) {
                console.log("verifyUser OK:", response);
            },
            error: function (xhr, status, error) {
                console.error("verifyUser error:", status, error);
            }
        });
    }

    verifyUser();
    setInterval(verifyUser, 120000);

    $("[data-toggle=hamburger]").on('click', function () {
        $(`${$(this).attr("data-target")}`).toggleClass("show");
        $('body').toggleClass("overflow-hidden")
    });

    $(".nile-resurrect-btn").on('click', function (e) {
        e.preventDefault();
        $('.tour-guide').removeClass('hidden');
    });
});