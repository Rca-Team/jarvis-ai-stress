import os
import cv2

# Base directory for auth
base_dir = os.path.dirname(os.path.abspath(__file__))
samples_dir = os.path.join(base_dir, 'samples')
os.makedirs(samples_dir, exist_ok=True)
cascade_path = os.path.join(base_dir, 'haarcascade_frontalface_default.xml')

cam = cv2.VideoCapture(0, cv2.CAP_DSHOW) # create a video capture object
cam.set(3, 640) # set video FrameWidth
cam.set(4, 480) # set video FrameHeight

detector = cv2.CascadeClassifier(cascade_path)

face_id = input("Enter a Numeric user ID here (e.g. 1): ")
total_samples = 200

print(f"Taking {total_samples} samples, please look at the camera...")
count = 0

while True:
    ret, img = cam.read()
    if not ret:
        print("Failed to capture image from camera.")
        break

    converted_image = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
    faces = detector.detectMultiScale(converted_image, 1.3, 5)

    for (x, y, w, h) in faces:
        cv2.rectangle(img, (x, y), (x + w, y + h), (255, 0, 0), 2)
        count += 1
        
        sample_path = os.path.join(samples_dir, f"face.{face_id}.{count}.jpg")
        cv2.imwrite(sample_path, converted_image[y:y+h, x:x+w])

    # Display progress on the frame
    cv2.putText(img, f"Samples: {count}/{total_samples}", (20, 40), cv2.FONT_HERSHEY_SIMPLEX, 0.8, (0, 255, 0), 2)
    cv2.imshow('Face Sampling', img)

    k = cv2.waitKey(50) & 0xff
    if k == 27: # Press 'ESC' to stop
        break
    elif count >= total_samples:
        break

print("Samples taken successfully! Now closing the camera...")
cam.release()
cv2.destroyAllWindows()