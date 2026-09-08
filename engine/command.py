import win32com.client
import pythoncom
import pyttsx3
import speech_recognition as sr
import eel
import time
import threading

class JarvisVoiceEngine:
    """High-performance Windows SAPI voice engine with instant barge-in interruption."""
    def __init__(self):
        self._lock = threading.Lock()
        self._voice = None
        self._pyttsx_engine = None
        self._init_voice()

    def _init_voice(self):
        try:
            pythoncom.CoInitialize()
            self._voice = win32com.client.Dispatch("SAPI.SpVoice")
            self._voice.Rate = 1  # Natural conversational rate
        except Exception as e:
            print(f"[Jarvis Voice Init Warning]: {e}, falling back to pyttsx3.")
            try:
                self._pyttsx_engine = pyttsx3.init('sapi5')
                voices = self._pyttsx_engine.getProperty('voices')
                if voices:
                    self._pyttsx_engine.setProperty('voice', voices[0].id)
                self._pyttsx_engine.setProperty('rate', 174)
            except Exception:
                pass

    def speak(self, text):
        """Asynchronously speak text. Purges prior speech so output starts immediately."""
        text = str(text).strip()
        if not text:
            return
        try:
            pythoncom.CoInitialize()
            if not self._voice and not self._pyttsx_engine:
                self._init_voice()
            if self._voice:
                # Flag 3 = SVSFPurgeBeforeSpeak (2) | SVSFlagsAsync (1)
                self._voice.Speak(text, 3)
                return
        except Exception as e:
            print(f"[Jarvis Voice Speak Error]: {e}")

        # Fallback to pyttsx3 in daemon thread if SAPI unavailable
        if self._pyttsx_engine:
            def _fallback():
                try:
                    self._pyttsx_engine.say(text)
                    self._pyttsx_engine.runAndWait()
                except Exception:
                    pass
            threading.Thread(target=_fallback, daemon=True).start()

    def stop(self):
        """Instantly interrupt any active speech (barge-in interruption)."""
        try:
            pythoncom.CoInitialize()
            if self._voice:
                # SVSFPurgeBeforeSpeak (2): Purges current speech buffer immediately
                self._voice.Speak("", 2)
        except Exception as e:
            print(f"[Jarvis Voice Stop Error]: {e}")
        if self._pyttsx_engine:
            try:
                self._pyttsx_engine.stop()
            except Exception:
                pass

    def is_speaking(self):
        """Check if Jarvis is actively outputting audio."""
        try:
            if self._voice:
                # 2 = SRSEIsSpeaking
                return self._voice.Status.RunningState == 2
        except Exception:
            pass
        return False

_voice_engine = JarvisVoiceEngine()

@eel.expose
def stop_speaking():
    """Immediately halt any active speech playback (barge-in interruption)."""
    global _voice_engine
    if _voice_engine:
        _voice_engine.stop()
    print("[Jarvis Voice]: Speech interrupted instantly (barge-in).")

def speak(text):
    text = str(text).strip()
    if not text:
        return

    # Update UI immediately so user sees message right away
    try:
        eel.DisplayMessage(text)()
    except Exception:
        try:
            eel.DisplayMessage(text)
        except Exception:
            pass

    try:
        eel.receiverText(text)()
    except Exception:
        try:
            eel.receiverText(text)
        except Exception:
            pass

    try:
        eel.updateSiriStatus(text)()
    except Exception:
        try:
            eel.updateSiriStatus(text)
        except Exception:
            pass

    # Speak asynchronously with instant barge-in support
    global _voice_engine
    if _voice_engine:
        _voice_engine.speak(text)


def takecommand():
    # If Jarvis is currently speaking, stop it instantly so microphone gets clean user input
    global _voice_engine
    if _voice_engine and _voice_engine.is_speaking():
        _voice_engine.stop()
        time.sleep(0.05)

    r = sr.Recognizer()
    try:
        with sr.Microphone() as source:
            print('listening....')
            try:
                eel.DisplayMessage('listening....')()
            except Exception:
                try:
                    eel.DisplayMessage('listening....')
                except Exception:
                    pass
            try:
                eel.updateSiriStatus("Listening...")()
            except Exception:
                try:
                    eel.updateSiriStatus("Listening...")
                except Exception:
                    pass

            # Improved thresholds to prevent cutting words off mid-speech
            r.pause_threshold = 0.8
            r.non_speaking_duration = 0.5
            r.energy_threshold = 300
            r.adjust_for_ambient_noise(source, duration=0.4)
            audio = r.listen(source, phrase_time_limit=8, timeout=6)
    except Exception as mic_err:
        print(f"Microphone listen error: {mic_err}")
        return ""

    try:
        print('recognizing....')
        try:
            eel.DisplayMessage('recognizing....')()
        except Exception:
            try:
                eel.DisplayMessage('recognizing....')
            except Exception:
                pass
        try:
            eel.updateSiriStatus("Recognizing...")()
        except Exception:
            try:
                eel.updateSiriStatus("Recognizing...")
            except Exception:
                pass

        query = r.recognize_google(audio, language='en-in')
        print(f"user said: {query}")
        try:
            eel.DisplayMessage(query)()
        except Exception:
            try:
                eel.DisplayMessage(query)
            except Exception:
                pass
        return query.strip().lower()
    except Exception as e:
        print(f"Recognition error / no speech: {e}")
        return ""

@eel.expose
def allCommands(message=1):
    if message == 1:
        query = takecommand()
        print("Voice query:", query)
        if not query or query.strip() == "":
            speak("I didn't catch that, sir.")
            try:
                eel.ShowHood()()
            except Exception:
                try:
                    eel.ShowHood()
                except Exception:
                    pass
            return
        try:
            eel.senderText(query)()
        except Exception:
            try:
                eel.senderText(query)
            except Exception:
                pass
    else:
        query = str(message).strip().lower()
        if not query:
            try:
                eel.ShowHood()()
            except Exception:
                try:
                    eel.ShowHood()
                except Exception:
                    pass
            return
        try:
            eel.senderText(query)()
        except Exception:
            try:
                eel.senderText(query)
            except Exception:
                pass

    # Clean leading wake words (e.g. "hey jarvis what time is it" -> "what time is it")
    wake_words = ["hey jarvis", "hi jarvis", "hello jarvis", "ok jarvis", "jarvis"]
    for w in wake_words:
        if query.startswith(w):
            query = query[len(w):].strip()
            break

    try:
        # 1. Study Notes Intent
        if any(query.startswith(k) for k in ["take note", "write note", "note down", "add note", "make note"]):
            import re
            note_content = re.sub(r'^(?:take\s+note|write\s+note|note\s+down|add\s+note|make\s+note)(?:\s+that|\s+to|\s*:|\s+)?', '', query).strip()
            if not note_content:
                speak("What would you like me to note down, sir?")
                note_content = takecommand()
            if note_content:
                from engine.features import take_study_note
                take_study_note(note_content)
            else:
                speak("Note creation cancelled.")

        # 2. Screenshot Capture Intent
        elif any(k in query for k in ["take screenshot", "capture screen", "screenshot", "save screen", "screen grab"]):
            from engine.features import capture_study_screenshot
            capture_study_screenshot()

        # 3. System Volume Controls
        elif any(k in query for k in ["volume up", "volume down", "mute", "unmute", "increase volume", "decrease volume", "lower volume"]):
            from engine.features import adjust_system_volume
            adjust_system_volume(query)

        # 4. Media Playback Controls
        elif any(k in query for k in ["pause music", "resume music", "next track", "previous track", "next song", "previous song", "stop music"]):
            from engine.features import manage_media_playback
            manage_media_playback(query)

        # 5. Window & Desktop Management
        elif any(k in query for k in ["minimize all", "show desktop", "minimize windows", "lock screen", "lock workstation"]):
            from engine.features import manage_windows
            manage_windows(query)

        # 6. Study PDF & Lecture Material
        elif any(k in query for k in ["open chapter", "open study pdf", "open notes", "open course book", "open lecture"]):
            from engine.features import open_study_pdf
            open_study_pdf(query)

        # 7. YouTube & Music playback intent
        elif ("play" in query and "youtube" in query) or query.startswith("play ") or "on youtube" in query:
            from engine.features import PlayYoutube
            PlayYoutube(query)

        # 8. Time query intent
        elif any(phrase in query for phrase in ["what time", "current time", "tell me the time", "what's the time", "what is the time"]):
            from datetime import datetime
            time_now = datetime.now().strftime("%I:%M %p")
            speak(f"The current time is {time_now}, sir.")

        # 9. Date / Day query intent
        elif any(phrase in query for phrase in ["what date", "current date", "today's date", "what is the date", "which day is today", "what day is it"]):
            from datetime import datetime
            date_now = datetime.now().strftime("%A, %B %d, %Y")
            speak(f"Today is {date_now}, sir.")

        # 10. Open applications or URLs (Universal Scanner)
        elif "open" in query or "launch" in query:
            from engine.features import openCommand
            openCommand(query)

        # 11. Contacts & Messaging
        elif "send message" in query or "phone call" in query or "video call" in query:
            from engine.features import findContact, whatsApp, makeCall, sendMessage
            contact_no, name = findContact(query)
            if contact_no != 0:
                speak("Which mode would you like to use, WhatsApp or mobile?")
                preference = takecommand()
                if "mobile" in preference:
                    if "send message" in query or "send sms" in query: 
                        speak("What message would you like to send?")
                        msg_text = takecommand()
                        sendMessage(msg_text, contact_no, name)
                    elif "phone call" in query:
                        makeCall(name, contact_no)
                    else:
                        speak("Please try again.")
                elif "whatsapp" in preference:
                    flag = 'message' if "send message" in query else ('call' if "phone call" in query else 'video call')
                    speak("What message would you like to send?")
                    msg_text = takecommand()
                    whatsApp(contact_no, msg_text, flag, name)
            else:
                speak("I could not find that contact in your database, sir.")

        # 12. 2-Minute Stress Cool Down Intent
        elif any(k in query for k in ["cool down", "2 min cool down", "2 minute cool down", "two minute cool down", "cooldown", "calm down", "emergency calm", "take a break"]):
            from engine.features import start_two_minute_cooldown
            start_two_minute_cooldown()

        # 13. Explicit Stress Level & Suggestion Query (Triggered ONLY when user queries for it)
        elif any(k in query for k in ["what is my stress", "what's my stress", "how stressed am i", "check my stress", "am i stressed", "stress level", "stress report", "give suggestion", "give me suggestion", "stress suggestion", "stress advice"]):
            from engine.features import report_stress_and_suggestions
            report_stress_and_suggestions()

        # 14. Exam Stress Counseling & Relief
        elif any(k in query for k in ["exam stress", "exam anxiety", "panic", "stressed about", "anxious", "can't focus", "burnout", "study burnout", "tired from study"]):
            from engine.features import get_exam_relief_guidance, trigger_relief_intervention
            trigger_relief_intervention(speak_alert=False)
            guidance = get_exam_relief_guidance(query)
            clean_speech = guidance.get("advice", "").replace("•", "").replace("**", "")
            speak(f"I hear you, sir. Let us reset. {clean_speech}")

        # 15. Camera Stress Monitor Toggle / General Relief
        elif any(k in query for k in ["stress monitor", "camera monitor"]):
            from engine.features import start_stress_monitor, stop_stress_monitor
            if any(w in query for w in ["stop", "disable", "turn off"]):
                stop_stress_monitor()
            else:
                start_stress_monitor()

        elif any(k in query for k in ["relief", "breathing", "relax"]):
            from engine.features import start_two_minute_cooldown
            start_two_minute_cooldown()

        # 16. Conversational Chatbot (Gemini + Local Academic Mentor)
        else:
            from engine.features import chatBot
            chatBot(query)

    except Exception as e:
        print(f"Command error: {e}")
        speak("I encountered an issue processing that command, sir.")

    # Return back to main dashboard with smooth transition
    time.sleep(0.4)
    try:
        eel.ShowHood()()
    except Exception:
        try:
            eel.ShowHood()
        except Exception:
            pass