import os
import time
import random
import requests
from supabase import create_client
from cerebras.cloud.sdk import Cerebras
from openai import OpenAI

THREADS_ACCESS_TOKEN = os.environ['THREADS_ACCESS_TOKEN']
THREADS_USER_ID = os.environ['THREADS_USER_ID']
CEREBRAS_API_KEY = os.environ['CEREBRAS_API_KEY']
GROQ_API_KEY = os.environ['GROQ_API_KEY']
SUPABASE_URL_THREADS = os.environ["SUPABASE_URL_THREADS"]
SUPABASE_KEY_THREADS = os.environ["SUPABASE_KEY_THREADS"]
API_VERSION_THREADS = os.environ['API_VERSION_THREADS']
BASE_URL_THREADS = os.environ['BASE_URL_THREADS']

print("THREADS_ACCESS_TOKEN:", THREADS_ACCESS_TOKEN)
print("THREADS_USER_ID:", THREADS_USER_ID)
print("CEREBRAS_API_KEY:", CEREBRAS_API_KEY)
print("GROQ_API_KEY:", GROQ_API_KEY)
print("SUPABASE_URL_THREADS:", SUPABASE_URL_THREADS)
print("SUPABASE_KEY_THREADS:", SUPABASE_KEY_THREADS)
print("API_VERSION_THREADS:", API_VERSION_THREADS)
print("BASE_URL_THREADS:", BASE_URL_THREADS)

DEFAULT_REPLY = [
    "You're so sweet! 😘",
    "Aww, you're amazing! 💕",
    "Sending love your way! ❤️",
    "You just made my day! 🌸",
    "Keep spreading positivity! ✨",
    "You're the best! 🥰",
    "Thanks for the love! 💞",
    "Your support means the world! 🌍",
    "You're such a gem! 💎",
    "I appreciate you! 🌟",
    "You light up my day! ☀️",
    "Thanks for being awesome! 🌈"
]

supabase_threads = create_client(SUPABASE_URL_THREADS, SUPABASE_KEY_THREADS)

# Initialize Cerebras and Groq clients
cerebras_client = Cerebras(api_key=CEREBRAS_API_KEY)
groq_client = OpenAI(
    api_key=GROQ_API_KEY,
    base_url="https://api.groq.com/openai/v1",
)

def prompt(user_comment):
    """
    Generates a prompt for the AI model based on the user's comment.
    This function is used to create a context for the AI to generate a reply.
    """
    return (
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

def filter_ai_reply(text):
    """
    Filters the generated text to remove any unwanted content, such as special characters like * or **.
    """
    # Remove all occurrences of * and ** from the text
    filtered_text = text.replace("*", "")
    filtered_text = filtered_text.replace("\"", "")
    return filtered_text

def get_ai_reply(user_comment):
    """
    Uses Cerebras API to generate text based on the input prompt.
    Falls back to Groq API if Cerebras fails or hits rate limit.
    Returns the generated text as a string.
    """
    # Try Cerebras first
    try:
        print("🤖 Trying Cerebras API...")
        chat_completion = cerebras_client.chat.completions.create(
            messages=[
                {
                    "role": "user",
                    "content": prompt(user_comment),
                }
            ],
            model="llama-3.3-70b",
        )
        print("✅ Cerebras API successful")
        return chat_completion.choices[0].message.content
    except Exception as e:
        print(f"❌ Cerebras API failed: {e}")
        
        # Fallback to Groq
        try:
            print("🔄 Falling back to Groq API...")
            chat_completion = groq_client.chat.completions.create(
                messages=[
                    {
                        "role": "user",
                        "content": prompt(user_comment),
                    }
                ],
                model="meta-llama/llama-guard-4-12b",
                temperature=1,
                max_completion_tokens=1024,
                top_p=1,
            )
            print("✅ Groq API successful")
            return chat_completion.choices[0].message.content
        except Exception as groq_error:
            print(f"❌ Groq API also failed: {groq_error}")
            return random.choice(DEFAULT_REPLY)

def create_reply_container(text, reply_to_id):
    """
    Create a reply to a specific reply under the root post on Threads.

    Parameters:
        text (str): The text of the reply.
        reply_to_id (str): The ID of the reply to respond to.

    Returns:
        dict: The response containing the Threads media container ID.
    """
    url = f"https://{BASE_URL_THREADS}/{API_VERSION_THREADS}/me/threads"
    payload = {
        "media_type": "TEXT_POST",
        "text": text,
        "reply_to_id": reply_to_id,
        "access_token": THREADS_ACCESS_TOKEN
    }
    response = requests.post(url, data=payload)
    print(f"📤 Creating Threads reply: {payload}")
    print(f"Response: {response.json()}")
    if response.status_code == 200:
        return response.json().get("id")
    else:
        print(f"❌ Error creating Threads reply: {response.status_code} {response.text}")
        return None

def publish_threads_reply(creation_id):
    """
    Publish the Threads media container created from the reply.

    Parameters:
        threads_user_id (str): The Threads user ID.
        creation_id (str): The ID of the Threads media container.

    Returns:
        dict: The response containing the Threads Reply Media ID.
    """
    url = f"https://{BASE_URL_THREADS}/{API_VERSION_THREADS}/{THREADS_USER_ID}/threads_publish"
    params = {
        "creation_id": creation_id,
        "access_token": THREADS_ACCESS_TOKEN
    }
    response = requests.post(url, params=params)
    if response.status_code == 200:
        return response.json()
    else:
        print(f"❌ Error publishing Threads reply: {response.status_code} {response.text}")
        return None
    
def get_earliest_replies():

    # 1️⃣ Pick random batch size between 10 and 15
    batch_size = random.randint(10, 15)
    print(f"📋 Fetching {batch_size} earliest unreplied replies...")

    # 2️⃣ Fetch earliest unreplied replies
    result = (
        supabase_threads.table("Thread Replies")
        .select("*")
        .eq("replied", False)
        .order("timestamp", desc=False)
        .limit(batch_size)
        .execute()
    )

    replies = result.data

    if not replies:
        print("✅ No pending replies to respond to.")
        return

    return replies

def process_replies(replies):
    """
    Reply to a list of Thread replies with AI-generated responses.

    Parameters:
        replies (list): A list of reply objects to respond to.
    """
    for reply in replies:
        reply_id = reply["reply_id"]
        reply_text = reply["reply"]
        username = reply["username"]

        print(f"\n👤 @{username} said: {reply_text}")

        # 3️⃣ Generate AI reply
        reply = get_ai_reply(reply_text)
        reply = filter_ai_reply(reply)
        print("🤖 AI reply:", reply)

        # 4️⃣ Post reply
        creation_id = create_reply_container(reply, reply_id)
        response = publish_threads_reply(creation_id)
        if response:
            print(f"✅ Replied to user {reply_id} with: {reply}")

            # 5️⃣ Mark as replied
            supabase_threads.table("Thread Replies").update({"replied": True}).eq("reply_id", reply_id).execute()
        else:
            print(f"❌ Failed to reply to reply {reply_id}")
            print(f"🗑️ Deleting reply {reply_id} from Supabase.")
            supabase_threads.table("Thread Replies").delete().eq("reply_id", reply_id).execute()

        # 6️⃣ Delay between replies
        print("⏳ Waiting 20 seconds before next reply...")
        time.sleep(20)

def main():
    replies = get_earliest_replies()
    print("Replies fetched:", replies)
    if replies:
        process_replies(replies)

if __name__ == "__main__":
    main()
