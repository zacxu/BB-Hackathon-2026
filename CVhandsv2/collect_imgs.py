import os

import cv2


DATA_DIR = './data'
if not os.path.exists(DATA_DIR):
    os.makedirs(DATA_DIR)

number_of_classes = 24
dataset_size = 100

# Try to initialize camera with multiple indices and backends
cap = None
camera_index = None
backends = [
    (cv2.CAP_DSHOW, 'DirectShow'),
    (cv2.CAP_ANY, 'Default'),
]

print("Attempting to initialize camera...")
for backend_id, backend_name in backends:
    for index in range(5):  # Try indices 0-4
        try:
            test_cap = cv2.VideoCapture(index, backend_id)
            if test_cap.isOpened():
                # Test if we can actually read a frame
                ret, frame = test_cap.read()
                if ret and frame is not None:
                    cap = test_cap
                    camera_index = index
                    print(f"✓ Camera found at index {index} using {backend_name} backend")
                    break
                else:
                    test_cap.release()
            else:
                test_cap.release()
        except Exception as e:
            if test_cap:
                test_cap.release()
            continue
    
    if cap is not None:
        break

if cap is None or not cap.isOpened():
    print("✗ Error: Could not initialize camera!")
    print("Please check:")
    print("  1. Camera is connected and powered on")
    print("  2. No other application is using the camera")
    print("  3. Camera permissions are enabled in Windows settings")
    print("  4. Camera drivers are installed")
    exit(1)
for j in range(number_of_classes):
    if not os.path.exists(os.path.join(DATA_DIR, str(j))):
        os.makedirs(os.path.join(DATA_DIR, str(j)))

    print('Collecting data for class {}'.format(j))

    done = False
    while True:
        ret, frame = cap.read()
        if not ret or frame is None:
            print("Warning: Could not read frame from camera. Trying to reconnect...")
            cap.release()
            cap = cv2.VideoCapture(camera_index)
            continue
        
        cv2.putText(frame, 'Ready? Press "Q" ! :)', (100, 50), cv2.FONT_HERSHEY_SIMPLEX, 1.3, (0, 255, 0), 3,
                    cv2.LINE_AA)
        cv2.imshow('frame', frame)
        if cv2.waitKey(25) == ord('q'):
            break

    counter = 0
    while counter < dataset_size:
        ret, frame = cap.read()
        if not ret or frame is None:
            print(f"Warning: Could not read frame {counter}. Skipping...")
            continue
        
        cv2.imshow('frame', frame)
        cv2.waitKey(25)
        q
        filepath = os.path.join(DATA_DIR, str(j), '{}.jpg'.format(counter))
        if cv2.imwrite(filepath, frame):
            print(f"Saved image {counter + 1}/{dataset_size} for class {j}")
        else:
            print(f"Error: Could not save image {counter} for class {j}")
        
        counter += 1

cap.release()
cv2.destroyAllWindows()
