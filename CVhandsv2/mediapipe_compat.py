"""
Compatibility wrapper to restore the old mediapipe.solutions API
using the new MediaPipe Tasks API.
"""
import mediapipe as mp
from mediapipe.tasks import python
from mediapipe.tasks.python import vision
import numpy as np

# Download model if not exists
import os
import urllib.request

MODEL_PATH = 'hand_landmarker.task'
MODEL_URL = 'https://storage.googleapis.com/mediapipe-models/hand_landmarker/hand_landmarker/float16/1/hand_landmarker.task'

if not os.path.exists(MODEL_PATH):
    print(f"Downloading hand landmarker model to {MODEL_PATH}...")
    urllib.request.urlretrieve(MODEL_URL, MODEL_PATH)
    print("Download complete!")

# Create a solutions-like module
class Solutions:
    class hands:
        class Hands:
            def __init__(self, static_image_mode=True, min_detection_confidence=0.3, **kwargs):
                base_options = python.BaseOptions(model_asset_path=MODEL_PATH)
                options = vision.HandLandmarkerOptions(
                    base_options=base_options,
                    num_hands=2,
                    min_hand_detection_confidence=min_detection_confidence,
                    min_hand_presence_confidence=min_detection_confidence,
                    min_tracking_confidence=min_detection_confidence,
                    running_mode=vision.RunningMode.IMAGE if static_image_mode else vision.RunningMode.VIDEO
                )
                self.detector = vision.HandLandmarker.create_from_options(options)
                self.static_image_mode = static_image_mode
                
            def process(self, image):
                if self.static_image_mode:
                    if isinstance(image, np.ndarray):
                        mp_image = mp.Image(image_format=mp.ImageFormat.SRGB, data=image)
                    else:
                        mp_image = image
                    detection_result = self.detector.detect(mp_image)
                    return LegacyResults(detection_result)
                else:
                    # For video mode
                    if isinstance(image, np.ndarray):
                        mp_image = mp.Image(image_format=mp.ImageFormat.SRGB, data=image)
                    else:
                        mp_image = image
                    detection_result = self.detector.detect_for_video(mp_image, int(mp_image.timestamp_ms))
                    return LegacyResults(detection_result)
            
            def close(self):
                self.detector.close()
        
        HAND_CONNECTIONS = mp.tasks.vision.HandLandmarksConnections.HAND_CONNECTIONS
    
    # Drawing utilities compatibility
    class drawing_utils:
        @staticmethod
        def draw_landmarks(image, hand_landmarks, connections, landmark_drawing_spec=None, connection_drawing_spec=None):
            # Convert hand_landmarks to the format expected by new API
            if hasattr(hand_landmarks, '__iter__') and not isinstance(hand_landmarks, (str, bytes)):
                # It's already a list of landmarks
                landmarks_list = list(hand_landmarks)
            else:
                landmarks_list = [hand_landmarks]
            
            # Use the new drawing utils
            mp.tasks.vision.drawing_utils.draw_landmarks(
                image,
                landmarks_list[0] if landmarks_list else None,
                connections,
                landmark_drawing_spec or mp.tasks.vision.drawing_styles.get_default_hand_landmarks_style(),
                connection_drawing_spec or mp.tasks.vision.drawing_styles.get_default_hand_connections_style()
            )
    
    # Drawing styles compatibility  
    class drawing_styles:
        @staticmethod
        def get_default_hand_landmarks_style():
            return mp.tasks.vision.drawing_styles.get_default_hand_landmarks_style()
        
        @staticmethod
        def get_default_hand_connections_style():
            return mp.tasks.vision.drawing_styles.get_default_hand_connections_style()


class LegacyResults:
    """Wrapper to convert new API results to old API format"""
    def __init__(self, detection_result):
        self.detection_result = detection_result
        self.multi_hand_landmarks = []
        
        if detection_result.hand_landmarks:
            for landmarks in detection_result.hand_landmarks:
                # Convert to old format (list of landmark objects)
                self.multi_hand_landmarks.append(landmarks)


# Monkey patch mediapipe to add solutions
mp.solutions = Solutions()
