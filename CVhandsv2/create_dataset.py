import os
import pickle

import mediapipe as mp
import cv2
import matplotlib.pyplot as plt


mp_hands = mp.solutions.hands
mp_drawing = mp.solutions.drawing_utils
mp_drawing_styles = mp.solutions.drawing_styles

hands = mp_hands.Hands(static_image_mode=True, min_detection_confidence=0.3)

DATA_DIR = './data'

data = []
labels = []
for dir_ in os.listdir(DATA_DIR):
    dir_path = os.path.join(DATA_DIR, dir_)
    # Skip if not a directory (e.g., .gitignore file)
    if not os.path.isdir(dir_path):
        continue
    
    for img_path in os.listdir(dir_path):
        # Skip if not an image file
        if not img_path.lower().endswith(('.jpg', '.jpeg', '.png', '.bmp')):
            continue
        
        img_filepath = os.path.join(DATA_DIR, dir_, img_path)
        img = cv2.imread(img_filepath)
        
        # Skip if image couldn't be loaded
        if img is None:
            print(f"Warning: Could not load image {img_filepath}")
            continue
        
        data_aux = []

        x_ = []
        y_ = []

        img_rgb = cv2.cvtColor(img, cv2.COLOR_BGR2RGB)

        results = hands.process(img_rgb)
        if results.multi_hand_landmarks:
            # Process only the first detected hand to ensure consistent data length
            hand_landmarks = results.multi_hand_landmarks[0]
            
            # MediaPipe hands have 21 landmarks
            # Each landmark has x and y coordinates
            for i in range(len(hand_landmarks.landmark)):
                x = hand_landmarks.landmark[i].x
                y = hand_landmarks.landmark[i].y

                x_.append(x)
                y_.append(y)

            # Normalize coordinates relative to the minimum values
            for i in range(len(hand_landmarks.landmark)):
                x = hand_landmarks.landmark[i].x
                y = hand_landmarks.landmark[i].y
                data_aux.append(x - min(x_))
                data_aux.append(y - min(y_))

            # Ensure consistent length: 21 landmarks * 2 coordinates = 42 values
            if len(data_aux) == 42:
                data.append(data_aux)
                labels.append(dir_)
            else:
                print(f"Warning: Skipping {img_filepath} - unexpected data length: {len(data_aux)}")

f = open('data.pickle', 'wb')
pickle.dump({'data': data, 'labels': labels}, f)
f.close()
