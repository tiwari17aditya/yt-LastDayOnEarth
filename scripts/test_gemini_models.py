"""Test and verify active Google Gemini models dynamically using Google GenAI SDK."""

import os
import sys
from pathlib import Path
from dotenv import load_dotenv

# Add project root to sys.path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

load_dotenv()


def test_models(api_key: str = None) -> None:
    api_key = api_key or os.getenv("GEMINI_API_KEY")
    if not api_key or api_key == "your-gemini-api-key-here":
        print("=" * 70)
        print(" [INFO] No GEMINI_API_KEY configured in .env")
        print(" The pipeline currently runs with the Local Heuristic Event Engine,")
        print(" which generates accurate 1-second gameplay action cues locally.")
        print("=" * 70)
        print("To test live Gemini models, get a free API key at:")
        print(" -> https://aistudio.google.com/app/apikey")
        print("And pass it to this script: python scripts/test_gemini_models.py <YOUR_API_KEY>")
        print("=" * 70)
        return

    print("=" * 70)
    print(" Testing Active Gemini Models on Google AI Studio API...")
    print("=" * 70)

    try:
        from google import genai
        client = genai.Client(api_key=api_key)

        print("\n1. Fetching available models for this API key via client.models.list()...")
        available_models = []
        try:
            for m in client.models.list():
                # Filter for content generation models
                name = getattr(m, "name", str(m))
                available_models.append(name)
            print(f"[OK] Discovered {len(available_models)} total models on endpoint.")
        except Exception as e:
            print(f"[WARN] client.models.list() returned: {e}")

        # Candidate list to verify
        candidates = [
            "gemini-2.0-flash",
            "gemini-1.5-flash",
            "gemini-1.5-pro",
            "gemini-1.0-pro",
        ]

        print("\n2. Testing live content generation on candidate models...")
        working_models = []
        for model_id in candidates:
            try:
                response = client.models.generate_content(
                    model=model_id,
                    contents="Say OK",
                )
                text = response.text.strip() if hasattr(response, "text") else "Response received"
                print(f" [PASS] Model '{model_id}': ACTIVE & WORKING (Response: '{text}')")
                working_models.append(model_id)
            except Exception as e:
                err_msg = str(e)
                if "404" in err_msg or "not found" in err_msg.lower():
                    print(f" [404 NOT FOUND] Model '{model_id}': DOES NOT EXIST on Google API!")
                elif "429" in err_msg or "quota" in err_msg.lower():
                    print(f" [429 RATE LIMIT] Model '{model_id}': Exists but quota limit reached.")
                else:
                    print(f" [ERROR] Model '{model_id}': FAILED ({e})")

        print("\n" + "=" * 70)
        print(" VERIFICATION SUMMARY:")
        print(f" Working & Available Models: {working_models}")
        if working_models:
            print(f" Recommended Primary Model:  '{working_models[0]}'")
            if len(working_models) > 1:
                print(f" Recommended Fallback Model: '{working_models[1]}'")
        print("=" * 70)

    except Exception as e:
        print(f"[ERROR] Could not initialize Google GenAI client: {e}")


if __name__ == "__main__":
    key_arg = sys.argv[1] if len(sys.argv) > 1 else None
    test_models(key_arg)
