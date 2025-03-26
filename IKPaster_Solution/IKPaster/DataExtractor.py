from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options
from selenium.webdriver import Keys, ActionChains
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import TimeoutException, NoSuchElementException
import time
import logging
import json
import os
import TelegramInteraction
from DataManager import data_manager

# Setup logging with default values - will be overridden with instance-specific config
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler("scraper.log"),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

# Load configuration
def load_config():
    try:
        with open("config.json", "r") as f:
            config = json.load(f)
        
        # Set up instance-specific logging
        instance_id = config.get("instance_id", 0)
        log_dir = config.get("log_dir", "logs")
        os.makedirs(log_dir, exist_ok=True)
        
        log_file = os.path.join(log_dir, "scraper.log")
        
        # Update the logger to use instance-specific settings
        global logger
        logger = logging.getLogger(f"scraper_{instance_id}")
        
        for handler in logger.handlers[:]:
            logger.removeHandler(handler)
            
        file_handler = logging.FileHandler(log_file)
        file_handler.setFormatter(logging.Formatter(f'[Instance {instance_id}] %(asctime)s - %(levelname)s - %(message)s'))
        
        stream_handler = logging.StreamHandler()
        stream_handler.setFormatter(logging.Formatter(f'[Instance {instance_id}] %(asctime)s - %(levelname)s - %(message)s'))
        
        logger.addHandler(file_handler)
        logger.addHandler(stream_handler)
        
        # Get credentials from config
        credentials = config.get("admin_credentials", {})
        username = credentials.get("username", "Istomin")
        password = credentials.get("password", "VnXJ7i47n4tjWj&g")
        
        logger.info(f"DataExtractor loaded configuration for instance {instance_id}")
        return username, password
    
    except Exception as e:
        logger.error(f"Error loading config: {e}")
        return "Istomin", "VnXJ7i47n4tjWj&g"  # Default credentials

class DataExtractorClass:
    def __init__(self, username=None, password=None):
        # Load from config if not provided
        if username is None or password is None:
            config_username, config_password = load_config()
            self.username = username or config_username
            self.password = password or config_password
        else:
            self.username = username
            self.password = password
            
        self.telegram_bot = TelegramInteraction
        
        # Initialize attributes
        self.driver = None
        self.example_descriptions = {}
        
        # URLs and element locators - centralized for easy updates
        self.urls = {
            "auth": "https://www.hardreset.info/admin/",
            "reset_info": "https://www.hardreset.info/admin/reset/resetinfo/",
            "other_descriptions": "https://www.hardreset.info/admin/reset/otherdescription/"
        }
        
        self.locators = {
            "username_field": (By.ID, "id_username"),
            "password_field": (By.ID, "id_password"),
            "login_button": (By.XPATH, "//input[@value='Log in']"),
            "search_field": (By.XPATH, "/html/body/div/div[3]/div/div/div[1]/form/div/input[1]"),
            "search_button": (By.XPATH, "/html/body/div/div[3]/div/div/div[1]/form/div/input[2]"),
            "other_desc_btn": (By.XPATH, "/html/body/div/div[3]/div/ul/li[1]/a"),
            "source_button": (By.CLASS_NAME, "cke_button cke_button__source cke_button_off"),
            "table": (By.CSS_SELECTOR, "table"),
            "table_rows": (By.CSS_SELECTOR, "tbody tr"),
            "table_cells": (By.CSS_SELECTOR, "td")
        }
    
    def setup_driver(self):
        """Initialize and configure the Chrome WebDriver"""
        options = Options()
        options.add_argument("--start-maximized")
        # Uncomment for headless mode if needed
        # options.add_argument("--headless")
        
        self.driver = webdriver.Chrome(options=options)
        logger.info("WebDriver initialized")
    
    def wait_for_element(self, locator, timeout=10):
        """Wait for an element to be present and return it"""
        try:
            element = WebDriverWait(self.driver, timeout).until(
                EC.presence_of_element_located(locator)
            )
            return element
        except TimeoutException:
            logger.error(f"Element not found: {locator}")
            return None
    
    def wait_for_clickable(self, locator, timeout=10):
        """Wait for an element to be clickable and return it"""
        try:
            element = WebDriverWait(self.driver, timeout).until(
                EC.element_to_be_clickable(locator)
            )
            return element
        except TimeoutException:
            logger.error(f"Element not clickable: {locator}")
            return None
    
    def fill_text_field(self, locator, text=None, clear_first=True):
        """Fill a text field with the provided text"""
        element = self.wait_for_element(locator)
        if element and element.tag_name in ["input", "textarea"]:
            if clear_first:
                element.clear()
            if text:
                element.send_keys(text)
            return True
        else:
            logger.error(f"Cannot fill text field: {locator}")
            return False
    
    def click_element(self, locator):
        """Click on an element"""
        element = self.wait_for_clickable(locator)
        if element:
            element.click()
            return True
        return False
    
    def find_device_link(self, device_name):
        """Find and click the device link in the search results table"""
        try:
            logger.info(f"Looking for device link for: '{device_name}'")
            
            # Take a screenshot to help with debugging
            screenshot_path = f"search_results_page_{time.strftime('%Y%m%d-%H%M%S')}.png"
            try:
                # Try to get instance ID from config for screenshot path
                with open("config.json", "r") as f:
                    config = json.load(f)
                    instance_id = config.get("instance_id", 0)
                    log_dir = config.get("log_dir", "logs")
                    screenshot_path = os.path.join(log_dir, f"instance_{instance_id}_" + screenshot_path)
            except:
                pass
                
            self.driver.save_screenshot(screenshot_path)
            
            # Wait for the table to load
            table = self.wait_for_element((By.TAG_NAME, "table"), timeout=10)
            if not table:
                logger.error("Table not found on page")
                return None
                
            # First try the specific link in the first column of the table
            # This targets the "RESET INFO" column which has the blue link
            specific_xpath = "//table//tr/td[1]/a"
            try:
                links = self.driver.find_elements(By.XPATH, specific_xpath)
                logger.info(f"Found {len(links)} links in first column")
                
                for link in links:
                    link_text = link.text.strip()
                    logger.info(f"Link text: '{link_text}'")
                    
                    # Check for exact match (case insensitive)
                    if link_text.lower() == device_name.lower():
                        logger.info(f"Found exact match for '{device_name}'")
                        return link
                        
                    # Check for partial match as fallback
                    if device_name.lower() in link_text.lower():
                        logger.info(f"Found partial match: '{link_text}' for '{device_name}'")
                        return link
            except Exception as e:
                logger.info(f"Error finding first column links: {e}")
            
            # If that didn't work, try the RESET INFO column
            reset_info_xpath = "//table//tr/th[@class='field-reset_info']/a"
            try:
                reset_links = self.driver.find_elements(By.XPATH, reset_info_xpath)
                logger.info(f"Found {len(reset_links)} links in RESET INFO column")
                
                for link in reset_links:
                    link_text = link.text.strip()
                    logger.info(f"RESET INFO link text: '{link_text}'")
                    
                    if device_name.lower() in link_text.lower():
                        logger.info(f"Found match in RESET INFO column: '{link_text}'")
                        return link
            except Exception as e:
                logger.info(f"Error finding RESET INFO links: {e}")
            
            # If still not found, try more general approaches...
            # [Previous implementation continues]
            
            # If we get here, we couldn't find the link
            logger.error(f"Could not find any link containing '{device_name}'")
            self.driver.save_screenshot(screenshot_path)
            return None
            
        except Exception as e:
            logger.error(f"Error in find_device_link: {e}")
            self.driver.save_screenshot(f"find_device_link_error_{time.strftime('%Y%m%d-%H%M%S')}.png")
            return None
    
    def authenticate(self):
        """Log in to the admin panel"""
        try:
            logger.info("Authenticating...")
            self.driver.get(self.urls["auth"])
            
            self.fill_text_field(self.locators["username_field"], self.username)
            self.fill_text_field(self.locators["password_field"], self.password)
            self.click_element(self.locators["login_button"])
            
            # Check if authentication was successful
            if "site administration" in self.driver.title.lower():
                logger.info("Authentication successful")
                return True
            else:
                logger.error("Authentication failed")
                return False
        except Exception as e:
            logger.error(f"Authentication error: {e}")
            return False
    
    def extract_reset_descriptions(self):
        try:
            # Wait for the table to load
            self.wait_for_element((By.XPATH, "//table"))
            
            reset_descriptions = {}
            row_index = 1
            
            # Continue until we don't find any more rows
            while True:
                try:
                    # Use the specific XPath pattern with increasing row index
                    link_xpath = f"/html/body/div/div[3]/div/div/form/div/table/tbody/tr[{row_index}]/th/a"
                    
                    # Find the link element directly
                    link_element = self.driver.find_element(By.XPATH, link_xpath)
                    
                    # Get the text from the link (this is our "Other name")
                    other_name = link_element.text.strip()
                    
                    if other_name:
                        # Store the element with the other_name as key
                        reset_descriptions[other_name] = link_element
                        logger.info(f"Found reset description: {other_name}")
                    
                    # Increment row index for the next iteration
                    row_index += 1
                    
                except NoSuchElementException:
                    # No more rows found, break the loop
                    break
                except Exception as e:
                    # Log any other error and continue to the next row
                    logger.error(f"Error extracting row {row_index}: {e}")
                    row_index += 1
            
            logger.info(f"Extracted {len(reset_descriptions)} reset descriptions")
            return reset_descriptions
        except Exception as e:
            logger.error(f"Error extracting reset descriptions: {e}")
            return {}
    
    def wait_for_example_model(self, timeout=300, check_interval=5):
        """
        Wait until example_model is available from TelegramInteraction.
        Timeout after the specified duration (in seconds).
        """
        start_time = time.time()
        logger.info("Waiting for example_model from Telegram...")
        
        while time.time() - start_time < timeout:
            # Check if example_model is set and not empty
            if hasattr(self.telegram_bot, 'example_model') and self.telegram_bot.example_model:
                example_model = self.telegram_bot.example_model
                logger.info(f"Received example_model: {example_model}")
                return example_model
            
            # Also check DataManager
            if data_manager.example_model:
                logger.info(f"Received example_model from DataManager: {data_manager.example_model}")
                return data_manager.example_model
            
            # Log waiting status periodically
            if (time.time() - start_time) % 30 < check_interval:
                logger.info(f"Still waiting for example_model... ({int(time.time() - start_time)} seconds elapsed)")
                
            # Wait before checking again
            time.sleep(check_interval)
        
        logger.error(f"Timed out waiting for example_model after {timeout} seconds")
        return None

    # [Rest of the implementation continues as in the original file]
    # The get_example_content method and other methods remain unchanged

    def run(self):
        """Main execution method"""
        try:
            self.setup_driver()
            
            if self.authenticate():
                # Wait for example_model from TelegramInteraction or DataManager
                example_model = self.wait_for_example_model()
                
                if example_model:
                    # Process the model
                    success = self.get_example_content(example_model)
                    
                    # Store results in DataManager
                    if success and self.example_descriptions:
                        data_manager.set_target_descriptions(self.example_descriptions)
                        logger.info(f"Stored {len(self.example_descriptions)} descriptions in DataManager")
                    
                else:
                    logger.error("No example_model received")
            else:
                logger.error("Could not proceed due to authentication failure")
        except Exception as e:
            logger.error(f"Error during execution: {e}")
        finally:
            # Ensure driver is quit properly
            if self.driver:
                logger.info("Closing WebDriver")
                time.sleep(5)
                self.driver.quit()