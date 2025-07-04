import os
import google.generativeai as genai
from PIL import Image
import io

# This function is correct as is.
def initialize_gemini(history=None):
    if history is None:
        history = []
    try:
        api_key = os.getenv("GOOGLE_API_KEY")
        genai.configure(api_key=api_key)
        model = genai.GenerativeModel('models/gemini-2.5-flash')
        chat = model.start_chat(history=history)
        return chat
    except Exception as e:
        print(f"CRITICAL ERROR initializing Gemini: {e}")
        return None

# --- THIS IS THE ONLY FUNCTION THAT IS CHANGED ---
# It now accepts a pre-built list of parts from app.py
def get_response_stream(chat_session, prompt_parts):
    """
    Yields chunks of a Gemini response for a given list of prompt parts.
    """
    if not chat_session:
        raise ConnectionError("Gemini chat session is not initialized.")
    try:
        # The prompt_parts list is already correctly formatted by app.py
        # We don't need to build it here anymore.
        print(f"-> Getting stream from Gemini with {len(prompt_parts)} part(s).")
        stream = chat_session.send_message(prompt_parts, stream=True)

        for chunk in stream:
            if chunk.text:
                yield chunk.text

    except Exception as e:
        print(f"Error during Gemini stream: {e}")
        raise e

# This function is correct as is.
def get_conversation_title(user_prompt: str, model_response: str) -> str:
    """
    Generates a short, descriptive title for a conversation.
    """
    try:
        model = genai.GenerativeModel('models/gemini-2.5-flash')
        title_prompt = (
            "Generate a very short, concise title (5-7 words maximum) for the following "
            "conversation. The title should be suitable for a sidebar history entry. "
            "Do not use quotation marks in the title.\n\n"
            f"USER: {user_prompt}\n\n"
            f"MODEL: {model_response}"
        )
        response = model.generate_content(title_prompt)
        title = response.text.strip().replace('"', '')
        print(f"-> Generated title: '{title}'")
        return title
    except Exception as e:
        print(f"Error generating conversation title: {e}")
        return "New Conversation"

# This function is correct as is.
def get_realtime_response_stream(prompt_with_context: str):
    try:
        api_key = os.getenv("GOOGLE_API_KEY")
        genai.configure(api_key=api_key)
        model = genai.GenerativeModel('models/gemini-2.5-flash')
        safety_config = {
            'HARM_CATEGORY_HARASSMENT': 'BLOCK_NONE',
            'HARM_CATEGORY_HATE_SPEECH': 'BLOCK_NONE',
            'HARM_CATEGORY_SEXUALLY_EXPLICIT': 'BLOCK_NONE',
            'HARM_CATEGORY_DANGEROUS_CONTENT': 'BLOCK_NONE',
        }
        print(f"-> Getting REALTIME stream from Gemini with prompt: '{prompt_with_context}'")
        response_stream = model.generate_content(
            prompt_with_context,
            stream=True,
            safety_settings=safety_config
        )
        for chunk in response_stream:
            if chunk.text:
                yield chunk.text
    except Exception as e:
        print(f"Error during REALTIME Gemini stream: {e}")
        raise e