import threading
import time
import logging
import json
import os
import TelegramInteraction
from Orchestrator import AutomationOrchestrator

def setup_logger():
    """Configure logging based on the instance configuration."""
    try:
        # Load configuration
        with open("config.json", "r") as f:
            config = json.load(f)
        
        instance_id = config.get("instance_id", 0)
        log_dir = config.get("log_dir", "logs")
        os.makedirs(log_dir, exist_ok=True)
        
        log_file = os.path.join(log_dir, "ikpaster.log")
        
        # Set up logging
        logger = logging.getLogger("ikpaster")
        logger.setLevel(logging.INFO)
        
        # Remove any existing handlers
        for handler in logger.handlers[:]:
            logger.removeHandler(handler)
        
        # Add file handler
        file_handler = logging.FileHandler(log_file)
        file_handler.setFormatter(logging.Formatter(f'[Instance {instance_id}] %(asctime)s - %(levelname)s - %(message)s'))
        logger.addHandler(file_handler)
        
        # Add console handler
        console_handler = logging.StreamHandler()
        console_handler.setFormatter(logging.Formatter(f'[Instance {instance_id}] %(asctime)s - %(levelname)s - %(message)s'))
        logger.addHandler(console_handler)
        
        return logger
        
    except Exception as e:
        # Fallback logging if config fails
        logging.basicConfig(
            level=logging.INFO,
            format='%(asctime)s - %(levelname)s - %(message)s',
            handlers=[
                logging.FileHandler("ikpaster.log"),
                logging.StreamHandler()
            ]
        )
        logger = logging.getLogger("ikpaster")
        logger.error(f"Error setting up logger: {e}")
        return logger

def main():
    """Main entry point for the application."""
    logger = setup_logger()
    logger.info("Starting IKPaster application")
    
    try:
        # Load configuration to get instance info
        with open("config.json", "r") as f:
            config = json.load(f)
        instance_id = config.get("instance_id", 0)
        
        logger.info(f"Running as Instance {instance_id}")
        
        # Start the Telegram bot in a background thread
        telegram_thread = threading.Thread(target=TelegramInteraction.start_bot)
        telegram_thread.daemon = True
        telegram_thread.start()
        
        logger.info("Telegram bot started in background thread")
        
        # Allow some time for the bot to initialize
        time.sleep(3)
        
        # Run the orchestrator
        orchestrator = AutomationOrchestrator()
        orchestrator.run()
        
        logger.info("IKPaster application completed")
        print("\nProcess completed. Keep this window open to continue receiving Telegram messages.")
        
        # Keep the main thread alive to allow the Telegram bot to run
        while telegram_thread.is_alive():
            time.sleep(1)
            
    except Exception as e:
        logger.error(f"Error in main function: {e}")
        print(f"\nAn error occurred: {e}")
        input("Press Enter to exit...")

if __name__ == "__main__":
    main()