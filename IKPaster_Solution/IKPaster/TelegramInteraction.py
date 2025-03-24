import telebot
from telebot import types
from DataManager import data_manager

TOKEN = ''
bot = telebot.TeleBot(TOKEN)

# Global variables for storing models
example_model = None
target_model = None
target_descriptions = {}

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
    
    # Update DataManager
    data_manager.example_model = example_model
    
    # Ask for target model
    msg = bot.send_message(message.chat.id, "Give me a target model:")
    bot.register_next_step_handler(msg, process_target_model_step)

# Process target model response
def process_target_model_step(message):
    global target_model
    target_model = message.text
    
    # Update DataManager with both models
    data_manager.set_models(example_model, target_model)
    
    # Thank the user and show the selected models
    response = f"Example: {example_model}, Target: {target_model}.\n\nStarting the automation process..."
    bot.send_message(message.chat.id, response)
    print(f"Models set: Example={example_model}, Target={target_model}")

# Command to show saved models
@bot.message_handler(commands=['show_models'])
def show_models(message):
    # Get models from DataManager for consistency
    dm_example = data_manager.example_model or example_model
    dm_target = data_manager.target_model or target_model
    
    if dm_example and dm_target:
        response = f"Saved models:\nExample: {dm_example}\nTarget: {dm_target}"
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
    
    # Clear DataManager
    data_manager.clear_data()
    
    bot.send_message(message.chat.id, "All data cleared. Use /start to begin again.")

# Add a function to start the bot (for Orchestrator to use)
def start_bot():
    print("Starting Telegram bot...")
    bot.polling(none_stop=True)

# Run the bot if this file is executed directly
if __name__ == '__main__':
    start_bot()