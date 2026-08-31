import os
import requests
from shlex import quote
import sqlite3
import struct
import subprocess
import time
import webbrowser
from playsound import playsound
import eel
import pyaudio
import pyautogui
from engine.command import speak
from engine.config import ASSISTANT_NAME
from google import genai
from google.genai import types
try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    pass

# Playing assistant sound function
import pywhatkit as kit
import pvporcupine

from engine.helper import extract_yt_term, remove_words

DB_PATH = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "jarvis.db")

def get_db():
    """Create a thread-safe per-call database connection."""
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn

def init_database():
    """Initialize all required tables."""
    try:
        conn = get_db()
        cursor = conn.cursor()
        cursor.execute('''CREATE TABLE IF NOT EXISTS commands
                         (id INTEGER PRIMARY KEY AUTOINCREMENT,
                          command TEXT NOT NULL,
                          response TEXT NOT NULL)''')
        cursor.execute('''CREATE TABLE IF NOT EXISTS contacts
                         (id INTEGER PRIMARY KEY AUTOINCREMENT,
                          name TEXT NOT NULL,
                          mobile_no TEXT NOT NULL)''')
        cursor.execute('''CREATE TABLE IF NOT EXISTS sys_command
                         (id INTEGER PRIMARY KEY AUTOINCREMENT,
                          name TEXT NOT NULL,
                          path TEXT NOT NULL)''')
        cursor.execute('''CREATE TABLE IF NOT EXISTS web_command
                         (id INTEGER PRIMARY KEY AUTOINCREMENT,
                          name TEXT NOT NULL,
                          url TEXT NOT NULL)''')
        cursor.execute('''CREATE TABLE IF NOT EXISTS chat_history
                         (id INTEGER PRIMARY KEY AUTOINCREMENT,
                          sender TEXT NOT NULL,
                          message TEXT NOT NULL,
                          timestamp DATETIME DEFAULT CURRENT_TIMESTAMP)''')
        cursor.execute('''CREATE TABLE IF NOT EXISTS stress_logs
                         (id INTEGER PRIMARY KEY AUTOINCREMENT,
                          stress_score INTEGER NOT NULL,
                          state TEXT NOT NULL,
                          advice TEXT NOT NULL,
                          timestamp DATETIME DEFAULT CURRENT_TIMESTAMP)''')
        conn.commit()
        conn.close()
    except Exception as e:
        print(f"Error creating tables: {e}")

init_database()

@eel.expose
def playAssistantSound():
    music_dir = "www/assets/audio/start_sound.mp3"
    playsound(music_dir)


COMMON_WINDOWS_APPS = {
    "chrome": "start chrome",
    "google chrome": "start chrome",
    "browser": "start chrome",
    "edge": "start msedge",
    "microsoft edge": "start msedge",
    "notepad": "notepad.exe",
    "text editor": "notepad.exe",
    "calculator": "calc.exe",
    "calc": "calc.exe",
    "file explorer": "explorer.exe",
    "explorer": "explorer.exe",
    "this pc": "explorer.exe",
    "my computer": "explorer.exe",
    "settings": "start ms-settings:",
    "windows settings": "start ms-settings:",
    "task manager": "taskmgr.exe",
    "taskmgr": "taskmgr.exe",
    "camera": "start microsoft.windows.camera:",
    "paint": "mspaint.exe",
    "mspaint": "mspaint.exe",
    "cmd": "cmd.exe",
    "command prompt": "cmd.exe",
    "terminal": "wt.exe",
    "powershell": "powershell.exe",
    "code": "code",
    "vs code": "code",
    "vscode": "code",
    "visual studio code": "code",
    "spotify": "start spotify:",
    "whatsapp": "start whatsapp:",
    "discord": "start discord:",
    "word": "winword.exe",
    "ms word": "winword.exe",
    "microsoft word": "winword.exe",
    "excel": "excel.exe",
    "ms excel": "excel.exe",
    "powerpoint": "powerpnt.exe",
    "control panel": "control.exe",
    "youtube": "https://www.youtube.com",
    "chatgpt": "https://chatgpt.com",
    "github": "https://github.com",
    "gmail": "https://mail.google.com",
    "mail": "https://mail.google.com",
    "google": "https://www.google.com",
    "twitter": "https://x.com",
    "x": "https://x.com",
    "linkedin": "https://www.linkedin.com",
    "instagram": "https://www.instagram.com",
    "reddit": "https://www.reddit.com"
}

def openCommand(query):
    query_clean = query.replace(ASSISTANT_NAME, "").replace("open", "").strip().lower()
    if not query_clean:
        return

    # Instant non-blocking speak
    speak(f"Opening {query_clean}")

    # 1. Check built-in quick map (instant 0.01s launch)
    if query_clean in COMMON_WINDOWS_APPS:
        target = COMMON_WINDOWS_APPS[query_clean]
        if target.startswith("http://") or target.startswith("https://"):
            webbrowser.open(target)
        elif target.startswith("start "):
            subprocess.Popen(target, shell=True, creationflags=0x08000000 if os.name == 'nt' else 0)
        else:
            try:
                os.startfile(target)
            except Exception:
                subprocess.Popen(target, shell=True)
        return

    # 2. Check Database custom sys_command / web_command
    try:
        conn = get_db()
        cursor = conn.cursor()
        cursor.execute('SELECT path FROM sys_command WHERE LOWER(name) LIKE ?', (f'%{query_clean}%',))
        sys_res = cursor.fetchall()
        if sys_res and sys_res[0][0]:
            target_path = sys_res[0][0]
            conn.close()
            try:
                os.startfile(target_path)
            except Exception:
                subprocess.Popen(f'start "" "{target_path}"', shell=True)
            return

        cursor.execute('SELECT url FROM web_command WHERE LOWER(name) LIKE ?', (f'%{query_clean}%',))
        web_res = cursor.fetchall()
        if web_res and web_res[0][0]:
            target_url = web_res[0][0]
            conn.close()
            webbrowser.open(target_url)
            return
        conn.close()
    except Exception as db_err:
        print(f"DB app search error: {db_err}")

    # 3. Fallback: direct silent shell start without CMD console flash
    try:
        subprocess.Popen(f'start "" "{query_clean}"', shell=True, creationflags=0x08000000 if os.name == 'nt' else 0)
    except Exception as e:
        print(f"App launch fallback failed: {e}")

def PlayYoutube(query):
    search_term = extract_yt_term(query)
    speak("Playing " + search_term + " on YouTube")
    encoded_term = quote(search_term)
    yt_url = f"https://www.youtube.com/results?search_query={encoded_term}"
    webbrowser.open(yt_url)

import ctypes
from ctypes import wintypes
import threading

_assistant_busy_lock = threading.Lock()
_is_assistant_listening = False
_last_activation_time = 0.0

def focus_jarvis_window():
    """Bring the Jarvis application window to foreground if minimized or backgrounded."""
    try:
        user32 = ctypes.windll.user32
        def enum_window_callback(hwnd, extra):
            if user32.IsWindowVisible(hwnd):
                length = user32.GetWindowTextLengthW(hwnd)
                if length > 0:
                    buff = ctypes.create_unicode_buffer(length + 1)
                    user32.GetWindowTextW(hwnd, buff, length + 1)
                    title = buff.value.lower()
                    if "jarvis" in title or "localhost:8000" in title:
                        user32.ShowWindow(hwnd, 9)  # SW_RESTORE
                        user32.SetForegroundWindow(hwnd)
                        return False
            return True

        WNDENUMPROC = ctypes.WINFUNCTYPE(ctypes.c_bool, ctypes.c_int, ctypes.c_int)
        user32.EnumWindows(WNDENUMPROC(enum_window_callback), 0)
    except Exception as e:
        pass

def trigger_hotkey_activation():
    """Instant real-time trigger for Jarvis when global hotkey is pressed."""
    global _is_assistant_listening, _last_activation_time
    curr_time = time.time()
    if curr_time - _last_activation_time < 0.9:
        print("[Global Hotkey]: Debounced duplicate hotkey trigger.")
        return
    _last_activation_time = curr_time

    if _assistant_busy_lock.locked():
        print("[Global Hotkey]: Assistant is currently busy handling a request.")
        return

    def _run_activation():
        if not _assistant_busy_lock.acquire(blocking=False):
            return
        global _is_assistant_listening
        _is_assistant_listening = True
        try:
            print("[Global Hotkey]: Instant hotkey activated! Starting assistant listener...")
            focus_jarvis_window()
            try:
                playAssistantSound()
            except Exception:
                pass

            try:
                eel.showListeningWave()()
            except Exception:
                try:
                    eel.showListeningWave()
                except Exception:
                    pass

            from engine.command import allCommands
            allCommands(message=1)
        except Exception as e:
            print(f"Error executing allCommands from hotkey: {e}")
        finally:
            _is_assistant_listening = False
            try:
                _assistant_busy_lock.release()
            except Exception:
                pass

    threading.Thread(target=_run_activation, daemon=True).start()

@eel.expose
def trigger_hotkey_from_ui():
    """Allow UI keybindings to trigger the unified hotkey activation workflow."""
    trigger_hotkey_activation()

def trigger_hotword_activation():
    """Trigger Jarvis assistant listening when hotword is detected."""
    trigger_hotkey_activation()

def setup_keyboard_hooks():
    """Setup ultra-low latency system-wide global hotkeys using keyboard hook."""
    try:
        import keyboard
        hotkeys = [
            'ctrl+j',
            'alt+j',
            'ctrl+space',
            'ctrl+alt+j',
            'ctrl+shift+j',
            'f8',
            'f2'
        ]
        for hk in hotkeys:
            try:
                keyboard.add_hotkey(hk, trigger_hotkey_activation, suppress=False)
                print(f"[Keyboard Hotkey Hook]: Registered '{hk}' globally.")
            except Exception as hk_err:
                print(f"[Keyboard Hotkey Hook]: Notice registering '{hk}': {hk_err}")
    except Exception as err:
        print(f"[Keyboard Hotkey Hook]: Keyboard module hook skipped ({err})")

def global_hotkey_listener():
    """System-wide real-time global hotkey listener with persistent auto-restart via Win32 RegisterHotKey."""
    print("[Win32 Global Hotkey]: Starting Always-On Win32 system-wide hotkeys (Ctrl+J, Alt+J, Win+J, Ctrl+Space, F8, F2)...")
    user32 = ctypes.windll.user32
    
    HOTKEYS = [
        (101, 0x0002 | 0x4000, 0x4A),          # Ctrl + J
        (102, 0x0001 | 0x4000, 0x4A),          # Alt + J
        (103, 0x0008 | 0x4000, 0x4A),          # Win + J
        (104, 0x0002 | 0x0001 | 0x4000, 0x4A), # Ctrl + Alt + J
        (105, 0x4000, 0x77),                   # F8
        (106, 0x0002 | 0x4000, 0x20),          # Ctrl + Space
        (107, 0x4000, 0x71)                    # F2
    ]

    while True:
        try:
            # Force message queue initialization for calling thread
            msg = wintypes.MSG()
            user32.PeekMessageW(ctypes.byref(msg), None, 0x0400, 0x0400, 0x0001)

            # Register hotkeys
            for hk_id, mod, vk in HOTKEYS:
                user32.UnregisterHotKey(None, hk_id)
                res = user32.RegisterHotKey(None, hk_id, mod, vk)
                if not res:
                    # Fallback without MOD_NOREPEAT (0x4000)
                    user32.RegisterHotKey(None, hk_id, mod & ~0x4000, vk)

            # Message pump loop
            while user32.GetMessageW(ctypes.byref(msg), None, 0, 0) != 0:
                if msg.message == 0x0312:  # WM_HOTKEY
                    print(f"[Win32 Global Hotkey]: Hotkey ID {msg.wParam} detected!")
                    trigger_hotkey_activation()
                user32.TranslateMessage(ctypes.byref(msg))
                user32.DispatchMessageW(ctypes.byref(msg))

        except Exception as e:
            print(f"[Win32 Global Hotkey Watchdog]: Exception {e}, restarting listener in 1s...")
            time.sleep(1)

def hotword():
    """Continuous background hotword listener for keyword 'Jarvis' with mic contention protection."""
    print("[Hotword]: Starting continuous ambient listener for keyword 'Jarvis' (24/7)...")
    import speech_recognition as sr

    # 1. Try Porcupine wake-word engine first if available
    try:
        porcupine = pvporcupine.create(keywords=["jarvis", "alexa"])
        paud = pyaudio.PyAudio()
        audio_stream = paud.open(
            rate=porcupine.sample_rate,
            channels=1,
            format=pyaudio.paInt16,
            input=True,
            frames_per_buffer=porcupine.frame_length
        )
        print("[Hotword]: Porcupine wake-word engine active for 'Jarvis'.")
        while True:
            if _is_assistant_listening or _assistant_busy_lock.locked():
                time.sleep(0.5)
                continue
            keyword = audio_stream.read(porcupine.frame_length, exception_on_overflow=False)
            keyword = struct.unpack_from("h" * porcupine.frame_length, keyword)
            keyword_index = porcupine.process(keyword)
            if keyword_index >= 0:
                print("[Hotword]: Wake word 'Jarvis' detected via Porcupine!")
                trigger_hotword_activation()
                time.sleep(2)
    except Exception as p_err:
        print(f"[Hotword]: Porcupine wake engine fallback ({p_err}). Starting speech recognizer wake listener...")

    # 2. Ambient Continuous Speech Recognizer fallback
    r = sr.Recognizer()
    r.pause_threshold = 0.5
    r.energy_threshold = 280
    r.non_speaking_duration = 0.3

    wake_words = ["jarvis", "hey jarvis", "hi jarvis", "hello jarvis", "ok jarvis", "wake up jarvis", "alexa"]

    while True:
        try:
            if _is_assistant_listening or _assistant_busy_lock.locked():
                time.sleep(0.5)
                continue

            with sr.Microphone() as source:
                r.adjust_for_ambient_noise(source, duration=0.3)
                audio = r.listen(source, phrase_time_limit=3, timeout=5)

            if _is_assistant_listening or _assistant_busy_lock.locked():
                time.sleep(0.5)
                continue

            try:
                text = r.recognize_google(audio, language='en-in').lower()
                print(f"[Hotword Ambient]: Heard '{text}'")

                matched = any(w in text for w in wake_words)
                if matched:
                    print(f"[Hotword]: Wake word matched in '{text}'! Activating assistant...")

                    # Check if user spoke command in same sentence e.g. "Jarvis what time is it"
                    cleaned_cmd = text
                    for w in wake_words:
                        cleaned_cmd = cleaned_cmd.replace(w, "").strip()

                    if cleaned_cmd and len(cleaned_cmd) > 2:
                        try:
                            playAssistantSound()
                        except Exception:
                            pass
                        try:
                            eel.showListeningWave()()
                        except Exception:
                            pass
                        from engine.command import allCommands
                        threading.Thread(target=allCommands, kwargs={"message": cleaned_cmd}, daemon=True).start()
                    else:
                        trigger_hotword_activation()

                    time.sleep(2)
            except sr.UnknownValueError:
                pass
            except sr.RequestError as req_err:
                print(f"[Hotword Request Error]: {req_err}")
                time.sleep(1)
        except Exception:
            time.sleep(1)

def start_background_listeners():
    """Start all background listeners (Keyboard Hooks, Win32 Global Hotkeys, and Hotwords) for 24/7 realtime listening."""
    # 1. Setup keyboard library low-level hook
    setup_keyboard_hooks()

    # 2. Start Win32 RegisterHotKey pump in daemon thread
    t_hotkey = threading.Thread(target=global_hotkey_listener, daemon=True, name="Win32HotkeyThread")
    t_hotkey.start()

    # 3. Start Hotword ambient listener in daemon thread
    t_hotword = threading.Thread(target=hotword, daemon=True, name="HotwordThread")
    t_hotword.start()
    print("[Background]: Global Hotkeys (Ctrl+J, Alt+J, Ctrl+Space, F8, F2) & Hotword listeners are now running 24/7.")

# find contacts
def findContact(query):
    words_to_remove = [ASSISTANT_NAME, 'make', 'a', 'to', 'phone', 'call', 'send', 'message', 'whatsapp', 'video']
    query = remove_words(query, words_to_remove)

    try:
        query = query.strip().lower()
        conn = get_db()
        cursor = conn.cursor()
        cursor.execute("SELECT mobile_no FROM contacts WHERE LOWER(name) LIKE ? OR LOWER(name) LIKE ?", ('%' + query + '%', query + '%'))
        results = cursor.fetchall()
        conn.close()
        if not results:
            speak('not exist in contacts')
            return 0, 0
        print(results[0][0])
        mobile_number_str = str(results[0][0])

        if not mobile_number_str.startswith('+91'):
            mobile_number_str = '+91' + mobile_number_str

        return mobile_number_str, query
    except:
        speak('not exist in contacts')
        return 0, 0

def whatsApp(mobile_no, message, flag, name):
    if flag == 'message':
        target_tab = 12
        jarvis_message = "message sent successfully to "+name
    elif flag == 'call':
        target_tab = 7
        message = ''
        jarvis_message = "calling to "+name
    else:
        target_tab = 6
        message = ''
        jarvis_message = "starting video call with "+name

    # Encode the message for URL
    encoded_message = quote(message)
    print(encoded_message)
    # Construct the URL
    whatsapp_url = f"whatsapp://send?phone={mobile_no}&text={encoded_message}"

    # Construct the full command
    full_command = f'start "" "{whatsapp_url}"'

    # Open WhatsApp with the constructed URL using cmd.exe
    subprocess.run(full_command, shell=True)
    time.sleep(5)
    subprocess.run(full_command, shell=True)
    
    pyautogui.hotkey('ctrl', 'f')

    for i in range(1, target_tab):
        pyautogui.hotkey('tab')

    pyautogui.hotkey('enter')
    speak(jarvis_message)

# Chatbot function with multi-turn history using google.genai
def get_genai_client():
    primary_key = os.getenv('GOOGLE_API_KEY', '')
    if not primary_key:
        return None
    return genai.Client(api_key=primary_key)

def chatBot(query):
    try:
        user_input = query.strip()
        # Save user query to history
        add_chat_history("user", user_input)
        
        # Retrieve recent conversation turns for context
        conn = get_db()
        cursor = conn.cursor()
        cursor.execute("SELECT sender, message FROM chat_history ORDER BY id DESC LIMIT 12")
        recent_rows = cursor.fetchall()[::-1]
        conn.close()
        
        client = get_genai_client()
        
        # Build contents from history
        contents = []
        for row in recent_rows[:-1]:
            role = "user" if row[0] == "user" else "model"
            contents.append(types.Content(role=role, parts=[types.Part.from_text(text=str(row[1]))]))
        contents.append(types.Content(role="user", parts=[types.Part.from_text(text=user_input)]))
        
        response_obj = None
        working_models = [
            'gemini-flash-lite-latest',
            'gemini-3-flash-preview',
            'gemini-3.1-flash-lite',
            'gemini-3.5-flash-lite',
            'gemini-flash-latest',
            'gemini-pro-latest'
        ]
        for model_name in working_models:
            try:
                response_obj = client.models.generate_content(
                    model=model_name,
                    contents=contents
                )
                if response_obj and response_obj.text:
                    break
            except Exception as model_err:
                print(f"Model {model_name} attempt: {model_err}")
                continue
                
        if response_obj and response_obj.text:
            response = response_obj.text.strip()
        else:
            response = "I am at your service, sir. All systems are operational."
            
        print("Gemini response:", response)
        
        # Save assistant reply to history
        add_chat_history("assistant", response)
        
        # Speak and update UI
        speak(response)
        return response
    except Exception as e:
        print(f"Error in chatBot: {e}")
        fallback_msg = "I am at your service, sir. I have processed your request."
        add_chat_history("assistant", fallback_msg)
        speak(fallback_msg)
        return fallback_msg

# Android automation
def makeCall(name, mobileNo):
    mobileNo = mobileNo.replace(" ", "")
    speak("Calling "+name)
    command = 'adb shell am start -a android.intent.action.CALL -d tel:'+mobileNo
    os.system(command)

# To send message
def sendMessage(message, mobileNo, name):
    from engine.helper import replace_spaces_with_percent_s, goback, keyEvent, tapEvents, adbInput
    message = replace_spaces_with_percent_s(message)
    mobileNo = replace_spaces_with_percent_s(mobileNo)
    speak("sending message")
    goback(4)
    time.sleep(1)
    keyEvent(3)
    # open sms app
    tapEvents(136, 2220)
    # start chat
    tapEvents(819, 2192)
    # search mobile no
    adbInput(mobileNo)
    # tap on name
    tapEvents(601, 574)
    # tap on input
    tapEvents(390, 2270)
    # message
    adbInput(message)
    # send
    tapEvents(957, 1397)
    speak("message sent successfully to "+name)

@eel.expose
def get_all_commands():
    try:
        conn = get_db()
        cursor = conn.cursor()
        cursor.execute("SELECT id, command, response FROM commands")
        commands = cursor.fetchall()
        result = [{"id": cmd[0], "command": cmd[1], "response": cmd[2]} for cmd in commands]
        conn.close()
        return result
    except Exception as e:
        print(f"Error getting commands: {e}")
        return []

@eel.expose
def get_command(cmd_id):
    try:
        conn = get_db()
        cursor = conn.cursor()
        cursor.execute("SELECT id, command, response FROM commands WHERE id = ?", (cmd_id,))
        cmd = cursor.fetchone()
        conn.close()
        if cmd:
            return {"id": cmd[0], "command": cmd[1], "response": cmd[2]}
        return None
    except Exception as e:
        print(f"Error getting command: {e}")
        return None

@eel.expose
def add_command(command, response):
    try:
        conn = get_db()
        cursor = conn.cursor()
        cursor.execute("INSERT INTO commands (command, response) VALUES (?, ?)", 
                      (command, response))
        conn.commit()
        conn.close()
        return True
    except Exception as e:
        print(f"Error adding command: {e}")
        return False

@eel.expose
def update_command(cmd_id, command, response):
    try:
        conn = get_db()
        cursor = conn.cursor()
        cursor.execute("UPDATE commands SET command = ?, response = ? WHERE id = ?", 
                      (command, response, cmd_id))
        conn.commit()
        conn.close()
        return True
    except Exception as e:
        print(f"Error updating command: {e}")
        return False

@eel.expose
def delete_command(cmd_id):
    try:
        conn = get_db()
        cursor = conn.cursor()
        cursor.execute("DELETE FROM commands WHERE id = ?", (cmd_id,))
        conn.commit()
        conn.close()
        return True
    except Exception as e:
        print(f"Error deleting command: {e}")
        return False

@eel.expose
def get_all_contacts():
    try:
        conn = get_db()
        cursor = conn.cursor()
        cursor.execute("SELECT id, name, mobile_no FROM contacts")
        contacts = cursor.fetchall()
        result = [{"id": c[0], "name": c[1], "mobile_no": c[2]} for c in contacts]
        conn.close()
        return result
    except Exception as e:
        print(f"Error getting contacts: {e}")
        return []

@eel.expose
def get_all_sys_commands():
    try:
        conn = get_db()
        cursor = conn.cursor()
        cursor.execute("SELECT id, name, path FROM sys_command")
        commands = cursor.fetchall()
        result = [{"id": c[0], "name": c[1], "path": c[2]} for c in commands]
        conn.close()
        return result
    except Exception as e:
        print(f"Error getting system commands: {e}")
        return []

@eel.expose
def get_all_web_commands():
    try:
        conn = get_db()
        cursor = conn.cursor()
        cursor.execute("SELECT id, name, url FROM web_command")
        commands = cursor.fetchall()
        result = [{"id": c[0], "name": c[1], "url": c[2]} for c in commands]
        conn.close()
        return result
    except Exception as e:
        print(f"Error getting web commands: {e}")
        return []

# Contact CRUD operations
@eel.expose
def add_contact(name, mobile_no):
    try:
        conn = get_db()
        cursor = conn.cursor()
        cursor.execute("INSERT INTO contacts (name, mobile_no) VALUES (?, ?)", 
                      (name, mobile_no))
        conn.commit()
        conn.close()
        return True
    except Exception as e:
        print(f"Error adding contact: {e}")
        return False

@eel.expose
def update_contact(contact_id, name, mobile_no):
    try:
        conn = get_db()
        cursor = conn.cursor()
        cursor.execute("UPDATE contacts SET name = ?, mobile_no = ? WHERE id = ?", 
                      (name, mobile_no, contact_id))
        conn.commit()
        conn.close()
        return True
    except Exception as e:
        print(f"Error updating contact: {e}")
        return False

# System Command CRUD operations
@eel.expose
def add_sys_command(name, path):
    try:
        conn = get_db()
        cursor = conn.cursor()
        cursor.execute("INSERT INTO sys_command (name, path) VALUES (?, ?)", 
                      (name, path))
        conn.commit()
        conn.close()
        return True
    except Exception as e:
        print(f"Error adding system command: {e}")
        return False

@eel.expose
def update_sys_command(cmd_id, name, path):
    try:
        conn = get_db()
        cursor = conn.cursor()
        cursor.execute("UPDATE sys_command SET name = ?, path = ? WHERE id = ?", 
                      (name, path, cmd_id))
        conn.commit()
        conn.close()
        return True
    except Exception as e:
        print(f"Error updating system command: {e}")
        return False

# Web Command CRUD operations
@eel.expose
def add_web_command(name, url):
    try:
        conn = get_db()
        cursor = conn.cursor()
        cursor.execute("INSERT INTO web_command (name, url) VALUES (?, ?)", 
                      (name, url))
        conn.commit()
        conn.close()
        return True
    except Exception as e:
        print(f"Error adding web command: {e}")
        return False

@eel.expose
def update_web_command(cmd_id, name, url):
    try:
        conn = get_db()
        cursor = conn.cursor()
        cursor.execute("UPDATE web_command SET name = ?, url = ? WHERE id = ?", 
                      (name, url, cmd_id))
        conn.commit()
        conn.close()
        return True
    except Exception as e:
        print(f"Error updating web command: {e}")
        return False

# Contact operations
@eel.expose
def get_contact(contact_id):
    try:
        conn = get_db()
        cursor = conn.cursor()
        cursor.execute("SELECT id, name, mobile_no FROM contacts WHERE id = ?", (contact_id,))
        contact = cursor.fetchone()
        conn.close()
        if contact:
            return {"id": contact[0], "name": contact[1], "mobile_no": contact[2]}
        return None
    except Exception as e:
        print(f"Error getting contact: {e}")
        return None

@eel.expose
def delete_contact(contact_id):
    try:
        conn = get_db()
        cursor = conn.cursor()
        cursor.execute("DELETE FROM contacts WHERE id = ?", (contact_id,))
        conn.commit()
        conn.close()
        return True
    except Exception as e:
        print(f"Error deleting contact: {e}")
        return False

# System Command operations
@eel.expose
def get_sys_command(cmd_id):
    try:
        conn = get_db()
        cursor = conn.cursor()
        cursor.execute("SELECT id, name, path FROM sys_command WHERE id = ?", (cmd_id,))
        cmd = cursor.fetchone()
        conn.close()
        if cmd:
            return {"id": cmd[0], "name": cmd[1], "path": cmd[2]}
        return None
    except Exception as e:
        print(f"Error getting system command: {e}")
        return None

@eel.expose
def delete_sys_command(cmd_id):
    try:
        conn = get_db()
        cursor = conn.cursor()
        cursor.execute("DELETE FROM sys_command WHERE id = ?", (cmd_id,))
        conn.commit()
        conn.close()
        return True
    except Exception as e:
        print(f"Error deleting system command: {e}")
        return False

# Web Command operations
@eel.expose
def get_web_command(cmd_id):
    try:
        conn = get_db()
        cursor = conn.cursor()
        cursor.execute("SELECT id, name, url FROM web_command WHERE id = ?", (cmd_id,))
        cmd = cursor.fetchone()
        conn.close()
        if cmd:
            return {"id": cmd[0], "name": cmd[1], "url": cmd[2]}
        return None
    except Exception as e:
        print(f"Error getting web command: {e}")
        return None

@eel.expose
def delete_web_command(cmd_id):
    try:
        conn = get_db()
        cursor = conn.cursor()
        cursor.execute("DELETE FROM web_command WHERE id = ?", (cmd_id,))
        conn.commit()
        conn.close()
        return True
    except Exception as e:
        print(f"Error deleting web command: {e}")
        return False

# Chat History operations
@eel.expose
def get_chat_history():
    try:
        conn = get_db()
        cursor = conn.cursor()
        cursor.execute("SELECT id, sender, message, timestamp FROM chat_history ORDER BY id ASC")
        rows = cursor.fetchall()
        result = [{"id": r[0], "sender": r[1], "message": r[2], "timestamp": str(r[3])} for r in rows]
        conn.close()
        return result
    except Exception as e:
        print(f"Error getting chat history: {e}")
        return []

@eel.expose
def add_chat_history(sender, message):
    try:
        conn = get_db()
        cursor = conn.cursor()
        cursor.execute("INSERT INTO chat_history (sender, message) VALUES (?, ?)", (sender, message))
        conn.commit()
        conn.close()
        return True
    except Exception as e:
        print(f"Error adding chat history: {e}")
        return False

@eel.expose
def clear_chat_history():
    try:
        conn = get_db()
        cursor = conn.cursor()
        cursor.execute("DELETE FROM chat_history")
        conn.commit()
        conn.close()
        return True
    except Exception as e:
        print(f"Error clearing chat history: {e}")
        return False

# Stress Monitor operations
@eel.expose
def start_stress_monitor():
    try:
        from engine.stress_monitor import stress_engine
        stress_engine.start()
        speak("AI Camera Stress Monitor is now active.")
        return {"status": "success", "active": True}
    except Exception as e:
        print(f"Error starting stress monitor: {e}")
        return {"status": "error", "message": str(e)}

@eel.expose
def stop_stress_monitor():
    try:
        from engine.stress_monitor import stress_engine
        stress_engine.stop()
        speak("Stress monitor has been deactivated.")
        return {"status": "success", "active": False}
    except Exception as e:
        print(f"Error stopping stress monitor: {e}")
        return {"status": "error", "message": str(e)}

@eel.expose
def get_stress_status():
    try:
        from engine.stress_monitor import stress_engine
        return stress_engine.get_status()
    except Exception as e:
        print(f"Error getting stress status: {e}")
        return {"active": False, "score": 20, "state": "Normal", "advice": "Monitor inactive."}

@eel.expose
def get_stress_history():
    try:
        conn = get_db()
        cursor = conn.cursor()
        cursor.execute("SELECT id, stress_score, state, advice, timestamp FROM stress_logs ORDER BY id DESC LIMIT 20")
        rows = cursor.fetchall()
        result = [{"id": r[0], "stress_score": r[1], "state": r[2], "advice": r[3], "timestamp": str(r[4])} for r in rows]
        conn.close()
        return result
    except Exception as e:
        print(f"Error getting stress history: {e}")
        return []

@eel.expose
def trigger_relief_intervention():
    try:
        from engine.stress_monitor import stress_engine
        status = stress_engine.get_status()
        speak(f"Opening Relief Center. Your current stress index is {status['score']} percent. Let's take a deep breath together.")
        return status
    except Exception as e:
        print(f"Error in trigger_relief_intervention: {e}")
        return {}
