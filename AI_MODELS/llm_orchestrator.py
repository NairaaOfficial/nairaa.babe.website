import os
import random
from .cerebras_model import generate_cerebras
from .groq_model import generate_groq
from .bytez import generate_bytez
from .openrouter_model import generate_openrouter

# LLM API Keys
CEREBRAS_API_KEY = os.environ['CEREBRAS_API_KEY']
GROQ_API_KEY = os.environ['GROQ_API_KEY']
BYTEZ_API_KEY = os.environ['BYTEZ_API_KEY']
OPENROUTER_API_KEY = os.environ['OPENROUTER_API_KEY']

DEFAULT_REPLY = [
    "omg stop, you're making me blush 🙈💕",
    "this is so sweet, needed this today 🥺✨",
    "you just made my whole week honestly 💗",
    "aww I love hearing from you! 😊",
    "your energy is everything, thank you 🌟",
    "wait this is the cutest thing ever 🥰",
    "I appreciate you more than you know 💫",
    "sending you all the good vibes right back! ✨💕",
    "you're literally the best, thank you 😘",
    "this message made me smile so big 😊💖",
    "your support means everything to me 🫶",
    "okay but you're actually amazing 🌸",
    "feeling so grateful for you rn 💗✨",
    "this is exactly what I needed today 🥹",
    "you always know how to brighten my day ☀️💕"
]

def generate(user_comment):
    """Read current model from file → use it → write next model to file."""
    
    file = "AI_MODELS/models.txt"
    
    prompt = (
        f"A follower messaged: '{user_comment}'.\n"
        "You are a single, charming, witty, and sweet female influencer replying to comments on Instagram.\n"
        "Reply in the same language and tone as the message.\n"
        "Be flirty but respectful, never vulgar.\n"
        "If they send love, return love with emojis and warmth.\n"
        "If they’re rude, reply kindly and ask them to spread positivity.\n"
        "Subtly tease that they can enjoy your dirty, naughty, cheesy side by visiting the link in your bio when it feels natural.\n"
        "Keep replies natural, short (under 20 words), one-liners when possible, and always human-like and original.\n"
        "DO NOT return explanations, formatting, or multiple options—just one final reply only.\n"
        "Do not mention you are an AI or a bot. Say you are a real female.\n"
        "If the message is just love emojis like ❤️ or 😘, reply only with similar love emojis back."
    )

    # Read current model from file
    current_model = open(file).read().strip().upper()
    
    print(f"📍 File says: {current_model}")
    
    # Define all models in order
    models = [
        ("CEREBRAS", lambda: generate_cerebras(CEREBRAS_API_KEY, prompt)),
        ("GROQ", lambda: generate_groq(GROQ_API_KEY, prompt)),
        ("OPENROUTER", lambda: generate_openrouter(OPENROUTER_API_KEY, prompt))
    ]
    # ("BYTEZ", lambda: generate_bytez(BYTEZ_API_KEY, prompt)),
    # Find current model index
    current_idx = next((i for i, (name, _) in enumerate(models) if name == current_model), 0)
    
    # Try current model first, then try all others if it fails
    for i in range(len(models)):
        idx = (current_idx + i) % len(models)
        model_name, model_func = models[idx]
        
        result = model_func()
        if result:
            # Success - write next model to file
            next_idx = (idx + 1) % len(models)
            next_model = models[next_idx][0]
            open(file, 'w').write(next_model)
            print(f"✍️ Writing to file: {next_model}")
            return result
    
    # All failed - return default
    print("⚠️ All models failed - using default caption")
    return random.choice(DEFAULT_REPLY)