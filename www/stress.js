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
        });
    }

    toggleCameraMonitor(enable) {
        if (typeof eel !== 'undefined' && eel.start_stress_monitor) {
            if (enable) {
                eel.start_stress_monitor()(res => this.handleToggleResponse(res));
            } else {
                eel.stop_stress_monitor()(res => this.handleToggleResponse(res));
            }
        } else {
            fetch('/api/stress/toggle', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ action: enable ? 'start' : 'stop' })
            })
            .then(res => res.json())
            .then(data => this.handleToggleResponse(data))
            .catch(err => console.error("Stress toggle error:", err));
        }
    }

    handleToggleResponse(res) {
        const isActive = (res && (res.active === true || res.status === 'success'));
        $("#stressCameraToggle").prop("checked", isActive);
        if (isActive) {
            $("#camStatusBadge").text("Cam Active").removeClass("bg-secondary").addClass("bg-success");
        } else {
            $("#camStatusBadge").text("Cam Off").removeClass("bg-success").addClass("bg-secondary");
        }
        this.fetchStatus();
    }

    startPolling() {
        this.fetchStatus();
        this.pollInterval = setInterval(() => this.fetchStatus(), 500);
    }

    fetchStatus() {
        if (typeof eel !== 'undefined' && eel.get_stress_status) {
            eel.get_stress_status()(status => {
                if (status) this.updateUI(status);
            });
        } else {
            fetch('/api/stress/status')
                .then(res => res.json())
                .then(data => {
                    if (data.status === 'success' && data.data) {
                        this.updateUI(data.data);
                    }
                })
                .catch(() => {});
        }
    }

    updateUI(status) {
        this.currentStatus = status;
        const score = Math.max(0, Math.min(100, status.score || 20));
        const state = status.state || "Calm & Relaxed";
        const advice = status.advice || "Keep breathing steady.";
        const isActive = status.active === true;
        const faceDetected = status.face_detected === true;

        $("#stressCameraToggle").prop("checked", isActive);
        if (isActive) {
            $("#camStatusBadge").text(faceDetected ? "Face Locked" : "Scanning...")
                .removeClass("bg-secondary bg-warning bg-success")
                .addClass(faceDetected ? "bg-success" : "bg-warning");
        } else {
            $("#camStatusBadge").text("Cam Off").removeClass("bg-success bg-warning").addClass("bg-secondary");
        }

        // Update live camera feed
        const liveFeed = document.getElementById("liveCamFeed");
        if (liveFeed) {
            if (isActive) {
                const expectedSrc = "/api/stress/video_feed";
                if (!liveFeed.src || !liveFeed.src.endsWith(expectedSrc)) {
                    liveFeed.src = expectedSrc;
                }
                liveFeed.style.display = "block";
                $("#liveCamPlaceholder").hide();
            } else {
                liveFeed.src = "";
                liveFeed.style.display = "none";
                $("#liveCamPlaceholder").show();
            }
        }

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
            $("#stressAlertText").text(`Elevated stress detected (${score}% > 40%). Auto relief active.`);

            // Automatically open Relief Center modal if stress is > 40% (with 60-second cooldown)
            const now = Date.now();
            if ((now - this.lastAutoHelpTime > 60000) && !$('#reliefModal').hasClass('show')) {
                this.lastAutoHelpTime = now;
                console.log(`[Auto Stress Help]: Stress is ${score}% (> 40%). Launching Relief Modal...`);
                $('#reliefModal').modal('show');
                if (typeof eel !== 'undefined' && eel.trigger_relief_intervention) {
                    eel.trigger_relief_intervention();
                }
            }
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

// Global Instances
let stressHUD = null;
let boxBreathing = null;
let ambientSound = null;

$(document).ready(function () {
    stressHUD = new StressHUDManager();
    boxBreathing = new BoxBreathingEngine();
    ambientSound = new AmbientSoundGenerator();
});
