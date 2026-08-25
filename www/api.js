/**
 * Jarvis AI - API & Real-time Hands-Free Voice Controller
 */

// Helper to format timestamps
function formatTime(timeStr) {
    if (!timeStr) {
        return new Date().toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' });
    }
    try {
        const d = new Date(timeStr);
        if (!isNaN(d.getTime())) {
            return d.toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' });
        }
        return timeStr;
    } catch (e) {
        return timeStr;
    }
}

// Append a message to the chat canvas UI
function appendChatMessage(sender, message, timestamp) {
    const chatBox = document.getElementById("chat-canvas-body");
    if (!chatBox || !message || message.trim() === "") return;

    const formattedTime = formatTime(timestamp);
    const isUser = (sender === 'user' || sender === 'sender');

    const messageHtml = isUser
        ? `<div class="row justify-content-end mb-3">
             <div class="width-size">
               <div class="sender_message">
                 ${escapeHtml(message)}
                 <span class="msg-timestamp text-end"><i class="bi bi-person-fill me-1"></i>${formattedTime}</span>
               </div>
             </div>
           </div>`
        : `<div class="row justify-content-start mb-3">
             <div class="width-size">
               <div class="receiver_message">
                 ${escapeHtml(message)}
                 <span class="msg-timestamp text-start"><i class="bi bi-robot me-1"></i>${formattedTime}</span>
               </div>
             </div>
           </div>`;

    chatBox.innerHTML += messageHtml;
    chatBox.scrollTop = chatBox.scrollHeight;
}

function escapeHtml(text) {
    if (typeof text !== 'string') return text;
    return text
        .replace(/&/g, "&amp;")
        .replace(/</g, "&lt;")
        .replace(/>/g, "&gt;")
        .replace(/"/g, "&quot;")
        .replace(/'/g, "&#039;");
}

// Load Chat History from Backend (Eel or REST API)
function loadChatHistory() {
    console.log("Loading chat history...");
    const chatBox = document.getElementById("chat-canvas-body");
    if (chatBox) {
        chatBox.innerHTML = '<div class="text-center text-muted py-3"><div class="spinner-border spinner-border-sm text-info me-2" role="status"></div>Loading messages...</div>';
    }

    if (typeof eel !== 'undefined' && eel.get_chat_history) {
        eel.get_chat_history()(function(history) {
            renderChatHistory(history);
        });
    } else {
        fetch('/api/chat/history')
            .then(res => res.json())
            .then(data => {
                if (data.status === 'success' && data.history) {
                    renderChatHistory(data.history);
                } else {
                    if (chatBox) chatBox.innerHTML = '<div class="text-center text-muted py-3">No messages yet.</div>';
                }
            })
            .catch(err => {
                console.warn("REST API history load failed:", err);
                if (chatBox) chatBox.innerHTML = '<div class="text-center text-muted py-3">Ready to chat.</div>';
            });
    }
}

// Render historical messages into Chat Box
function renderChatHistory(history) {
    const chatBox = document.getElementById("chat-canvas-body");
    if (!chatBox) return;
    chatBox.innerHTML = "";

    if (!history || history.length === 0) {
        chatBox.innerHTML = '<div class="text-center text-muted py-3"><i class="bi bi-chat-dots me-1"></i>No previous messages. Start a conversation!</div>';
        return;
    }

    history.forEach(item => {
        appendChatMessage(item.sender, item.message, item.timestamp);
    });

    chatBox.scrollTop = chatBox.scrollHeight;
}

// Clear Chat History
function clearChatHistory() {
    if (confirm("Are you sure you want to clear all chat history?")) {
        if (typeof eel !== 'undefined' && eel.clear_chat_history) {
            eel.clear_chat_history()(function(success) {
                if (success) {
                    const chatBox = document.getElementById("chat-canvas-body");
                    if (chatBox) {
                        chatBox.innerHTML = '<div class="text-center text-muted py-3"><i class="bi bi-check-circle text-success me-1"></i>Chat history cleared.</div>';
                    }
                } else {
                    alert("Failed to clear chat history");
                }
            });
        } else {
            fetch('/api/chat/history', { method: 'DELETE' })
                .then(res => res.json())
                .then(data => {
                    if (data.status === 'success') {
                        const chatBox = document.getElementById("chat-canvas-body");
                        if (chatBox) {
                            chatBox.innerHTML = '<div class="text-center text-muted py-3"><i class="bi bi-check-circle text-success me-1"></i>Chat history cleared.</div>';
                        }
                    } else {
                        alert("Failed to clear chat history");
                    }
                })
                .catch(err => console.error("Clear history error:", err));
        }
    }
}

// Real-Time Hands-Free Voice Manager
class RealtimeVoiceManager {
    constructor() {
        this.isActive = false;
        this.isListening = false;
        this.isSpeaking = false;
        this.recognition = null;
        this.synthesis = window.speechSynthesis;
        this.initRecognition();
    }

    initRecognition() {
        const SpeechRecognition = window.SpeechRecognition || window.webkitSpeechRecognition;
        if (!SpeechRecognition) {
            console.warn("Web Speech API not supported on this browser.");
            return;
        }

        this.recognition = new SpeechRecognition();
        this.recognition.continuous = false;
        this.recognition.interimResults = true;
        this.recognition.lang = 'en-IN';

        this.recognition.onstart = () => {
            this.isListening = true;
            this.updateUIStatus("Listening...");
            this.showWave(true);
        };

        this.recognition.onresult = (event) => {
            let interimTranscript = '';
            let finalTranscript = '';

            for (let i = event.resultIndex; i < event.results.length; ++i) {
                if (event.results[i].isFinal) {
                    finalTranscript += event.results[i][0].transcript;
                } else {
                    interimTranscript += event.results[i][0].transcript;
                }
            }

            if (interimTranscript) {
                this.updateUIStatus(`Listening: "${interimTranscript}"`);
            }

            if (finalTranscript && finalTranscript.trim() !== '') {
                let query = finalTranscript.trim();
                console.log("Recognized final speech:", query);

                const lower = query.toLowerCase();
                if (lower === 'jarvis' || lower === 'hey jarvis' || lower === 'hi jarvis' || lower === 'hello jarvis') {
                    this.updateUIStatus("Yes, I am listening...");
                    this.speakWeb("Yes, sir? How can I help you?");
                    return;
                }

                if (lower.startsWith('jarvis ') || lower.startsWith('hey jarvis ') || lower.startsWith('hi jarvis ')) {
                    query = query.replace(/^jarvis\s+/i, '').replace(/^hey jarvis\s+/i, '').replace(/^hi jarvis\s+/i, '');
                }

                this.updateUIStatus(`Processing: "${query}"`);
                this.handleVoiceInput(query);
            }
        };

        this.recognition.onerror = (event) => {
            console.warn("Speech recognition error:", event.error);
            if (event.error === 'not-allowed') {
                this.stop();
                alert("Microphone access was denied. Please allow microphone permissions.");
                return;
            }
            if (this.isActive && !this.isSpeaking) {
                setTimeout(() => this.startListening(), 1000);
            }
        };

        this.recognition.onend = () => {
            this.isListening = false;
            if (this.isActive && !this.isSpeaking) {
                // Keep listening loop active in hands-free mode
                setTimeout(() => {
                    if (this.isActive && !this.isSpeaking) {
                        this.startListening();
                    }
                }, 500);
            }
        };
    }

    start() {
        this.isActive = true;
        $("#voiceToggleLabel").text("On");
        $("#MicBtn").addClass("handsfree-active");
        this.startListening();
    }

    stop() {
        this.isActive = false;
        this.isListening = false;
        $("#voiceToggleLabel").text("Off");
        $("#MicBtn").removeClass("handsfree-active");
        if (this.recognition) {
            try { this.recognition.stop(); } catch (e) {}
        }
        this.showWave(false);
        this.updateUIStatus("Hello, I am Jarvis");
    }

    toggle() {
        if (this.isActive) {
            this.stop();
        } else {
            this.start();
        }
    }

    startListening() {
        if (!this.recognition || this.isListening || this.isSpeaking) return;
        try {
            this.recognition.start();
        } catch (e) {
            console.warn("Could not start recognition:", e);
        }
    }

    handleVoiceInput(query) {
        if (!query) return;

        // If Eel is connected, pass to backend allCommands
        if (typeof eel !== 'undefined' && typeof eel.allCommands === 'function') {
            $("#Oval").attr("hidden", true);
            $("#SiriWave").attr("hidden", false);
            this.updateUIStatus("Thinking...");
            eel.allCommands(query);
        } else {
            // Standalone web mode fallback
            appendChatMessage("user", query);
            this.updateUIStatus("Thinking...");
            fetch('/api/chat', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ message: query })
            })
            .then(res => res.json())
            .then(data => {
                if (data.status === 'success') {
                    appendChatMessage("assistant", data.reply);
                    this.speakWeb(data.reply);
                } else {
                    this.speakWeb("Sorry, I could not process that request.");
                }
            })
            .catch(err => {
                console.error("Chat API error:", err);
                this.speakWeb("I encountered a connection problem.");
            });
        }
    }

    speakWeb(text) {
        if (!this.synthesis) return;
        this.isSpeaking = true;
        if (this.recognition) {
            try { this.recognition.stop(); } catch(e) {}
        }

        const utterance = new SpeechSynthesisUtterance(text);
        utterance.rate = 1.0;
        utterance.pitch = 1.0;

        utterance.onstart = () => {
            this.updateUIStatus(text);
            this.showWave(true);
        };

        utterance.onend = () => {
            this.isSpeaking = false;
            if (this.isActive) {
                this.updateUIStatus("Listening...");
                setTimeout(() => this.startListening(), 400);
            } else {
                this.showWave(false);
                this.updateUIStatus("Hello, I am Jarvis");
            }
        };

        utterance.onerror = () => {
            this.isSpeaking = false;
            if (this.isActive) {
                setTimeout(() => this.startListening(), 500);
            }
        };

        this.synthesis.speak(utterance);
    }

    updateUIStatus(status) {
        $(".siri-status").text(status);
        if (typeof DisplayMessage === 'function') {
            DisplayMessage(status);
        }
    }

    showWave(show) {
        if (show) {
            $("#Oval").attr("hidden", true);
            $("#SiriWave").attr("hidden", false);
        } else {
            $("#Oval").attr("hidden", false);
            $("#SiriWave").attr("hidden", true);
        }
    }
}

// Global Voice Manager Instance
const voiceManager = new RealtimeVoiceManager();
