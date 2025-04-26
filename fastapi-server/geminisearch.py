import google.generativeai as genai
import os
from dotenv import load_dotenv

# Load your Gemini API key from .env
load_dotenv()
genai.configure(api_key=os.getenv("GEMINI_API_KEY"))

def summarize_query(query: str) -> str:
    """
    Takes a string query, processes it through Gemini API, and returns a general summary.
    """
    # Create a model instance
    model = genai.GenerativeModel('gemini-2.5-flash-preview-04-17')  # Make sure your Gemini version matches your access

    # Grounding the query
    response = model.generate_content(
    f"""
    For the health query: '{query}'
    
    Return ONLY 3 bullet points that Baymax would display to assist someone experiencing homelessness. 
    
    Format requirements:
    - Start each bullet with '*'
    - Each bullet must be 5-10 words maximum
    - No introduction, explanation, or conclusion text
    - No quotation marks around bullets
    
    Bullets must provide:
    - Actionable advice for limited-resource scenarios
    - Simple language appropriate for all literacy levels
    - Practical information relevant to unhoused individuals
    
    Example correct format:
    * Find free mental health drop-in centers.
    * Drink water every few hours.
    * Call 211 for emergency shelter tonight.
    """
)
    # Return the text part
    return response.text.strip()

# Example usage:
if __name__ == "__main__":
    user_query = input("Enter your query: ")
    summary = summarize_query(user_query)
    print(f"Summary: {summary}")


