import os
import subprocess
import eel

from engine.features import *
from engine.command import *
from engine.auth import recoganize
def start():
    
    eel.init("www")

    # Start Realtime 24/7 Global Hotkey and Hotword background listeners
    try:
        start_background_listeners()
    except Exception as e:
        print(f"Error starting background listeners: {e}")

    playAssistantSound()
    @eel.expose
    def init():
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
            eel.hideFaceAuth()
            speak("Face Authentication Successful")
            eel.hideFaceAuthSuccess()
            speak("Hello, Welcome Sir, How can i Help You")
            eel.hideStart()
            playAssistantSound()
            # Start AI Stress Monitor after authentication succeeds
            from engine.stress_monitor import stress_engine
            stress_engine.start()
        else:
            speak("Face Authentication Fail")
    os.system('start msedge.exe --app="http://localhost:8000/index.html"')

    eel.start('index.html', mode=None, host='localhost', block=True)