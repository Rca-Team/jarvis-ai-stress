import os
import sqlite3
from flask import Flask, request, jsonify, send_from_directory
from google import genai
from google.genai import types
try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    pass

app = Flask(__name__, static_folder='www', static_url_path='')

GOOGLE_API_KEY = os.getenv('GOOGLE_API_KEY', '')


DB_PATH = 'jarvis.db'

def get_db_connection():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn

def init_db():
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute('''CREATE TABLE IF NOT EXISTS chat_history
                     (id INTEGER PRIMARY KEY AUTOINCREMENT,
                      sender TEXT NOT NULL,
                      message TEXT NOT NULL,
                      timestamp DATETIME DEFAULT CURRENT_TIMESTAMP)''')
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
    cursor.execute('''CREATE TABLE IF NOT EXISTS stress_logs
                     (id INTEGER PRIMARY KEY AUTOINCREMENT,
                      stress_score INTEGER NOT NULL,
                      state TEXT NOT NULL,
                      advice TEXT NOT NULL,
                      timestamp DATETIME DEFAULT CURRENT_TIMESTAMP)''')
    conn.commit()
    conn.close()

init_db()

def get_gemini_response(prompt, conversation_history=None):
    api_key = os.getenv('GOOGLE_API_KEY') or GOOGLE_API_KEY
    if not api_key:
        return "Gemini API Key is not configured. Please add GOOGLE_API_KEY to your .env file."
    try:
        client = genai.Client(api_key=api_key)
        contents = []
        if conversation_history:
            for item in conversation_history:
                sender = item.get('sender') or item.get('role')
                msg = item.get('message') or item.get('content') or item.get('parts', [''])[0]
                if msg:
                    role = 'user' if sender == 'user' else 'model'
                    contents.append(types.Content(role=role, parts=[types.Part.from_text(text=str(msg))]))
        contents.append(types.Content(role="user", parts=[types.Part.from_text(text=prompt)]))
        
        # Check local quick response first
        from engine.features import local_quick_response
        local_reply = local_quick_response(prompt)
        if local_reply:
            return local_reply

        response = None
        working_models = [
            'gemini-2.5-flash',
            'gemini-2.0-flash',
            'gemini-1.5-flash',
            'gemini-1.5-pro'
        ]
        leaked_key = False
        for model_name in working_models:
            try:
                response = client.models.generate_content(
                    model=model_name,
                    contents=contents
                )
                if response and response.text:
                    break
            except Exception as m_err:
                err_text = str(m_err).lower()
                if 'leaked' in err_text or 'permission_denied' in err_text or '403' in err_text:
                    leaked_key = True
                    break
                continue
                
        if response and response.text:
            return response.text.strip()
        if leaked_key:
            return "Notice: Your Gemini API key was reported as leaked or expired by Google. Please update GOOGLE_API_KEY in your .env file."
        return "I heard you, sir. How else may I assist you?"
    except Exception as e:
        print(f"Gemini API Error: {e}")
        return "I am at your service, sir. Please let me know how I can help."

@app.route('/')
def index():
    return send_from_directory('www', 'index.html')

@app.route('/eel.js')
def eel_dummy():
    return "// Eel stub for standalone Flask mode\nvar eel = {};", 200, {'Content-Type': 'application/javascript'}

@app.route('/<path:path>')
def static_files(path):
    return send_from_directory('www', path)

@app.route('/api/chat', methods=['POST'])
def chat_endpoint():
    try:
        data = request.get_json() or {}
        user_message = data.get('message', '').strip()
        if not user_message:
            return jsonify({'status': 'error', 'message': 'Message is required'}), 400

        conn = get_db_connection()
        cursor = conn.cursor()
        
        # Save user message
        cursor.execute("INSERT INTO chat_history (sender, message) VALUES (?, ?)", ('user', user_message))
        conn.commit()

        # Fetch recent history for context
        cursor.execute("SELECT sender, message FROM chat_history ORDER BY id DESC LIMIT 12")
        recent_rows = cursor.fetchall()[::-1]
        
        history_for_gemini = []
        for r in recent_rows[:-1]: # exclude current user message
            history_for_gemini.append({'sender': r['sender'], 'message': r['message']})

        # Get AI response
        ai_reply = get_gemini_response(user_message, history_for_gemini)

        # Save assistant message
        cursor.execute("INSERT INTO chat_history (sender, message) VALUES (?, ?)", ('assistant', ai_reply))
        conn.commit()

        # Retrieve updated history
        cursor.execute("SELECT id, sender, message, timestamp FROM chat_history ORDER BY id ASC")
        all_history = [{'id': r['id'], 'sender': r['sender'], 'message': r['message'], 'timestamp': str(r['timestamp'])} for r in cursor.fetchall()]
        conn.close()

        return jsonify({
            'status': 'success',
            'reply': ai_reply,
            'history': all_history
        })
    except Exception as e:
        print(f"Chat endpoint error: {e}")
        return jsonify({'status': 'error', 'message': str(e)}), 500

@app.route('/api/chat/history', methods=['GET'])
def get_history_endpoint():
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT id, sender, message, timestamp FROM chat_history ORDER BY id ASC")
        history = [{'id': r['id'], 'sender': r['sender'], 'message': r['message'], 'timestamp': str(r['timestamp'])} for r in cursor.fetchall()]
        conn.close()
        return jsonify({'status': 'success', 'history': history})
    except Exception as e:
        return jsonify({'status': 'error', 'message': str(e)}), 500

@app.route('/api/chat/history', methods=['DELETE'])
def clear_history_endpoint():
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute("DELETE FROM chat_history")
        conn.commit()
        conn.close()
        return jsonify({'status': 'success', 'message': 'Chat history cleared'})
    except Exception as e:
        return jsonify({'status': 'error', 'message': str(e)}), 500

# Stress Monitor REST Endpoints
@app.route('/api/stress/status', methods=['GET'])
def stress_status_endpoint():
    try:
        from engine.stress_monitor import stress_engine
        status = stress_engine.get_status()
        return jsonify({'status': 'success', 'data': status})
    except Exception as e:
        return jsonify({'status': 'error', 'message': str(e)}), 500

@app.route('/api/stress/toggle', methods=['POST'])
def stress_toggle_endpoint():
    try:
        from engine.stress_monitor import stress_engine
        data = request.get_json() or {}
        action = data.get('action')
        
        if action == 'start' or (action is None and not stress_engine.is_running):
            stress_engine.start()
            is_active = True
        else:
            stress_engine.stop()
            is_active = False

        return jsonify({'status': 'success', 'active': is_active, 'data': stress_engine.get_status()})
    except Exception as e:
        return jsonify({'status': 'error', 'message': str(e)}), 500

@app.route('/api/stress/history', methods=['GET'])
def stress_history_endpoint():
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT id, stress_score, state, advice, timestamp FROM stress_logs ORDER BY id DESC LIMIT 20")
        rows = [{'id': r['id'], 'stress_score': r['stress_score'], 'state': r['state'], 'advice': r['advice'], 'timestamp': str(r['timestamp'])} for r in cursor.fetchall()]
        conn.close()
        return jsonify({'status': 'success', 'history': rows})
    except Exception as e:
        return jsonify({'status': 'error', 'message': str(e)}), 500

@app.route('/api/stress/relief', methods=['POST'])
def stress_relief_endpoint():
    try:
        from engine.stress_monitor import stress_engine
        status = stress_engine.get_status()
        return jsonify({'status': 'success', 'data': status, 'message': 'Relief session activated'})
    except Exception as e:
        return jsonify({'status': 'error', 'message': str(e)}), 500

@app.route('/api/student/exam_relief', methods=['POST', 'GET'])
def student_exam_relief_endpoint():
    try:
        from engine.features import get_exam_relief_guidance
        subject = "exam"
        if request.method == 'POST':
            data = request.get_json() or {}
            subject = data.get('subject', 'exam')
        guidance = get_exam_relief_guidance(subject)
        return jsonify({'status': 'success', 'data': guidance})
    except Exception as e:
        return jsonify({'status': 'error', 'message': str(e)}), 500

@app.route('/api/student/cooldown', methods=['POST', 'GET'])
def student_cooldown_endpoint():
    try:
        from engine.features import start_two_minute_cooldown
        result = start_two_minute_cooldown()
        return jsonify(result)
    except Exception as e:
        return jsonify({'status': 'error', 'message': str(e)}), 500

@app.route('/api/student/stress_suggestion', methods=['POST', 'GET'])
def student_stress_suggestion_endpoint():
    try:
        from engine.features import report_stress_and_suggestions
        result = report_stress_and_suggestions()
        return jsonify(result)
    except Exception as e:
        return jsonify({'status': 'error', 'message': str(e)}), 500

@app.route('/api/student/study_note', methods=['POST'])
def student_study_note_endpoint():
    try:
        from engine.features import take_study_note
        data = request.get_json() or {}
        note = data.get('note', '')
        if not note:
            return jsonify({'status': 'error', 'message': 'Empty note content'}), 400
        saved = take_study_note(note)
        return jsonify({'status': 'success', 'entry': saved})
    except Exception as e:
        return jsonify({'status': 'error', 'message': str(e)}), 500

@app.route('/api/student/action', methods=['POST'])
def student_action_endpoint():
    try:
        data = request.get_json() or {}
        action = data.get('action', '')
        target = data.get('target', '')
        from engine.features import (capture_study_screenshot, adjust_system_volume,
                                     manage_media_playback, manage_windows,
                                     open_study_pdf, find_and_open_app)
        
        if action == 'screenshot':
            success = capture_study_screenshot()
            return jsonify({'status': 'success', 'captured': success})
        elif action == 'volume':
            adjust_system_volume(target)
            return jsonify({'status': 'success', 'volume': target})
        elif action == 'media':
            manage_media_playback(target)
            return jsonify({'status': 'success', 'media': target})
        elif action == 'windows':
            manage_windows(target)
            return jsonify({'status': 'success', 'window': target})
        elif action == 'open_pdf':
            opened = open_study_pdf(target or "chapter")
            return jsonify({'status': 'success', 'opened': opened})
        elif action == 'open_app':
            opened = find_and_open_app(target)
            return jsonify({'status': 'success', 'opened': opened})
        else:
            return jsonify({'status': 'error', 'message': f'Unknown action: {action}'}), 400
    except Exception as e:
        return jsonify({'status': 'error', 'message': str(e)}), 500

@app.route('/api/stress/video_feed')
def stress_video_feed():
    """Live MJPEG video stream with real-time biometric HUD overlay."""
    from flask import Response
    from engine.stress_monitor import stress_engine
    if not stress_engine.is_running:
        stress_engine.start()
    return Response(stress_engine.generate_video_frames(),
                    mimetype='multipart/x-mixed-replace; boundary=frame')

if __name__ == '__main__':
    try:
        from engine.features import start_background_listeners
        start_background_listeners()
    except Exception as bg_err:
        print(f"Notice: background listeners could not start: {bg_err}")
    print(f"Starting Jarvis Server on http://localhost:8000 ...")
    app.run(host='0.0.0.0', port=8000, debug=False, use_reloader=False)

