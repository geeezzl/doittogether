import os
import datetime
from flask import Flask, request, abort
from linebot.v3 import (
    WebhookHandler
)
from linebot.v3.exceptions import (
    InvalidSignatureError
)
from linebot.v3.messaging import (
    Configuration,
    ApiClient,
    MessagingApi,
    ReplyMessageRequest,
    TextMessage
)
from linebot.v3.webhooks import (
    MessageEvent,
    TextMessageContent,
    FollowEvent
)

app = Flask(__name__)

# --- IMPORTANT: SET THESE IN YOUR ENVIRONMENT ---
# Get these values from your LINE Developer Console
CHANNEL_ACCESS_TOKEN = os.environ.get('EKYb+wID9yQIMM0Vt6aKtT+LFgSXKE7peXmqIzYLy/DyfZJawLhpAlwIF6y9iMvYkPiPtLWoYwfmzDUVlWpD/iR5rGb+DiEl880TGNK4GEpUoREXHA6VikhDQe7zZJk9ENujOjRH1mxlNgUdO6hP4AdB04t89/1O/w1cDnyilFU=','EKYb+wID9yQIMM0Vt6aKtT+LFgSXKE7peXmqIzYLy/DyfZJawLhpAlwIF6y9iMvYkPiPtLWoYwfmzDUVlWpD/iR5rGb+DiEl880TGNK4GEpUoREXHA6VikhDQe7zZJk9ENujOjRH1mxlNgUdO6hP4AdB04t89/1O/w1cDnyilFU=')
CHANNEL_SECRET = os.environ.get('b951f559a715e686a77e649cb2213e60','b951f559a715e686a77e649cb2213e60')
# ------------------------------------------------

configuration = Configuration(access_token=CHANNEL_ACCESS_TOKEN)
handler = WebhookHandler(CHANNEL_SECRET)

# --- This is your "database" for now ---
# NOTE: This is temporary! It will reset every time you restart the server.
# Your next step will be to replace this with a real database (like SQLite or Firestore).
posts_db = []
# ------------------------------------------------

@app.route("/callback", methods=['POST'])
def callback():
    # Get X-Line-Signature header value
    signature = request.headers['X-Line-Signature']

    # Get request body as text
    body = request.get_data(as_text=True)
    app.logger.info("Request body: " + body)

    # Handle webhook body
    try:
        handler.handle(body, signature)
    except InvalidSignatureError:
        app.logger.info("Invalid signature. Please check your channel access token/channel secret.")
        abort(400)
    except Exception as e:
        app.logger.error(f"Error handling webhook: {e}")
        abort(500)

    return 'OK'

@handler.add(FollowEvent)
def handle_follow(event):
    """Handles when a user adds the bot as a friend."""
    with ApiClient(configuration) as api_client:
        line_bot_api = MessagingApi(api_client)
        
        # Get user's profile
        try:
            profile = line_bot_api.get_profile(event.source.user_id)
            user_name = profile.display_name
        except Exception:
            user_name = "Student"

        welcome_message = (
            f"Hi {user_name}, welcome!\n\n"
            "You can find people or post an activity.\n\n"
            "Try these commands:\n"
            "1. `!post [your activity]`\n"
            "   (e.g., !post Need 5 for basketball tonight at 7)\n\n"
            "2. `!search`\n"
            "   (to see all current posts)"
        )
        
        line_bot_api.reply_message(
            ReplyMessageRequest(
                reply_token=event.reply_token,
                messages=[TextMessage(text=welcome_message)]
            )
        )

@handler.add(MessageEvent, message=TextMessageContent)
def handle_message(event):
    """Handles text messages from users."""
    text = event.message.text.strip()
    user_id = event.source.user_id
    
    with ApiClient(configuration) as api_client:
        line_bot_api = MessagingApi(api_client)
        
        try:
            # Get user's profile to make posts more personal
            profile = line_bot_api.get_profile(user_id)
            user_name = profile.display_name
        except Exception as e:
            app.logger.error(f"Could not get profile: {e}")
            user_name = "A Student"

        reply_message = ""

        # --- Your Function 1: Post ---
        if text.lower().startswith('!post '):
            post_content = text[6:].strip() # Get everything after "!post "
            if not post_content:
                reply_message = "Please write what you want to post after `!post`."
            else:
                new_post = {
                    "user_name": user_name,
                    "content": post_content,
                    "timestamp": datetime.datetime.now()
                }
                posts_db.append(new_post)
                reply_message = "✅ Your post has been added!"
        
        # --- Your Function 2: Search ---
        elif text.lower() == '!search':
            if not posts_db:
                reply_message = "Nobody has posted anything yet. Be the first! (Try `!post ...`)"
            else:
                reply_message = "Here are the current posts:\n"
                # Loop in reverse to show newest first
                for post in reversed(posts_db):
                    # Format timestamp nicely
                    time_str = post['timestamp'].strftime("%I:%M %p")
                    reply_message += f"\n• [{time_str}] {post['user_name']}:\n   {post['content']}\n"
        
        # --- Help Message ---
        else:
            reply_message = (
                "Sorry, I didn't understand that.\n\n"
                "Try `!post [your message]` or `!search`."
            )

        # Send the reply
        line_bot_api.reply_message(
            ReplyMessageRequest(
                reply_token=event.reply_token,
                messages=[TextMessage(text=reply_message)]
            )
        )

if __name__ == "__main__":
    # Get port from environment variable or default to 5000
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port, debug=True)
