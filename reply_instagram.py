import os
import time
import random
import requests
from supabase import create_client
from AI_MODELS.llm_orchestrator import generate

INSTAGRAM_ACCESS_TOKEN = os.environ['INSTAGRAM_ACCESS_TOKEN']
INSTAGRAM_USER_ID = os.environ['INSTAGRAM_USER_ID']
SUPABASE_URL_INSTAGRAM = os.environ["SUPABASE_URL_INSTAGRAM"]
SUPABASE_KEY_INSTAGRAM = os.environ["SUPABASE_KEY_INSTAGRAM"]
API_VERSION_INSTAGRAM = os.environ['API_VERSION_INSTAGRAM']
BASE_URL_INSTAGRAM = os.environ['BASE_URL_INSTAGRAM']

print("INSTAGRAM_ACCESS_TOKEN:", INSTAGRAM_ACCESS_TOKEN)
print("INSTAGRAM_USER_ID:", INSTAGRAM_USER_ID)
print("SUPABASE_URL_INSTAGRAM:", SUPABASE_URL_INSTAGRAM)
print("SUPABASE_KEY_INSTAGRAM:", SUPABASE_KEY_INSTAGRAM)
print("API_VERSION_INSTAGRAM:", API_VERSION_INSTAGRAM)
print("BASE_URL_INSTAGRAM:", BASE_URL_INSTAGRAM)

supabase_instagram = create_client(SUPABASE_URL_INSTAGRAM, SUPABASE_KEY_INSTAGRAM)

def filter_ai_reply(text):
    """
    Filters the generated text to remove any unwanted content, such as special characters like * or **.
    """
    # Remove all occurrences of * and ** from the text
    filtered_text = text.replace("*", "")
    filtered_text = filtered_text.replace("\"", "")
    return filtered_text
    
def reply_to_comment(comment_id, message):
    """
    Reply to a given Instagram comment using Graph API.
    """
    url = f"https://{BASE_URL_INSTAGRAM}/{API_VERSION_INSTAGRAM}/{comment_id}/replies"
    payload = {
        "message": message,
        "access_token": INSTAGRAM_ACCESS_TOKEN
    }

    response = requests.post(url, data=payload)
    
    if response.status_code != 200:
        print(f"❌ API Error {response.status_code}: {response.text}")
    
    return response

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
        reply = generate(comment_text)
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
