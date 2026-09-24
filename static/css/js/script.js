/* =====================================================
   STUDENT MANAGEMENT SYSTEM
   MAIN JAVASCRIPT
===================================================== */


/* =====================================================
   PAGE LOADED
===================================================== */

document.addEventListener(
    "DOMContentLoaded",
    function () {


        /* =============================================
           ATTENDANCE CIRCLE
        ============================================= */

        const attendanceCircle =
            document.querySelector(
                ".attendance-circle"
            );


        if (attendanceCircle) {

            let percentage =
                parseFloat(
                    attendanceCircle.dataset.percentage
                );


            if (isNaN(percentage)) {
                percentage = 0;
            }


            percentage =
                Math.max(
                    0,
                    Math.min(
                        100,
                        percentage
                    )
                );


            const degrees =
                percentage * 3.6;


            attendanceCircle.style.background =
                `conic-gradient(
                    #16c8ed 0deg ${degrees}deg,
                    rgba(255,255,255,0.06)
                    ${degrees}deg 360deg
                )`;

        }



        /* =============================================
           ATTENDANCE BAR GRAPH
        ============================================= */

        const chartBars =
            document.querySelectorAll(
                ".chart-bar"
            );


        chartBars.forEach(
            function (bar) {

                let height =
                    parseFloat(
                        bar.dataset.height
                    );


                if (isNaN(height)) {
                    height = 0;
                }


                height =
                    Math.max(
                        3,
                        Math.min(
                            100,
                            height
                        )
                    );


                bar.style.height =
                    height + "%";

            }
        );



        /* =============================================
           PHOTO PREVIEW
        ============================================= */

        const photoInput =
            document.getElementById(
                "photo"
            );


        if (photoInput) {

            photoInput.addEventListener(
                "change",
                function () {

                    previewStudentPhoto(
                        this
                    );

                }
            );

        }

    }
);



/* =====================================================
   DELETE CONFIRMATION
===================================================== */

function confirmDelete() {

    return confirm(
        "Are you sure you want to delete this student?"
    );

}



/* =====================================================
   PHOTO PREVIEW
===================================================== */

function previewStudentPhoto(input) {

    const preview =
        document.getElementById(
            "photoPreview"
        );


    if (!preview) {
        return;
    }


    const file =
        input.files[0];


    if (!file) {

        preview.innerHTML =
            "<span>👤</span>";

        return;
    }


    const allowedTypes = [

        "image/jpeg",
        "image/png",
        "image/webp"

    ];


    if (
        !allowedTypes.includes(
            file.type
        )
    ) {

        alert(
            "Please select JPG, JPEG, PNG or WEBP image."
        );


        input.value = "";


        preview.innerHTML =
            "<span>👤</span>";


        return;
    }


    const reader =
        new FileReader();


    reader.onload =
        function (event) {

            preview.innerHTML = `
                <img
                    src="${event.target.result}"
                    alt="Student Photo Preview"
                >
            `;

        };


    reader.readAsDataURL(file);

}