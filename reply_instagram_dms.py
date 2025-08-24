import os
import time
import random
import requests
from supabase import create_client

INSTAGRAM_ACCESS_TOKEN = os.environ['INSTAGRAM_ACCESS_TOKEN']
GEMINI_API_KEY_INSTAGRAM = os.environ['GEMINI_API_KEY_INSTAGRAM']
INSTAGRAM_USER_ID = os.environ['INSTAGRAM_USER_ID']
SUPABASE_URL_INSTAGRAM_DMS = os.environ["SUPABASE_URL_INSTAGRAM_DMS"]
SUPABASE_KEY_INSTAGRAM_DMS = os.environ["SUPABASE_KEY_INSTAGRAM_DMS"]
API_VERSION_INSTAGRAM = os.environ['API_VERSION_INSTAGRAM']
BASE_URL_INSTAGRAM = os.environ['BASE_URL_INSTAGRAM']

print("INSTAGRAM_ACCESS_TOKEN:", INSTAGRAM_ACCESS_TOKEN)
print("GEMINI_API_KEY_INSTAGRAM:", GEMINI_API_KEY_INSTAGRAM)
print("INSTAGRAM_USER_ID:", INSTAGRAM_USER_ID)
print("SUPABASE_URL_INSTAGRAM_DMS:", SUPABASE_URL_INSTAGRAM_DMS)
print("SUPABASE_KEY_INSTAGRAM_DMS:", SUPABASE_KEY_INSTAGRAM_DMS)
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

supabase_instagram_dms = create_client(SUPABASE_URL_INSTAGRAM_DMS, SUPABASE_KEY_INSTAGRAM_DMS)
supabase_instagram_subscribers = create_client(SUPABASE_URL_INSTAGRAM_DMS, SUPABASE_KEY_INSTAGRAM_DMS)

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
        "Encourage them to follow you in a fun, subtle way. \n"
        "Keep replies natural, short (under 20 words), one-liners when possible, and always human-like and original.\n"
        "DO NOT return explanations, formatting, or multiple options—just one final reply only.\n"
        "Do not mention you are an AI or a bot. Say you are a real female.\n"
        "Do not always ask them to follow you, or once in a conversation.\n"
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
    Returns the generated text as a string.
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

    params = {"key": GEMINI_API_KEY_INSTAGRAM}
    response = requests.post(url, headers=headers, params=params, json=payload)
    if response.status_code == 200:
        result = response.json()
        try:
            return result["candidates"][0]["content"]["parts"][0]["text"]
        except (KeyError, IndexError):
            return random.choice(DEFAULT_REPLY)
    else:
        return random.choice(DEFAULT_REPLY)

def get_earliest_dms():

    # 1️⃣ Pick random batch size between 10 and 15
    batch_size = random.randint(10, 15)
    print(f"📋 Fetching {batch_size} earliest unreplied dms...")

    # 2️⃣ Fetch earliest unreplied dms
    result = (
        supabase_instagram_dms.table("Instagram DMS")
        .select("*")
        .eq("replied", False)
        .order("timestamp", desc=False)
        .limit(batch_size)
        .execute()
    )

    dms = result.data
    
    if not dms:
        print("✅ No pending dms to reply.")
        return
    
    return dms

def reply_to_dms(recipient_id, message_text):
    """
    Send a direct message to an Instagram user using the Facebook Graph API.

    Parameters:
        recipient_id (str): The Instagram user ID of the recipient.
        message_text (str): The text of the message to send.

    Returns:
        Response: The response object from the requests library.
    """

    url = f"https://{BASE_URL_INSTAGRAM}/{API_VERSION_INSTAGRAM}/me/messages"
    headers = {
        "Content-Type": "application/json"
    }
    payload = {
        "recipient": {
            "id": recipient_id
        },
        "message": {
            "text": message_text
        }
    }
    params = {
        "access_token": INSTAGRAM_ACCESS_TOKEN
    }

    response = requests.post(url, headers=headers, json=payload, params=params)
    return response

def process_direct_message(dms):
    print("📬 New DMs to process:")
    for dm in dms:
        try:
            # Handle Instagram Direct Messages (DMs)
            print(f"📊 Processing DM: {dm}")
            sender_id = dm["sender_id"]
            recipient_id = dm["recipient_id"]
            message_text = dm["message_text"]
            print(f"📩 DM from {sender_id}: {message_text}")
            print(f"📩 Recipient ID: {recipient_id}")
            print("📩 Message text:", message_text)
            
            if message_text:
                print(f"📩 DM from {sender_id}: {message_text}")
                reply = get_gemini_reply(message_text, GEMINI_API_KEY_INSTAGRAM)
                reply = filter_gemini_reply(reply)
                print("🤖 AI DM reply:", reply)
                # Post reply back to the message
                response = reply_to_dms(sender_id, reply)
                if response:
                    print(f"✅ Replied to message {sender_id} with: {reply}")
                else:
                    print(f"❌ Failed to reply to message {sender_id}")
                print("Response:", response.status_code, response.text)

            # if supabase_instagram_subscribers.table("Instagram Subscribers").select("subscriber_id").eq("subscriber_id", sender_id).execute().data:
            #     if message_text:
            #         print(f"📩 DM from {sender_id}: {message_text}")
            #         reply = get_gemini_reply(message_text, GEMINI_API_KEY_INSTAGRAM)
            #         reply = filter_gemini_reply(reply)
            #         print("🤖 AI DM reply:", reply)
            #         # Post reply back to the message
            #         response = reply_to_dms(sender_id, reply)
            #         if response:
            #             print(f"✅ Replied to message {sender_id} with: {reply}")
            #         else:
            #             print(f"❌ Failed to reply to message {sender_id}")
            #         print("Response:", response.status_code, response.text)
            # else:
            #     print(f"❌ {sender_id} is not a subscriber.")
            #     # Post reply back to the message
            #     DEFAULT_REPLY = "Sorry, you are not a subscriber ❤️❤️❤️."
            #     response = reply_to_dms(sender_id, DEFAULT_REPLY)
            #     if response:
            #         print(f"✅ Replied to message {sender_id} with: {DEFAULT_REPLY}")
            #     else:
            #         print(f"❌ Failed to reply to message {sender_id}")
            #     print("Response:", response.status_code, response.text)

        except Exception as e:
            print(f"❌ Error processing DM: {str(e)}")
        time.sleep(20)  # Sleep for 2 seconds between processing each DM

def main():
    dms = get_earliest_dms()
    print("dms fetched:", dms)
    if dms:
        process_direct_message(dms)

if __name__ == "__main__":
    main()
