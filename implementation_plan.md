# Implementation Plan - Gemini API Key, Chat History, and Realtime Voice Function

Configure Jarvis AI with the provided Gemini API key (`AIzaSyBnqh7CyKty76H1eqBXmOwpkqhRuxX3IDU`), implement persistent multi-turn chat history with backend SQLite storage & frontend UI canvas sync, and enable continuous hands-free real-time voice mode with synchronized visual wave animations.

## User Review Required

> [!NOTE]
> The provided API key `AIzaSyBnqh7CyKty76H1eqBXmOwpkqhRuxX3IDU` will be configured as the primary key for Gemini 2.5 Flash and Gemini 1.5 Flash fallback across all backend modules (`app.py`, `config.py`, and `engine/features.py`).

> [!IMPORTANT]
> Chat history will now be persisted in SQLite (`jarvis.db`) under a new `chat_history` table and fed to Gemini as multi-turn conversation context so Jarvis remembers past interactions across sessions.

## Proposed Changes

---

### Backend Components (`app.py`, `config.py`, `engine/features.py`)

#### [MODIFY] [config.py](file:///c:/Users/pukhr/Downloads/Jarvis-AI/config.py)
- Set default `GOOGLE_API_KEY` fallback to `AIzaSyBnqh7CyKty76H1eqBXmOwpkqhRuxX3IDU`.

#### [MODIFY] [app.py](file:///c:/Users/pukhr/Downloads/Jarvis-AI/app.py)
- Update default `GOOGLE_API_KEY` to `AIzaSyBnqh7CyKty76H1eqBXmOwpkqhRuxX3IDU`.
- Initialize `chat_history` table in SQLite (`id`, `sender`, `message`, `timestamp`).
- Update `get_gemini_response(prompt, history)` to accept multi-turn chat context and pass history to Gemini (`client.chats.create` or `contents` payload).
- Update `/api/chat` to save user messages, build history context, query Gemini, save model response to SQLite DB, and return response.
- Add `GET /api/chat/history` endpoint to retrieve past chat messages.
- Add `DELETE /api/chat/history` endpoint to clear stored history.

#### [MODIFY] [engine/features.py](file:///c:/Users/pukhr/Downloads/Jarvis-AI/engine/features.py)
- Replace outdated hardcoded API key in `chatBot` with `GOOGLE_API_KEY` (`AIzaSyBnqh7CyKty76H1eqBXmOwpkqhRuxX3IDU`).
- Add SQLite table creation for `chat_history`.

---

### Frontend Components (`www/index.html`, `www/api.js`, `www/controller.js`, `www/main.js`, `www/style.css`)

#### [MODIFY] [www/index.html](file:///c:/Users/pukhr/Downloads/Jarvis-AI/www/index.html)
- Add a "Clear History" button and Realtime Hands-Free Voice Mode toggle to the Chat canvas header.
- Ensure audio/mic and SiriWave UI containers are properly structured for real-time state feedback.

#### [MODIFY] [www/api.js](file:///c:/Users/pukhr/Downloads/Jarvis-AI/www/api.js)
- Fetch and load stored chat history on page startup via `/api/chat/history`.
- Implement `clearChatHistory` function to clear backend history and wipe UI messages.
- Upgrade Speech Synthesis (`speak()`) with `onstart` and `onend` event handlers to drive SiriWave animation and trigger hands-free continuous listening when speech finishes.
- Upgrade Speech Recognition (`recognition`) with interim results, status tracking ("Listening...", "Thinking...", "Speaking..."), and automatic restart in hands-free realtime voice mode.

#### [MODIFY] [www/controller.js](file:///c:/Users/pukhr/Downloads/Jarvis-AI/www/controller.js)
- Ensure sender and receiver chat messages append cleanly and auto-scroll.
- Support initial population of chat history from DB records.

#### [MODIFY] [www/main.js](file:///c:/Users/pukhr/Downloads/Jarvis-AI/www/main.js)
- Wire up Clear History button event listener.
- Wire up Realtime Hands-Free toggle button listener.

#### [MODIFY] [www/style.css](file:///c:/Users/pukhr/Downloads/Jarvis-AI/www/style.css)
- Add styles for Clear History button, hands-free realtime voice toggle, and timestamp badges in chat history.

---

## Verification Plan

### Automated Tests
- Test `/api/chat` with multi-turn messages using `curl` / Python requests to verify conversational context memory.
- Test `/api/chat/history` GET and DELETE endpoints.

### Manual Verification
- Launch application server (`python app.py`) and verify access via browser.
- Verify user input receives intelligent responses using the provided Gemini API key.
- Verify chat history persists across browser reloads.
- Test real-time voice mode: speak into microphone, observe wave animation, verify AI response spoken aloud, and test hands-free continuous voice conversation loop.
