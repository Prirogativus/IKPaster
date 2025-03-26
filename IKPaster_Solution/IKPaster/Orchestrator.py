import logging
import time
import threading
import json
import os
import TelegramInteraction
import DataExtractor
import AnthropicAPI
import ContentPublisher
from DataManager import data_manager

def setup_logger():
    """Configure logging based on the instance configuration."""
    try:
        # Load configuration
        with open("config.json", "r") as f:
            config = json.load(f)
        
        instance_id = config.get("instance_id", 0)
        log_dir = config.get("log_dir", "logs")
        os.makedirs(log_dir, exist_ok=True)
        
        log_file = os.path.join(log_dir, "orchestrator.log")
        
        # Set up logging
        logger = logging.getLogger("orchestrator")
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
                logging.FileHandler("orchestrator.log"),
                logging.StreamHandler()
            ]
        )
        logger = logging.getLogger("orchestrator")
        logger.error(f"Error setting up logger: {e}")
        return logger

# Global logger instance
logger = setup_logger()

class AutomationOrchestrator:
    """
    Orchestrates the workflow between Telegram bot, DataExtractor, AnthropicAPI, and ContentPublisher.
    Uses DataManager for in-memory data exchange between components.
    """
    
    def __init__(self):
        """Initialize the orchestrator with values from config file."""
        try:
            # Load configuration
            with open("config.json", "r") as f:
                config = json.load(f)
            
            credentials = config.get("admin_credentials", {})
            self.username = credentials.get("username", "Istomin")
            self.password = credentials.get("password", "VnXJ7i47n4tjWj&g")
            self.instance_id = config.get("instance_id", 0)
            
            # Status flags
            self.extraction_complete = False
            self.anthropic_complete = False
            
            logger.info(f"AutomationOrchestrator initialized for instance {self.instance_id}")
            
        except Exception as e:
            logger.error(f"Error initializing AutomationOrchestrator: {e}")
            # Default values as fallback
            self.username = "Istomin"
            self.password = "VnXJ7i47n4tjWj&g"
            self.instance_id = 0
            self.extraction_complete = False
            self.anthropic_complete = False
    
    def wait_for_telegram_inputs(self, timeout=3600, check_interval=5):
        """
        Wait for model data to be set by the Telegram bot in DataManager.
        Timeout after the specified duration (in seconds).
        """
        logger.info("Waiting for model inputs from Telegram bot...")
        
        start_time = time.time()
        while time.time() - start_time < timeout:
            # Check if models are available in DataManager
            if data_manager.example_model and data_manager.target_model:
                logger.info(f"Received inputs: Example={data_manager.example_model}, Target={data_manager.target_model}")
                return True
            
            # Log waiting status periodically (every minute)
            if (time.time() - start_time) % 60 < check_interval:
                logger.info(f"Still waiting for model data... ({int(time.time() - start_time)} seconds elapsed)")
                
                # Debug info
                logger.info(f"Current DataManager state: example_model={data_manager.example_model}, target_model={data_manager.target_model}")
                
                # Also check TelegramInteraction directly
                if hasattr(TelegramInteraction, 'example_model') and TelegramInteraction.example_model and \
                   hasattr(TelegramInteraction, 'target_model') and TelegramInteraction.target_model:
                    logger.info("Found models in TelegramInteraction but not in DataManager, synchronizing...")
                    data_manager.set_models(TelegramInteraction.example_model, TelegramInteraction.target_model)
                    return True
            
            time.sleep(check_interval)
        
        logger.error(f"Timed out waiting for model data after {timeout} seconds")
        return False
    
    def run_data_extractor(self):
        """
        Run the DataExtractor to extract content for the example model.
        """
        logger.info("Starting DataExtractor...")
        
        try:
            # Create DataExtractor instance
            data_extractor = DataExtractor.DataExtractorClass(
                username=self.username,
                password=self.password
            )
            
            # Run the extractor
            data_extractor.run()
            
            # Store the extracted descriptions in DataManager
            if hasattr(data_extractor, 'example_descriptions') and data_extractor.example_descriptions:
                data_manager.set_target_descriptions(data_extractor.example_descriptions)
                logger.info(f"Stored {len(data_extractor.example_descriptions)} descriptions in DataManager")
            
            # Set flag to indicate completion
            self.extraction_complete = True
            logger.info("DataExtractor completed successfully")
            
        except Exception as e:
            logger.error(f"Error in DataExtractor: {e}")
            # In case of error, make sure we don't block the process
            self.extraction_complete = True
    
    def run_anthropic_api(self):
        """
        Run the AnthropicAPI to process the extracted content.
        This will wait for the extraction to complete.
        """
        logger.info("Preparing to run AnthropicAPI...")
        
        # Wait for data extraction to complete
        while not self.extraction_complete:
            logger.info("Waiting for DataExtractor to complete...")
            time.sleep(5)
        
        try:
            # Get descriptions from DataManager
            descriptions = data_manager.get_target_descriptions()
            
            if not descriptions:
                logger.error("No descriptions available in DataManager for processing")
                self.anthropic_complete = True
                return
            
            logger.info(f"Retrieved {len(descriptions)} descriptions from DataManager")
            logger.info("Starting AnthropicAPI processing...")
            
            # Run the AnthropicAPI
            success = AnthropicAPI.get_target_text()
            
            # Set flag to indicate completion
            self.anthropic_complete = True
            logger.info("AnthropicAPI processing completed successfully" if success else "AnthropicAPI processing failed")
            
        except Exception as e:
            logger.error(f"Error in AnthropicAPI: {e}")
            # In case of error, make sure we don't block the process
            self.anthropic_complete = True
    
    def run_content_publisher(self):
        """
        Run the ContentPublisher to publish the processed content.
        This will wait for AnthropicAPI to complete.
        """
        logger.info("Preparing to run ContentPublisher...")
        
        # Wait for Anthropic processing to complete
        while not self.anthropic_complete:
            logger.info("Waiting for AnthropicAPI to complete...")
            time.sleep(5)
        
        try:
            logger.info("Starting ContentPublisher...")
            
            # Get descriptions from DataManager
            descriptions = data_manager.get_target_descriptions()
            
            if not descriptions:
                logger.error("No descriptions available in DataManager for publishing")
                return
            
            logger.info(f"Retrieved {len(descriptions)} descriptions from DataManager for publishing")
            
            # Prepare the descriptions for publishing
            logger.info("Preparing content for publishing...")
            data_manager.prepare_descriptions_for_publishing()
            
            # Create ContentPublisher instance
            content_publisher = ContentPublisher.ContentPublisher(
                username=self.username,
                password=self.password
            )
            
            # Run the publisher
            success = content_publisher.run()
            
            logger.info("ContentPublisher completed successfully" if success else "ContentPublisher failed")
            
            # Clear data when done
            data_manager.clear_data()
            logger.info("Cleared data from DataManager")
            
        except Exception as e:
            logger.error(f"Error in ContentPublisher: {e}")
    
    def run(self):
        """
        Main execution method that orchestrates the entire workflow.
        """
        try:
            logger.info(f"Starting the automation workflow for instance {self.instance_id}...")
            
            # Wait for Telegram inputs
            if not self.wait_for_telegram_inputs():
                logger.error("Failed to get inputs from Telegram, aborting workflow")
                return False
            
            # Start DataExtractor in a separate thread
            extractor_thread = threading.Thread(target=self.run_data_extractor)
            extractor_thread.start()
            
            # Start AnthropicAPI in a separate thread
            anthropic_thread = threading.Thread(target=self.run_anthropic_api)
            anthropic_thread.start()
            
            # Start ContentPublisher in a separate thread
            publisher_thread = threading.Thread(target=self.run_content_publisher)
            publisher_thread.start()
            
            # Wait for all threads to complete
            extractor_thread.join()
            logger.info("DataExtractor thread completed")
            
            anthropic_thread.join()
            logger.info("AnthropicAPI thread completed")
            
            publisher_thread.join()
            logger.info("ContentPublisher thread completed")
            
            logger.info(f"Automation workflow completed for instance {self.instance_id}")
            return True
            
        except Exception as e:
            logger.error(f"Error in automation workflow: {e}")
            return False

# Only run the following code if this file is executed directly
if __name__ == "__main__":
    # This is for backwards compatibility when running the orchestrator standalone
    # Start the Telegram bot in a background thread
    telegram_thread = threading.Thread(target=TelegramInteraction.start_bot)
    telegram_thread.daemon = True  # This will allow the main program to exit even if the thread is running
    telegram_thread.start()
    
    # Give the Telegram bot a moment to initialize
    time.sleep(2)
    
    print("Telegram bot started in background thread")
    
    # Run the orchestrator in the main thread
    orchestrator = AutomationOrchestrator()
    orchestrator.run()