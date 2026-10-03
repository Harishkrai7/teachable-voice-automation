from dotenv import load_dotenv
load_dotenv()
import os

key = os.getenv("GEMINI_API_KEY", "")
print(f"Key loaded: {bool(key)}")
if key:
    print(f"Key prefix: {key[:8]}")
else:
    print("Key is EMPTY - check your .env file")
    exit(1)

try:
    import google.generativeai as genai
    genai.configure(api_key=key)
    model = genai.GenerativeModel("gemini-1.5-flash")
    resp = model.generate_content("Reply with only the word: WORKING")
    print(f"Gemini response: {resp.text.strip()}")
    print("SUCCESS - Gemini API is working!")
except Exception as e:
    print(f"FAILED - Error: {e}")
    print("Your API key may be invalid. Please get a fresh key from: https://aistudio.google.com/app/apikey")
