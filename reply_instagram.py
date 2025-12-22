import os
import time
import random
import requests
from supabase import create_client
from cerebras.cloud.sdk import Cerebras
from openai import OpenAI

INSTAGRAM_ACCESS_TOKEN = os.environ['INSTAGRAM_ACCESS_TOKEN']
CEREBRAS_API_KEY = os.environ['CEREBRAS_API_KEY']
GROQ_API_KEY = os.environ['GROQ_API_KEY']
INSTAGRAM_USER_ID = os.environ['INSTAGRAM_USER_ID']
SUPABASE_URL_INSTAGRAM = os.environ["SUPABASE_URL_INSTAGRAM"]
SUPABASE_KEY_INSTAGRAM = os.environ["SUPABASE_KEY_INSTAGRAM"]
API_VERSION_INSTAGRAM = os.environ['API_VERSION_INSTAGRAM']
BASE_URL_INSTAGRAM = os.environ['BASE_URL_INSTAGRAM']

print("INSTAGRAM_ACCESS_TOKEN:", INSTAGRAM_ACCESS_TOKEN)
print("CEREBRAS_API_KEY:", CEREBRAS_API_KEY)
print("GROQ_API_KEY:", GROQ_API_KEY)
print("INSTAGRAM_USER_ID:", INSTAGRAM_USER_ID)
print("SUPABASE_URL_INSTAGRAM:", SUPABASE_URL_INSTAGRAM)
print("SUPABASE_KEY_INSTAGRAM:", SUPABASE_KEY_INSTAGRAM)
print("API_VERSION_INSTAGRAM:", API_VERSION_INSTAGRAM)
print("BASE_URL_INSTAGRAM:", BASE_URL_INSTAGRAM)

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

supabase_instagram = create_client(SUPABASE_URL_INSTAGRAM, SUPABASE_KEY_INSTAGRAM)

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
    
def reply_to_comment(comment_id, message):
    """
    Reply to a given Instagram comment using Graph API.
    """
    url = f"https://{BASE_URL_INSTAGRAM}/{API_VERSION_INSTAGRAM}/{comment_id}/replies"
    payload = {
        "message": message,
        "access_token": INSTAGRAM_ACCESS_TOKEN
    }

    return requests.post(url, json=payload)

def get_earliest_comments():

    # 1️⃣ Pick random batch size between 10 and 15
    batch_size = random.randint(10, 15)
    print(f"📋 Fetching {batch_size} earliest unreplied comments...")

    # 2️⃣ Fetch earliest unreplied comments
    result = (
        supabase_instagram.table("Instagram Comments")
        .select("*")
        .eq("replied", False)
        .order("timestamp", desc=False)
        .limit(batch_size)
        .execute()
    )

    comments = result.data
    
    if not comments:
        print("✅ No pending comments to reply.")
        return
    
    return comments

def process_comments(comments):
    """
    Reply to a list of Instagram comments with AI-generated responses.

    Parameters:
        comments (list): A list of comment objects to reply to.
    """
    for comment in comments:
        comment_id = comment["comment_id"]
        comment_text = comment["comment"]
        username = comment["username"]

        print(f"\n👤 @{username} said: {comment_text}")

        # 3️⃣ Generate AI reply
        reply = get_ai_reply(comment_text)
        reply = filter_ai_reply(reply)
        print("🤖 AI reply:", reply)

        # 4️⃣ Post reply
        response = reply_to_comment(comment_id, reply)
        if response:
            print(f"✅ Replied to comment {comment_id} with: {reply}")

            # 5️⃣ Mark as replied
            supabase_instagram.table("Instagram Comments").update({"replied": True}).eq("comment_id", comment_id).execute()
        else:
            print(f"❌ Failed to reply to comment {comment_id}")
            print(f"🗑️ Deleting comment {comment_id} from Supabase.")
            supabase_instagram.table("Instagram Comments").delete().eq("comment_id", comment_id).execute()

        # 6️⃣ Delay between replies
        print("⏳ Waiting 20 seconds before next reply...")
        time.sleep(20)

def main():
    comments = get_earliest_comments()
    print("Comments fetched:", comments)
    if comments:
        process_comments(comments)

if __name__ == "__main__":
    main()
