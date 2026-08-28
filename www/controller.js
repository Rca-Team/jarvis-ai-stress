$(document).ready(function () {

    // Display Speak Message
    function DisplayMessage(message) {
        $(".siri-message").text(message);
        if ($.fn && $.fn.textillate) {
            try {
                $('.siri-message').textillate('start');
            } catch (e) {}
        }
    }

    // Display hood
    function ShowHood() {
        $("#Oval").attr("hidden", false);
        $("#SiriWave").attr("hidden", true);
    }

    function senderText(message, timestamp) {
        if (typeof appendChatMessage === 'function') {
            appendChatMessage('user', message, timestamp);
        } else {
            var chatBox = document.getElementById("chat-canvas-body");
            if (chatBox && message && message.trim() !== "") {
                chatBox.innerHTML += `<div class="row justify-content-end mb-4">
                <div class = "width-size">
                <div class="sender_message">${message}</div>
            </div>`; 
                chatBox.scrollTop = chatBox.scrollHeight;
            }
        }
    }

    function receiverText(message, timestamp) {
        if (typeof appendChatMessage === 'function') {
            appendChatMessage('assistant', message, timestamp);
        } else {
            var chatBox = document.getElementById("chat-canvas-body");
            if (chatBox && message && message.trim() !== "") {
                chatBox.innerHTML += `<div class="row justify-content-start mb-4">
                <div class = "width-size">
                <div class="receiver_message">${message}</div>
                </div>
            </div>`; 
                chatBox.scrollTop = chatBox.scrollHeight;
            }
        }
    }

    // Hide Loader and display Face Auth animation
    function hideLoader() {
        $("#Loader").attr("hidden", true);
        $("#FaceAuth").attr("hidden", false);
    }

    // Hide Face auth and display Face Auth success animation
    function hideFaceAuth() {
        $("#FaceAuth").attr("hidden", true);
        $("#FaceAuthSuccess").attr("hidden", false);
    }

    // Hide success and display hello greet
    function hideFaceAuthSuccess() {
        $("#FaceAuthSuccess").attr("hidden", true);
        $("#HelloGreet").attr("hidden", false);
    }

    // Hide Start Page and display blob
    function hideStart() {
        $("#Start").attr("hidden", true);

        setTimeout(function () {
            $("#Oval").addClass("animate__animated animate__zoomIn");
            $("#Oval").attr("hidden", false);
            // Refresh and activate Stress Monitor post-authentication
            if (typeof stressHUD !== 'undefined' && stressHUD) {
                stressHUD.fetchStatus();
            }
        }, 1000);
    // Update UI to active Siri wave listening mode
    function showListeningWave() {
        $("#Oval").attr("hidden", true);
        $("#SiriWave").attr("hidden", false);
        $(".siri-status").text("Listening...");
    }

    // Trigger voice listening when 'Jarvis' hotword is spoken
    function startListening() {
        console.log("[Jarvis]: Voice listening activated!");
        if (typeof eel !== 'undefined' && eel.playAssistantSound) {
            try { eel.playAssistantSound(); } catch (e) {}
        }
        showListeningWave();
        if (typeof eel !== 'undefined' && eel.allCommands) {
            try { eel.allCommands()(); } catch (e) {}
        }
    }

    // Expose functions to window globally
    window.DisplayMessage = DisplayMessage;
    window.ShowHood = ShowHood;
    window.senderText = senderText;
    window.receiverText = receiverText;
    window.hideLoader = hideLoader;
    window.hideFaceAuth = hideFaceAuth;
    window.hideFaceAuthSuccess = hideFaceAuthSuccess;
    window.hideStart = hideStart;
    window.showListeningWave = showListeningWave;
    window.startListening = startListening;

    // Safely expose to Eel if running in Eel environment
    if (typeof eel !== 'undefined' && eel.expose) {
        try {
            eel.expose(DisplayMessage);
            eel.expose(ShowHood);
            eel.expose(senderText);
            eel.expose(receiverText);
            eel.expose(hideLoader);
            eel.expose(hideFaceAuth);
            eel.expose(hideFaceAuthSuccess);
            eel.expose(hideStart);
            eel.expose(showListeningWave);
            eel.expose(startListening);
        } catch (e) {
            console.warn("Eel expose skipped:", e);
        }
    }
});