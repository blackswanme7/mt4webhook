from telegram.ext import Updater, CommandHandler
import json
import logging
import threading
import os 
from mt4grpc.sdk.python3 import mt4_pb2_grpc
from mt4grpc.sdk.python3.mt4_pb2 import *
import grpc

# Enable logging
logging.basicConfig(format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
                    level=logging.INFO)
logger = logging.getLogger(__name__)

# Load environment variables

# Bot Token from .env file
TOKEN = os.environ.get('TELEGRAM_TOKEN')
WEBHOOK_URL = os.environ.get('WEBHOOK_URL')
# Load or initialize config
def load_config():
    try:
        with open('config.json', 'r') as file:
            return json.load(file)
    except FileNotFoundError:
        return {}

config = load_config()
# Global variable to store the current state of removal process
removal_state = {}
# Save config to file
def save_config():
    with open('config.json', 'w') as file:
        json.dump(config, file, indent=4)

# Load or initialize authorized users
def load_authorized_users():
    try:
        with open('authorized_users.json', 'r') as file:
            return json.load(file)
    except FileNotFoundError:
        return []

authorized_users = load_authorized_users()

# Check if a user is authorized
def is_user_authorized(username):
    return username in authorized_users

# Command Handlers
def start(update, context):
    user = update.message.from_user
    logger.info(f"Bot started by: Username - {user.username}, User ID - {user.id}")
    update.message.reply_text('Welcome to the Config Bot. Use commands like /add, /remove, /view.')

def add_config(update, context):
    user = update.message.from_user

    if not is_user_authorized(user.username):
        update.message.reply_text('You are not authorized to use this command.')
        return

    args = context.args
    if len(args) == 3:
        numeric_user_id, password, host = args  # Adjust the order of arguments

        # Attempt to connect to MT4 with provided credentials
        try:
            channel = grpc.secure_channel('mt4grpc.mtapi.io:443', grpc.ssl_channel_credentials())
            connection = mt4_pb2_grpc.ConnectionStub(channel)

            req = ConnectRequest(user=int(numeric_user_id), password=password, host=host, port=443)
            res = connection.Connect(req)

            if res.error.message:
                update.message.reply_text(f"Client not added. Error: {res.error.message}")
                return

            # Save config under numeric user ID
            config[numeric_user_id] = {"host": host, "user": numeric_user_id, "pass": password}
            save_config()
            update.message.reply_text(f'Configuration added and client account connected for user ID {numeric_user_id}.')
        
        except Exception as e:
            update.message.reply_text(f"Failed to connect to MT4. Error: {str(e)}")
            logger.error(f"MT4 connection error for user ID {numeric_user_id}: {str(e)}")

    else:
        update.message.reply_text('Usage: /add <user_id> <password> <host>')


def remove_config(update, context):
    user = update.message.from_user

    if not is_user_authorized(user.username):
        update.message.reply_text('You are not authorized to use this command.')
        return

    # List all usernames for selection
    if not context.args:
        message = "/remove <user_id>\nSelect which user to remove:\n"
        for user_id in config.keys():
            message += f"- {user_id}\n"
        update.message.reply_text(message)
        removal_state[user.username] = "awaiting_selection"
        return

    # Process the removal if the username is provided
    if removal_state.get(user.username) == "awaiting_selection":
        selected_user_id = context.args[0]
        if selected_user_id in config:
            del config[selected_user_id]
            save_config()
            update.message.reply_text(f'Removed configuration for user {selected_user_id}.')
            removal_state[user.username] = None
        else:
            update.message.reply_text(f'No configuration found for user {selected_user_id}.')
    else:
        update.message.reply_text('Please use the command like this: /remove <user_id>')


def view_config(update, context):
    user = update.message.from_user

    if user.username not in authorized_users:
        update.message.reply_text('You are not authorized to use this command.')
        return

    message = "Webhook URLs and Configurations:\n"
    for user_id, details in config.items():
        host = details.get("host", "Not set")
        username = details.get("user", "Not set")
        # Construct the webhook URL for each user
        webhook_url = f"{WEBHOOK_URL}/{user_id}"
        message += f"\nWebhook URL: {webhook_url}\nHost: {host}\nUsername: {username}\n"

    update.message.reply_text(message)



# Main function to start the bot
def run_bot():
    updater = Updater(token=TOKEN)
    dispatcher = updater.dispatcher

    # Add command handlers
    dispatcher.add_handler(CommandHandler("start", start))
    dispatcher.add_handler(CommandHandler("add", add_config, pass_args=True))
    dispatcher.add_handler(CommandHandler("remove", remove_config, pass_args=True))
    dispatcher.add_handler(CommandHandler("view", view_config))

    # Start the bot
    updater.start_polling()
    updater.idle()


def start_telegram_bot():
    thread = threading.Thread(target=run_bot)
    thread.start()

if __name__ == '__main__':
    run_bot()
# Run the bot in a separate thread