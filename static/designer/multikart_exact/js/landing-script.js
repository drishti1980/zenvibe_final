/*-----------------------------------------------------------------------------------

    Template Name:Multikart - Multipurpose Ecommerce Template
    Template URI: https://themes.pixelstrap.com/multikart
    Author: Pixelstrap
    Author URL: https://themeforest.net/user/pixelstrap

----------------------------------------------------------------------------------- */
/* 01 Slider js */
/* 02 Tooltip js */
/* 03 sticky header js */
/* 04 Tap to top js */
/* 05 Custom Cursor js */
/* 06 Header scrollspy js  */


/*====================
 01. Slider js
=======================*/
$(document).ready(function () {
    $('.owl-carousel').owlCarousel({
        loop: true,
        margin: 24,
        nav: false,
        center: true,
        dots: false,
        stagePadding: 200,
        responsive: {
            0: {
                items: 1,
                stagePadding: 50,
                margin: 15,
            },
            480: {
                items: 2,
                stagePadding: 10,
                margin: 15,
            },
            600: {
                items: 2,
                stagePadding: 20,
            },
            1340: {
                items: 3,
                stagePadding: 100,
            },
            1320: {
                items: 3
            }
        }
    })
});


/*====================
 02. Tooltip js
=======================*/
document.addEventListener('DOMContentLoaded', function () {
    function myFunction(e) {
        var x = e.clientX;
        var y = e.clientY;
        var tooltip = document.getElementById("tooltip");

        // Adjust the tooltip position with an offset
        var offsetX = 0;
        var offsetY = -100;

        tooltip.style.left = (x + offsetX) + "px";
        tooltip.style.top = (y + offsetY) + "px";
        tooltip.style.display = "block";

        // Debugging: Inspect the target element
        console.dir(e.target);

        var tooltipText = e.target.getAttribute("data-tooltip");


        if (!tooltipText) {
            tooltip.style.opacity = 0;
            return;
        }

        if (tooltipText !== null) {
            tooltip.innerHTML = tooltipText;
            tooltip.style.opacity = 1;
        } else {
            tooltip.innerHTML = "No tooltip text";
        }
    }

    document.querySelectorAll('.hoverable').forEach(function (element) {
        element.addEventListener('mousemove', myFunction);
        element.addEventListener('mouseleave', function () {
            document.getElementById("tooltip").style.display = "none";
        });
    });
});


/*====================
 03. sticky header js
=======================*/
const header = document.querySelector("header");
const toggleClass = "sticky";

window.addEventListener("scroll", () => {
    const currentScroll = window.pageYOffset;
    if (currentScroll > 150) {
        header.classList.add(toggleClass);
    } else {
        header.classList.remove(toggleClass);
    }
});


/*====================
  04. Tap to top js
=======================*/
const btn = document.querySelector(".scroll");

btn.addEventListener("click", function () {
    scroll(0, 200);
});

window.onscroll = function showHide() {
    if (
        document.body.scrollTop > 500 ||
        document.documentElement.scrollTop > 500
    ) {
        btn.style.transform = "scale(1)";
    } else {
        btn.style.transform = "scale(0)";
    }
};

function scroll(target, duration) {
    if (duration <= 0) {
        return;
    }
    let difference = target - document.documentElement.scrollTop;
    let speed = (difference / duration) * 10;
    setTimeout(function () {
        document.documentElement.scrollTop += speed;
        if (document.documentElement.scrollTop == target) {
            return;
        }
        scroll(target, duration - 10);
    }, 10);
}


/*=====================
  05. Custom Cursor js
==========================*/
const cursor = document.querySelector("#cursor");
const cursorBorder = document.querySelector("#cursor-border");
const cursorPos = {
    x: 0,
    y: 0
};
const cursorBorderPos = {
    x: 0,
    y: 0
};

document.addEventListener("mousemove", (e) => {
    cursorPos.x = e.clientX;
    cursorPos.y = e.clientY;

    cursor.style.transform = `translate(${e.clientX}px, ${e.clientY}px)`;
});

requestAnimationFrame(function loop() {
    const easting = 8;
    cursorBorderPos.x += (cursorPos.x - cursorBorderPos.x) / easting;
    cursorBorderPos.y += (cursorPos.y - cursorBorderPos.y) / easting;

    cursorBorder.style.transform = `translate(${cursorBorderPos.x}px, ${cursorBorderPos.y}px)`;
    requestAnimationFrame(loop);
});

document.querySelectorAll("[data-cursor]").forEach((item) => {
    item.addEventListener("mouseover", (e) => {
        if (item.dataset.cursor === "pointer") {
            cursorBorder.style.backgroundColor = "rgba(236, 137,81, .3)";
            cursorBorder.style.setProperty("--size", "60px");
        }
    });
    item.addEventListener("mouseout", (e) => {
        cursorBorder.style.backgroundColor = "unset";
        cursorBorder.style.mixBlendMode = "unset";
        cursorBorder.style.setProperty("--size", "30px");
    });
});


/*=====================
   06. Header scrollspy js 
==========================*/
const sections = document.querySelectorAll("section[id]");

window.addEventListener("scroll", navHighlighter);

function navHighlighter() {

    // Get current scroll position
    let scrollY = window.pageYOffset;

    // Now we loop through sections to get height, top and ID values for each
    sections.forEach(current => {
        const sectionHeight = current.offsetHeight;
        const sectionTop = current.offsetTop - 50;
        sectionId = current.getAttribute("id");

        if (
            scrollY > sectionTop &&
            scrollY <= sectionTop + sectionHeight
        ) {
            document.querySelector(".nav-item a[href*=" + sectionId + "]").classList.add("active");
        } else {
            document.querySelector(".nav-item a[href*=" + sectionId + "]").classList.remove("active");
        }

    });
}

/*=====================
   06. AOS js 
==========================*/
AOS.init();