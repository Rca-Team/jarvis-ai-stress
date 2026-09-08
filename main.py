import os
import subprocess
import eel

from engine.features import *
from engine.command import *
from engine.auth import recoganize

_is_authenticated = False

def start():
    global _is_authenticated
    _is_authenticated = False

    eel.init("www")

    playAssistantSound()

    @eel.expose
    def init():
        global _is_authenticated
        import shutil
        if shutil.which('adb') and os.path.exists('device.bat'):
            try:
                subprocess.Popen([r'device.bat'], shell=True)
            except Exception:
                pass

        eel.hideLoader()
        speak("Ready for Face Authentication")
        flag = recoganize.AuthenticateFace()

        if flag == 1:
            _is_authenticated = True
            eel.hideFaceAuth()
            speak("Face Authentication Successful")
            eel.hideFaceAuthSuccess()
            speak("Hello, Welcome Sir, How can I help you today?")
            eel.hideStart()
            playAssistantSound()

            # Start Realtime 24/7 Global Hotkeys and Hotword listeners ONLY after successful authentication
            try:
                start_background_listeners()
            except Exception as e:
                print(f"[Jarvis Auth]: Notice starting listeners: {e}")

            # Start AI Stress Monitor after authentication succeeds
            try:
                from engine.stress_monitor import stress_engine
                stress_engine.start()
            except Exception as se:
                print(f"[Jarvis Auth]: Notice starting stress engine: {se}")
        else:
            _is_authenticated = False
            eel.faceAuthFailed()
            speak("Face Authentication Failed. Access Denied.")

    @eel.expose
    def retry_auth():
        print("[Jarvis Auth]: Retrying Face Authentication...")
        init()

    os.system('start msedge.exe --app="http://localhost:8000/index.html"')

    eel.start('index.html', mode=None, host='localhost', block=True)