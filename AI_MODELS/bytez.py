from openai import OpenAI

def generate_bytez(api_key, prompt):
    try:
        print("🤖 Bytez...")
        client = OpenAI(
            api_key=api_key,
            base_url="https://api.bytez.com/models/v2/openai/v1"
        )
        response = client.chat.completions.create(
            messages=[{"role": "user", "content": prompt}],
            model="meta-llama/Meta-Llama-3.1-8B-Instruct",
            temperature=0.5,
            max_tokens=1000
        )
        print("✅ Bytez done")
        return response.choices[0].message.content
    except Exception as e:
        print(f"❌ Bytez: {e}")
        return None

