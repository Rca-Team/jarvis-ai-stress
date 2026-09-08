$(document).ready(function () {

    // Display Speak Message
    function DisplayMessage(message) {
        $(".siri-message").text(message);
        $("#pipResponseText").text(message);
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

    // Instantly skip directly to main Jarvis dashboard
    function skipToDashboard() {
        $("#Start").attr("hidden", true);
        $("#Loader").attr("hidden", true);
        $("#FaceAuth").attr("hidden", true);
        $("#FaceAuthSuccess").attr("hidden", true);
        $("#FaceAuthFail").attr("hidden", true);
        $("#HelloGreet").attr("hidden", true);
        $("#Oval").removeClass("animate__animated animate__zoomIn animate__fadeIn");
        $("#Oval").addClass("animate__animated animate__zoomIn");
        $("#Oval").attr("hidden", false);
        if (typeof stressHUD !== 'undefined' && stressHUD) {
            stressHUD.fetchStatus();
        }
    }

    // Hide Start Page and display blob
    function hideStart() {
        skipToDashboard();
    }

    // Face Auth Failed handler
    function faceAuthFailed() {
        console.warn("[Face Auth]: Access Denied - Face Authentication Failed");
        $("#Loader").attr("hidden", true);
        $("#FaceAuth").attr("hidden", true);
        $("#FaceAuthSuccess").attr("hidden", true);
        $("#HelloGreet").attr("hidden", true);
        $("#FaceAuthFail").attr("hidden", false);
        $("#WishMessage").text("Access Denied: Face Authentication Failed");
        $("#retryAuthBtn").attr("hidden", false);
        $("#skipStartBtn").attr("hidden", true);
    }

    // Reset UI to attempt face authentication again
    function resetToAuth() {
        $("#FaceAuthFail").attr("hidden", true);
        $("#FaceAuthSuccess").attr("hidden", true);
        $("#HelloGreet").attr("hidden", true);
        $("#Loader").attr("hidden", true);
        $("#FaceAuth").attr("hidden", false);
        $("#WishMessage").text("Ready for Face Authentication...");
        $("#retryAuthBtn").attr("hidden", true);
    }

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

    // Picture-in-Picture mode disabled
    function set_pip_mode_ui(isPip) {
        $('body').removeClass('pip-mode');
        $('#pipOverlay').addClass('d-none');
    }

    // Bind PiP Mode Toggles (disabled)
    $("#pipToggleBtn, #pipExitBtn").click(function () {
        set_pip_mode_ui(false);
    });

    // Bind Live Screen Vision Button
    $("#seeScreenBtn, #pipSeeScreenBtn").click(function () {
        if (typeof eel !== 'undefined' && eel.eel_see_screen) {
            eel.eel_see_screen("What is on my screen and how can you assist me with it?")();
        } else {
            fetch('/api/vision/screen', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ query: "What is on my screen and how can you assist me with it?" })
            }).then(r => r.json()).then(d => {
                if (d.response) {
                    DisplayMessage(d.response);
                }
            });
        }
    });

    // Expose functions to window globally
    window.DisplayMessage = DisplayMessage;
    window.ShowHood = ShowHood;
    window.senderText = senderText;
    window.receiverText = receiverText;
    window.hideLoader = hideLoader;
    window.hideFaceAuth = hideFaceAuth;
    window.hideFaceAuthSuccess = hideFaceAuthSuccess;
    window.hideStart = hideStart;
    window.skipToDashboard = skipToDashboard;
    window.faceAuthFailed = faceAuthFailed;
    window.resetToAuth = resetToAuth;
    window.showListeningWave = showListeningWave;
    window.startListening = startListening;
    window.set_pip_mode_ui = set_pip_mode_ui;

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
            eel.expose(skipToDashboard);
            eel.expose(faceAuthFailed);
            eel.expose(resetToAuth);
            eel.expose(showListeningWave);
            eel.expose(startListening);
            eel.expose(set_pip_mode_ui);
        } catch (e) {
            console.warn("Eel expose skipped:", e);
        }
    }
});