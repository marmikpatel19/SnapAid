import os

# Suppress gRPC logs
os.environ["GRPC_VERBOSITY"] = "ERROR"
os.environ["GRPC_LOG_SEVERITY_LEVEL"] = "ERROR"

# Suppress absl logging
import absl.logging
absl.logging.set_verbosity('error')

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
    model = genai.GenerativeModel('models/gemini-1.5-flash-002')  # Make sure your Gemini version matches your access

    # Grounding the query
    response = model.generate_content(
    contents=f"""
    For the health query: '{query}'
    
    Return a realistic 3-4 line summary for someone experiencing homelessness.

    Requirements:
    - Use simple, practical, and reality-based advice.
    - Base advice on common web search results, not imagination.
    - Provide both quick analysis and helpful actionable steps.
    - No exaggerated or unrealistic suggestions.
    
    Output should sound grounded, empathetic, and easy to understand.
    """,
    tools="google_search_retrieval"
)
    # Return the text part
    return response.text.strip()

# Example usage:
if __name__ == "__main__":
    user_query = input("Enter your query: ")
    summary = summarize_query(user_query)
    print(f"Summary: {summary}")