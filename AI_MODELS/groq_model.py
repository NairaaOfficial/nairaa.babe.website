from groq import Groq

def generate_groq(api_key, prompt):
    try:
        print("🤖 Groq...")
        client = Groq(api_key=api_key)
        response = client.chat.completions.create(
            messages=[{"role": "user", "content": prompt}],
            model="llama-3.1-8b-instant"
        )
        print("✅ Groq done")
        return response.choices[0].message.content
    except Exception as e:
        print(f"❌ Groq: {e}")
        return None
