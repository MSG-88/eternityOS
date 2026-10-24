import QtQuick 2.0;
import calamares.slideshow 1.0;

Presentation
{
    id: presentation

    Timer {
        interval: 12000
        running: true
        repeat: true
        onTriggered: presentation.goToNextSlide()
    }

    Slide {
        Image {
            source: "slide-1.png"
            width: 760; height: 428
            fillMode: Image.PreserveAspectFit
            anchors.centerIn: parent
        }
    }

    Slide {
        Image {
            source: "slide-2.png"
            width: 760; height: 428
            fillMode: Image.PreserveAspectFit
            anchors.centerIn: parent
        }
    }

    function onActivate() { presentation.currentSlide = 0; }
    function onLeave() { }
}
