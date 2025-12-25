import os
import time
import random
import requests
from supabase import create_client
from AI_MODELS.llm_orchestrator import generate

THREADS_ACCESS_TOKEN = os.environ['THREADS_ACCESS_TOKEN']
THREADS_USER_ID = os.environ['THREADS_USER_ID']
SUPABASE_URL_THREADS = os.environ["SUPABASE_URL_THREADS"]
SUPABASE_KEY_THREADS = os.environ["SUPABASE_KEY_THREADS"]
API_VERSION_THREADS = os.environ['API_VERSION_THREADS']
BASE_URL_THREADS = os.environ['BASE_URL_THREADS']

print("THREADS_ACCESS_TOKEN:", THREADS_ACCESS_TOKEN)
print("THREADS_USER_ID:", THREADS_USER_ID)
print("SUPABASE_URL_THREADS:", SUPABASE_URL_THREADS)
print("SUPABASE_KEY_THREADS:", SUPABASE_KEY_THREADS)
print("API_VERSION_THREADS:", API_VERSION_THREADS)
print("BASE_URL_THREADS:", BASE_URL_THREADS)

supabase_threads = create_client(SUPABASE_URL_THREADS, SUPABASE_KEY_THREADS)

def filter_ai_reply(text):
    """
    Filters the generated text to remove any unwanted content, such as special characters like * or **.
    """
    # Remove all occurrences of * and ** from the text
    filtered_text = text.replace("*", "")
    filtered_text = filtered_text.replace("\"", "")
    return filtered_text

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
        reply = generate(reply_text)
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
