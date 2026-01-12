from flask import Flask, render_template, request
import os
import time
import requests
from supabase import create_client
from datetime import datetime, timedelta, timezone

app = Flask(__name__)
app.secret_key = '12345678'  # Replace with a secure key

PROCESSED_TUPLES_FILE = "processed_tuples.txt"

@app.route('/')
def home():
    """Home page with app description and navigation."""
    return render_template('home.html')

@app.route('/privacy-policy')
def privacy_policy():
    """Privacy policy page."""
    return render_template('privacy_policy.html')

@app.route('/terms-of-service')
def terms_of_service():
    """Terms of Service page."""
    return render_template('terms_of_service.html')

####################################################################################################
##########################################  INSTAGRAM  #############################################
####################################################################################################

SUPABASE_URL_INSTAGRAM = os.environ['SUPABASE_URL_INSTAGRAM']
SUPABASE_KEY_INSTAGRAM = os.environ['SUPABASE_KEY_INSTAGRAM']
SUPABASE_URL_INSTAGRAM_DMS = os.environ['SUPABASE_URL_INSTAGRAM_DMS']
SUPABASE_KEY_INSTAGRAM_DMS = os.environ['SUPABASE_KEY_INSTAGRAM_DMS']
VERIFY_TOKEN_INSTAGRAM = os.environ['VERIFY_TOKEN_INSTAGRAM']
USERNAME_INSTAGRAM = os.environ['USERNAME_INSTAGRAM']
INSTAGRAM_USER_ID = os.environ['INSTAGRAM_USER_ID']

print("SUPABASE_URL_INSTAGRAM:", SUPABASE_URL_INSTAGRAM)
print("SUPABASE_KEY_INSTAGRAM:", SUPABASE_KEY_INSTAGRAM)
print("SUPABASE_URL_INSTAGRAM_DMS:", SUPABASE_URL_INSTAGRAM_DMS)
print("SUPABASE_KEY_INSTAGRAM_DMS:", SUPABASE_KEY_INSTAGRAM_DMS)
print("VERIFY_TOKEN_INSTAGRAM:", VERIFY_TOKEN_INSTAGRAM)
print("USERNAME_INSTAGRAM:", USERNAME_INSTAGRAM)
print("INSTAGRAM_USER_ID:", INSTAGRAM_USER_ID)

supabase_instagram = create_client(SUPABASE_URL_INSTAGRAM, SUPABASE_KEY_INSTAGRAM)
supabase_instagram_dms = create_client(SUPABASE_URL_INSTAGRAM_DMS, SUPABASE_KEY_INSTAGRAM_DMS)

def send_instagram_private_reply(comment_id, message_text):
    """Send a private reply to an Instagram comment using Graph API.
    
    Returns: (success: bool, result: dict)
    """
    # Get required config from Facebook env vars (Instagram uses graph.facebook.com)
    if not INSTAGRAM_USER_ID:
        print("❌ INSTAGRAM_USER_ID not configured")
        return False, {"error": "INSTAGRAM_USER_ID not configured"}
    
    # These are defined in the Facebook section
    try:
        access_token = FACEBOOK_ACCESS_TOKEN
        base_url = BASE_URL_FACEBOOK
        api_version = API_VERSION_FACEBOOK
    except NameError:
        print("❌ Missing Facebook config (needed for Instagram API)")
        return False, {"error": "Missing Facebook configuration"}
    
    url = f"https://{base_url}/{api_version}/{INSTAGRAM_USER_ID}/messages"
    headers = {
        "Authorization": f"Bearer {access_token}",
        "Content-Type": "application/json"
    }
    payload = {
        "recipient": {"comment_id": comment_id},
        "message": {"text": message_text}
    }
    
    try:
        response = requests.post(url, json=payload, headers=headers, timeout=15)
        if response.status_code == 200:
            data = response.json()
            print(f"✅ Private reply sent: recipient_id={data.get('recipient_id')}, message_id={data.get('message_id')}")
            return True, data
        else:
            print(f"❌ Failed to send private reply: {response.status_code} - {response.text}")
            return False, {"error": response.text, "status_code": response.status_code}
    except Exception as e:
        print(f"❌ Exception sending private reply: {str(e)}")
        return False, {"error": str(e)}

def process_instagram_comments(data):
    """
    Handle Instagram Page webhook notifications for comments.
    """
    # Process each entry in the webhook data
    print(f"📊 Processing {len(data['entry'])} entries")
    for entry in data.get("entry", []):
        if "changes" not in entry or not entry["changes"]:
            print("⚠️ No changes in entry:", entry.get("id", "unknown"))
            continue

        # Extract the time value from the entry
        timestamp = entry.get("time", "unknown")
        # UTC+5:30 offset
        IST = timezone(timedelta(hours=5, minutes=30))
        timestamp = datetime.fromtimestamp(timestamp, tz=IST).isoformat()
        # Process each change in the entry
        print(f"📊 Processing {len(entry['changes'])} changes in entry {entry.get('id', 'unknown')}")
        for change in entry.get("changes", []):
            # Only process comment changes
            if change["field"] != "comments":
                print(f"ℹ️ Ignoring non-comment field: {change['field']}")
                continue
                
            try:
                value = change["value"]
                comment = value["text"]
                comment_id = value["id"]
                username = value["from"]["username"]
                
                # Skip if the comment is from our own account
                if username == USERNAME_INSTAGRAM:
                    print("👤 Skipping our own comment")
                    continue

                # Extract only the fields you care about
                record = {
                    "username": username,
                    "comment_id": comment_id,
                    "comment": comment,
                    "timestamp": timestamp,
                    "replied": False
                }

                # Check if comment contains "test" - if so, send private reply
                if isinstance(comment, str) and "test" in comment.lower():
                    print(f"🧪 'test' detected in comment from @{username}: {comment}")
                    success, result = send_instagram_private_reply(comment_id, "Thanks for your comment!")
                    if success:
                        print(f"✅ Private reply sent successfully")
                    else:
                        print(f"❌ Failed to send private reply: {result}")
                else:
                    # Insert into Supabase table
                    response = supabase_instagram.table("Instagram Comments").insert(record).execute()
                    # Optional: log errors
                    if response.data:
                        print("Inserted:", response.data)
                    else:
                        print("Error:", response)    

            except KeyError as e:
                print(f"❌ Error processing comment: Missing field {str(e)}")
                print("Change data:", change)
                continue
    
def process_instagram_dms(data):
    # Handle Instagram Direct Messages (DMs)
    print(f"📊 Processing {len(data['entry'])} entries")
    for entry in data.get("entry", []):

        # Extract the time value from the entry
        timestamp = entry.get("time", "unknown")
        if isinstance(timestamp, int):  # Ensure timestamp is an integer
            timestamp = timestamp / 1000  # Convert milliseconds to seconds
        # UTC+5:30 offset
        IST = timezone(timedelta(hours=5, minutes=30))
        timestamp = datetime.fromtimestamp(timestamp, tz=IST).isoformat()

        for messaging_event in entry.get("messaging", []):
            try:
                message = messaging_event["message"]
                sender_id = messaging_event["sender"]["id"]
                recipient_id = messaging_event["recipient"]["id"]
                message_text = message["text"]
                print(f"📩 DM from {sender_id}: {message_text}")
                print(f"📩 Recipient ID: {recipient_id}")
                print("📩 Message text:", message_text)

                # Extract only the fields you care about
                record = {
                    "sender_id": sender_id,
                    "message_text": message_text,
                    "recipient_id": recipient_id,
                    "timestamp": timestamp,
                    "replied": False
                }

                # Insert into Supabase table
                response = supabase_instagram_dms.table("Instagram DMS").insert(record).execute()

                # Optional: log errors
                if response.data:
                    print("Inserted:", response.data)
                else:
                    print("Error:", response)  

            except Exception as e:
                print(f"❌ Error processing DM: {str(e)}")
                continue

@app.route('/webhookinstagram', methods=['GET'])
def verify_webhook_instagram():
    print("🔎 Query params:", request.args)

    mode = request.args.get("hub.mode")
    token = request.args.get("hub.verify_token")
    challenge = request.args.get("hub.challenge")

    print("🔍 Mode:", mode)
    print("🔍 Token from Meta:", token)
    print("🔍 Challenge:", challenge)
    print("🔐 Local VERIFY_TOKEN:", VERIFY_TOKEN_INSTAGRAM)

    if mode == "subscribe" and token == VERIFY_TOKEN_INSTAGRAM:
        print("✅ Webhook verified.")
        return challenge, 200  # Must return challenge as plain text
    else:
        print("❌ Verification failed.")
        return "Verification failed", 403

@app.route('/webhookinstagram', methods=['POST'])
def webhook_instagram():
    data = request.get_json()
    print("📥 Received data:", data)
    time.sleep(2)  # Simulate processing delay
    # Check if we have the expected structure
    if not data or "entry" not in data or not data["entry"]:
        print("❌ Invalid data format")
        return "OK", 200
    if "changes" in data["entry"][0] and data["entry"][0]["changes"]:
        process_instagram_comments(data)
    if "messaging" in data["entry"][0] and data["entry"][0]["messaging"]:
        process_instagram_dms(data)
    return "OK", 200

#####################################################################################################
##########################################  FACEBOOK  ###############################################
#####################################################################################################

SUPABASE_URL_FACEBOOK = os.environ['SUPABASE_URL_FACEBOOK']
SUPABASE_KEY_FACEBOOK = os.environ['SUPABASE_KEY_FACEBOOK']
VERIFY_TOKEN_FACEBOOK = os.environ['VERIFY_TOKEN_FACEBOOK']
USERNAME_FACEBOOK = os.environ['USERNAME_FACEBOOK']
print("SUPABASE_URL_FACEBOOK:", SUPABASE_URL_FACEBOOK)
print("SUPABASE_KEY_FACEBOOK:", SUPABASE_KEY_FACEBOOK)
print("VERIFY_TOKEN_FACEBOOK:", VERIFY_TOKEN_FACEBOOK)
print("USERNAME_FACEBOOK:", USERNAME_FACEBOOK)

# Facebook Page Configuration
FACEBOOK_ACCESS_TOKEN = os.environ['FACEBOOK_ACCESS_TOKEN']
FACEBOOK_PAGE_ID = os.environ['FACEBOOK_PAGE_ID']
BASE_URL_FACEBOOK = os.environ['BASE_URL_FACEBOOK']
API_VERSION_FACEBOOK = os.environ['API_VERSION_FACEBOOK']
print("FACEBOOK_ACCESS_TOKEN:", FACEBOOK_ACCESS_TOKEN)
print("FACEBOOK_PAGE_ID:", FACEBOOK_PAGE_ID)
print("BASE_URL_FACEBOOK:", BASE_URL_FACEBOOK)
print("API_VERSION_FACEBOOK:", API_VERSION_FACEBOOK)

supabase_facebook = create_client(SUPABASE_URL_FACEBOOK, SUPABASE_KEY_FACEBOOK)

def process_facebook_comments(data):
    """
    Handle Facebook Page webhook notifications for feed events.
    """
    print("📘 Processing Facebook Page webhook")
    
    # Process each entry in the webhook data
    print(f"📊 Processing {len(data['entry'])} entries")
    for entry in data.get("entry", []):
        if "changes" not in entry or not entry["changes"]:
            print("⚠️ No changes in entry:", entry.get("id", "unknown"))
            continue
        # Extract the time value from the entry
        timestamp = entry.get("time", "unknown")
        # UTC+5:30 offset
        IST = timezone(timedelta(hours=5, minutes=30))
        timestamp = datetime.fromtimestamp(timestamp, tz=IST).isoformat()
        # Process each change in the entry
        print(f"📊 Processing {len(entry['changes'])} changes in entry {entry.get('id', 'unknown')}")
        for change in entry.get("changes", []):
            # Only process feed changes
            if change["field"] != "feed":
                print(f"ℹ️ Ignoring non-feed field: {change['field']}")
                continue
                
            try:
                value = change["value"]
                item_type = value.get("item", "")
                verb = value.get("verb", "")
                
                print(f"📋 Feed event - Item: {item_type}, Verb: {verb}")
                
                # Only process comments
                if item_type == "comment" and verb == "add":
                    # Someone commented on a post
                    comment_id = value.get("comment_id")
                    post_id = value.get("post_id")
                    message = value.get("message", "")
                    from_user = value.get("from", {})
                    user_name = from_user.get("name", "Unknown")
                    user_id = from_user.get("id", "")  # Get PSID for @mention
                    
                    print(f"💬 {user_name} (ID: {user_id}) commented: {message}")
                    print(f"💬 Comment ID: {comment_id}")
                    
                    # Skip if the comment is from the Page itself (to avoid infinite loop)
                    if user_name == USERNAME_FACEBOOK:
                        print(f"👤 Skipping our own Facebook Page comment from {user_name}")
                        continue
                    
                    # Extract only the fields you care about
                    record = {
                        "username": user_name,
                        "comment_id": comment_id,
                        "comment": message,
                        "timestamp": timestamp,
                        "replied": False,
                        "user_id": user_id
                    }
                    
                     # Insert into Supabase table
                    response = supabase_facebook.table("Facebook Comments").insert(record).execute()

                    # Optional: log errors
                    if response.data:
                        print("Inserted:", response.data)
                    else:
                        print("Error:", response)    

                else:
                    print(f"ℹ️ Ignoring feed event: {item_type} - {verb}")
                    
            except KeyError as e:
                print(f"❌ Error processing feed event: Missing field {str(e)}")
                print("Change data:", change)
                continue

def process_facebook_dms(data):
    return  # Placeholder for Facebook DMs processing

@app.route('/subscribe-page', methods=['GET', 'POST'])
def subscribe_facebook_page():
    """
    Subscribe the Facebook Page to the app for feed webhooks.
    This needs to be called once to enable webhook notifications.
    """
    if not FACEBOOK_PAGE_ID or not FACEBOOK_ACCESS_TOKEN:
        return {"error": "FACEBOOK_PAGE_ID and FACEBOOK_ACCESS_TOKEN must be configured"}, 400
    
    url = f"https://{BASE_URL_FACEBOOK}/{API_VERSION_FACEBOOK}/{FACEBOOK_PAGE_ID}/subscribed_apps"
    params = {
        "subscribed_fields": "feed",
        "access_token": FACEBOOK_ACCESS_TOKEN
    }
    
    response = requests.post(url, params=params)
    
    if response.status_code == 200:
        result = response.json()
        return {"success": True, "message": "Page subscribed to app successfully", "data": result}, 200
    else:
        return {"success": False, "error": response.text, "status_code": response.status_code}, response.status_code

@app.route('/check-page-subscription', methods=['GET'])
def check_facebook_page_subscription():
    """
    Check which apps the Facebook Page has subscribed to.
    """
    if not FACEBOOK_PAGE_ID or not FACEBOOK_ACCESS_TOKEN:
        return {"error": "FACEBOOK_PAGE_ID and FACEBOOK_ACCESS_TOKEN must be configured"}, 400
    
    url = f"https://{BASE_URL_FACEBOOK}/{API_VERSION_FACEBOOK}/{FACEBOOK_PAGE_ID}/subscribed_apps"
    params = {
        "access_token": FACEBOOK_ACCESS_TOKEN
    }
    
    response = requests.get(url, params=params)
    
    if response.status_code == 200:
        return response.json(), 200
    else:
        return {"error": response.text}, response.status_code
    
@app.route('/debug-facebook-token', methods=['GET'])
def debug_facebook_token():
    """Debug Facebook token to see what permissions it has."""
    if not FACEBOOK_ACCESS_TOKEN:
        return {"error": "FACEBOOK_ACCESS_TOKEN not configured"}, 400
    
    # Check what the token represents

    url = f"https://{BASE_URL_FACEBOOK}/{API_VERSION_FACEBOOK}/me"    
    params = {"access_token": FACEBOOK_ACCESS_TOKEN}
    response = requests.get(url, params=params)
    
    token_info = response.json() if response.status_code == 200 else {"error": response.text}
    
    # Check token permissions
    debug_url = f"https://{BASE_URL_FACEBOOK}/{API_VERSION_FACEBOOK}/debug_token"
    debug_params = {
        "input_token": FACEBOOK_ACCESS_TOKEN,
        "access_token": FACEBOOK_ACCESS_TOKEN
    }
    debug_response = requests.get(debug_url, params=debug_params)
    
    return {
        "token_info": token_info,
        "token_debug": debug_response.json() if debug_response.status_code == 200 else {"error": debug_response.text},
        "configured_page_id": FACEBOOK_PAGE_ID
    }, 200

@app.route('/webhookfacebook', methods=['GET'])
def verify_webhook_facebook():
    print("🔎 Query params:", request.args)

    mode = request.args.get("hub.mode")
    token = request.args.get("hub.verify_token")
    challenge = request.args.get("hub.challenge")

    print("🔍 Mode:", mode)
    print("🔍 Token from Meta:", token)
    print("🔍 Challenge:", challenge)
    print("🔐 Local VERIFY_TOKEN:", VERIFY_TOKEN_FACEBOOK)

    if mode == "subscribe" and token == VERIFY_TOKEN_FACEBOOK:
        print("✅ Webhook verified.")
        return challenge, 200  # Must return challenge as plain text
    else:
        print("❌ Verification failed.")
        return "Verification failed", 403

@app.route('/webhookfacebook', methods=['POST'])
def webhook_facebook():
    data = request.get_json()
    print("📥 Received data:", data)
    time.sleep(2)  # Simulate processing delay
    # Check if we have the expected structure
    if not data or "entry" not in data or not data["entry"]:
        print("❌ Invalid data format")
        return "OK", 200
    if "changes" in data["entry"][0] and data["entry"][0]["changes"]:
        process_facebook_comments(data)
    if "messaging" in data["entry"][0] and data["entry"][0]["messaging"]:
        process_facebook_dms(data)
    return "OK", 200

#####################################################################################################
##########################################  THREADS  ################################################
#####################################################################################################

SUPABASE_URL_THREADS = os.environ['SUPABASE_URL_THREADS']
SUPABASE_KEY_THREADS = os.environ['SUPABASE_KEY_THREADS']
VERIFY_TOKEN_THREADS = os.environ['VERIFY_TOKEN_THREADS']
USERNAME_THREADS = os.environ['USERNAME_THREADS']

print("SUPABASE_URL_THREADS:", SUPABASE_URL_THREADS)
print("SUPABASE_KEY_THREADS:", SUPABASE_KEY_THREADS)
print("VERIFY_TOKEN_THREADS:", VERIFY_TOKEN_THREADS)
print("USERNAME_THREADS:", USERNAME_THREADS)

supabase_threads = create_client(SUPABASE_URL_THREADS, SUPABASE_KEY_THREADS)

def load_processed_tuples():
    if not os.path.exists(PROCESSED_TUPLES_FILE):
        return set()
    processed = set()
    with open(PROCESSED_TUPLES_FILE, "r") as f:
        for line in f:
            line = line.strip()
            if line:
                # Each line is a tuple string, eval to tuple
                try:
                    processed.add(eval(line))
                except Exception:
                    pass
    return processed

def save_processed_tuple(processed_tuple):
    with open(PROCESSED_TUPLES_FILE, "a") as f:
        f.write(f"{repr(processed_tuple)}\n")

# Store processed comment IDs to filter duplicates
processed_comment_tuples = load_processed_tuples()

def process_replies(data):
    """
    Handle Threads Page webhook notifications for replies.
    """
    print(f"📊 Processing {len(data['values'])} values")
    for value_obj in data["values"]:
        try:
            value = value_obj.get("value", {})
            comment_text = value.get("text", "")
            comment_id = value.get("id", "")
            username = value.get("username", "")
            replied_to = value.get("replied_to", {}).get("id", None)
            root_post = value.get("root_post", {})
            root_owner = root_post.get("owner_id", None)
            root_username = root_post.get("username", None)
            timestamp = value.get("timestamp", None)
            # Define IST timezone
            IST = timezone(timedelta(hours=5, minutes=30))
            # Parse the incoming UTC timestamp string
            dt_utc = datetime.strptime(timestamp, "%Y-%m-%dT%H:%M:%S%z")
            # Convert to IST and format as ISO string
            timestamp = dt_utc.astimezone(IST).isoformat()

            # Skip if the comment is from our own account
            if username == USERNAME_THREADS:
                print("👤 Skipping our own comment")
                continue

            # Create tuple for duplicate detection (now includes timestamp)
            processed_tuple = (comment_text, comment_id, username, replied_to, root_owner, root_username, timestamp)
            if processed_tuple in processed_comment_tuples:
                print(f"🔁 Duplicate webhook for tuple {processed_tuple}, skipping.")
                continue
            processed_comment_tuples.add(processed_tuple)
            save_processed_tuple(processed_tuple)

            print(f"👤 @{username} said: {comment_text}")

            # Extract only the fields you care about
            record = {
                "username": username,
                "reply_id": comment_id,
                "reply": comment_text,
                "timestamp": timestamp,
                "replied": False
            }

            # Insert into Supabase table
            response = supabase_threads.table("Thread Replies").insert(record).execute()

            # Optional: log errors
            if response.data:
                print("Inserted:", response.data)
            else:
                print("Error:", response)

        except Exception as e:
            print(f"❌ Error processing Threads value: {str(e)}")
            print("Value data:", value_obj)
            continue

@app.route('/webhookthreads', methods=['GET'])
def verify_webhook_threads():
    print("🔎 Query params:", request.args)

    mode = request.args.get("hub.mode")
    token = request.args.get("hub.verify_token")
    challenge = request.args.get("hub.challenge")

    print("🔍 Mode:", mode)
    print("🔍 Token from Meta:", token)
    print("🔍 Challenge:", challenge)
    print("🔐 Local VERIFY_TOKEN:", VERIFY_TOKEN_THREADS)

    if mode == "subscribe" and token == VERIFY_TOKEN_THREADS:
        print("✅ Webhook verified.")
        return challenge, 200  # Must return challenge as plain text
    else:
        print("❌ Verification failed.")
        return "Verification failed", 403

@app.route('/webhookthreads', methods=['POST'])
def webhook_threads():
    data = request.get_json()
    print("📥 Received data:", data)
    time.sleep(2)  # Simulate processing delay
    # Threads webhook payload structure is different from Instagram
    if not data or "values" not in data or not data["values"]:
        print("❌ Invalid Threads data format")
        return "OK", 200

    process_replies(data)
    return "OK", 200

if __name__ == '__main__':
    app.run(debug=True)