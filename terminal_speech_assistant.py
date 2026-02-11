# terminal_speech_assistant.py - Speech-to-Text & Text-to-Speech Terminal App
import speech_recognition as sr
import pyttsx3  # For text-to-speech
import sys
import os
import json
from datetime import datetime

class TerminalSpeechAssistant:
    def __init__(self):
        self.recognizer = sr.Recognizer()
        self.tts_engine = None
        self.conversation_history = []
        self.history_file = "speech_history.json"
        
    def init_tts(self):
        """Initialize text-to-speech engine"""
        try:
            self.tts_engine = pyttsx3.init()
            
            # Configure TTS properties
            self.tts_engine.setProperty('rate', 180)  # Speech speed (words per minute)
            self.tts_engine.setProperty('volume', 0.9)  # Volume (0.0 to 1.0)
            
            # Get available voices
            voices = self.tts_engine.getProperty('voices')
            if voices:
                # Use the first available voice (usually system default)
                self.tts_engine.setProperty('voice', voices[0].id)
            
            return True
        except Exception as e:
            print(f"Failed to initialize TTS: {e}")
            return False
    
    def text_to_speech(self, text, save_audio=False):
        """Convert text to speech and optionally save as audio file"""
        if not self.tts_engine:
            if not self.init_tts():
                print("TTS engine not available")
                return False
        
        try:
            print(f"Speaking: '{text}'")
            
            if save_audio:
                # Generate filename with timestamp
                timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
                filename = f"speech_output_{timestamp}.mp3"
                
                # Save to file
                self.tts_engine.save_to_file(text, filename)
                self.tts_engine.runAndWait()
                print(f"💾 Audio saved as: {filename}")
                
                # Add to history
                self.conversation_history.append({
                    'type': 'tts',
                    'text': text,
                    'file': filename,
                    'timestamp': datetime.now().isoformat()
                })
                self.save_history()
                
            else:
                # Speak immediately
                self.tts_engine.say(text)
                self.tts_engine.runAndWait()
                
                # Add to history
                self.conversation_history.append({
                    'type': 'tts',
                    'text': text,
                    'timestamp': datetime.now().isoformat()
                })
                self.save_history()
            
            return True
            
        except Exception as e:
            print(f"TTS Error: {e}")
            return False
    
    def speech_to_text_mic(self):
        """Convert microphone speech to text"""
        try:
            with sr.Microphone() as source:
                print("\nAdjusting for ambient noise...")
                self.recognizer.adjust_for_ambient_noise(source, duration=1)
                
                print("Listening... Speak now!")
                print("(Speak clearly, wait for 'Listening...' message)")
                print("-" * 40)
                
                # Listen for speech
                audio = self.recognizer.listen(source, timeout=5, phrase_time_limit=10)
                
                print("Processing speech...")
                
                # Convert to text using Google Web Speech API
                text = self.recognizer.recognize_google(audio)
                
                print("\nRESULT:")
                print("=" * 40)
                print(f"You said: {text}")
                print(f"Length: {len(text)} characters")
                print(f"Words: {len(text.split())}")
                
                # Add to history
                self.conversation_history.append({
                    'type': 'stt',
                    'text': text,
                    'timestamp': datetime.now().isoformat()
                })
                self.save_history()
                
                # Save to text file
                with open("speech_output.txt", "a", encoding='utf-8') as f:
                    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                    f.write(f"[{timestamp}] {text}\n")
                print(f"Appended to 'speech_output.txt'")
                
                # Ask if user wants to hear it back
                choice = input("\nDo you want to hear this spoken back? (y/n): ").strip().lower()
                if choice == 'y':
                    self.text_to_speech(f"You said: {text}")
                
                return text
                
        except sr.WaitTimeoutError:
            print("Timeout: No speech detected")
        except sr.UnknownValueError:
            print("Could not understand audio")
        except sr.RequestError as e:
            print(f"API error: {e}")
        except Exception as e:
            print(f"Error: {e}")
            print("\nTROUBLESHOOTING:")
            print("1. Check if microphone is connected")
            print("2. Try speaking louder")
            print("3. Ensure pyaudio is installed")
            print("4. You can still use Option 2 (audio file)")
        
        return None
    
    def speech_to_text_file(self, file_path):
        """Convert audio file to text"""
        try:
            # Check if file exists
            if not os.path.exists(file_path):
                print(f"File not found: {file_path}")
                return None
                
            # Check if it's a WAV file (SpeechRecognition works best with WAV)
            if not file_path.lower().endswith('.wav'):
                print("Warning: For best results, use WAV format")
                choice = input("Continue anyway? (y/n): ").strip().lower()
                if choice != 'y':
                    return None
            
            with sr.AudioFile(file_path) as source:
                print("Reading audio file...")
                audio = self.recognizer.record(source)
                
                print("Converting to text...")
                text = self.recognizer.recognize_google(audio)
                
                print("\nRESULT:")
                print("=" * 40)
                print(f"Text from audio: {text}")
                
                # Add to history
                self.conversation_history.append({
                    'type': 'stt_file',
                    'file': file_path,
                    'text': text,
                    'timestamp': datetime.now().isoformat()
                })
                self.save_history()
                
                # Save to text file
                with open("audio_output.txt", "w", encoding='utf-8') as f:
                    f.write(text)
                print(f"Saved to 'audio_output.txt'")
                
                # Ask if user wants to hear it back
                choice = input("\nDo you want to hear this spoken? (y/n): ").strip().lower()
                if choice == 'y':
                    self.text_to_speech(f"The audio file says: {text}")
                
                return text
                
        except FileNotFoundError:
            print(f"File not found: {file_path}")
        except Exception as e:
            print(f"Error: {e}")
            print(f"\nFile must be in WAV format for best results")
        
        return None
    
    # ====================
    def interactive_tts(self):
        """Interactive text-to-speech mode"""
        print("\nTEXT TO SPEECH MODE")
        print("=" * 40)
        print("Type text and press Enter to hear it spoken")
        print("Commands:")
        print("  'exit' - Return to main menu")
        print("  'save <text>' - Save speech as audio file")
        print("  'voices' - List available voices")
        print("  'rate <speed>' - Set speech rate (100-300)")
        print("  'volume <0.1-1.0>' - Set volume")
        print("  'history' - Show speech history")
        print("-" * 40)
        
        while True:
            user_input = input("\nEnter text to speak (or command): ").strip()
            
            if user_input.lower() == 'exit':
                print("Returning to main menu...")
                break
            elif user_input.lower() == 'help':
                print("\nCommands:")
                print("  'exit' - Return to main menu")
                print("  'save <text>' - Save speech as audio file")
                print("  'voices' - List available voices")
                print("  'rate <speed>' - Set speech rate (100-300)")
                print("  'volume <0.1-1.0>' - Set volume")
                print("  'history' - Show speech history")
                continue
            elif user_input.lower() == 'voices':
                self.list_voices()
                continue
            elif user_input.lower().startswith('rate '):
                try:
                    rate = int(user_input[5:])
                    if 100 <= rate <= 300:
                        self.tts_engine.setProperty('rate', rate)
                        print(f"Speech rate set to: {rate}")
                    else:
                        print("Rate must be between 100 and 300")
                except ValueError:
                    print("Invalid rate value")
                continue
            elif user_input.lower().startswith('volume '):
                try:
                    volume = float(user_input[7:])
                    if 0.1 <= volume <= 1.0:
                        self.tts_engine.setProperty('volume', volume)
                        print(f"Volume set to: {volume}")
                    else:
                        print("Volume must be between 0.1 and 1.0")
                except ValueError:
                    print("Invalid volume value")
                continue
            elif user_input.lower() == 'history':
                self.show_history()
                continue
            
            # Check if user wants to save
            save_audio = user_input.lower().startswith('save ')
            text_to_speak = user_input[5:] if save_audio else user_input
            
            if text_to_speak:  # Don't speak empty text
                self.text_to_speech(text_to_speak, save_audio=save_audio)
            else:
                print("No text provided")
    # ====================
    
    def list_voices(self):
        """List available TTS voices"""
        if not self.tts_engine:
            self.init_tts()
        
        voices = self.tts_engine.getProperty('voices')
        print("\nAvailable Voices:")
        for i, voice in enumerate(voices):
            print(f"  {i+1}. {voice.name} ({voice.id})")
        
        if voices:
            choice = input("\nSelect voice number (or press Enter to skip): ").strip()
            if choice.isdigit():
                idx = int(choice) - 1
                if 0 <= idx < len(voices):
                    self.tts_engine.setProperty('voice', voices[idx].id)
                    print(f"Voice set to: {voices[idx].name}")
                    # Test the voice
                    self.tts_engine.say(f"This is voice {idx + 1}")
                    self.tts_engine.runAndWait()
    
    def save_history(self):
        """Save conversation history to JSON file"""
        try:
            with open(self.history_file, 'w', encoding='utf-8') as f:
                json.dump(self.conversation_history, f, indent=2, ensure_ascii=False)
        except Exception as e:
            print(f"Could not save history: {e}")
    
    def load_history(self):
        """Load conversation history from JSON file"""
        try:
            if os.path.exists(self.history_file):
                with open(self.history_file, 'r', encoding='utf-8') as f:
                    self.conversation_history = json.load(f)
                print(f"Loaded {len(self.conversation_history)} history entries")
        except Exception as e:
            print(f"Could not load history: {e}")
            self.conversation_history = []
    
    def show_history(self):
        """Display conversation history"""
        if not self.conversation_history:
            print("\nNo history yet")
            return
        
        print("\nSPEECH HISTORY:")
        print("=" * 60)
        for i, entry in enumerate(self.conversation_history[-10:]):  # Show last 10
            time_str = entry.get('timestamp', 'unknown').split('T')[1][:8]
            entry_type = entry.get('type', 'unknown')
            
            if entry_type == 'stt':
                prefix = "Heard:"
            elif entry_type == 'tts':
                prefix = "Spoke:"
            elif entry_type == 'stt_file':
                prefix = "From file:"
            else:
                prefix = "Unknown:"
            
            text_preview = entry.get('text', '')[:50]
            if len(entry.get('text', '')) > 50:
                text_preview += "..."
            
            print(f"{i+1:2d}. [{time_str}] {prefix} {text_preview}")
        
        print(f"\nTotal entries: {len(self.conversation_history)}")
        
        # Option to clear history
        choice = input("\nClear history? (y/n): ").strip().lower()
        if choice == 'y':
            self.conversation_history = []
            self.save_history()
            print("History cleared")
    
    def run(self):
        """Main application loop"""
        self.load_history()
        
        print("\n" + "="*60)
        print("TERMINAL SPEECH ASSISTANT")
        print("="*60)
        print("Speech-to-Text and Text-to-Speech Terminal Application")
        print("\nFeatures:")
        print("  1. Speech-to-Text (Use microphone)")
        print("  2. Speech-to-Text (Convert audio file)")
        print("  3. Text-to-Speech (Type and hear it)")
        print("  4. View Speech History")
        print("  5. TTS Settings (Voices, Speed, Volume)")
        print("  0. Exit Program")
        print("="*60)
        
        # Initialize TTS on startup
        if not self.init_tts():
            print("Text-to-Speech may not work properly")
        
        while True:
            try:
                print("\n" + "="*60)
                print("MAIN MENU")
                print("="*60)
                print("1. Speak → Text (Use microphone)")
                print("2. Audio File → Text (Convert WAV file)")
                print("3. Text → Speech (Type and hear it)")
                print("4. View Speech History")
                print("5. TTS Settings (Voices, Speed, Volume)")
                print("0. Exit Program")
                print("-"*60)
                
                choice = input("\nSelect an option (0-5): ").strip()
                
                if choice == "0":
                    print("\nThank you for using Terminal Speech Assistant!")
                    print(f"History saved to {self.history_file}")
                    print("="*60)
                    break
                    
                elif choice == "1":
                    self.speech_to_text_mic()
                    
                elif choice == "2":
                    # Show example files in current directory
                    wav_files = [f for f in os.listdir('.') if f.lower().endswith('.wav')]
                    if wav_files:
                        print("\nWAV files in current directory:")
                        for f in wav_files:
                            print(f"  - {f}")
                    
                    file_path = input("\nEnter path to audio file (or press Enter to list more): ").strip()
                    if file_path:
                        self.speech_to_text_file(file_path)
                    elif wav_files:
                        # Use first WAV file if user just pressed Enter
                        use_first = input(f"Use '{wav_files[0]}'? (y/n): ").strip().lower()
                        if use_first == 'y':
                            self.speech_to_text_file(wav_files[0])
                    else:
                        print("No file path provided")
                        
                elif choice == "3":
                    self.interactive_tts()
                    
                elif choice == "4":
                    self.show_history()
                    
                elif choice == "5":
                    # ====================
                    while True:
                        print("\nTTS SETTINGS")
                        print("="*40)
                        
                        # Get current settings
                        if self.tts_engine:
                            current_rate = self.tts_engine.getProperty('rate')
                            current_volume = self.tts_engine.getProperty('volume')
                            current_voice = self.tts_engine.getProperty('voice')
                            
                            print(f"Current speech rate: {current_rate} (100-300)")
                            print(f"Current volume: {current_volume:.1f} (0.1-1.0)")
                            print(f"Current voice ID: {current_voice}")
                        else:
                            print("TTS engine not initialized")
                        
                        print("\nSettings Menu:")
                        print("1. Change speech rate")
                        print("2. Change volume")
                        print("3. Change voice")
                        print("4. Test current settings")
                        print("0. Back to main menu")
                        
                        setting_choice = input("\nSelect setting option: ").strip()
                        
                        if setting_choice == "0":
                            print("Returning to main menu...")
                            break
                            
                        elif setting_choice == "1":
                            new_rate = input(f"Enter new speech rate (100-300) [{current_rate}]: ").strip()
                            if new_rate:
                                try:
                                    rate = int(new_rate)
                                    if 100 <= rate <= 300:
                                        self.tts_engine.setProperty('rate', rate)
                                        print(f"Rate set to {rate}")
                                        # Test new rate
                                        test_text = f"Testing speech rate {rate}"
                                        self.text_to_speech(test_text)
                                    else:
                                        print("Rate must be between 100 and 300")
                                except ValueError:
                                    print("Please enter a valid number")
                            else:
                                print("Rate not changed")
                                
                        elif setting_choice == "2":
                            new_vol = input(f"Enter new volume (0.1-1.0) [{current_volume:.1f}]: ").strip()
                            if new_vol:
                                try:
                                    vol = float(new_vol)
                                    if 0.1 <= vol <= 1.0:
                                        self.tts_engine.setProperty('volume', vol)
                                        print(f"Volume set to {vol:.1f}")
                                        # Test new volume
                                        test_text = f"Testing volume level {vol:.1f}"
                                        self.text_to_speech(test_text)
                                    else:
                                        print("Volume must be between 0.1 and 1.0")
                                except ValueError:
                                    print("Please enter a valid number")
                            else:
                                print("Volume not changed")
                                
                        elif setting_choice == "3":
                            self.list_voices()
                            
                        elif setting_choice == "4":
                            test_text = "This is a test of the text to speech system with current settings. Hello, world!"
                            print(f"\nTesting: '{test_text}'")
                            self.text_to_speech(test_text)
                        
                        else:
                            print("Invalid option")
                        
                        input("\nPress Enter to continue...")
                    # ====================
                    
                else:
                    print("Invalid option. Please select 0-5.")
                    
            except KeyboardInterrupt:
                print("\nProgram interrupted by user")
                self.save_history()
                break
            except Exception as e:
                print(f"\nUnexpected error: {e}")
                print("Restarting menu...")

def main():
    """Main entry point"""
    print("\n" + "="*60)
    print("TERMINAL SPEECH ASSISTANT - STARTING")
    print("="*60)
    
    # Check for required packages
    try:
        import speech_recognition
        print("SpeechRecognition loaded")
    except ImportError:
        print("SpeechRecognition not installed!")
        print("Run: pip install SpeechRecognition")
        return
    
    try:
        import pyttsx3
        print("pyttsx3 loaded")
    except ImportError:
        print("pyttsx3 not installed!")
        print("Run: pip install pyttsx3")
        return
    
    # Check for pyaudio (optional, for microphone)
    try:
        import pyaudio
        print("pyaudio loaded (microphone available)")
    except ImportError:
        print("pyaudio not installed (microphone disabled)")
        print("You can still use audio file functionality")
        print("Install with: pip install pyaudio")
    
    print("="*60)
    
    try:
        assistant = TerminalSpeechAssistant()
        assistant.run()
    except KeyboardInterrupt:
        print("\nGoodbye!")
    except Exception as e:
        print(f"\nFatal error: {e}")
        print("\nTROUBLESHOOTING:")
        print("1. Make sure all packages are installed")
        print("2. Check if microphone is connected")
        print("3. Try using audio files instead of microphone")
        print("4. Check error message above for details")

if __name__ == "__main__":
    main()