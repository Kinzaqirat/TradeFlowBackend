"""
Google Gemini AI client wrapper.
Handles model initialization and message sending.
API key is loaded from environment — never exposed to frontend.
"""
import google.generativeai as genai
from app.config import settings


def get_gemini_model():
    """Initialize and return the Gemini 2.5 Flash model."""
    if not settings.GEMINI_API_KEY:
        raise ValueError("GEMINI_API_KEY is not configured in environment variables.")
    genai.configure(api_key=settings.GEMINI_API_KEY)
    return genai.GenerativeModel("models/gemini-2.5-flash")


async def send_message(system_context: str, user_message: str) -> str:
    """
    Send a message to Gemini with trading context and return the response text.

    Args:
        system_context: Background info about the trader's data to inject
        user_message: The trader's actual question

    Returns:
        AI response as string
    """
    model = get_gemini_model()
    full_prompt = f"{system_context}\n\nTrader's question: {user_message}"

    try:
        # Use async version to avoid blocking the event loop
        response = await model.generate_content_async(full_prompt)

        # Check if response was blocked or empty
        if not response.candidates:
            return "I apologize, but I couldn't generate a response. The prompt might have been blocked or no content was returned."

        return response.text
    except Exception as e:
        # Wrap API errors in RuntimeError to be caught by the router as 502
        raise RuntimeError(f"Gemini API error: {str(e)}")
