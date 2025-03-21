import logging
import time
import threading
import os
import json
import TelegramInteraction
import DataExtractor
import AnthropicAPI
import ContentPublisher
from DataManager import data_manager

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler("orchestrator.log"),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

# File paths for communication between processes
MODEL_DATA_FILE = "telegram_model_data.json"
DESCRIPTIONS_FILE = "descriptions_data.json"

class AutomationOrchestrator:
    """
    Orchestrates the workflow between Telegram bot, DataExtractor, AnthropicAPI, and ContentPublisher.
    Uses DataManager for inter-module communication.
    """
    
    def __init__(self):
        self.telegram_bot = TelegramInteraction
        
        # Initialize credentials
        self.username = "Istomin"
        self.password = "VnXJ7i47n4tjWj&g"
        
        # Status flags
        self.extraction_complete = False
        self.anthropic_complete = False
        
        # Model data
        self.example_model = None
        self.target_model = None
        
        logger.info("AutomationOrchestrator initialized")
    
    def save_models_to_data_manager(self):
        """
        Save the model data to DataManager for use by other components.
        """
        data_manager.set_models(self.example_model, self.target_model)
        logger.info(f"Saved models to DataManager: Example={self.example_model}, Target={self.target_model}")
    
    def check_model_file(self):
        """
        Check if the model data file exists and contains valid data.
        Returns a tuple (has_data, example_model, target_model)
        """
        if os.path.exists(MODEL_DATA_FILE):
            try:
                with open(MODEL_DATA_FILE, 'r') as f:
                    data = json.load(f)
                    
                example_model = data.get('example_model')
                target_model = data.get('target_model')
                
                if example_model and target_model:
                    return True, example_model, target_model
            
            except Exception as e:
                logger.error(f"Error reading model file: {e}")
        
        return False, None, None
    
    def wait_for_telegram_inputs(self, timeout=3600, check_interval=5):
        """
        Wait for the model data file to be created by the Telegram bot.
        """
        logger.info("Waiting for Telegram bot inputs (checking for data file)...")
        
        start_time = time.time()
        while time.time() - start_time < timeout:
            has_data, example_model, target_model = self.check_model_file()
            
            if has_data:
                self.example_model = example_model
                self.target_model = target_model
                
                # Save to DataManager for other components
                self.save_models_to_data_manager()
                
                logger.info(f"Received inputs from file - Example: {example_model}, Target: {target_model}")
                return True
            
            # Log waiting status periodically (every minute)
            if (time.time() - start_time) % 60 < check_interval:
                logger.info(f"Still waiting for model data file... ({int(time.time() - start_time)} seconds elapsed)")
            
            time.sleep(check_interval)
        
        logger.error(f"Timed out waiting for model data file after {timeout} seconds")
        return False
    
    def save_descriptions_to_file(self, descriptions):
        """
        Save the extracted descriptions to a file.
        """
        try:
            with open(DESCRIPTIONS_FILE, 'w') as f:
                json.dump(descriptions, f)
            logger.info(f"Saved {len(descriptions)} descriptions to file")
            return True
        except Exception as e:
            logger.error(f"Error saving descriptions to file: {e}")
            return False
    
    def load_descriptions_from_file(self):
        """
        Load the extracted descriptions from a file.
        """
        if os.path.exists(DESCRIPTIONS_FILE):
            try:
                with open(DESCRIPTIONS_FILE, 'r') as f:
                    descriptions = json.load(f)
                logger.info(f"Loaded {len(descriptions)} descriptions from file")
                return descriptions
            except Exception as e:
                logger.error(f"Error loading descriptions from file: {e}")
        
        logger.error("Descriptions file not found")
        return {}
    
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
            
            # Save the extracted descriptions to file and DataManager
            if hasattr(data_extractor, 'example_descriptions') and data_extractor.example_descriptions:
                # Save to file for backup
                self.save_descriptions_to_file(data_extractor.example_descriptions)
                
                # Save to DataManager
                data_manager.set_target_descriptions(data_extractor.example_descriptions)
            
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
            # Make sure data is available in DataManager
            descriptions = data_manager.get_target_descriptions()
            if not descriptions:
                logger.info("No descriptions in DataManager, trying to load from file")
                descriptions = self.load_descriptions_from_file()
                if descriptions:
                    data_manager.set_target_descriptions(descriptions)
            
            if not descriptions:
                logger.error("No descriptions available for processing")
                self.anthropic_complete = True
                return
            
            logger.info("Starting AnthropicAPI processing...")
            
            # Run the AnthropicAPI
            success = AnthropicAPI.get_target_text()
            
            if success:
                # Save processed descriptions to file for backup
                self.save_descriptions_to_file(data_manager.get_target_descriptions())
                logger.info("Descriptions saved to file after processing")
            
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
            
            # Make sure data is available in DataManager
            descriptions = data_manager.get_target_descriptions()
            if not descriptions:
                logger.info("No descriptions in DataManager, trying to load from file")
                descriptions = self.load_descriptions_from_file()
                if descriptions:
                    data_manager.set_target_descriptions(descriptions)
            
            if not descriptions:
                logger.error("No descriptions available for publishing")
                return
            
            # Prepare the descriptions for publishing (clean up, validate, etc.)
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
            
            # Clean up files
            self.cleanup_files()
            
        except Exception as e:
            logger.error(f"Error in ContentPublisher: {e}")
    
    def cleanup_files(self):
        """
        Clean up the temporary files.
        """
        try:
            if os.path.exists(MODEL_DATA_FILE):
                os.remove(MODEL_DATA_FILE)
                logger.info(f"Removed file: {MODEL_DATA_FILE}")
            
            if os.path.exists(DESCRIPTIONS_FILE):
                os.remove(DESCRIPTIONS_FILE)
                logger.info(f"Removed file: {DESCRIPTIONS_FILE}")
        except Exception as e:
            logger.error(f"Error cleaning up files: {e}")
    
    def run(self):
        """
        Main execution method that orchestrates the entire workflow.
        """
        try:
            logger.info("Starting the automation workflow...")
            
            # Wait for Telegram inputs
            if not self.wait_for_telegram_inputs():
                logger.error("Failed to get inputs from Telegram file, aborting workflow")
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
            
            logger.info("Automation workflow completed")
            return True
            
        except Exception as e:
            logger.error(f"Error in automation workflow: {e}")
            return False

# Run the orchestrator when executed directly
if __name__ == "__main__":
    # Initialize and run the orchestrator
    orchestrator = AutomationOrchestrator()
    orchestrator.run()