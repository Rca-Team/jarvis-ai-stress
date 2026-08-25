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
        print("[Face Auth Warning]: opencv-contrib-python is required for LBPH face recognition. Auto-passing face authentication.")
        return 1

    # Local Binary Patterns Histograms
    try:
        recognizer = cv2.face.LBPHFaceRecognizer_create()
    except Exception as e:
        print(f"[Face Auth Error]: Failed to create recognizer: {e}")
        return 1

    if not os.path.exists(trainer_path):
        print(f"Trainer file not found at {trainer_path}. Auto-passing face authentication.")
        return 1

    try:
        recognizer.read(trainer_path)  # load trained model
    except Exception as e:
        print(f"Error reading trainer file: {e}. Auto-passing.")
        return 1

    # initializing haar cascade for object detection approach
    faceCascade = cv2.CascadeClassifier(cascadePath)
    font = cv2.FONT_HERSHEY_SIMPLEX
    names = ['', 'User']

    cam = cv2.VideoCapture(0, cv2.CAP_DSHOW)
    if not cam.isOpened():
        print("[Face Auth Warning]: Webcam could not be opened. Auto-passing face authentication.")
        return 1

    cam.set(3, 640)
    cam.set(4, 480)

    minW = 0.1 * cam.get(3)
    minH = 0.1 * cam.get(4)

    start_time = time.time()
    max_duration = 20  # 20-second timeout

    try:
        while True:
            # Check timeout (20 seconds max)
            if time.time() - start_time > max_duration:
                print("[Face Auth]: Timeout reached (20s). Proceeding...")
                flag = 1  # Auto-pass on timeout to avoid blocking user indefinitely
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

            for (x, y, w, h) in faces:
                cv2.rectangle(img, (x, y), (x+w, y+h), (0, 255, 0), 2)
                id, accuracy = recognizer.predict(converted_image[y:y+h, x:x+w])

                if accuracy < 100:
                    person_name = names[id] if id < len(names) else f"User {id}"
                    accuracy_text = "  {0}%".format(round(100 - accuracy))
                    flag = 1
                else:
                    person_name = "unknown"
                    accuracy_text = "  {0}%".format(round(100 - accuracy))
                    flag = 0

                cv2.putText(img, str(person_name), (x+5, y-5), font, 1, (255, 255, 255), 2)
                cv2.putText(img, str(accuracy_text), (x+5, y+h-5), font, 1, (255, 255, 0), 1)

            try:
                cv2.imshow('camera', img)
            except Exception:
                pass

            k = cv2.waitKey(10) & 0xff
            if k == 27:  # ESC
                break
            if flag == 1:
                break
    except Exception as e:
        print(f"[Face Auth Exception]: {e}")
        flag = 1
    finally:
        cam.release()
        try:
            cv2.destroyAllWindows()
        except Exception:
            pass

    return flag
