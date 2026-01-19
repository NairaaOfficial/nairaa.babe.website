import requests

def generate_openrouter(api_key, prompt):
    try:
        print("🤖 OpenRouter...")
        response = requests.post(
            url="https://openrouter.ai/api/v1/chat/completions",
            headers={
                "Authorization": f"Bearer {api_key}",
                "Content-Type": "application/json"
            },
            json={
                "model": "meta-llama/llama-3.3-70b-instruct:free",
                "messages": [{"role": "user", "content": prompt}]
            }
        )
        response.raise_for_status()
        print("✅ OpenRouter done")
        return response.json()["choices"][0]["message"]["content"]
    except Exception as e:
        print(f"❌ OpenRouter: {e}")
        return None
