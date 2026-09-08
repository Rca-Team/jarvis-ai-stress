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
        if _is_authenticated:
            print("[Jarvis Auth]: Session already authenticated. Restoring dashboard immediately on refresh.")
            def _restore_dashboard():
                time.sleep(0.1)
                try:
                    eel.hideLoader()()
                    eel.hideFaceAuth()()
                    eel.hideFaceAuthSuccess()()
                    eel.hideStart()()
                except Exception:
                    try:
                        eel.hideLoader()
                        eel.hideFaceAuth()
                        eel.hideFaceAuthSuccess()
                        eel.hideStart()
                    except Exception:
                        pass
            threading.Thread(target=_restore_dashboard, daemon=True).start()
            return

        def _auth_worker():
            global _is_authenticated
            # Coordinate camera: pause stress monitor if running to release camera 0
            try:
                from engine.stress_monitor import stress_engine
                if stress_engine.is_running:
                    stress_engine.stop()
                    time.sleep(0.4)
            except Exception:
                pass

            import shutil
            if shutil.which('adb') and os.path.exists('device.bat'):
                try:
                    subprocess.Popen([r'device.bat'], shell=True)
                except Exception:
                    pass

            try:
                eel.hideLoader()()
            except Exception:
                try:
                    eel.hideLoader()
                except Exception:
                    pass

            speak("Ready for Face Authentication")
            flag = recoganize.AuthenticateFace()

            if flag == 1:
                _is_authenticated = True
                try:
                    eel.hideFaceAuth()()
                except Exception:
                    try:
                        eel.hideFaceAuth()
                    except Exception:
                        pass
                speak("Face Authentication Successful")
                try:
                    eel.hideFaceAuthSuccess()()
                except Exception:
                    try:
                        eel.hideFaceAuthSuccess()
                    except Exception:
                        pass
                speak("Hello, Welcome Sir, How can I help you today?")
                try:
                    eel.hideStart()()
                except Exception:
                    try:
                        eel.hideStart()
                    except Exception:
                        pass
                playAssistantSound()

                # Start Realtime 24/7 Global Hotkeys and Hotword listeners
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
                try:
                    eel.faceAuthFailed()()
                except Exception:
                    try:
                        eel.faceAuthFailed()
                    except Exception:
                        pass
                speak("Face Authentication Failed. Access Denied.")

        threading.Thread(target=_auth_worker, daemon=True).start()

    @eel.expose
    def retry_auth():
        print("[Jarvis Auth]: Retrying Face Authentication...")
        init()

    os.system('start msedge.exe --app="http://localhost:8000/index.html"')

    eel.start('index.html', mode=None, host='localhost', block=True)