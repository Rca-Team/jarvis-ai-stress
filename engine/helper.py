import os
import re
import time


def extract_yt_term(command):
    cmd = str(command).strip()
    # Pattern 1: play <term> on youtube
    m = re.search(r'play\s+(.*?)\s+on\s+youtube', cmd, re.IGNORECASE)
    if m and m.group(1).strip():
        return m.group(1).strip()
    
    # Pattern 2: search youtube for <term> / search on youtube <term>
    m = re.search(r'(?:search|find)\s+(?:on\s+)?youtube\s+(?:for\s+)?(.*)', cmd, re.IGNORECASE)
    if m and m.group(1).strip():
        return m.group(1).strip()
        
    # Pattern 3: <term> on youtube
    m = re.search(r'(.*?)\s+on\s+youtube', cmd, re.IGNORECASE)
    if m and m.group(1).strip():
        term = m.group(1).strip()
        term = re.sub(r'^(?:play|search|find|open)\s+', '', term, flags=re.IGNORECASE).strip()
        if term:
            return term

    # Pattern 4: play <term> (e.g. "play believer")
    m = re.search(r'^play\s+(.*)', cmd, re.IGNORECASE)
    if m and m.group(1).strip():
        term = m.group(1).strip()
        term = re.sub(r'\s+on\s+youtube$', '', term, flags=re.IGNORECASE).strip()
        if term:
            return term

    # Fallback: remove common noise words
    cleaned = re.sub(r'\b(play|on youtube|youtube|jarvis|search|video|song)\b', '', cmd, flags=re.IGNORECASE).strip()
    return cleaned if cleaned else cmd



def remove_words(input_string, words_to_remove):
    # Split the input string into words
    words = input_string.split()

    # Remove unwanted words
    filtered_words = [word for word in words if word.lower() not in words_to_remove]

    # Join the remaining words back into a string
    result_string = ' '.join(filtered_words)

    return result_string



# key events like receive call, stop call, go back
def keyEvent(key_code):
    command =  f'adb shell input keyevent {key_code}'
    os.system(command)
    time.sleep(1)

# Tap event used to tap anywhere on screen
def tapEvents(x, y):
    command =  f'adb shell input tap {x} {y}'
    os.system(command)
    time.sleep(1)

# Input Event is used to insert text in mobile
def adbInput(message):
    command =  f'adb shell input text "{message}"'
    os.system(command)
    time.sleep(1)

# to go complete back
def goback(key_code):
    for i in range(6):
        keyEvent(key_code)

# To replace space in string with %s for complete message send
def replace_spaces_with_percent_s(input_string):
    return input_string.replace(' ', '%s')
