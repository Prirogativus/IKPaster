import telebot
from telebot import types
import json
import os
import logging
from DataManager import data_manager

class TelegramBot:
    def __init__(self, config_path="config.json"):
        # Load configuration
        try:
            with open(config_path, "r") as f:
                config = json.load(f)
                
            self.instance_id = config.get("instance_id", 0)
            self.token = config.get("telegram_token", "")
            
            # Setup logging
            log_dir = config.get("log_dir", "logs")
            os.makedirs(log_dir, exist_ok=True)
            
            log_file = os.path.join(log_dir, "telegram.log")
            logging.basicConfig(
                level=logging.INFO,
                format=f'[Instance {self.instance_id}] %(asctime)s - %(levelname)s - %(message)s',
                handlers=[
                    logging.FileHandler(log_file),
                    logging.StreamHandler()
                ]
            )
            self.logger = logging.getLogger(f"telegram_bot_{self.instance_id}")
            
            # Initialize bot
            self.bot = telebot.TeleBot(self.token)
            
            # Global variables for storing models
            self.example_model = None
            self.target_model = None
            self.target_descriptions = {}
            
            # Share with DataManager module
            global example_model, target_model, target_descriptions
            example_model = self.example_model
            target_model = self.target_model
            target_descriptions = self.target_descriptions
            
            # Register handlers
            self._register_handlers()
            
            self.logger.info(f"Telegram bot for instance {self.instance_id} initialized with token: {self.token[:5]}...{self.token[-5:]}")
            
        except Exception as e:
            print(f"Error initializing TelegramBot: {e}")
            raise
            
    def _register_handlers(self):
        """Register all message handlers"""
        
        # Command handler for /start
        @self.bot.message_handler(commands=['start'])
        def start_message(message):
            self.bot.send_message(message.chat.id, f"Hi! I am your automatization bot (Instance {self.instance_id}).")
            self.ask_example_model(message.chat.id)
        
        # Command to show saved models
        @self.bot.message_handler(commands=['show_models'])
        def show_models(message):
            # Get models from DataManager for consistency
            dm_example = data_manager.example_model or self.example_model
            dm_target = data_manager.target_model or self.target_model
            
            if dm_example and dm_target:
                response = f"Saved models (Instance {self.instance_id}):\nExample: {dm_example}\nTarget: {dm_target}"
            else:
                response = f"No models saved yet for Instance {self.instance_id}. Please use /start command first."
            self.bot.send_message(message.chat.id, response)
        
        # Command to clear all data
        @self.bot.message_handler(commands=['clear'])
        def clear_data(message):
            # Clear instance variables
            self.example_model = None
            self.target_model = None
            self.target_descriptions = {}
            
            # Update global variables for compatibility
            global example_model, target_model, target_descriptions
            example_model = None
            target_model = None
            target_descriptions = {}
            
            # Clear DataManager
            data_manager.clear_data()
            
            self.bot.send_message(message.chat.id, f"All data cleared for Instance {self.instance_id}. Use /start to begin again.")
    
    def ask_example_model(self, chat_id):
        """Function to request example model"""
        msg = self.bot.send_message(chat_id, "Give me an example model:")
        self.bot.register_next_step_handler(msg, self.process_example_model_step)
    
    def process_example_model_step(self, message):
        """Process example model response"""
        self.example_model = message.text
        
        # Update global variable for compatibility
        global example_model
        example_model = self.example_model
        
        # Update DataManager
        data_manager.example_model = self.example_model
        
        # Ask for target model
        msg = self.bot.send_message(message.chat.id, "Give me a target model:")
        self.bot.register_next_step_handler(msg, self.process_target_model_step)
    
    def process_target_model_step(self, message):
        """Process target model response"""
        self.target_model = message.text
        
        # Update global variable for compatibility
        global target_model
        target_model = self.target_model
        
        # Update DataManager with both models
        data_manager.set_models(self.example_model, self.target_model)
        
        # Thank the user and show the selected models
        response = f"Example: {self.example_model}, Target: {self.target_model}.\n\nStarting the automation process..."
        self.bot.send_message(message.chat.id, response)
        self.logger.info(f"Models set: Example={self.example_model}, Target={self.target_model}")
    
    def start_bot(self):
        """Start the bot polling"""
        self.logger.info(f"Starting Telegram bot for instance {self.instance_id}...")
        self.bot.polling(none_stop=True)

# For compatibility with existing code that imports from this module
example_model = None
target_model = None
target_descriptions = {}

# Initialize the bot when this module is imported
telegram_bot = None

def start_bot():
    """Function to start the bot (for backwards compatibility)"""
    global telegram_bot
    if telegram_bot is None:
        telegram_bot = TelegramBot()
    telegram_bot.start_bot()

# Run the bot if this file is executed directly
if __name__ == '__main__':
    start_bot()