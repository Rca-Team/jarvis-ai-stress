import os
import subprocess
import eel

from engine.features import *
from engine.command import *
from engine.auth import recoganize

_is_authenticated = True

def start():
    global _is_authenticated
    _is_authenticated = True

    eel.init("www")

    playAssistantSound()

    @eel.expose
    def init():
        global _is_authenticated
        _is_authenticated = True
        print("[Jarvis Startup]: Direct Access enabled (Face Authentication disabled).")

        def _direct_launch():
            time.sleep(0.1)
            try:
                eel.skipToDashboard()()
            except Exception:
                try:
                    eel.skipToDashboard()
                except Exception:
                    try:
                        eel.hideLoader()
                        eel.hideFaceAuth()
                        eel.hideFaceAuthSuccess()
                        eel.hideStart()
                    except Exception:
                        pass

            speak("Hello, Welcome Sir, How can I help you today?")
            playAssistantSound()

            # Start Realtime 24/7 Global Hotkeys and Hotword listeners
            try:
                start_background_listeners()
            except Exception as e:
                print(f"[Jarvis Startup]: Notice starting listeners: {e}")

            # Start AI Stress Monitor
            try:
                from engine.stress_monitor import stress_engine
                stress_engine.start()
            except Exception as se:
                print(f"[Jarvis Startup]: Notice starting stress engine: {se}")

        threading.Thread(target=_direct_launch, daemon=True).start()

    @eel.expose
    def retry_auth():
        init()

    os.system('start msedge.exe --app="http://localhost:8000/index.html"')

    eel.start('index.html', mode=None, host='localhost', block=True)