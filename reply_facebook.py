import os
import time
import random
import requests
from supabase import create_client
from AI_MODELS.llm_orchestrator import generate

FACEBOOK_ACCESS_TOKEN = os.environ['FACEBOOK_ACCESS_TOKEN']
FACEBOOK_PAGE_ID = os.environ['FACEBOOK_PAGE_ID']
SUPABASE_URL_FACEBOOK = os.environ["SUPABASE_URL_FACEBOOK"]
SUPABASE_KEY_FACEBOOK = os.environ["SUPABASE_KEY_FACEBOOK"]
API_VERSION_FACEBOOK = os.environ['API_VERSION_FACEBOOK']
BASE_URL_FACEBOOK = os.environ['BASE_URL_FACEBOOK']

print("FACEBOOK_ACCESS_TOKEN:", FACEBOOK_ACCESS_TOKEN)
print("FACEBOOK_PAGE_ID:", FACEBOOK_PAGE_ID)
print("SUPABASE_URL_FACEBOOK:", SUPABASE_URL_FACEBOOK)
print("SUPABASE_KEY_FACEBOOK:", SUPABASE_KEY_FACEBOOK)
print("API_VERSION_FACEBOOK:", API_VERSION_FACEBOOK)
print("BASE_URL_FACEBOOK:", BASE_URL_FACEBOOK)

supabase_facebook = create_client(SUPABASE_URL_FACEBOOK, SUPABASE_KEY_FACEBOOK)

def filter_ai_reply(text):
    """
    Filters the generated text to remove any unwanted content, such as special characters like * or **.
    """
    # Remove all occurrences of * and ** from the text
    filtered_text = text.replace("*", "")
    filtered_text = filtered_text.replace("\"", "")
    return filtered_text
    
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
        reply = generate(comment_text)
        reply = filter_ai_reply(reply)
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
