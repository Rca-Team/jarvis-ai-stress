/**
 * Jarvis AI - Stress Monitor HUD, Guided Box Breathing & Procedural Ambient Sound Generator
 */

class StressHUDManager {
    constructor() {
        this.pollInterval = null;
        this.currentStatus = { active: false, score: 20, state: "Relaxed", advice: "Normal" };
        this.lastAutoHelpTime = 0;
        this.init();
    }

    init() {
        this.startPolling();
        this.bindEvents();
    }

    bindEvents() {
        // Camera Monitor Switch
        $("#stressCameraToggle").change((e) => {
            const shouldStart = $(e.currentTarget).is(":checked");
            this.toggleCameraMonitor(shouldStart);
        });

        // Relief button click opens Relief Modal
        $("#ReliefBtn, #hudReliefBtn, #quickReliefAlertBtn").click(() => {
            $("#reliefModal").modal("show");
            if (typeof eel !== 'undefined' && eel.trigger_relief_intervention) {
                eel.trigger_relief_intervention();
            }
        });

        // Refresh status when modal opens
        $('#reliefModal').on('shown.bs.modal', () => {
            this.updateModalAdvice();
            this.checkCamFeedVisibility();
        });
        $('#reliefModal').on('hidden.bs.modal', () => {
            this.stopCamFeed();
        });
        $(document).on('shown.bs.tab', () => {
            this.checkCamFeedVisibility();
        });
    }

    checkCamFeedVisibility() {
        const liveFeed = document.getElementById("liveCamFeed");
        const liveTab = document.getElementById("liveCamContent");
        const modal = document.getElementById("reliefModal");
        const isModalOpen = modal && ($(modal).hasClass("show") || $(modal).is(":visible"));
        const isTabActive = liveTab && (liveTab.classList.contains("active") || $(liveTab).hasClass("show"));
        const isActive = this.currentStatus && this.currentStatus.active === true;

        if (liveFeed) {
            if (isActive && isModalOpen && isTabActive) {
                const expectedSrc = "/api/stress/video_feed";
                if (!liveFeed.src || !liveFeed.src.endsWith(expectedSrc)) {
                    liveFeed.src = expectedSrc;
                }
                liveFeed.style.display = "block";
                $("#liveCamPlaceholder").hide();
            } else {
                if (liveFeed.src && liveFeed.src !== "") {
                    liveFeed.src = "";
                }
                liveFeed.style.display = "none";
                $("#liveCamPlaceholder").show();
            }
        }
    }

    stopCamFeed() {
        const liveFeed = document.getElementById("liveCamFeed");
        if (liveFeed && liveFeed.src) {
            liveFeed.src = "";
            liveFeed.style.display = "none";
            $("#liveCamPlaceholder").show();
        }
    }

    startPolling() {
        this.fetchStatus();
        if (this.pollInterval) clearInterval(this.pollInterval);
        this.pollInterval = setInterval(() => this.fetchStatus(), 1200);
    }

    fetchStatus() {
        if (this.isFetching) return;
        this.isFetching = true;

        if (typeof eel !== 'undefined' && eel.get_stress_status) {
            eel.get_stress_status()(status => {
                this.isFetching = false;
                if (status) this.updateUI(status);
            });
        } else {
            fetch('/api/stress/status')
                .then(res => res.json())
                .then(data => {
                    this.isFetching = false;
                    if (data.status === 'success' && data.data) {
                        this.updateUI(data.data);
                    }
                })
                .catch(() => {
                    this.isFetching = false;
                });
        }
    }

    updateUI(status) {
        if (!status) return;
        this.currentStatus = status;
        const score = Math.max(0, Math.min(100, status.score || 20));
        const state = status.state || "Calm & Relaxed";
        const advice = status.advice || "Keep breathing steady.";
        const isActive = status.active === true;
        const faceDetected = status.face_detected === true;

        // Skip DOM thrashing if status has not changed
        if (this._lastScore === score && this._lastState === state && 
            this._lastActive === isActive && this._lastFace === faceDetected && 
            this._lastAdvice === advice) {
            return;
        }
        this._lastScore = score;
        this._lastState = state;
        this._lastActive = isActive;
        this._lastFace = faceDetected;
        this._lastAdvice = advice;

        $("#stressCameraToggle").prop("checked", isActive);
        if (isActive) {
            $("#camStatusBadge").text(faceDetected ? "Face Locked" : "Scanning...")
                .removeClass("bg-secondary bg-warning bg-success")
                .addClass(faceDetected ? "bg-success" : "bg-warning");
        } else {
            $("#camStatusBadge").text("Cam Off").removeClass("bg-success bg-warning").addClass("bg-secondary");
        }

        // On-demand camera feed check
        this.checkCamFeedVisibility();

        // Update HUD Gauge with smooth CSS transition
        $("#stressScoreVal").text(`${score}%`);
        $("#stressStateBadge").text(state);
        $("#stressAdviceTooltip").attr("title", advice);

        // Color coding & Automatic Help when stress > 40
        let color = "#00e676"; // Green
        let badgeClass = "badge bg-success";

        if (score > 40) {
            if (score > 70) {
                color = "#ff1744"; // Crimson Red
                badgeClass = "badge bg-danger";
            } else {
                color = "#ff9100"; // Orange
                badgeClass = "badge bg-warning text-dark";
            }

            $("#stressAlertBanner").removeClass("d-none");
            $("#stressAlertText").text(`Elevated stress detected (${score}%). Ask Jarvis for relief.`);
            // Passive monitoring: Modal and speech alerts are triggered only when user requests them.
        } else if (score > 25) {
            color = "#00e5ff"; // Cyan
            badgeClass = "badge bg-info text-dark";
            $("#stressAlertBanner").addClass("d-none");
        } else {
            $("#stressAlertBanner").addClass("d-none");
        }

        $("#stressGaugeBar").css({
            "width": `${score}%`,
            "background-color": color,
            "box-shadow": `0 0 10px ${color}`,
            "transition": "width 0.4s cubic-bezier(0.4,0,0.2,1), background-color 0.4s ease"
        });
        $("#stressStateBadge").attr("class", badgeClass);

        // Update Bottom HUD Deck Biometrics Card
        $("#deckStressVal").text(`${score}%`);
        $("#deckStressBadge").attr("class", badgeClass).text(state);
        $("#deckStressProgress").css({
            "width": `${score}%`,
            "background-color": color
        });
        $("#deckCameraLabel").html(isActive 
            ? '<i class="bi bi-camera-video-fill text-success me-1"></i>Cam Active' 
            : '<i class="bi bi-camera-video me-1"></i>Cam Off');

        this.updateModalAdvice();
    }

    updateModalAdvice() {
        $("#modalStressScore").text(`${this.currentStatus.score || 20}%`);
        $("#modalStressState").text(this.currentStatus.state || "Normal");
        $("#modalStressAdvice").text(this.currentStatus.advice || "Stay relaxed and breathe deeply.");
        // Update live camera tab badges
        $(".livecam-score").text(this.currentStatus.score || "--");
        $(".livecam-state").text(this.currentStatus.state || "--");
    }
}

// ---------------------------------------------------------------------------
// Guided Box Breathing Visualizer (Inhale 4s -> Hold 4s -> Exhale 4s -> Hold 4s)
// ---------------------------------------------------------------------------
class BoxBreathingEngine {
    constructor() {
        this.isRunning = false;
        this.currentPhase = 0; // 0: Inhale, 1: Hold, 2: Exhale, 3: Hold
        this.phases = [
            { name: "Inhale Slowly", duration: 4, action: "expand", prompt: "Deep breath in through your nose..." },
            { name: "Hold Breath", duration: 4, action: "hold-max", prompt: "Keep lungs full and relax your shoulders..." },
            { name: "Exhale Gently", duration: 4, action: "contract", prompt: "Release all air through your mouth..." },
            { name: "Hold Breath", duration: 4, action: "hold-min", prompt: "Rest calmly before the next cycle..." }
        ];
        this.secondsRemaining = 4;
        this.completedCycles = 0;
        this.timer = null;
        this.audioCtx = null;
        this.bindEvents();
    }

    bindEvents() {
        $("#startBreathingBtn").click(() => this.toggle());
        $("#resetBreathingBtn").click(() => this.reset());
        $("#hudCooldownBtn, #quickReliefAlertBtn, #quick2mCalmBtn").click(() => this.startTwoMinuteCoolDown());
    }

    initAudio() {
        if (!this.audioCtx) {
            const AudioContext = window.AudioContext || window.webkitAudioContext;
            if (AudioContext) {
                this.audioCtx = new AudioContext();
            }
        }
    }

    playChime(freq = 440) {
        try {
            this.initAudio();
            if (!this.audioCtx) return;
            const osc = this.audioCtx.createOscillator();
            const gain = this.audioCtx.createGain();

            osc.type = "sine";
            osc.frequency.setValueAtTime(freq, this.audioCtx.currentTime);
            gain.gain.setValueAtTime(0.15, this.audioCtx.currentTime);
            gain.gain.exponentialRampToValueAtTime(0.001, this.audioCtx.currentTime + 0.8);

            osc.connect(gain);
            gain.connect(this.audioCtx.destination);

            osc.start();
            osc.stop(this.audioCtx.currentTime + 0.8);
        } catch (e) {}
    }

    toggle() {
        if (this.isRunning) {
            this.pause();
        } else {
            this.start();
        }
    }

    start() {
        this.initAudio();
        this.isRunning = true;
        $("#startBreathingBtn").html('<i class="bi bi-pause-fill"></i> Pause');
        this.runStep();
    }

    pause() {
        this.isRunning = false;
        clearInterval(this.timer);
        $("#startBreathingBtn").html('<i class="bi bi-play-fill"></i> Resume');
        $("#breathingPhaseTitle").text("Paused");
    }

    reset() {
        this.pause();
        this.currentPhase = 0;
        this.secondsRemaining = 4;
        this.completedCycles = 0;
        $("#startBreathingBtn").html('<i class="bi bi-play-fill"></i> Start Breathing');
        $("#breathingPhaseTitle").text("Ready to Begin");
        $("#breathingInstruction").text("Click Start to begin 4-4-4-4 Box Breathing.");
        $("#breathingCountdown").text("4");
        $("#completedCyclesCount").text("0");
        $("#breathingCircle").removeClass("circle-expand circle-contract circle-hold");
    }

    runStep() {
        clearInterval(this.timer);
        const phase = this.phases[this.currentPhase];
        this.secondsRemaining = phase.duration;

        $("#breathingPhaseTitle").text(phase.name);
        $("#breathingInstruction").text(phase.prompt);
        $("#breathingCountdown").text(this.secondsRemaining);

        // Animate visual circle
        const circle = $("#breathingCircle");
        circle.removeClass("circle-expand circle-contract circle-hold");
        if (phase.action === "expand") {
            circle.addClass("circle-expand");
            this.playChime(528); // 528 Hz Solfeggio frequency for clarity
        } else if (phase.action === "contract") {
            circle.addClass("circle-contract");
            this.playChime(396); // 396 Hz for grounding
        } else {
            circle.addClass("circle-hold");
            this.playChime(440);
        }

        this.timer = setInterval(() => {
            this.secondsRemaining--;
            if (this.secondsRemaining > 0) {
                $("#breathingCountdown").text(this.secondsRemaining);
            } else {
                // Next phase
                this.currentPhase = (this.currentPhase + 1) % this.phases.length;
                if (this.currentPhase === 0) {
                    this.completedCycles++;
                    $("#completedCyclesCount").text(this.completedCycles);
                }
                this.runStep();
            }
        }, 1000);
    }

    startTwoMinuteCoolDown() {
        // Open Relief Modal on breathing tab
        $('#reliefModal').modal('show');
        $('#breathing-tab').tab('show');

        this.reset();
        this.isTwoMinMode = true;
        this.twoMinRemaining = 120; // 2-minute countdown

        // Start soothing rain audio if available
        if (typeof ambientSound !== 'undefined' && ambientSound) {
            const btn = $('.ambient-toggle[data-sound="rain"]');
            if (!ambientSound.activeSounds.rain) {
                ambientSound.toggleSound("rain", btn);
            }
        }

        $("#breathingInstruction").html('<span class="text-warning fw-bold"><i class="bi bi-stopwatch-fill me-1"></i>2-Minute Cool Down Active:</span> Inhale 4s, Hold 4s, Exhale 4s, Hold 4s. Release all academic tension.');
        $("#startBreathingBtn").html('<i class="bi bi-stopwatch-fill me-1"></i>Cool Down (2:00)');
        this.start();

        clearInterval(this.twoMinTimer);
        this.twoMinTimer = setInterval(() => {
            if (!this.isRunning) return;
            this.twoMinRemaining--;
            const mins = Math.floor(this.twoMinRemaining / 60);
            const secs = this.twoMinRemaining % 60;
            const timeStr = `${mins}:${String(secs).padStart(2, '0')}`;
            $("#startBreathingBtn").html(`<i class="bi bi-stopwatch-fill me-1"></i>Cool Down (${timeStr})`);

            if (this.twoMinRemaining <= 0) {
                clearInterval(this.twoMinTimer);
                this.isTwoMinMode = false;
                this.pause();
                this.playChime(528);
                $("#breathingInstruction").html('<span class="text-success fw-bold"><i class="bi bi-check-circle-fill me-1"></i>2-Minute Cool Down Complete!</span> Your stress index is lowered and your mind is refreshed.');
                $("#startBreathingBtn").html('<i class="bi bi-play-fill"></i> Start Breathing');
            }
        }, 1000);
    }
}

// ---------------------------------------------------------------------------
// Web Audio Ambient Relaxation Sound Generator (Rain, Ocean Waves, Alpha 10Hz)
// ---------------------------------------------------------------------------
class AmbientSoundGenerator {
    constructor() {
        this.audioCtx = null;
        this.activeSounds = {
            rain: null,
            ocean: null,
            alpha: null
        };
        this.bindEvents();
    }

    initAudio() {
        if (!this.audioCtx) {
            const AudioContext = window.AudioContext || window.webkitAudioContext;
            if (AudioContext) {
                this.audioCtx = new AudioContext();
            }
        }
    }

    bindEvents() {
        $(".ambient-toggle").click((e) => {
            const btn = $(e.currentTarget);
            const soundType = btn.data("sound");
            this.toggleSound(soundType, btn);
        });

        $(".ambient-vol").on("input", (e) => {
            const slider = $(e.currentTarget);
            const soundType = slider.data("sound");
            const val = parseFloat(slider.val());
            this.setVolume(soundType, val);
        });
    }

    toggleSound(type, btn) {
        this.initAudio();
        if (this.activeSounds[type]) {
            // Stop sound
            this.stopSound(type);
            btn.removeClass("btn-info").addClass("btn-outline-info").html('<i class="bi bi-play-circle me-1"></i>Play');
        } else {
            // Start sound
            this.startSound(type);
            btn.removeClass("btn-outline-info").addClass("btn-info").html('<i class="bi bi-stop-circle me-1"></i>Stop');
        }
    }

    startSound(type) {
        if (!this.audioCtx) return;

        if (type === "rain") {
            // Pink noise generator with low-pass filter
            const bufferSize = 2 * this.audioCtx.sampleRate;
            const noiseBuffer = this.audioCtx.createBuffer(1, bufferSize, this.audioCtx.sampleRate);
            const output = noiseBuffer.getChannelData(0);
            let b0 = 0, b1 = 0, b2 = 0, b3 = 0, b4 = 0, b5 = 0, b6 = 0;
            for (let i = 0; i < bufferSize; i++) {
                const white = Math.random() * 2 - 1;
                b0 = 0.99886 * b0 + white * 0.0555179;
                b1 = 0.99332 * b1 + white * 0.0750759;
                b2 = 0.96900 * b2 + white * 0.1538520;
                b3 = 0.86650 * b3 + white * 0.3104856;
                b4 = 0.55000 * b4 + white * 0.5329522;
                b5 = -0.7616 * b5 - white * 0.0168980;
                output[i] = (b0 + b1 + b2 + b3 + b4 + b5 + b6 + white * 0.5362) * 0.11;
                b6 = white * 0.115926;
            }

            const whiteNoise = this.audioCtx.createBufferSource();
            whiteNoise.buffer = noiseBuffer;
            whiteNoise.loop = true;

            const filter = this.audioCtx.createBiquadFilter();
            filter.type = "lowpass";
            filter.frequency.setValueAtTime(1200, this.audioCtx.currentTime);

            const gain = this.audioCtx.createGain();
            const vol = parseFloat($("#rainVol").val() || 0.5);
            gain.gain.setValueAtTime(vol * 0.6, this.audioCtx.currentTime);

            whiteNoise.connect(filter);
            filter.connect(gain);
            gain.connect(this.audioCtx.destination);
            whiteNoise.start();

            this.activeSounds.rain = { source: whiteNoise, gain: gain };

        } else if (type === "ocean") {
            // Modulated ocean noise waves
            const bufferSize = 4 * this.audioCtx.sampleRate;
            const noiseBuffer = this.audioCtx.createBuffer(1, bufferSize, this.audioCtx.sampleRate);
            const output = noiseBuffer.getChannelData(0);
            for (let i = 0; i < bufferSize; i++) {
                output[i] = (Math.random() * 2 - 1) * 0.3;
            }

            const noise = this.audioCtx.createBufferSource();
            noise.buffer = noiseBuffer;
            noise.loop = true;

            const filter = this.audioCtx.createBiquadFilter();
            filter.type = "bandpass";
            filter.frequency.setValueAtTime(450, this.audioCtx.currentTime);
            filter.Q.setValueAtTime(1.5, this.audioCtx.currentTime);

            // LFO for wave modulation
            const lfo = this.audioCtx.createOscillator();
            lfo.frequency.setValueAtTime(0.12, this.audioCtx.currentTime); // 8-second wave cycle
            const lfoGain = this.audioCtx.createGain();
            lfoGain.gain.setValueAtTime(300, this.audioCtx.currentTime);
            lfo.connect(lfoGain);
            lfoGain.connect(filter.frequency);

            const gain = this.audioCtx.createGain();
            const vol = parseFloat($("#oceanVol").val() || 0.5);
            gain.gain.setValueAtTime(vol * 0.7, this.audioCtx.currentTime);

            noise.connect(filter);
            filter.connect(gain);
            gain.connect(this.audioCtx.destination);

            noise.start();
            lfo.start();

            this.activeSounds.ocean = { source: noise, lfo: lfo, gain: gain };

        } else if (type === "alpha") {
            // 10 Hz Binaural Alpha beat (200 Hz Left, 210 Hz Right)
            const merger = this.audioCtx.createChannelMerger(2);
            const oscL = this.audioCtx.createOscillator();
            const oscR = this.audioCtx.createOscillator();

            oscL.frequency.setValueAtTime(200, this.audioCtx.currentTime);
            oscR.frequency.setValueAtTime(210, this.audioCtx.currentTime);

            const gain = this.audioCtx.createGain();
            const vol = parseFloat($("#alphaVol").val() || 0.5);
            gain.gain.setValueAtTime(vol * 0.25, this.audioCtx.currentTime);

            oscL.connect(merger, 0, 0);
            oscR.connect(merger, 0, 1);
            merger.connect(gain);
            gain.connect(this.audioCtx.destination);

            oscL.start();
            oscR.start();

            this.activeSounds.alpha = { oscL: oscL, oscR: oscR, gain: gain };
        }
    }

    setVolume(type, val) {
        if (this.activeSounds[type] && this.activeSounds[type].gain) {
            const mult = (type === 'alpha' ? 0.3 : 0.7);
            this.activeSounds[type].gain.gain.setValueAtTime(val * mult, this.audioCtx.currentTime);
        }
    }

    stopSound(type) {
        const sound = this.activeSounds[type];
        if (sound) {
            try {
                if (sound.source) sound.source.stop();
                if (sound.lfo) sound.lfo.stop();
                if (sound.oscL) sound.oscL.stop();
                if (sound.oscR) sound.oscR.stop();
            } catch (e) {}
            this.activeSounds[type] = null;
        }
    }
}

// Student Exam Stress & Pomodoro Manager
class ExamStressManager {
    constructor() {
        this.timer = null;
        this.timeLeft = 25 * 60; // 25 minutes
        this.isRunning = false;
        this.bindEvents();
    }

    bindEvents() {
        // AI Advice Button
        $("#getExamAdviceBtn").click(() => {
            const subject = $("#examSubjectInput").val().trim() || "my upcoming exam";
            this.fetchExamAdvice(subject);
        });

        // 2-Min Emergency Calm Button
        $("#quick2mCalmBtn").click(() => {
            $("#examAdviceText").text("Emergency 2-minute calming activated. Inhale 4s, hold 7s, exhale 8s. Lo-Fi rain sound started.");
            if (typeof ambientSound !== 'undefined' && ambientSound) {
                const btn = $('.ambient-toggle[data-sound="rain"]');
                if (!ambientSound.activeSounds.rain) {
                    ambientSound.toggleSound("rain", btn);
                }
            }
            $("#breathing-tab").trigger("click");
            if (typeof boxBreathing !== 'undefined' && boxBreathing) {
                boxBreathing.start();
            }
        });

        // Active Recall Tip Button
        $("#quickActiveRecallBtn").click(() => {
            const tips = [
                "Feynman Technique: Explain this chapter out loud in simple words without looking at the book.",
                "Blurting Method: Spend 5 minutes writing everything you remember from memory on a blank page, then check your gaps in red ink.",
                "Flashcard 3-Box Rule: Test difficult questions daily, medium questions every 3 days, and easy questions weekly.",
                "Interleaving: Don't spend 6 hours on one subject. Switch topics every 50 minutes to keep neural connections sharp."
            ];
            const chosen = tips[Math.floor(Math.random() * tips.length)];
            $("#examAdviceText").html(`<strong>Active Recall Strategy:</strong> ${chosen}`);
        });

        // Pomodoro Timer Controls
        $("#pomodoroStartBtn").click(() => this.startPomodoro());
        $("#pomodoroPauseBtn").click(() => this.pausePomodoro());
        $("#pomodoroResetBtn").click(() => this.resetPomodoro());

        // Modal Note Saver
        $("#modalSaveNoteBtn").click(() => {
            const note = $("#modalQuickNoteInput").val().trim();
            if (!note) return;
            if (typeof eel !== 'undefined' && eel.eel_take_study_note) {
                eel.eel_take_study_note(note);
            } else {
                fetch('/api/student/study_note', {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({ note: note })
                });
            }
            $("#modalQuickNoteInput").val("");
            $("#modalQuickNoteInput").attr("placeholder", "Saved to Notepad!");
            setTimeout(() => {
                $("#modalQuickNoteInput").attr("placeholder", "Type key reminder...");
            }, 2500);
        });
    }

    fetchExamAdvice(subject) {
        $("#examAdviceText").html('<div class="spinner-border spinner-border-sm text-info me-2"></div>Generating tailored cognitive relief strategy...');
        if (typeof eel !== 'undefined' && eel.get_exam_relief_guidance) {
            eel.get_exam_relief_guidance(subject)(res => {
                if (res && res.advice) {
                    const formatted = res.advice.replace(/\n/g, '<br>');
                    $("#examAdviceText").html(formatted);
                }
            });
        } else {
            fetch('/api/student/exam_relief', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ subject: subject })
            })
            .then(r => r.json())
            .then(d => {
                if (d.status === 'success' && d.data && d.data.advice) {
                    const formatted = d.data.advice.replace(/\n/g, '<br>');
                    $("#examAdviceText").html(formatted);
                }
            })
            .catch(() => {
                $("#examAdviceText").text("Exam anxiety is normal. Take 3 deep breaths. Break your revision into small 10-minute micro-goals.");
            });
        }
    }

    startPomodoro() {
        if (this.isRunning) return;
        this.isRunning = true;
        $("#pomodoroStateLabel").text("Focus Session Active");
        $("#pomodoroBadge").text("Focusing...").removeClass("bg-warning").addClass("bg-success");
        this.timer = setInterval(() => {
            if (this.timeLeft > 0) {
                this.timeLeft--;
                this.updatePomodoroDisplay();
            } else {
                this.completePomodoro();
            }
        }, 1000);
    }

    pausePomodoro() {
        this.isRunning = false;
        clearInterval(this.timer);
        $("#pomodoroStateLabel").text("Session Paused");
        $("#pomodoroBadge").text("Paused").removeClass("bg-success").addClass("bg-warning");
    }

    resetPomodoro() {
        this.pausePomodoro();
        this.timeLeft = 25 * 60;
        this.updatePomodoroDisplay();
        $("#pomodoroStateLabel").text("Ready to Focus");
        $("#pomodoroBadge").text("25m Focus");
    }

    completePomodoro() {
        this.resetPomodoro();
        $("#pomodoroStateLabel").text("Session Complete! Take 5 min break.");
        if (typeof eel !== 'undefined' && eel.playAssistantSound) {
            try { eel.playAssistantSound(); } catch (e) {}
        }
        alert("Study Session Complete! Time for a 5-minute eye and breathing break.");
    }

    updatePomodoroDisplay() {
        const mins = Math.floor(this.timeLeft / 60);
        const secs = this.timeLeft % 60;
        const formatted = `${String(mins).padStart(2, '0')}:${String(secs).padStart(2, '0')}`;
        $("#pomodoroTimeDisplay").text(formatted);
    }
}

// Global Instances
let stressHUD = null;
let boxBreathing = null;
let ambientSound = null;
let examStress = null;

$(document).ready(function () {
    stressHUD = new StressHUDManager();
    boxBreathing = new BoxBreathingEngine();
    ambientSound = new AmbientSoundGenerator();
    examStress = new ExamStressManager();

    window.startTwoMinuteCoolDown = function () {
        if (boxBreathing) {
            boxBreathing.startTwoMinuteCoolDown();
        }
    };

    window.openReliefCenter = function () {
        $('#reliefModal').modal('show');
    };

    if (typeof eel !== 'undefined') {
        eel.expose(window.startTwoMinuteCoolDown, 'ui_start_two_minute_cooldown');
        eel.expose(window.openReliefCenter, 'ui_open_relief_center');
    }
});

