import pickle
import time
import sys
import os
import threading

import cv2
import mediapipe as mp
import numpy as np

# --web: run by OmniBridge; Camera/Start = run script + send Q, Stop = send ESC. Frame in .media, output in User A message box.
WEB_MODE = "--web" in sys.argv
FRAME_OUTPUT_PATH = os.environ.get("FRAME_OUTPUT_PATH", "gesture_frame.jpg")
# Optional file-based I/O when script runs in new console (e.g. Windows camera access)
GESTURE_CMD_FILE = os.environ.get("GESTURE_CMD_FILE")
GESTURE_OUTPUT_FILE = os.environ.get("GESTURE_OUTPUT_FILE")

_next_command = None
_should_exit = False

def _read_web_command():
    """In web mode: read command from stdin or from file if GESTURE_CMD_FILE is set."""
    global _next_command, _should_exit
    if GESTURE_CMD_FILE and os.path.isfile(GESTURE_CMD_FILE):
        try:
            with open(GESTURE_CMD_FILE, "r") as f:
                line = f.read().strip().upper()
            os.remove(GESTURE_CMD_FILE)
            if line == "Q":
                _next_command = "Q"
            elif line in ("ESC", "ESCAPE", "27"):
                _should_exit = True
        except Exception:
            pass
        return
    # stdin path (when not using file)
    pass  # stdin_reader thread handles it

def stdin_reader():
    global _next_command, _should_exit
    while True:
        try:
            line = sys.stdin.readline()
            if not line:
                break
            line = line.strip().upper()
            if line == "Q":
                _next_command = "Q"
            elif line in ("ESC", "ESCAPE", "27"):
                _should_exit = True
                break
        except Exception:
            break

if WEB_MODE and not GESTURE_CMD_FILE:
    threading.Thread(target=stdin_reader, daemon=True).start()

_script_dir = os.path.dirname(os.path.abspath(__file__))
_model_path = os.path.join(_script_dir, "model.p")
model_dict = pickle.load(open(_model_path, "rb"))
model = model_dict["model"]

cap = None
camera_index = None
backends = [
    (cv2.CAP_DSHOW, "DirectShow"),
    (cv2.CAP_ANY, "Default"),
]

if not WEB_MODE:
    print("Attempting to initialize camera...")
for backend_id, backend_name in backends:
    for index in range(5):
        try:
            test_cap = cv2.VideoCapture(index, backend_id)
            if test_cap.isOpened():
                ret, frame = test_cap.read()
                if ret and frame is not None:
                    cap = test_cap
                    camera_index = index
                    if not WEB_MODE:
                        print(f"✓ Camera found at index {index} using {backend_name} backend")
                    break
                else:
                    test_cap.release()
            else:
                test_cap.release()
        except Exception:
            if test_cap:
                test_cap.release()
            continue
    if cap is not None:
        break

if cap is None or not cap.isOpened():
    print("✗ Error: Could not initialize camera!", flush=True)
    if WEB_MODE:
        try:
            fallback = np.zeros((240, 320, 3), dtype=np.uint8)
            fallback[:] = (60, 60, 60)
            cv2.putText(fallback, "Camera unavailable", (20, 120), cv2.FONT_HERSHEY_SIMPLEX, 0.8, (255, 255, 255), 2, cv2.LINE_AA)
            cv2.imwrite(FRAME_OUTPUT_PATH, fallback)
        except Exception:
            pass
    exit(1)

mp_hands = mp.solutions.hands
mp_drawing = mp.solutions.drawing_utils
mp_drawing_styles = mp.solutions.drawing_styles

hands = mp_hands.Hands(static_image_mode=False, min_detection_confidence=0.3)

labels_dict = {
    0: "A", 1: "B", 2: "C", 3: "D", 4: "E", 5: "F", 6: "G", 7: "H", 8: "I",
    9: "K", 10: "L", 11: "M", 12: "N", 13: "O", 14: "P", 15: "Q", 16: "R",
    17: "S", 18: "T", 19: "U", 20: "V", 21: "W", 22: "X", 23: "Y",
}

last_detected_letter = None
detection_start_time = None
CONFIRMATION_TIME = 2
confirmed_letter = None

is_recording = False
recorded_string = ""
_last_output_sent = None

if not WEB_MODE:
    print("Press 'q' to start/stop")
    print("Hold your hand gesture for 2 seconds to confirm the letter")

if WEB_MODE:
    for _ in range(20):
        cap.read()
        time.sleep(0.02)

while True:
    if WEB_MODE and _should_exit:
        if GESTURE_OUTPUT_FILE:
            try:
                with open(GESTURE_OUTPUT_FILE, "w") as f:
                    f.write(recorded_string)
            except Exception:
                pass
        break

    if WEB_MODE:
        _read_web_command()
    if WEB_MODE and _next_command == "Q":
        _next_command = None
        is_recording = not is_recording
        if is_recording:
            recorded_string = ""
            detection_start_time = None
            last_detected_letter = None
            confirmed_letter = None

    data_aux = []
    x_ = []
    y_ = []

    ret, frame = cap.read()
    if not ret or frame is None:
        if WEB_MODE:
            time.sleep(0.03)
        continue

    H, W, _ = frame.shape
    frame_rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
    results = hands.process(frame_rgb)

    if results.multi_hand_landmarks:
        hand_landmarks = results.multi_hand_landmarks[0]
        mp_drawing.draw_landmarks(
            frame,
            hand_landmarks,
            mp_hands.HAND_CONNECTIONS,
            mp_drawing_styles.get_default_hand_landmarks_style(),
            mp_drawing_styles.get_default_hand_connections_style(),
        )

        for i in range(len(hand_landmarks.landmark)):
            x = hand_landmarks.landmark[i].x
            y = hand_landmarks.landmark[i].y
            x_.append(x)
            y_.append(y)

        for i in range(len(hand_landmarks.landmark)):
            x = hand_landmarks.landmark[i].x
            y = hand_landmarks.landmark[i].y
            data_aux.append(x - min(x_))
            data_aux.append(y - min(y_))

        if len(data_aux) == 42:
            x1 = int(min(x_) * W) - 10
            y1 = int(min(y_) * H) - 10
            x2 = int(max(x_) * W) + 10
            y2 = int(max(y_) * H) + 10

            prediction = model.predict([np.asarray(data_aux)])
            predicted_character = labels_dict[int(prediction[0])]
            current_time = time.time()

            if predicted_character != last_detected_letter:
                last_detected_letter = predicted_character
                detection_start_time = current_time
                confirmed_letter = None
            else:
                if detection_start_time is not None:
                    elapsed_time = current_time - detection_start_time
                    if elapsed_time >= CONFIRMATION_TIME:
                        if is_recording:
                            recorded_string += predicted_character
                            detection_start_time = current_time
                        if is_recording:
                            cv2.rectangle(frame, (x1, y1), (x2, y2), (0, 255, 0), 1)
                            cv2.putText(frame, f"{predicted_character}", (x1, y1 - 10), cv2.FONT_HERSHEY_SIMPLEX, 1.3, (0, 255, 0), 2, cv2.LINE_AA)
                        else:
                            cv2.rectangle(frame, (x1, y1), (x2, y2), (255, 255, 255), 1)
                            cv2.putText(frame, predicted_character, (x1, y1 - 10), cv2.FONT_HERSHEY_SIMPLEX, 1.3, (255, 255, 255), 2, cv2.LINE_AA)
                    else:
                        remaining_time = CONFIRMATION_TIME - elapsed_time
                        progress = elapsed_time / CONFIRMATION_TIME
                        if is_recording:
                            bar_width = int((x2 - x1) * progress)
                            cv2.rectangle(frame, (x1, y2 + 5), (x1 + bar_width, y2 + 15), (0, 255, 255), -1)
                            cv2.rectangle(frame, (x1, y2 + 5), (x2, y2 + 15), (255, 255, 255), 2)
                            cv2.putText(frame, f"{predicted_character} ({remaining_time:.1f}s)", (x1, y1 - 10), cv2.FONT_HERSHEY_SIMPLEX, 1.3, (255, 255, 255), 2, cv2.LINE_AA)
                        else:
                            cv2.putText(frame, predicted_character, (x1, y1 - 10), cv2.FONT_HERSHEY_SIMPLEX, 1.3, (255, 255, 255), 2, cv2.LINE_AA)
                        cv2.rectangle(frame, (x1, y1), (x2, y2), (255, 255, 255), 1)
                else:
                    detection_start_time = current_time
                    cv2.rectangle(frame, (x1, y1), (x2, y2), (255, 255, 255), 1)
                    cv2.putText(frame, predicted_character, (x1, y1 - 10), cv2.FONT_HERSHEY_SIMPLEX, 1.3, (255, 255, 255), 2, cv2.LINE_AA)
    else:
        last_detected_letter = None
        detection_start_time = None
        confirmed_letter = None

    if is_recording:
        cv2.putText(frame, "Recording", (10, 30), cv2.FONT_HERSHEY_SIMPLEX, 0.8, (0, 0, 255), 2, cv2.LINE_AA)
        cv2.putText(frame, f"Output text: {recorded_string}", (10, 60), cv2.FONT_HERSHEY_SIMPLEX, 0.7, (255, 255, 255), 2, cv2.LINE_AA)

    if WEB_MODE:
        try:
            cv2.imwrite(FRAME_OUTPUT_PATH, frame)
        except Exception:
            pass
        if recorded_string != _last_output_sent:
            _last_output_sent = recorded_string
            print("OUTPUT: " + recorded_string, flush=True)
            if GESTURE_OUTPUT_FILE:
                try:
                    with open(GESTURE_OUTPUT_FILE, "w") as f:
                        f.write(recorded_string)
                except Exception:
                    pass
        time.sleep(0.03)
        continue

    key = cv2.waitKey(1) & 0xFF
    if key == ord("q"):
        is_recording = not is_recording
        if is_recording:
            recorded_string = ""
            detection_start_time = None
            last_detected_letter = None
            confirmed_letter = None
            print("\n>>> Recording started. Confirmed letters will be added")
        else:
            if recorded_string:
                print(f"\n>>> Recording stopped. Final string: '{recorded_string}'")
            else:
                print("\n>>> Recording stopped. No letters were recorded.")
    elif key == 27:
        if is_recording and recorded_string:
            print(f"\n>>> Exiting. Final recorded string: '{recorded_string}'")
        break

    cv2.imshow("frame", frame)

cap.release()
if not WEB_MODE:
    cv2.destroyAllWindows()
