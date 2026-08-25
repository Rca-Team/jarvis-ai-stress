import pyttsx3
import speech_recognition as sr
import eel
import time
import threading

_tts_lock = threading.Lock()

def _get_tts_engine():
    """Get or create a fresh TTS engine with sapi5."""
    try:
        engine = pyttsx3.init('sapi5')
        voices = engine.getProperty('voices')
        if voices:
            engine.setProperty('voice', voices[0].id)
        engine.setProperty('rate', 174)
        return engine
    except Exception as e:
        print(f"TTS init error: {e}")
        return None

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

    # TTS audio playback
    def _speak_thread():
        with _tts_lock:
            try:
                import pythoncom
                pythoncom.CoInitialize()
            except Exception:
                pass
            try:
                eng = _get_tts_engine()
                if eng:
                    eng.say(text)
                    eng.runAndWait()
            except Exception as err:
                print(f"TTS speak error: {err}")

    t = threading.Thread(target=_speak_thread, daemon=True)
    t.start()


def takecommand():
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

            r.pause_threshold = 0.5
            r.energy_threshold = 280
            r.adjust_for_ambient_noise(source, duration=0.3)
            audio = r.listen(source, phrase_time_limit=7, timeout=5)
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
        return query.lower()
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
        query = str(message).strip()
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

    try:
        if "open" in query:
            from engine.features import openCommand
            openCommand(query)
        elif "on youtube" in query:
            from engine.features import PlayYoutube
            PlayYoutube(query)
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
        elif "stress" in query or "relief" in query or "breathing" in query or "relax" in query:
            from engine.features import trigger_relief_intervention, start_stress_monitor, stop_stress_monitor
            if "start" in query or "enable" in query or "turn on" in query:
                start_stress_monitor()
            elif "stop" in query or "disable" in query or "turn off" in query:
                stop_stress_monitor()
            else:
                trigger_relief_intervention()
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