import openai
import speech_recognition as sr
import re
import threading
import time
import os
from dotenv import load_dotenv
import json
from typing import Dict, List, Optional, Union

# Load environment variables from .env file
load_dotenv()

# OpenAI API configuration
openai.api_key = os.getenv("OPENAI_API_KEY")

# Constants
PAUSE_THRESHOLD = 0.8  # Seconds of silence to consider a pause
EMERGENCY_KEYWORDS = [
    "chest pain", "stroke", "heart attack", "seizure", "ambulance", 
    "911", "emergency", "collapsed", "unconscious", "can't breathe",
    "severe bleeding", "anaphylaxis", "allergic reaction"
]

class MedicalTranscriber:
    def __init__(self):
        self.recognizer = sr.Recognizer()
        self.recognizer.pause_threshold = PAUSE_THRESHOLD
        self.microphone = sr.Microphone()
        self.is_listening = False
        self.transcription_history = []
        self.current_query = ""
        
        # Calibrate for ambient noise
        with self.microphone as source:
            print("Calibrating for ambient noise... Please be silent.")
            self.recognizer.adjust_for_ambient_noise(source, duration=2)
            print("Calibration complete.")
    
    def start_listening(self):
        """Start the listening thread and process speech continuously"""
        self.is_listening = True
        self.listen_thread = threading.Thread(target=self._listen_continuously)
        self.listen_thread.daemon = True
        self.listen_thread.start()
        print("Listening for voice input... (Press Ctrl+C to exit)")
        
        try:
            while self.is_listening:
                time.sleep(0.1)  # Prevent CPU overuse
        except KeyboardInterrupt:
            self.stop_listening()
            print("\nTranscription stopped.")
    
    def stop_listening(self):
        """Stop the listening thread"""
        self.is_listening = False
        if hasattr(self, 'listen_thread'):
            self.listen_thread.join(1.0)
    
    def _listen_continuously(self):
        """Background thread for continuous listening"""
        while self.is_listening:
            try:
                with self.microphone as source:
                    print("\nListening...")
                    audio = self.recognizer.listen(source)
                    print("Processing speech...")
                
                # Use Whisper API for speech recognition
                try:
                    transcript = self._transcribe_with_whisper(audio)
                    if transcript.strip():
                        self.current_query += " " + transcript
                        print(f"Transcribed: {transcript}")
                        
                        # Check if this is the end of a thought or question
                        if self._is_end_of_thought(transcript):
                            self._process_query()
                            self.current_query = ""
                except Exception as e:
                    print(f"Error transcribing audio: {e}")
            
            except sr.WaitTimeoutError:
                continue
            except Exception as e:
                print(f"Error in listening loop: {e}")
                continue
    
    def _transcribe_with_whisper(self, audio_data):
        """Transcribe audio using OpenAI's Whisper API"""
        audio_file = self._save_audio_temp(audio_data)
        
        try:
            # Create a client instance using the newer OpenAI Python client syntax
            client = openai.OpenAI()
            
            print(f"DEBUG - Attempting to transcribe file: {audio_file}")
            print(f"DEBUG - File exists: {os.path.exists(audio_file)}")
            print(f"DEBUG - File size: {os.path.getsize(audio_file)} bytes")
            
            # Open the file in binary mode and create the transcription
            with open(audio_file, "rb") as file:
                # Use the correct method from the newer API
                response = client.audio.transcriptions.create(
                    model="whisper-1",
                    file=file,
                    response_format="text",
                    language="en"
                )
            
            # Clean up the temporary file
            os.remove(audio_file)
            
            # With the newer API, response should be directly usable as a string
            print(f"DEBUG - Transcription completed successfully: {response[:30]}...")
            return response
                
        except Exception as e:
            # Print detailed error information
            print(f"DEBUG - Transcription error: {type(e).__name__}: {str(e)}")
            import traceback
            traceback.print_exc()
            
            # Clean up temp file if it exists
            if os.path.exists(audio_file):
                os.remove(audio_file)
            
            # Re-raise the exception to be handled by the caller
            raise e
    
    def _save_audio_temp(self, audio_data):
        """Save audio data to a temporary WAV file"""
        temp_file = "temp_audio.wav"
        with open(temp_file, "wb") as f:
            f.write(audio_data.get_wav_data())
        return temp_file
    
    def _is_end_of_thought(self, text):
        """Determine if the text likely represents the end of a complete thought"""
        # Check for typical sentence endings
        if re.search(r'[.?!]\s*$', text):
            return True
        
        # Check for question indicators
        if re.search(r'\b(what|how|why|when|where|who|which|is|are|can|could|would|should|do|does)\b', 
                    text.lower()):
            return True
            
        # Check for long enough pause after speaking (handled by recognizer.pause_threshold)
        return False
    
    def _process_query(self):
        """Process the completed query and generate a response"""
        query = self.current_query.strip()
        if not query:
            return
            
        self.transcription_history.append(query)
        print(f"\nProcessing full query: '{query}'")
        
        # Check for emergency keywords
        if self._check_for_emergency(query):
            self._display_emergency_warning()
        
        # Generate medical response
        response = self._generate_medical_response(query)
        print("\n" + "="*80)
        print("MEDICAL INFORMATION:")
        print(response)
        print("="*80)
    
    def _check_for_emergency(self, text):
        """Check if the text contains emergency medical keywords"""
        text_lower = text.lower()
        for keyword in EMERGENCY_KEYWORDS:
            if keyword in text_lower:
                return True
        return False
    
    def _display_emergency_warning(self):
        """Display warning for potential medical emergencies"""
        warning = """
        ⚠️ WARNING: POSSIBLE MEDICAL EMERGENCY DETECTED ⚠️
        Please seek immediate medical attention by calling emergency services.
        """
        print("\n" + "!"*80)
        print(warning)
        print("!"*80)
    
    def _generate_medical_response(self, query):
        """Generate medical information response using GPT"""
        try:
            # Detect query type (symptom, drug, procedure, or general)
            query_type = self._detect_query_type(query)
            
            # Construct prompt based on query type
            prompt = self._construct_medical_prompt(query, query_type)
            
            print(f"DEBUG - Generating medical response for query type: {query_type}")
            
            # Call GPT API with new client format
            client = openai.OpenAI()
            response = client.chat.completions.create(
                model="gpt-4",  # Using GPT-4 for medical accuracy
                messages=[
                    {"role": "system", "content": prompt["system"]},
                    {"role": "user", "content": prompt["user"]}
                ],
                max_tokens=400,  # For approximately 200 words
                temperature=0.3  # Lower temperature for more factual responses
            )
            
            # Access the content properly in the response object
            content = response.choices[0].message.content
            print(f"DEBUG - Response generated successfully: {content[:30]}...")
            return content
            
        except Exception as e:
            print(f"DEBUG - Error generating medical response: {type(e).__name__}: {str(e)}")
            import traceback
            traceback.print_exc()
            return f"Error generating medical information: {e}\n\nPlease consult with a healthcare professional for accurate medical advice."
    
    def _detect_query_type(self, query):
        """Detect the type of medical query"""
        query_lower = query.lower()
        
        # Drug-related query
        drug_indicators = ["drug", "medication", "medicine", "pill", "prescription", 
                          "take", "dose", "dosage", "side effect", "interact"]
        
        # Symptom-related query
        symptom_indicators = ["symptom", "feel", "pain", "ache", "hurt", "sore", 
                             "fever", "cough", "headache", "nausea", "dizzy"]
        
        # Procedure or condition query
        procedure_indicators = ["surgery", "operation", "procedure", "treatment", 
                               "therapy", "diagnosis", "condition", "disease", 
                               "disorder", "syndrome", "recovery"]
        
        # Count indicator words for each category
        drug_count = sum(1 for word in drug_indicators if word in query_lower)
        symptom_count = sum(1 for word in symptom_indicators if word in query_lower)
        procedure_count = sum(1 for word in procedure_indicators if word in query_lower)
        
        # Determine the most likely query type
        max_count = max(drug_count, symptom_count, procedure_count)
        
        if max_count == 0:
            return "general"  # General medical query
        elif max_count == drug_count:
            return "drug"
        elif max_count == symptom_count:
            return "symptom"
        else:
            return "procedure"
    
    def _construct_medical_prompt(self, query, query_type):
        """Construct appropriate prompt based on query type"""
        base_system_prompt = """
        You are a medical information assistant providing factual, evidence-based information.
        Keep your answers concise (under 200 words), neutral, and focused on the query.
        Always include a disclaimer that this information does not replace professional medical advice.
        """
        
        type_specific_prompts = {
            "drug": base_system_prompt + """
            For drug queries, provide:
            1. Primary uses of the medication
            2. Common side effects
            3. Important warnings or precautions
            4. Potential major drug interactions if relevant
            """,
            
            "symptom": base_system_prompt + """
            For symptom queries, provide:
            1. Possible common causes (without diagnosing)
            2. When medical attention is typically recommended
            3. General information about self-management if appropriate
            """,
            
            "procedure": base_system_prompt + """
            For procedures or conditions, provide:
            1. Brief description of the procedure/condition
            2. Typical treatment approaches
            3. General recovery information if applicable
            4. Common risk factors if discussing a condition
            """,
            
            "general": base_system_prompt + """
            Provide factual medical information that directly answers the query.
            If asked to define terms, provide both layman's terms and a brief technical description.
            """
        }
        
        user_prompt = f"Please provide medical information about: {query}"
        
        return {
            "system": type_specific_prompts.get(query_type, type_specific_prompts["general"]),
            "user": user_prompt
        }


def main():
    print("Medical Voice Transcription and Analysis System")
    print("-----------------------------------------------")
    print("This system transcribes spoken medical queries and provides")
    print("relevant medical information in real-time.")
    print("\nNOTE: This system is for informational purposes only and")
    print("does not replace professional medical advice or diagnosis.")
    print("-----------------------------------------------")
    
    # Check for API key
    if not os.getenv("OPENAI_API_KEY"):
        print("\nERROR: OpenAI API key not found.")
        print("Please set your API key in a .env file or environment variable as OPENAI_API_KEY")
        return
    
    # Initialize and start the transcriber
    transcriber = MedicalTranscriber()
    transcriber.start_listening()


if __name__ == "__main__":
    main()