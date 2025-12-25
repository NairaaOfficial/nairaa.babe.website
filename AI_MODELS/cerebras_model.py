"""Cerebras - Simple function."""
from cerebras.cloud.sdk import Cerebras

def generate_cerebras(api_key, prompt):
    try:
        print("🤖 Cerebras...")
        client = Cerebras(api_key=api_key)
        response = client.chat.completions.create(
            messages=[{"role": "user", "content": prompt}],
            model="llama-3.3-70b"
        )
        print("✅ Cerebras done")
        return response.choices[0].message.content
    except Exception as e:
        print(f"❌ Cerebras: {e}")
        return None
