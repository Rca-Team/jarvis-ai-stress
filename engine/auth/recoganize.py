import os
import time
import cv2

base_dir = os.path.dirname(os.path.abspath(__file__))
trainer_path = os.path.join(base_dir, 'trainer', 'trainer.yml')
cascadePath = os.path.join(base_dir, 'haarcascade_frontalface_default.xml')

def AuthenticateFace():
    flag = 0

    # Safely check opencv face recognizer availability
    if not hasattr(cv2, 'face'):
        print("[Face Auth Error]: opencv-contrib-python is required for LBPH face recognition.")
        return 0

    # Local Binary Patterns Histograms
    try:
        recognizer = cv2.face.LBPHFaceRecognizer_create()
    except Exception as e:
        print(f"[Face Auth Error]: Failed to create recognizer: {e}")
        return 0

    if not os.path.exists(trainer_path):
        print(f"[Face Auth Error]: Trainer file not found at {trainer_path}. Please run sample.py and trainer.py.")
        return 0

    try:
        recognizer.read(trainer_path)  # load trained model
    except Exception as e:
        print(f"[Face Auth Error]: Error reading trainer file: {e}")
        return 0

    if not os.path.exists(cascadePath):
        print(f"[Face Auth Error]: Cascade file not found at {cascadePath}.")
        return 0

    faceCascade = cv2.CascadeClassifier(cascadePath)
    font = cv2.FONT_HERSHEY_SIMPLEX
    names = ['', 'Authorized User']

    cam = cv2.VideoCapture(0, cv2.CAP_DSHOW)
    if not cam.isOpened():
        print("[Face Auth Error]: Webcam could not be opened for Face Authentication.")
        return 0

    cam.set(3, 640)
    cam.set(4, 480)

    minW = 0.1 * cam.get(3)
    minH = 0.1 * cam.get(4)

    start_time = time.time()
    max_duration = 18  # 18-second timeout for verification
    consecutive_matches = 0
    required_consecutive_matches = 3

    print("[Face Auth]: Looking for authorized face...")

    try:
        while True:
            # Check timeout - strictly fail if duration exceeded without verified face
            if time.time() - start_time > max_duration:
                print("[Face Auth]: Verification timeout reached. Authentication Failed.")
                flag = 0
                break

            ret, img = cam.read()
            if not ret or img is None:
                time.sleep(0.05)
                continue

            converted_image = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)

            faces = faceCascade.detectMultiScale(
                converted_image,
                scaleFactor=1.2,
                minNeighbors=5,
                minSize=(int(minW), int(minH)),
            )

            current_frame_matched = False

            for (x, y, w, h) in faces:
                id, distance = recognizer.predict(converted_image[y:y+h, x:x+w])

                # In LBPH, lower distance indicates higher similarity (0 = identical, 100+ = different)
                if distance < 80:
                    confidence = round(max(0, 100 - distance))
                    person_name = names[id] if id < len(names) else f"User {id}"
                    accuracy_text = f"Verified {confidence}% ({consecutive_matches + 1}/{required_consecutive_matches})"
                    box_color = (0, 255, 0)
                    current_frame_matched = True
                else:
                    person_name = "Unknown"
                    accuracy_text = f"Mismatch ({round(distance)})"
                    box_color = (0, 0, 255)

                cv2.rectangle(img, (x, y), (x+w, y+h), box_color, 2)
                cv2.putText(img, str(person_name), (x+5, y-8), font, 0.8, (255, 255, 255), 2)
                cv2.putText(img, str(accuracy_text), (x+5, y+h+20), font, 0.6, box_color, 2)

            if current_frame_matched:
                consecutive_matches += 1
                if consecutive_matches >= required_consecutive_matches:
                    print(f"[Face Auth]: Face recognized successfully with {consecutive_matches} confirmed frames!")
                    flag = 1
                    break
            else:
                consecutive_matches = max(0, consecutive_matches - 1)

            # Draw HUD status overlay on webcam preview
            elapsed = round(max_duration - (time.time() - start_time))
            cv2.putText(img, f"Authenticating... [{elapsed}s remaining]", (20, 30), font, 0.7, (0, 255, 255), 2)
            cv2.putText(img, "Press ESC to cancel", (20, 60), font, 0.5, (200, 200, 200), 1)

            try:
                cv2.imshow('Jarvis Biometric Authentication', img)
            except Exception:
                pass

            k = cv2.waitKey(15) & 0xff
            if k == 27:  # ESC to cancel
                print("[Face Auth]: Authentication cancelled by user.")
                flag = 0
                break

    except Exception as e:
        print(f"[Face Auth Exception]: {e}")
        flag = 0
    finally:
        cam.release()
        try:
            cv2.destroyAllWindows()
        except Exception:
            pass

    return flag

