import time
import logging
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait, Select
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import TimeoutException, NoSuchElementException, ElementClickInterceptedException
from selenium.webdriver.common.keys import Keys
import TelegramInteraction
from DataManager import data_manager  # Import the data manager

# Set up logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler("publisher.log"),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

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
    # Primary save button (Save and add another)
    "primary_save_button": [
        (By.XPATH, "//input[@value='Save and add another']"),
        (By.XPATH, "//input[@name='_addanother']"),
        (By.CSS_SELECTOR, ".submit-row input[value='Save and add another']")
    ],
    # Fallback save button (only used if primary fails)
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
    
    def __init__(self, username, password):
        """Set up the publisher with login credentials."""
        self.username = username
        self.password = password
        self.urls = URLS
        self.elements = ELEMENTS
        self.driver = None
        
        # Target device will be obtained from DataManager
        self.target_device = None
        
        logger.info("ContentPublisher initialized")
    
    def start_browser(self):
        """Start the Chrome browser."""
        options = Options()
        options.add_argument("--start-maximized")
        # Add these options for better stability
        options.add_argument("--disable-dev-shm-usage")
        options.add_argument("--no-sandbox")
        options.add_argument("--disable-gpu")
        options.add_argument("--disable-extensions")
        # Increase page load timeout for better stability
        options.page_load_strategy = 'eager'
        
        self.driver = webdriver.Chrome(options=options)
        # Set longer timeouts for stability
        self.driver.set_script_timeout(120)
        self.driver.set_page_load_timeout(120)
        logger.info("Browser started")
        return True
    
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
            
            # Fill in username and password
            username_field = self.wait_for_element(self.elements["username_field"])
            password_field = self.wait_for_element(self.elements["password_field"])
            login_button = self.wait_for_element(self.elements["login_button"])
            
            if not (username_field and password_field and login_button):
                logger.error("Login form elements not found")
                return False
            
            username_field.clear()
            username_field.send_keys(self.username)
            
            password_field.clear()
            password_field.send_keys(self.password)
            
            login_button.click()
            time.sleep(2)  # Wait for login to complete
            
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
    
    def select_select2_option(self, select_id, option_text):
        """
        Select an option from a Select2 dropdown ensuring exact text match.
        This will only select an option that exactly matches the provided text.
        """
        try:
            logger.info(f"Selecting '{option_text}' from Select2 dropdown: {select_id}")
            
            # First check if the dropdown is a Select2 dropdown
            try:
                select2_container = self.driver.find_element(By.CSS_SELECTOR, f".select2-selection[aria-labelledby='select2-{select_id}-container']")
                
                # Click to open the dropdown
                select2_container.click()
                time.sleep(1)  # Wait for dropdown to open
                
                # Look for search field
                try:
                    search_box = self.driver.find_element(By.CSS_SELECTOR, ".select2-search__field")
                    search_box.clear()
                    search_box.send_keys(option_text)
                    time.sleep(1)  # Wait for search results
                    logger.info(f"Searching for '{option_text}' in Select2 dropdown")
                except:
                    logger.info("No search box found in Select2 dropdown")
                
                # Find exact match option using XPath
                xpath = f"//li[contains(@class, 'select2-results__option') and text()='{option_text}']"
                try:
                    option = WebDriverWait(self.driver, 5).until(
                        EC.presence_of_element_located((By.XPATH, xpath))
                    )
                    
                    # Click the option
                    option.click()
                    logger.info(f"Selected exact match '{option_text}' from Select2 dropdown")
                    time.sleep(1)  # Wait for selection to apply
                    return True
                    
                except TimeoutException:
                    logger.error(f"No exact match for '{option_text}' found in Select2 dropdown")
                    
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
        """Enter content into the CKEditor with chunking for large content."""
        try:
            logger.info("Entering content into editor")
            
            # Click source button to access HTML mode
            source_button = self.wait_for_element(self.elements["source_button"])
            if not source_button:
                logger.error("Source button not found")
                return False
            
            source_button.click()
            time.sleep(1)  # Wait for editor mode to change
            
            # Find the textarea
            textarea = self.wait_for_element(self.elements["editor_textarea"])
            if not textarea:
                logger.error("Editor textarea not found")
                return False
            
            # Clear the textarea
            textarea.clear()
            time.sleep(1)  # Wait after clearing
            if len(content) > 5000:
                logger.info(f"Content is large ({len(content)} chars), using chunking approach")
                # Split the content into manageable chunks
                chunk_size = 1000
                chunks = [content[i:i+chunk_size] for i in range(0, len(content), chunk_size)]
                
                # Insert content chunk by chunk with small pauses
                for i, chunk in enumerate(chunks):
                    logger.info(f"Inserting chunk {i+1}/{len(chunks)} ({len(chunk)} chars)")
                    # Execute JavaScript to insert the chunk at the current position
                    js_script = f"arguments[0].value += arguments[1];"
                    self.driver.execute_script(js_script, textarea, chunk)
                    time.sleep(0.5)  # Give browser time to process
                    
                    # Every few chunks, perform a refocus to ensure browser stability
                    if (i+1) % 5 == 0:
                        logger.info("Refocusing textarea")
                        self.driver.execute_script("arguments[0].focus();", textarea)
                        time.sleep(0.5)
            else:
                # For smaller content, use direct send_keys
                textarea.send_keys(content)
                
            logger.info("Content entered successfully")
            return True
            
        except Exception as e:
            logger.error(f"Error entering editor content: {e}")
            return False
    
    def save_form(self):
        """
        Save the form prioritizing 'Save and add another' button.
        Only fall back to regular 'Save' button if primary button fails.
        """
        try:
            logger.info("Trying to save form")
            
            # Take screenshot before saving
            self.driver.save_screenshot(f"before_save_{time.strftime('%Y%m%d-%H%M%S')}.png")
            
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
            self.driver.save_screenshot(f"save_failed_{time.strftime('%Y%m%d-%H%M%S')}.png")
            return False
                
        except Exception as e:
            logger.error(f"Error in save_form method: {e}")
            self.driver.save_screenshot(f"save_error_{time.strftime('%Y%m%d-%H%M%S')}.png")
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
                self.driver.save_screenshot(f"button_found_{time.strftime('%Y%m%d-%H%M%S')}.png")
                
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
        '''"""Publish a single description without content size management."""
        try:
            logger.info(f"Publishing description: '{description_name}'")
            
            # Get the target device from DataManager if not already set
            if not self.target_device:
                self.target_device = data_manager.get_target_model()
                logger.info(f"Using target device from DataManager: {self.target_device}")
            
            if not self.target_device:
                logger.error("No target device available. Ensure target_model is set in DataManager.")
                return False
            
            # Remove code block markers if present
            if content.strip().startswith("```html"):
                logger.info(f"Removing code block markers from '{description_name}'")
                content = content.strip().replace("```html", "", 1)
                if content.endswith("```"):
                    content = content[:-3]
                content = content.strip()
            
            # Navigate to add description page
            self.driver.get(self.urls["add_description"])
            time.sleep(3)  # Wait for page load
            
            # Select the description name from dropdown
            if not self.select_select2_option("id_other_name", description_name):
                logger.error(f"Failed to select '{description_name}' from dropdown")
                return False
            
            # Select the device from dropdown
            if not self.select_select2_option("id_reset_info", self.target_device):
                logger.error(f"Failed to select '{self.target_device}' from dropdown")
                return False
            
            # Enter content
            if not self.enter_editor_content(content):
                return False
            
            # Save the form using our enhanced save method
            if not self.save_form():
                return False
            
            logger.info(f"Successfully published '{description_name}'")
            return True
            
        except Exception as e:
            logger.error(f"Error publishing description: {e}")
            self.driver.save_screenshot(f"error_{time.strftime('%Y%m%d-%H%M%S')}.png")
            return False
            """Alternative method to enter content into editor."""'''
        try:
            logger.info("Using alternative method to enter content")
            
            # Click source button to access HTML mode
            source_button = self.wait_for_element(self.elements["source_button"])
            if not source_button:
                logger.error("Source button not found")
                return False
            
            source_button.click()
            time.sleep(1)
            
            # Find the textarea
            textarea = self.wait_for_element(self.elements["editor_textarea"])
            if not textarea:
                logger.error("Editor textarea not found")
                return False
            
            # Method 1: Use clipboard
            logger.info("Trying clipboard method")
            try:
                # Copy content to clipboard using pyperclip
                import pyperclip
                pyperclip.copy(content)
                
                # Focus the textarea
                textarea.click()
                
                # Send keyboard shortcut to paste
                textarea.send_keys(Keys.CONTROL, 'v')
                time.sleep(2)
                return True
            except Exception as e:
                logger.error(f"Clipboard method failed: {e}")
            
            # Method 2: Direct JavaScript insertion
            logger.info("Trying direct JavaScript insertion")
            try:
                script = """
                arguments[0].value = arguments[1];
                arguments[0].dispatchEvent(new Event('change', { bubbles: true }));
                """
                self.driver.execute_script(script, textarea, content)
                time.sleep(2)
                return True
            except Exception as e:
                logger.error(f"Direct JavaScript insertion failed: {e}")
                
            return False
        
        except Exception as e:
            logger.error(f"All content entry methods failed: {e}")
            return False
    
    def run(self):
        """
        Run the complete publishing process using data from DataManager.
        Includes retry mechanism and better error handling.
        """
        try:
            logger.info("Starting content publisher")
            
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
            
            # Start browser
            if not self.start_browser():
                return False
            
            # Login
            if not self.login():
                return False
            
            # Create a list of descriptions for processing
            description_items = list(descriptions.items())
            success_count = 0
            
            # Track retry counts for each description
            retry_counts = {}
            max_retries = 2
            
            # Process descriptions until all are done or failed
            while description_items:
                name, content = description_items.pop(0)
                logger.info(f"Publishing description ({len(description_items)+1} remaining): '{name}'")
                
                retry_count = retry_counts.get(name, 0)
                success = self.publish_description(name, content)
                
                if success:
                    success_count += 1
                    logger.info(f"Successfully published '{name}'")
                else:
                    logger.error(f"Failed to publish '{name}'")
                    # Add back to the list for retry if under max retries
                    if retry_count < max_retries:
                        retry_counts[name] = retry_count + 1
                        description_items.append((name, content))
                        logger.info(f"Added '{name}' back to queue for retry ({retry_count+1}/{max_retries})")
                        
                        # Restart the browser session if we've seen multiple failures
                        if retry_count >= 1:
                            logger.info("Restarting browser session due to multiple failures")
                            if self.driver:
                                self.driver.quit()
                            time.sleep(2)
                            if not self.start_browser() or not self.login():
                                logger.error("Failed to restart browser session, aborting")
                                break
                
                # Add a short delay between publishing attempts
                time.sleep(1)
            
            logger.info(f"Content publishing completed. Published {success_count} of {len(descriptions)} descriptions")
            
            # Clear data when done
            data_manager.clear_data()
            logger.info("Cleared data from DataManager")
            
            return success_count > 0
            
        except Exception as e:
            logger.error(f"Error running publisher: {e}")
            return False
        finally:
            # Always close the browser
            if self.driver:
                logger.info("Closing browser")
                self.driver.quit()


# For standalone testing
if __name__ == "__main__":
    # Set up test data if running independently
    if not data_manager.get_target_model():
        data_manager.set_models("AGM G1 Pro", "AGM G2 Pro")
        print(f"Set default target_model for testing: {data_manager.get_target_model()}")
        
    if not data_manager.get_target_descriptions():
        test_data = {
            "Hard Reset": "This is a sample reset description for testing.",
            "Developer Options": "This is how to enable developer options."
        }
        data_manager.set_target_descriptions(test_data)
        print(f"Set default target_descriptions for testing with {len(test_data)} items")
    
    # Create and run the publisher
    publisher = ContentPublisher(username="Istomin", password="VnXJ7i47n4tjWj&g")
    success = publisher.run()
    
    if success:
        print("Publishing completed successfully")
    else:
        print("Publishing failed")