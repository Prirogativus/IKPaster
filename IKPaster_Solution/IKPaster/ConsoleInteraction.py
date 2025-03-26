from DataManager import data_manager
import logging

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler("console.log"),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

# Global variables for storing models (for compatibility with existing code)
example_model = None
target_model = None
target_descriptions = {}

def get_user_input():
    """Gets the example and target models from user via console input"""
    global example_model, target_model
    
    print("Hi! I am your automatization bot.")
    
    # Get example model
    example_model = input("Give me an example model: ")
    
    # Get target model
    target_model = input("Give me a target model: ")
    
    # Update DataManager
    data_manager.set_models(example_model, target_model)
    
    # Thank the user and show the selected models
    print(f"Example: {example_model}, Target: {target_model}")
    print("Starting the automation process...")
    logger.info(f"Models set: Example={example_model}, Target={target_model}")

def start_console():
    """Start the console interaction"""
    logger.info("Starting console interaction...")
    get_user_input()

# Run the console interface if this file is executed directly
if __name__ == '__main__':
    start_console()