import os
from typing import Literal

from google import generativeai as genai
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Configure Gemini
genai.configure(api_key=os.getenv("GEMINI_API_KEY"))

# Define the workflow types
WorkflowType = Literal["A", "B", "C", "D", "E", "F", "G"]

async def determine_workflow(user_prompt: str) -> WorkflowType:
    """
    Use Gemini to determine which workflow to execute based on the user's prompt.
    
    Args:
        user_prompt: The user's input prompt
        
    Returns:
        A single letter indicating the workflow type (A-G)
    """
    model = genai.GenerativeModel('gemini-2.0-flash-001')
    
    prompt = f"""
    You are an orchestration agent for an app to help homeless people get healthcare support.
    Based on the following conversation, decide which of the following categories best fits and return ONLY the corresponding letter:
    
    A: Physical injury (visible wounds, broken bones, etc.)
    B: Internal medical problem (non-physical issues like fever, pain, mental health, etc.)
    C: Resource locator - shelter
    D: Resource locator - pharmacy
    E: Resource locator - medical center
    F: Resource locator - washroom
    G: Resource locator - physical resource (clothing, food, etc.)
    
    User prompt: {user_prompt}
    
    Return ONLY the single letter (A-G) that best matches the user's needs.
    """
    
    response = model.generate_content(prompt)
    workflow_type = response.text.strip().upper()
    
    # Validate the response
    if workflow_type not in ["A", "B", "C", "D", "E", "F", "G"]:
        raise ValueError(f"Invalid workflow type returned: {workflow_type}")
    
    return workflow_type 