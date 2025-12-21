import os
import time
import random
import requests
from supabase import create_client

FACEBOOK_ACCESS_TOKEN = os.environ['FACEBOOK_ACCESS_TOKEN']
GEMINI_API_KEYS_FACEBOOK = os.environ['GEMINI_API_KEYS_FACEBOOK']
FACEBOOK_PAGE_ID = os.environ['FACEBOOK_PAGE_ID']
SUPABASE_URL_FACEBOOK = os.environ["SUPABASE_URL_FACEBOOK"]
SUPABASE_KEY_FACEBOOK = os.environ["SUPABASE_KEY_FACEBOOK"]
API_VERSION_FACEBOOK = os.environ['API_VERSION_FACEBOOK']
BASE_URL_FACEBOOK = os.environ['BASE_URL_FACEBOOK']

print("FACEBOOK_ACCESS_TOKEN:", FACEBOOK_ACCESS_TOKEN)
print("GEMINI_API_KEYS_FACEBOOK:", GEMINI_API_KEYS_FACEBOOK)
print("FACEBOOK_PAGE_ID:", FACEBOOK_PAGE_ID)
print("SUPABASE_URL_FACEBOOK:", SUPABASE_URL_FACEBOOK)
print("SUPABASE_KEY_FACEBOOK:", SUPABASE_KEY_FACEBOOK)
print("API_VERSION_FACEBOOK:", API_VERSION_FACEBOOK)
print("BASE_URL_FACEBOOK:", BASE_URL_FACEBOOK)

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

supabase_facebook = create_client(SUPABASE_URL_FACEBOOK, SUPABASE_KEY_FACEBOOK)

# Load multiple Gemini API keys from environment variables
GEMINI_API_KEYS_FACEBOOK = GEMINI_API_KEYS_FACEBOOK.split(',')

current_key_index = 0

# Function to switch to the next API key
def switch_gemini_key():
    global current_key_index
    current_key_index = (current_key_index + 1) % len(GEMINI_API_KEYS_FACEBOOK)
    return GEMINI_API_KEYS_FACEBOOK[current_key_index]

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

def filter_gemini_reply(text):
    """
    Filters the generated text to remove any unwanted content, such as special characters like * or **.
    """
    # Remove all occurrences of * and ** from the text
    filtered_text = text.replace("*", "")
    filtered_text = filtered_text.replace("\"", "")
    return filtered_text

def get_gemini_reply(user_comment):
    """
    Uses Google Gemini API to generate text based on the input prompt.
    Handles rate limiting by switching API keys.
    """
    url = "https://generativelanguage.googleapis.com/v1beta/models/gemini-2.0-flash:generateContent"
    headers = {"Content-Type": "application/json"}
    payload = {
        "contents": [
            {
                "parts": [{
                    "text": (
                        prompt(user_comment)
                    )
                }]
            }
        ]
    }

    for _ in range(len(GEMINI_API_KEYS_FACEBOOK)):
        current_key = GEMINI_API_KEYS_FACEBOOK[current_key_index]
        params = {"key": current_key}
        response = requests.post(url, headers=headers, params=params, json=payload)

        if response.status_code == 200:
            result = response.json()
            try:
                return result["candidates"][0]["content"]["parts"][0]["text"]
            except (KeyError, IndexError):
                return random.choice(DEFAULT_REPLY)
        elif response.status_code == 429:  # Rate limit error
            print(f"Rate limit reached for key: {current_key}. Switching to next key.")
            switch_gemini_key()
        else:
            print(f"Error with key {current_key}: {response.status_code}. Trying next key.")
            switch_gemini_key()

    # If all keys fail, return a default reply
    return random.choice(DEFAULT_REPLY)
    
def reply_to_comment(comment_id, message, user_id=None):
    """
    Reply to a Facebook Page comment using Graph API.
    Optionally @mention the user by including their PSID.
    """
    url = f"https://{BASE_URL_FACEBOOK}/{API_VERSION_FACEBOOK}/{comment_id}/comments"
    
    # If user_id is provided, add @mention to the message
    if user_id:
        message = f"@[{user_id}] {message}"
    
    payload = {
        "message": message,
        "access_token": FACEBOOK_ACCESS_TOKEN
    }

    return requests.post(url, json=payload)

def get_earliest_comments():

    # 1️⃣ Pick random batch size between 10 and 15
    batch_size = random.randint(10, 15)
    print(f"📋 Fetching {batch_size} earliest unreplied comments...")

    # 2️⃣ Fetch earliest unreplied comments
    result = (
        supabase_facebook.table("Facebook Comments")
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
    Reply to a list of Facebook comments with AI-generated responses.

    Parameters:
        comments (list): A list of comment objects to reply to.
    """
    for comment in comments:
        comment_id = comment["comment_id"]
        comment_text = comment["comment"]
        user_id = comment["user_id"]
        username = comment["username"]

        print(f"\n👤 @{username} said: {comment_text}")

        # 3️⃣ Generate AI reply
        reply = get_gemini_reply(comment_text)
        reply = filter_gemini_reply(reply)
        print("🤖 AI reply:", reply)

        # 4️⃣ Post reply
        response = reply_to_comment(comment_id, reply, user_id)
        if response:
            print(f"✅ Replied to comment {comment_id} with: {reply}")

            # 5️⃣ Mark as replied
            supabase_facebook.table("Facebook Comments").update({"replied": True}).eq("comment_id", comment_id).execute()
        else:
            print(f"❌ Failed to reply to comment {comment_id}")
            print(f"🗑️ Deleting comment {comment_id} from Supabase.")
            supabase_facebook.table("Facebook Comments").delete().eq("comment_id", comment_id).execute()

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
