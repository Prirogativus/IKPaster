import telebot
from telebot import types
import json
import os

TOKEN = ''
bot = telebot.TeleBot(TOKEN)

# Global variables for storing models
example_model = None
target_model = None
target_descriptions = {}

# File path for communication with orchestrator
MODEL_DATA_FILE = "telegram_model_data.json"

# Helper function to save model data to file
def save_models_to_file():
    try:
        data = {
            'example_model': example_model,
            'target_model': target_model
        }
        with open(MODEL_DATA_FILE, 'w') as f:
            json.dump(data, f)
        print(f"Saved models to file: Example={example_model}, Target={target_model}")
        return True
    except Exception as e:
        print(f"Error saving models to file: {e}")
        return False

# Command handler for /start
@bot.message_handler(commands=['start'])
def start_message(message):
    bot.send_message(message.chat.id, "Hi! I am your automatization bot.")
    ask_example_model(message.chat.id)

# Function to request example model
def ask_example_model(chat_id):
    msg = bot.send_message(chat_id, "Give me an example model:")
    bot.register_next_step_handler(msg, process_example_model_step)

# Process example model response
def process_example_model_step(message):
    global example_model
    example_model = message.text
    
    # Ask for target model
    msg = bot.send_message(message.chat.id, "Give me a target model:")
    bot.register_next_step_handler(msg, process_target_model_step)

# Process target model response
def process_target_model_step(message):
    global target_model
    target_model = message.text
    
    # Save models to file for the orchestrator
    save_models_to_file()
    
    # Thank the user and show the selected models
    response = f"Example: {example_model}, Target: {target_model}.\n\nStarting the automation process..."
    bot.send_message(message.chat.id, response)
    print(f"Models set: Example={example_model}, Target={target_model}")

# Command to show saved models
@bot.message_handler(commands=['show_models'])
def show_models(message):
    if example_model and target_model:
        response = f"Saved models:\nExample: {example_model}\nTarget: {target_model}"
    else:
        response = "No models saved yet. Please use /start command first."
    bot.send_message(message.chat.id, response)

# Command to clear all data
@bot.message_handler(commands=['clear'])
def clear_data(message):
    global example_model, target_model, target_descriptions
    
    # Clear global variables
    example_model = None
    target_model = None
    target_descriptions = {}
    
    # Remove the data file if it exists
    if os.path.exists(MODEL_DATA_FILE):
        try:
            os.remove(MODEL_DATA_FILE)
            status = "and removed data file"
        except:
            status = "but failed to remove data file"
    else:
        status = "(no data file found)"
    
    bot.send_message(message.chat.id, f"All data cleared {status}. Use /start to begin again.")

# Run the bot
if __name__ == '__main__':
    print("Starting Telegram bot...")
    bot.polling(none_stop=True)             