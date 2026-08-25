$(document).ready(function () {

    function updateSiriStatus(status) {
        $(".siri-status").text(status);
    }
    window.updateSiriStatus = updateSiriStatus;
    if (typeof eel !== 'undefined' && eel.expose) {
        try {
            eel.expose(updateSiriStatus);
        } catch (e) {}
    }

    if (typeof eel !== 'undefined' && eel.init && typeof eel.init === 'function') {
        try {
            eel.init()();
        } catch (e) {
            console.warn("Eel init exception:", e);
        }
    }

    // Enter / Skip Start screen button
    $("#skipStartBtn").click(function () {
        $("#Start").attr("hidden", true);
        $("#Oval").removeClass("animate__animated animate__zoomIn");
        $("#Oval").addClass("animate__animated animate__fadeIn");
        $("#Oval").attr("hidden", false);
    });

    // Auto-transition to dashboard if running in web mode or if 1.5s passes
    if (typeof eel === 'undefined' || !eel.init || typeof eel.init !== 'function') {
        setTimeout(function () {
            $("#Start").attr("hidden", true);
            $("#Oval").addClass("animate__animated animate__fadeIn");
            $("#Oval").attr("hidden", false);
        }, 1200);
    } else {
        // In desktop mode, safety fallback if face auth is slow
        setTimeout(function () {
            if ($("#Start").is(":visible") && !$("#Start").attr("hidden")) {
                $("#Start").attr("hidden", true);
                $("#Oval").addClass("animate__animated animate__fadeIn");
                $("#Oval").attr("hidden", false);
            }
        }, 4500);
    }

    // Load persisted chat history on startup
    if (typeof loadChatHistory === 'function') {
        loadChatHistory();
    }

    // Clear History Button handler
    $("#clearHistoryBtn").click(function () {
        if (typeof clearChatHistory === 'function') {
            clearChatHistory();
        }
    });

    // Realtime Hands-Free Voice Mode toggle handler
    $("#realtimeVoiceToggle").change(function () {
        if (typeof voiceManager !== 'undefined') {
            if ($(this).is(":checked")) {
                voiceManager.start();
            } else {
                voiceManager.stop();
            }
        }
    });

    // Chat Drawer Button click handler (refresh history on open)
    $("#ChatBtn").click(function () {
        if (typeof loadChatHistory === 'function') {
            loadChatHistory();
        }
    });

    try {
        if ($.fn && $.fn.textillate) {
            $('.text').textillate({
                loop: true,
                sync: true,
                in: { effect: "bounceIn" },
                out: { effect: "bounceOut" }
            });
            $('.siri-message').textillate({
                loop: true,
                sync: true,
                in: { effect: "fadeInUp", sync: true },
                out: { effect: "fadeOutUp", sync: true }
            });
        }
    } catch (e) {
        console.warn("Textillate init warning:", e);
    }

    // Siri configuration
    try {
        if (typeof SiriWave !== 'undefined') {
            var siriWave = new SiriWave({
                container: document.getElementById("siri-container"),
                width: 800,
                height: 200,
                style: "ios9",
                amplitude: "1",
                speed: "0.30",
                autostart: true
            });
        }
    } catch (e) {
        console.warn("SiriWave init warning:", e);
    }

    // mic button click event
    $("#MicBtn").click(function () { 
        if (typeof voiceManager !== 'undefined' && $("#realtimeVoiceToggle").is(":checked")) {
            voiceManager.startListening();
            return;
        }

        if (typeof eel !== 'undefined' && typeof eel.playAssistantSound === 'function') {
            try { eel.playAssistantSound(); } catch (e) {}
            $("#Oval").attr("hidden", true);
            $("#SiriWave").attr("hidden", false);
            updateSiriStatus("Listening...");
            if (typeof eel.allCommands === 'function') {
                eel.allCommands()();
            }
        } else if (typeof voiceManager !== 'undefined') {
            voiceManager.startListening();
        }
    });

    // Real-Time Instant Hotkey Listener (Ctrl+J, Alt+J, Win+J, Ctrl+Space, F8, F2)
    function handleInstantHotkey(e) {
        const isJ = (e.key === 'j' || e.key === 'J' || e.code === 'KeyJ');
        const isSpace = (e.code === 'Space' || e.key === ' ');
        const isF8 = (e.key === 'F8' || e.code === 'F8');
        const isF2 = (e.key === 'F2' || e.code === 'F2');

        const isCtrlJ = (e.ctrlKey || e.metaKey) && isJ;
        const isAltJ = e.altKey && isJ;
        const isCtrlSpace = (e.ctrlKey || e.metaKey) && isSpace;

        if (isCtrlJ || isAltJ || isCtrlSpace || isF8 || isF2) {
            e.preventDefault();
            e.stopPropagation();

            console.log("[Hotkey]: Instant hotkey activated:", e.key || e.code);

            // Instant visual & audio response
            if (typeof eel !== 'undefined' && typeof eel.playAssistantSound === 'function') {
                try { eel.playAssistantSound(); } catch (err) {}
            }
            $("#Oval").attr("hidden", true);
            $("#SiriWave").attr("hidden", false);
            updateSiriStatus("Listening...");

            // Trigger listener immediately
            if (typeof eel !== 'undefined' && typeof eel.allCommands === 'function') {
                eel.allCommands()();
            } else if (typeof voiceManager !== 'undefined') {
                voiceManager.startListening();
            }
        } else if (e.key === 'Escape') {
            if (!$("#SiriWave").is(":hidden")) {
                $("#SiriWave").attr("hidden", true);
                $("#Oval").attr("hidden", false);
                updateSiriStatus("Hello, I am Jarvis");
            }
        }
    }

    // Attach to window keydown with capture phase for 0-latency instant trigger
    window.addEventListener('keydown', handleInstantHotkey, true);

    // to play assistant 
    function PlayAssistant(message) {
        if (message && message.trim() != "") {
            const userMsg = message.trim();
            $("#Oval").attr("hidden", true);
            $("#SiriWave").attr("hidden", false);
            updateSiriStatus("Thinking...");

            if (typeof eel !== 'undefined' && typeof eel.allCommands === 'function') {
                eel.allCommands(userMsg);
            } else if (typeof voiceManager !== 'undefined') {
                voiceManager.handleVoiceInput(userMsg);
            }

            $("#chatbox").val("");
            $("#MicBtn").attr('hidden', false);
            $("#SendBtn").attr('hidden', true);
        }
    }

    // toggle function to hide and display mic and send button 
    function ShowHideButton(message) {
        if (message.length == 0) {
            $("#MicBtn").attr('hidden', false);
            $("#SendBtn").attr('hidden', true);
        }
        else {
            $("#MicBtn").attr('hidden', true);
            $("#SendBtn").attr('hidden', false);
        }
    }

    // key up event handler on text box
    $("#chatbox").keyup(function () {
        let message = $("#chatbox").val();
        ShowHideButton(message);
    });
    
    // send button event handler
    $("#SendBtn").click(function () {
        let message = $("#chatbox").val();
        PlayAssistant(message);
    });

    // enter press event handler on chat box
    $("#chatbox").keypress(function (e) {
        const key = e.which;
        if (key == 13) {
            let message = $("#chatbox").val();
            PlayAssistant(message);
        }
    });

    // Initialize Bootstrap tooltips
    if (typeof bootstrap !== 'undefined' && bootstrap.Tooltip) {
        try {
            document.querySelectorAll('[data-bs-toggle="tooltip"]').forEach(el => new bootstrap.Tooltip(el));
        } catch (e) {}
    }

    // Settings button click handler
    $("#SettingsBtn").click(function() {
        console.log("Loading data...");
        loadAllData();
        $('#settingsModal').modal('show');
    });

    function loadAllData() {
        loadCommands();
        loadContacts();
        loadSysCommands();
        loadWebCommands();
    }

    function loadCommands() {
        eel.get_all_commands()(function(commands) {
            console.log("Commands loaded:", commands);
            const tbody = $("#commandsList");
            tbody.empty();
            
            commands.forEach(cmd => {
                tbody.append(`
                    <tr>
                        <td>${cmd.command}</td>
                        <td>${cmd.response}</td>
                        <td>
                            <button class="btn btn-sm btn-primary action-btn edit-cmd" data-id="${cmd.id}">
                                <i class="bi bi-pencil"></i>
                            </button>
                            <button class="btn btn-sm btn-danger action-btn delete-cmd" data-id="${cmd.id}">
                                <i class="bi bi-trash"></i>
                            </button>
                        </td>
                    </tr>
                `);
            });
        });
    }

    // Add new command button handler
    $("#addNewCommand").click(function() {
        $("#commandId").val("");
        $("#command").val("");
        $("#response").val("");
        $("#commandModalLabel").text("Add Command");
        $("#commandModal").modal("show");
    });

    // Edit command handler
    $(document).on("click", ".edit-cmd", function() {
        const cmdId = $(this).data("id");
        console.log("Editing command:", cmdId);
        eel.get_command(cmdId)(function(cmd) {
            if (cmd) {
                $("#commandId").val(cmd.id);
                $("#command").val(cmd.command);
                $("#response").val(cmd.response);
                $("#commandModalLabel").text("Edit Command");
                $("#commandModal").modal("show");
            }
        });
    });

    // Delete command handler
    $(document).on("click", ".delete-cmd", function() {
        const cmdId = $(this).data("id");
        if (confirm("Are you sure you want to delete this command?")) {
            eel.delete_command(cmdId)(function(success) {
                if (success) {
                    loadCommands();
                } else {
                    alert("Failed to delete command");
                }
            });
        }
    });

    // Form submit handler
    $("#commandForm").submit(function(e) {
        e.preventDefault();
        const cmdId = $("#commandId").val();
        const command = $("#command").val();
        const response = $("#response").val();
        
        if (cmdId) {
            // Update existing command
            eel.update_command(cmdId, command, response)(function(success) {
                if (success) {
                    $("#commandModal").modal("hide");
                    loadCommands();
                } else {
                    alert("Failed to update command");
                }
            });
        } else {
            // Add new command
            eel.add_command(command, response)(function(success) {
                if (success) {
                    $("#commandModal").modal("hide");
                    loadCommands();
                } else {
                    alert("Failed to add command");
                }
            });
        }
    });

    function loadContacts() {
        eel.get_all_contacts()(function(contacts) {
            const tbody = $("#contactsList");
            tbody.empty();
            
            contacts.forEach(contact => {
                tbody.append(`
                    <tr>
                        <td>${contact.name}</td>
                        <td>${contact.mobile_no}</td>
                        <td>
                            <button class="btn btn-sm btn-primary action-btn edit-contact" data-id="${contact.id}">
                                <i class="bi bi-pencil"></i>
                            </button>
                            <button class="btn btn-sm btn-danger action-btn delete-contact" data-id="${contact.id}">
                                <i class="bi bi-trash"></i>
                            </button>
                        </td>
                    </tr>
                `);
            });
        });
    }

    function loadSysCommands() {
        eel.get_all_sys_commands()(function(commands) {
            const tbody = $("#sysCommandsList");
            tbody.empty();
            
            commands.forEach(cmd => {
                tbody.append(`
                    <tr>
                        <td>${cmd.name}</td>
                        <td>${cmd.path}</td>
                        <td>
                            <button class="btn btn-sm btn-primary action-btn edit-sys-cmd" data-id="${cmd.id}">
                                <i class="bi bi-pencil"></i>
                            </button>
                            <button class="btn btn-sm btn-danger action-btn delete-sys-cmd" data-id="${cmd.id}">
                                <i class="bi bi-trash"></i>
                            </button>
                        </td>
                    </tr>
                `);
            });
        });
    }

    function loadWebCommands() {
        eel.get_all_web_commands()(function(commands) {
            const tbody = $("#webCommandsList");
            tbody.empty();
            
            commands.forEach(cmd => {
                tbody.append(`
                    <tr>
                        <td>${cmd.name}</td>
                        <td>${cmd.url}</td>
                        <td>
                            <button class="btn btn-sm btn-primary action-btn edit-web-cmd" data-id="${cmd.id}">
                                <i class="bi bi-pencil"></i>
                            </button>
                            <button class="btn btn-sm btn-danger action-btn delete-web-cmd" data-id="${cmd.id}">
                                <i class="bi bi-trash"></i>
                            </button>
                        </td>
                    </tr>
                `);
            });
        });
    }

    // Add event handlers for the new add/edit/delete buttons for each table

    // Contact handlers
    $("#addNewContact").click(function() {
        $("#contactId").val("");
        $("#name").val("");
        $("#mobile_no").val("");
        $("#contactModalLabel").text("Add Contact");
        $("#contactModal").modal("show");
    });

    $("#contactForm").submit(function(e) {
        e.preventDefault();
        const contactId = $("#contactId").val();
        const name = $("#name").val();
        const mobile_no = $("#mobile_no").val();
        
        if (contactId) {
            eel.update_contact(contactId, name, mobile_no)(function(success) {
                if (success) {
                    $("#contactModal").modal("hide");
                    loadContacts();
                } else {
                    alert("Failed to update contact");
                }
            });
        } else {
            eel.add_contact(name, mobile_no)(function(success) {
                if (success) {
                    $("#contactModal").modal("hide");
                    loadContacts();
                } else {
                    alert("Failed to add contact");
                }
            });
        }
    });

    // System Command handlers
    $("#addNewSysCommand").click(function() {
        $("#sysCommandId").val("");
        $("#sysName").val("");
        $("#path").val("");
        $("#sysCommandModalLabel").text("Add System Command");
        $("#sysCommandModal").modal("show");
    });

    $("#sysCommandForm").submit(function(e) {
        e.preventDefault();
        const cmdId = $("#sysCommandId").val();
        const name = $("#sysName").val();
        const path = $("#path").val();
        
        if (cmdId) {
            eel.update_sys_command(cmdId, name, path)(function(success) {
                if (success) {
                    $("#sysCommandModal").modal("hide");
                    loadSysCommands();
                } else {
                    alert("Failed to update system command");
                }
            });
        } else {
            eel.add_sys_command(name, path)(function(success) {
                if (success) {
                    $("#sysCommandModal").modal("hide");
                    loadSysCommands();
                } else {
                    alert("Failed to add system command");
                }
            });
        }
    });

    // Web Command handlers
    $("#addNewWebCommand").click(function() {
        $("#webCommandId").val("");
        $("#webName").val("");
        $("#url").val("");
        $("#webCommandModalLabel").text("Add Web Command");
        $("#webCommandModal").modal("show");
    });

    $("#webCommandForm").submit(function(e) {
        e.preventDefault();
        const cmdId = $("#webCommandId").val();
        const name = $("#webName").val();
        const url = $("#url").val();
        
        if (cmdId) {
            eel.update_web_command(cmdId, name, url)(function(success) {
                if (success) {
                    $("#webCommandModal").modal("hide");
                    loadWebCommands();
                } else {
                    alert("Failed to update web command");
                }
            });
        } else {
            eel.add_web_command(name, url)(function(success) {
                if (success) {
                    $("#webCommandModal").modal("hide");
                    loadWebCommands();
                } else {
                    alert("Failed to add web command");
                }
            });
        }
    });

    // Contact edit/delete handlers
    $(document).on("click", ".edit-contact", function() {
        const contactId = $(this).data("id");
        eel.get_contact(contactId)(function(contact) {
            if (contact) {
                $("#contactId").val(contact.id);
                $("#name").val(contact.name);
                $("#mobile_no").val(contact.mobile_no);
                $("#contactModalLabel").text("Edit Contact");
                $("#contactModal").modal("show");
            }
        });
    });

    $(document).on("click", ".delete-contact", function() {
        const contactId = $(this).data("id");
        if (confirm("Are you sure you want to delete this contact?")) {
            eel.delete_contact(contactId)(function(success) {
                if (success) {
                    loadContacts();
                } else {
                    alert("Failed to delete contact");
                }
            });
        }
    });

    // System Command edit/delete handlers
    $(document).on("click", ".edit-sys-cmd", function() {
        const cmdId = $(this).data("id");
        eel.get_sys_command(cmdId)(function(cmd) {
            if (cmd) {
                $("#sysCommandId").val(cmd.id);
                $("#sysName").val(cmd.name);
                $("#path").val(cmd.path);
                $("#sysCommandModalLabel").text("Edit System Command");
                $("#sysCommandModal").modal("show");
            }
        });
    });

    $(document).on("click", ".delete-sys-cmd", function() {
        const cmdId = $(this).data("id");
        if (confirm("Are you sure you want to delete this system command?")) {
            eel.delete_sys_command(cmdId)(function(success) {
                if (success) {
                    loadSysCommands();
                } else {
                    alert("Failed to delete system command");
                }
            });
        }
    });

    // Web Command edit/delete handlers
    $(document).on("click", ".edit-web-cmd", function() {
        const cmdId = $(this).data("id");
        eel.get_web_command(cmdId)(function(cmd) {
            if (cmd) {
                $("#webCommandId").val(cmd.id);
                $("#webName").val(cmd.name);
                $("#url").val(cmd.url);
                $("#webCommandModalLabel").text("Edit Web Command");
                $("#webCommandModal").modal("show");
            }
        });
    });

    $(document).on("click", ".delete-web-cmd", function() {
        const cmdId = $(this).data("id");
        if (confirm("Are you sure you want to delete this web command?")) {
            eel.delete_web_command(cmdId)(function(success) {
                if (success) {
                    loadWebCommands();
                } else {
                    alert("Failed to delete web command");
                }
            });
        }
    });

    // Add a new function to be called when speech input ends
    eel.expose(speechInputEnded);
    function speechInputEnded() {
        updateSiriStatus("Recognizing...");
    }

    // When returning to initial state, reset the greeting
    eel.expose(resetStatus);
    function resetStatus() {
        updateSiriStatus("Hello, I am Jarvis");
    }

    // Prompt suggestion chips click handler
    $(document).on("click", ".prompt-chip", function () {
        const query = $(this).data("query");
        if (query) {
            $("#chatbox").val(query);
            PlayAssistant(query);
        }
    });

    // Real-time digital clock and date in deck
    function updateSystemClock() {
        const now = new Date();
        const timeStr = now.toLocaleTimeString([], { hour: '2-digit', minute: '2-digit', second: '2-digit' });
        const dateStr = now.toLocaleDateString(undefined, { weekday: 'short', month: 'short', day: 'numeric' });
        $("#deckDigitalClock").text(timeStr);
        $("#deckDateStr").text(dateStr);
    }
    setInterval(updateSystemClock, 1000);
    updateSystemClock();

    // Deck Voice Toggle Button
    $("#deckVoiceToggle").click(function () {
        const toggle = $("#realtimeVoiceToggle");
        const nextState = !toggle.is(":checked");
        toggle.prop("checked", nextState).trigger("change");
        $(this).text(nextState ? "Voice: On" : "Voice: Off")
               .toggleClass("btn-info btn-outline-info");
    });

    // Sync deck button when voice toggle changes from drawer
    $("#realtimeVoiceToggle").on("change", function () {
        const isChecked = $(this).is(":checked");
        $("#deckVoiceToggle").text(isChecked ? "Voice: On" : "Voice: Off")
            .toggleClass("btn-info", isChecked)
            .toggleClass("btn-outline-info", !isChecked);
    });

    // Deck Relief Button
    $("#deckReliefBtn").click(function () {
        $("#ReliefBtn").trigger("click");
    });

    // Deck Chat History Drawer Button
    $("#deckChatBtn").click(function () {
        $("#ChatBtn").trigger("click");
    });

    // Deck Settings Modal Button
    $("#deckSettingsBtn").click(function () {
        $("#SettingsBtn").trigger("click");
    });

    // Quick Ambient sound toggles from deck
    $(document).on("click", ".quick-ambient-btn", function () {
        const soundType = $(this).data("sound");
        if (typeof ambientSound !== 'undefined' && ambientSound) {
            const correspondingModalBtn = $(`.ambient-toggle[data-sound="${soundType}"]`);
            ambientSound.toggleSound(soundType, correspondingModalBtn);
            
            const isPlaying = !!ambientSound.activeSounds[soundType];
            $(this).toggleClass("active", isPlaying);
            
            // Update badge text
            let activeCount = Object.values(ambientSound.activeSounds).filter(Boolean).length;
            if (activeCount === 0) {
                $("#ambientPlayingBadge").text("All Off").removeClass("bg-info text-dark").addClass("bg-dark text-info");
            } else {
                $("#ambientPlayingBadge").text(`${activeCount} Active`).removeClass("bg-dark text-info").addClass("bg-info text-dark");
            }
        }
    });

});