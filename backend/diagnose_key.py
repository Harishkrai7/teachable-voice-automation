from dotenv import load_dotenv
load_dotenv()
import os

key = os.getenv("GEMINI_API_KEY", "")
print(f"Key loaded: {bool(key)}")
print(f"Key starts with: {key[:10] if key else 'EMPTY'}")
print()

try:
    import google.generativeai as genai
    genai.configure(api_key=key)

    print("Listing all models your key can access...")
    print("-" * 50)
    models_found = []
    for m in genai.list_models():
        if "generateContent" in m.supported_generation_methods:
            print(f"  AVAILABLE: {m.name}")
            models_found.append(m.name)
    print("-" * 50)
    print(f"Total models found: {len(models_found)}")
    if models_found:
        print("Key is WORKING. Send me the model names listed above.")
    else:
        print("No models found - key may be wrong type.")
except Exception as e:
    print(f"Error: {e}")
