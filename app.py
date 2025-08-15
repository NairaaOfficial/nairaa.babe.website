from flask import Flask, render_template, request
import os
import time
from supabase import create_client
from datetime import datetime, timedelta, timezone

app = Flask(__name__)
app.secret_key = '12345678'  # Replace with a secure key

PROCESSED_TUPLES_FILE = "processed_tuples.txt"

# Load from environment variables for safety
SUPABASE_URL_INSTAGRAM = os.environ['SUPABASE_URL_INSTAGRAM']
SUPABASE_KEY_INSTAGRAM = os.environ['SUPABASE_KEY_INSTAGRAM']
VERIFY_TOKEN_INSTAGRAM = os.environ['VERIFY_TOKEN_INSTAGRAM']
USERNAME_INSTAGRAM = os.environ['USERNAME_INSTAGRAM']

print("SUPABASE_URL_INSTAGRAM:", SUPABASE_URL_INSTAGRAM)
print("SUPABASE_KEY_INSTAGRAM:", SUPABASE_KEY_INSTAGRAM)
print("VERIFY_TOKEN_INSTAGRAM:", VERIFY_TOKEN_INSTAGRAM)
print("USERNAME_INSTAGRAM:", USERNAME_INSTAGRAM)

SUPABASE_URL_THREADS = os.environ['SUPABASE_URL_THREADS']
SUPABASE_KEY_THREADS = os.environ['SUPABASE_KEY_THREADS']
VERIFY_TOKEN_THREADS = os.environ['VERIFY_TOKEN_THREADS']
USERNAME_THREADS = os.environ['USERNAME_THREADS']

print("SUPABASE_URL_THREADS:", SUPABASE_URL_THREADS)
print("SUPABASE_KEY_THREADS:", SUPABASE_KEY_THREADS)
print("VERIFY_TOKEN_THREADS:", VERIFY_TOKEN_THREADS)
print("USERNAME_THREADS:", USERNAME_THREADS)

supabase_instagram = create_client(SUPABASE_URL_INSTAGRAM, SUPABASE_KEY_INSTAGRAM)
supabase_threads = create_client(SUPABASE_URL_THREADS, SUPABASE_KEY_THREADS)

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

def process_comments(data):
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

@app.route('/webhookinstagram', methods=['POST'])
def webhook_instagram():
    data = request.get_json()
    print("📥 Received data:", data)
    time.sleep(2)  # Simulate processing delay
    # Check if we have the expected structure
    if not data or "entry" not in data or not data["entry"]:
        print("❌ Invalid data format")
        return "OK", 200

    process_comments(data)
    return "OK", 200

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

