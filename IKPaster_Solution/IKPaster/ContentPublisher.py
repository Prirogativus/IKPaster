import time
import logging
import os
import json
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait, Select
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import TimeoutException, NoSuchElementException, ElementClickInterceptedException
from selenium.webdriver.common.keys import Keys
import TelegramInteraction
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
        
        log_file = os.path.join(log_dir, "publisher.log")
        
        # Set up logging
        logger = logging.getLogger("publisher")
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
                logging.FileHandler("publisher.log"),
                logging.StreamHandler()
            ]
        )
        logger = logging.getLogger("publisher")
        logger.error(f"Error setting up logger: {e}")
        return logger

# Global logger instance
logger = setup_logger()

# URLs - modify these if the admin URLs change
URLS = {
    "login": "https://www.hardreset.info/admin/",
    "add_description": "https://www.hardreset.info/admin/reset/otherdescription/add/"
}

# Element IDs and selectors - modify these if the website structure changes
ELEMENTS = {
    "username_field": (By.ID, "id_username"),
    "password_field": (By.ID, "id_password"),
    "login_button": (By.XPATH, "//input[@value='Log in']"),
    "other_name_dropdown": (By.ID, "id_other_name"),
    "reset_info_dropdown": (By.ID, "id_reset_info"),
    "source_button": (By.CSS_SELECTOR, "a.cke_button__source"),
    "editor_textarea": (By.XPATH, "//textarea[contains(@class, 'cke_source')]"),
    "popup_name_field": (By.ID, "id_name"),
    "popup_save_button": (By.XPATH, "//input[@value='Save']"),
    "primary_save_button": [
        (By.XPATH, "//input[@value='Save and add another']"),
        (By.XPATH, "//input[@name='_addanother']"),
        (By.CSS_SELECTOR, ".submit-row input[value='Save and add another']")
    ],
    "fallback_save_button": [
        (By.XPATH, "//input[@value='Save']"),
        (By.CSS_SELECTOR, ".submit-row input[value='Save']"),
        (By.XPATH, "//input[@value='SAVE']")
    ]
}

class ContentPublisher:
    """
    A tool for publishing content to a Django admin site with Select2 dropdown support.
    Uses DataManager for data exchange with other modules.
    """
    def __init__(self, username=None, password=None):
        """Set up the publisher with login credentials."""
        # Try to load from config
        try:
            with open("config.json", "r") as f:
                config = json.load(f)
            
            self.instance_id = config.get("instance_id", 0)
            
            # Get credentials from config if not provided
            if username is None or password is None:
                credentials = config.get("admin_credentials", {})
                self.username = username or credentials.get("username", "Istomin")
                self.password = password or credentials.get("password", "VnXJ7i47n4tjWj&g")
            else:
                self.username = username
                self.password = password
                
        except Exception as e:
            logger.error(f"Error loading config: {e}")
            # Default values
            self.instance_id = 0
            self.username = username or "Istomin"
            self.password = password or "VnXJ7i47n4tjWj&g"
            
        self.urls = URLS
        self.elements = ELEMENTS
        self.driver = None
        self.target_device = None
        self.skip_list = []  # Items to skip after multiple failures
        logger.info(f"ContentPublisher initialized for instance {self.instance_id}")
    
    def start_browser(self):
        """Start the Chrome browser with improved stability and session handling."""
        options = Options()
        options.add_argument("--start-maximized")
        options.add_argument("--disable-dev-shm-usage")
        options.add_argument("--no-sandbox")
        options.add_argument("--disable-gpu")
        
        # Add these options for better session stability
        options.add_argument("--disable-extensions")
        options.add_argument("--disable-browser-side-navigation")
        options.add_argument("--disable-features=IsolateOrigins,site-per-process")
        options.add_argument("--disable-popup-blocking")
        
        # Change page load strategy to normal
        options.page_load_strategy = 'normal'
        
        try:
            self.driver = webdriver.Chrome(options=options)
            self.driver.set_script_timeout(180)
            self.driver.set_page_load_timeout(180)
            
            # Set a cookie to help maintain the session
            self.driver.get(self.urls["login"])
            self.driver.add_cookie({"name": "session_stability", "value": "true"})
            
            logger.info("Browser started with improved session handling")
            return True
        except Exception as e:
            logger.error(f"Error starting browser: {e}")
            return False
    
    def wait_for_element(self, locator, timeout=15):
        """Wait for an element to appear and return it."""
        try:
            element = WebDriverWait(self.driver, timeout).until(
                EC.presence_of_element_located(locator)
            )
            return element
        except TimeoutException:
            logger.error(f"Element not found: {locator}")
            return None
    
    def login(self):
        """Log in to the admin site."""
        try:
            logger.info("Logging in...")
            self.driver.get(self.urls["login"])
            time.sleep(3)  # Wait for page to load
            
            # Fill in username and password
            username_field = self.wait_for_element(self.elements["username_field"])
            password_field = self.wait_for_element(self.elements["password_field"])
            login_button = self.wait_for_element(self.elements["login_button"])
            
            if not (username_field and password_field and login_button):
                logger.error("Login form elements not found")
                return False
            
            username_field.clear()
            username_field.send_keys(self.username)
            time.sleep(1)
            
            password_field.clear()
            password_field.send_keys(self.password)
            time.sleep(1)
            
            login_button.click()
            time.sleep(3)  # Wait for login to complete
            
            # Check if login was successful
            if "site administration" in self.driver.title.lower():
                logger.info("Login successful")
                return True
            else:
                logger.error("Login failed")
                return False
                
        except Exception as e:
            logger.error(f"Error during login: {e}")
            return False
    def save_form(self):
        """
        Save the form prioritizing 'Save and add another' button.
        Only fall back to regular 'Save' button if primary button fails.
        """
        try:
            logger.info("Trying to save form")
            time.sleep(2)  # Add delay before saving
            
            # Take instance-specific screenshot before saving
            screenshot_path = f"before_save_{time.strftime('%Y%m%d-%H%M%S')}.png"
            try:
                # Get log directory from config
                with open("config.json", "r") as f:
                    config = json.load(f)
                    log_dir = config.get("log_dir", "logs")
                    os.makedirs(log_dir, exist_ok=True)
                    screenshot_path = os.path.join(log_dir, screenshot_path)
            except:
                pass
                
            self.driver.save_screenshot(screenshot_path)
            
            # First try PRIMARY save button (Save and add another)
            primary_success = self._try_save_with_button_list(self.elements["primary_save_button"])
            
            # If primary method succeeded, return True
            if primary_success:
                return True
                
            # If primary method failed, try fallback (regular Save button)
            logger.info("Primary save button failed, trying fallback Save button")
            fallback_success = self._try_save_with_button_list(self.elements["fallback_save_button"])
            
            # If fallback succeeded, return True
            if fallback_success:
                return True
            
            # Last resort: Try tab navigation and Enter key
            logger.info("Trying keyboard navigation as last resort")
            try:
                body = self.driver.find_element(By.TAG_NAME, "body")
                body.send_keys(Keys.TAB * 10)  # Try to tab to the save button
                body.send_keys(Keys.ENTER)
                time.sleep(3)
                if "add" in self.driver.current_url or "change" in self.driver.current_url:
                    logger.info("Form saved successfully with keyboard navigation")
                    return True
            except:
                logger.info("Keyboard navigation failed")
            
            # If we're still here, try all submit buttons as last resort
            try:
                all_buttons = self.driver.find_elements(By.CSS_SELECTOR, "input[type='submit']")
                logger.info(f"Found {len(all_buttons)} submit buttons on page")
                
                for i, btn in enumerate(all_buttons):
                    value = btn.get_attribute('value')
                    # Skip buttons we've already tried
                    if value in ["Save and add another", "Save"]:
                        continue
                        
                    logger.info(f"Trying button {i+1}: value='{value}'")
                    try:
                        self.driver.execute_script("arguments[0].scrollIntoView({block: 'center'});", btn)
                        time.sleep(1)
                        self.driver.execute_script("arguments[0].click();", btn)
                        time.sleep(3)
                        if "add" in self.driver.current_url or "change" in self.driver.current_url:
                            logger.info(f"Form saved successfully with button {i+1}")
                            return True
                    except:
                        continue
            except Exception as e:
                logger.info(f"Error trying all buttons: {e}")
                
            # If we get here, all approaches failed
            logger.error("All save approaches failed")
            
            # Instance-specific screenshot path
            error_screenshot_path = f"save_failed_{time.strftime('%Y%m%d-%H%M%S')}.png"
            try:
                with open("config.json", "r") as f:
                    config = json.load(f)
                    log_dir = config.get("log_dir", "logs")
                    os.makedirs(log_dir, exist_ok=True)
                    error_screenshot_path = os.path.join(log_dir, error_screenshot_path)
            except:
                pass
                
            self.driver.save_screenshot(error_screenshot_path)
            return False
                
        except Exception as e:
            logger.error(f"Error in save_form method: {e}")
            
            # Instance-specific screenshot path
            error_screenshot_path = f"save_error_{time.strftime('%Y%m%d-%H%M%S')}.png"
            try:
                with open("config.json", "r") as f:
                    config = json.load(f)
                    log_dir = config.get("log_dir", "logs")
                    os.makedirs(log_dir, exist_ok=True)
                    error_screenshot_path = os.path.join(log_dir, error_screenshot_path)
            except:
                pass
                
            self.driver.save_screenshot(error_screenshot_path)
            return False
    
    def _try_save_with_button_list(self, button_locators):
        """Helper method to try multiple approaches with a list of button locators."""
        for button_locator in button_locators:
            try:
                logger.info(f"Trying save button: {button_locator}")
                save_button = self.wait_for_element(button_locator)
                
                if not save_button:
                    logger.info(f"Button not found: {button_locator}")
                    continue
                
                # Take screenshot of the found button
                screenshot_path = f"button_found_{time.strftime('%Y%m%d-%H%M%S')}.png"
                try:
                    # Get log directory from config
                    with open("config.json", "r") as f:
                        config = json.load(f)
                        log_dir = config.get("log_dir", "logs")
                        os.makedirs(log_dir, exist_ok=True)
                        screenshot_path = os.path.join(log_dir, screenshot_path)
                except:
                    pass
                    
                self.driver.save_screenshot(screenshot_path)
                
                # Approach 1: Direct click
                try:
                    logger.info("Trying direct click")
                    save_button.click()
                    time.sleep(3)
                    if "add" in self.driver.current_url or "change" in self.driver.current_url:
                        logger.info("Form saved successfully with direct click")
                        return True
                except ElementClickInterceptedException:
                    logger.info("Direct click intercepted, trying alternatives")
                except Exception as e:
                    logger.info(f"Direct click failed: {e}")
                
                # Approach 2: JavaScript click
                try:
                    logger.info("Trying JavaScript click")
                    self.driver.execute_script("arguments[0].click();", save_button)
                    time.sleep(3)
                    if "add" in self.driver.current_url or "change" in self.driver.current_url:
                        logger.info("Form saved successfully with JavaScript click")
                        return True
                except Exception as e:
                    logger.info(f"JavaScript click failed: {e}")
                
                # Approach 3: Scroll into view first, then JS click
                try:
                    logger.info("Trying scroll then JavaScript click")
                    self.driver.execute_script("arguments[0].scrollIntoView({block: 'center'});", save_button)
                    time.sleep(1)
                    self.driver.execute_script("arguments[0].click();", save_button)
                    time.sleep(3)
                    if "add" in self.driver.current_url or "change" in self.driver.current_url:
                        logger.info("Form saved successfully with scroll+JS click")
                        return True
                except Exception as e:
                    logger.info(f"Scroll+JS click failed: {e}")
                    
            except Exception as e:
                logger.info(f"Error with button {button_locator}: {e}")
                continue
                
        # If we reach here, all approaches with this list of buttons failed
        return False
    
    def publish_description(self, description_name, content):
        """Publish a single description without content size management."""
        try:
            # Skip certain items if needed
            if description_name in self.skip_list:
                logger.info(f"Skipping '{description_name}' as it's in the skip list")
                return False

            logger.info(f"Publishing description: '{description_name}'")
            
            # Get the target device from DataManager if not already set
            if not self.target_device:
                self.target_device = data_manager.get_target_model()
                # Normalize the case for "PRO" to "Pro"
                if "PRO" in self.target_device:
                    self.target_device = self.target_device.replace("PRO", "Pro")
                logger.info(f"Using target device from DataManager: {self.target_device}")
            
            if not self.target_device:
                logger.error("No target device available. Ensure target_model is set in DataManager.")
                return False
            
            # Add an initial delay to pace requests
            time.sleep(2)

            # Navigate to add description page
            self.driver.get(self.urls["add_description"])
            time.sleep(5)  # Increased wait time for page load
            
            # Select the description name from dropdown
            if not self.select_select2_option("id_other_name", description_name):
                logger.error(f"Failed to select '{description_name}' from dropdown")
                return False
            
            # Add a delay between dropdown selections
            time.sleep(3)
            
            # Select the device from dropdown
            if not self.select_select2_option("id_reset_info", self.target_device):
                logger.error(f"Failed to select '{self.target_device}' from dropdown")
                return False
            
            # Add another delay before content entry
            time.sleep(3)
            
            # Enter content
            if not self.enter_editor_content(content):
                return False
            
            # Add delay before saving
            time.sleep(3)
            
            # Save the form using our enhanced save method
            if not self.save_form():
                return False
            
            logger.info(f"Successfully published '{description_name}'")
            return True
            
        except Exception as e:
            logger.error(f"Error publishing description: {e}")
            
            # Instance-specific screenshot path
            error_screenshot_path = f"error_{time.strftime('%Y%m%d-%H%M%S')}.png"
            try:
                with open("config.json", "r") as f:
                    config = json.load(f)
                    log_dir = config.get("log_dir", "logs")
                    os.makedirs(log_dir, exist_ok=True)
                    error_screenshot_path = os.path.join(log_dir, error_screenshot_path)
            except:
                pass
                
            self.driver.save_screenshot(error_screenshot_path)
            return False
    def select_select2_option(self, select_id, option_text):
        """
        Select an option from a Select2 dropdown with case-insensitive matching.
        """
        try:
            logger.info(f"Selecting '{option_text}' from Select2 dropdown: {select_id}")
            
            # First check if the dropdown is a Select2 dropdown
            try:
                select2_container = self.driver.find_element(By.CSS_SELECTOR, f".select2-selection[aria-labelledby='select2-{select_id}-container']")
                
                # Click to open the dropdown
                select2_container.click()
                time.sleep(2)  # Wait for dropdown to open
                
                # Look for search field
                try:
                    search_box = self.driver.find_element(By.CSS_SELECTOR, ".select2-search__field")
                    search_box.clear()
                    search_box.send_keys(option_text)
                    time.sleep(2)  # Wait for search results
                    logger.info(f"Searching for '{option_text}' in Select2 dropdown")
                except:
                    logger.info("No search box found in Select2 dropdown")
                
                # Find option using XPath with case-insensitive contains instead of exact match
                xpath = f"//li[contains(@class, 'select2-results__option') and translate(text(), 'ABCDEFGHIJKLMNOPQRSTUVWXYZ', 'abcdefghijklmnopqrstuvwxyz')=translate('{option_text}', 'ABCDEFGHIJKLMNOPQRSTUVWXYZ', 'abcdefghijklmnopqrstuvwxyz')]"
                try:
                    option = WebDriverWait(self.driver, 5).until(
                        EC.presence_of_element_located((By.XPATH, xpath))
                    )
                    
                    # Click the option
                    option.click()
                    logger.info(f"Selected match '{option_text}' from Select2 dropdown (case-insensitive)")
                    time.sleep(2)  # Wait for selection to apply
                    return True
                    
                except TimeoutException:
                    # Try partial match as fallback
                    logger.info(f"No exact case-insensitive match found, trying partial match")
                    xpath_partial = f"//li[contains(@class, 'select2-results__option') and contains(translate(text(), 'ABCDEFGHIJKLMNOPQRSTUVWXYZ', 'abcdefghijklmnopqrstuvwxyz'), translate('{option_text}', 'ABCDEFGHIJKLMNOPQRSTUVWXYZ', 'abcdefghijklmnopqrstuvwxyz'))]"
                    try:
                        option = WebDriverWait(self.driver, 5).until(
                            EC.presence_of_element_located((By.XPATH, xpath_partial))
                        )
                        option_text_actual = option.text
                        option.click()
                        logger.info(f"Selected partial match '{option_text_actual}' for '{option_text}' from Select2 dropdown")
                        time.sleep(2)
                        return True
                    except TimeoutException:
                        logger.error(f"No match for '{option_text}' found in Select2 dropdown")
                        
                        # Close the dropdown by clicking elsewhere
                        try:
                            self.driver.find_element(By.TAG_NAME, "body").click()
                        except:
                            pass
                        
                        return False
            
            except NoSuchElementException:
                # Not a Select2 dropdown, try standard dropdown
                logger.info(f"{select_id} is not a Select2 dropdown, trying standard dropdown")
                return self.select_standard_dropdown(select_id, option_text)
                
        except Exception as e:
            logger.error(f"Error selecting from Select2 dropdown: {e}")
            
            # Close the dropdown if it's open
            try:
                self.driver.find_element(By.TAG_NAME, "body").click()
            except:
                pass
                
            return False
    
    def select_standard_dropdown(self, select_id, option_text):
        """Select an option from a standard HTML select dropdown."""
        try:
            logger.info(f"Selecting '{option_text}' from standard dropdown: {select_id}")
            
            # Find the dropdown
            dropdown = self.driver.find_element(By.ID, select_id)
            select = Select(dropdown)
            
            # Try to select by exact text
            try:
                select.select_by_visible_text(option_text)
                logger.info(f"Selected exact match '{option_text}' from standard dropdown")
                return True
            except:
                logger.error(f"No exact match for '{option_text}' in standard dropdown")
                return False
                
        except Exception as e:
            logger.error(f"Error selecting from standard dropdown: {e}")
            return False
    
    def enter_editor_content(self, content):
        """Enter content into the CKEditor using JavaScript for reliability."""
        try:
            logger.info("Entering content into editor")
            logger.info(f"Content length: {len(content)}")
            
            # Click source button to access HTML mode
            source_button = self.wait_for_element(self.elements["source_button"])
            if not source_button:
                logger.error("Source button not found")
                return False
            
            source_button.click()
            time.sleep(2)  # Wait for editor mode to change
            
            # Find the textarea
            textarea = self.wait_for_element(self.elements["editor_textarea"])
            if not textarea:
                logger.error("Editor textarea not found")
                return False
            
            # Clear the textarea
            textarea.clear()
            time.sleep(2)  # Wait after clearing
            
            # Try multiple methods to enter content
            content_entered = False
            
            # Method 1: Try direct JavaScript insertion (most reliable)
            try:
                logger.info("Trying direct JavaScript insertion")
                script = """
                arguments[0].value = arguments[1];
                arguments[0].dispatchEvent(new Event('change', { bubbles: true }));
                """
                self.driver.execute_script(script, textarea, content)
                time.sleep(3)
                
                # Verify content length
                actual_content = self.driver.execute_script("return arguments[0].value;", textarea)
                if len(actual_content) >= len(content) * 0.9:  # At least 90% entered
                    logger.info("Content entered successfully via JavaScript")
                    content_entered = True
                else:
                    logger.warning(f"JavaScript method did not enter all content: {len(actual_content)}/{len(content)} chars")
            except Exception as e:
                logger.error(f"Direct JavaScript insertion failed: {e}")
            
            # Method 2: If JavaScript failed, try clipboard
            if not content_entered:
                try:
                    logger.info("Trying clipboard method")
                    import pyperclip
                    pyperclip.copy(content)
                    
                    # Focus the textarea
                    textarea.click()
                    time.sleep(1)
                    
                    # Send keyboard shortcut to paste
                    textarea.send_keys(Keys.CONTROL, 'v')
                    time.sleep(3)
                    
                    # Verify content length
                    actual_content = self.driver.execute_script("return arguments[0].value;", textarea)
                    if len(actual_content) >= len(content) * 0.9:  # At least 90% entered
                        logger.info("Content entered successfully via clipboard")
                        content_entered = True
                    else:
                        logger.warning(f"Clipboard method did not enter all content: {len(actual_content)}/{len(content)} chars")
                except Exception as e:
                    logger.error(f"Clipboard method failed: {e}")
            
            # Method 3: If both methods failed, try chunking as a last resort
            if not content_entered:
                try:
                    logger.info("Trying chunking method")
                    chunk_size = 500
                    chunks = [content[i:i+chunk_size] for i in range(0, len(content), chunk_size)]
                    
                    for i, chunk in enumerate(chunks):
                        logger.info(f"Inserting chunk {i+1}/{len(chunks)}")
                        js_script = "arguments[0].value += arguments[1];"
                        self.driver.execute_script(js_script, textarea, chunk)
                        time.sleep(1)
                        
                        # Refocus every few chunks
                        if (i+1) % 2 == 0:
                            self.driver.execute_script("arguments[0].focus();", textarea)
                            time.sleep(0.5)
                    
                    # Verify content length
                    actual_content = self.driver.execute_script("return arguments[0].value;", textarea)
                    logger.info(f"Content entered using chunking method: {len(actual_content)}/{len(content)} chars")
                    content_entered = True
                except Exception as e:
                    logger.error(f"Chunking method failed: {e}")
            
            if not content_entered:
                logger.error("All content entry methods failed")
                return False
                
            logger.info("Content entry completed")
            return True
            
        except Exception as e:
            logger.error(f"Error entering editor content: {e}")
            return False
    def run(self):
        """
        Run the complete publishing process using data from DataManager.
        Implements batch processing to reduce server load.
        """
        try:
            logger.info(f"Starting content publisher for instance {self.instance_id}")
            
            # Get data from DataManager
            self.target_device = data_manager.get_target_model()
            descriptions = data_manager.get_target_descriptions()
            
            # Check if we have the necessary data
            if not self.target_device:
                logger.error("No target_model found in DataManager")
                return False
                
            if not descriptions:
                logger.error("No target_descriptions found in DataManager")
                return False
            
            logger.info(f"Running with target device: {self.target_device}")
            logger.info(f"Found {len(descriptions)} descriptions to publish")
            
            # Process in smaller batches to reduce server load
            max_items_per_batch = 5  # Adjust as needed
            description_items = list(descriptions.items())
            total_success = 0
            
            # Process in batches
            for batch_start in range(0, len(description_items), max_items_per_batch):
                batch = description_items[batch_start:batch_start + max_items_per_batch]
                logger.info(f"Processing batch {batch_start//max_items_per_batch + 1} with {len(batch)} items")
                
                # Start browser for this batch
                if not self.start_browser():
                    logger.error("Failed to start browser for this batch, skipping")
                    continue
                    
                if not self.login():
                    logger.error("Failed to login for this batch, skipping")
                    if self.driver:
                        self.driver.quit()
                        self.driver = None
                    continue
                
                # Process items in this batch
                batch_success = 0
                retry_counts = {}
                retry_delays = {}
                max_retries = 3
                
                # Create a copy of the batch to allow for retries
                batch_items = batch.copy()
                
                while batch_items:
                    name, content = batch_items.pop(0)
                    
                    # Skip if in skip list
                    if name in self.skip_list:
                        logger.info(f"Skipping '{name}' as it's in the skip list")
                        continue
                    
                    # Get current retry info
                    retry_count = retry_counts.get(name, 0)
                    delay = retry_delays.get(name, 1)  # Start with 1 second
                    
                    logger.info(f"Publishing description (Batch {batch_start//max_items_per_batch + 1}, {len(batch_items)} remaining): '{name}'")
                    
                    # Add delay if this is a retry
                    if retry_count > 0:
                        logger.info(f"Waiting {delay} seconds before retry {retry_count}/{max_retries}")
                        time.sleep(delay)
                    
                    # Try to publish the description
                    success = self.publish_description(name, content)
                    
                    if success:
                        batch_success += 1
                        total_success += 1
                        logger.info(f"Successfully published '{name}'")
                    else:
                        logger.error(f"Failed to publish '{name}'")
                        
                        # Add back for retry if under max attempts
                        if retry_count < max_retries:
                            retry_counts[name] = retry_count + 1
                            # Exponential backoff - double the delay
                            retry_delays[name] = min(delay * 2, 30)
                            batch_items.append((name, content))
                            logger.info(f"Added '{name}' back to queue for retry ({retry_count+1}/{max_retries})")
                            
                            # Restart browser on multiple failures
                            if retry_count >= 1:
                                logger.info("Restarting browser due to multiple failures")
                                if self.driver:
                                    self.driver.quit()
                                    self.driver = None
                                time.sleep(5)
                                if not self.start_browser() or not self.login():
                                    logger.error("Failed to restart browser, skipping remaining items in batch")
                                    # Add remaining items to skip list
                                    for remaining_name, _ in batch_items:
                                        if remaining_name not in self.skip_list:
                                            self.skip_list.append(remaining_name)
                                    batch_items.clear()
                                    break
                        else:
                            # Add to skip list after too many retries
                            logger.warning(f"Adding '{name}' to skip list after {retry_count + 1} failed attempts")
                            self.skip_list.append(name)
                    
                    # Add delay between items
                    time.sleep(3)
                
                # Close browser between batches
                if self.driver:
                    self.driver.quit()
                    self.driver = None
                
                logger.info(f"Batch {batch_start//max_items_per_batch + 1} complete. Published {batch_success} of {len(batch)} items")
                
                # Add substantial delay between batches
                if batch_start + max_items_per_batch < len(description_items):
                    logger.info("Waiting 15 seconds before starting next batch")
                    time.sleep(15)
            
            logger.info(f"Content publishing completed. Published {total_success} of {len(descriptions)} descriptions")
            
            # Clear data when done
            data_manager.clear_data()
            logger.info("Cleared data from DataManager")
            
            return total_success > 0
            
        except Exception as e:
            logger.error(f"Error running publisher: {e}")
            return False
        finally:
            # Always close the browser
            if self.driver:
                logger.info("Closing browser")
                self.driver.quit()