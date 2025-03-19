import time
import logging
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import TimeoutException, NoSuchElementException

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler("publisher.log"),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

class ContentPublisher:
    def __init__(self, username, password, target_device):
        self.username = username
        self.password = password
        self.target_device = target_device
        self.driver = None
        
        # URLs and element locators
        self.urls = {
            "auth": "https://www.hardreset.info/admin/",
            "add_description": "https://www.hardreset.info/admin/reset/otherdescription/add/"
        }
        
        self.locators = {
            # Login page
            "username_field": (By.ID, "id_username"),
            "password_field": (By.ID, "id_password"),
            "login_button": (By.XPATH, "//input[@value='Log in']"),
            
            # Add description page
            "other_name_field": (By.ID, "id_other_name"),
            "other_name_textarea": (By.XPATH, "/html/body/div[1]/div[3]/div/form/div/fieldset/div[1]/div/div/span/span[1]/span"),
            "other_name_options": (By.XPATH, "/html/body/div[1]/div[3]/div/form/div/fieldset/div[2]/div/div/span/span[1]/span"),
            "reset_info_field": (By.ID, "id_reset_info"),
            "reset_info_textarea": (By.XPATH, "//span[@aria-labelledby='select2-id_reset_info-container']"),
            "reset_info_search": (By.XPATH, "//input[@class='select2-search__field']"),
            "reset_info_options": (By.XPATH, "//ul[@id='select2-id_reset_info-results']/li"),
            "source_button": (By.CSS_SELECTOR, "a.cke_button__source"),
            "editor_textarea": (By.XPATH, "//textarea[contains(@class, 'cke_source')]"),
            "save_button": (By.XPATH, "//input[@value='Save and add another']")
        }
    
    def setup_driver(self):
        """Initialize and configure Chrome WebDriver"""
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
    
    def capture_screenshot(self, name="screenshot"):
        """Capture a screenshot for debugging purposes"""
        try:
            timestamp = time.strftime("%Y%m%d-%H%M%S")
            filename = f"{name}_{timestamp}.png"
            self.driver.save_screenshot(filename)
            logger.info(f"Screenshot saved as {filename}")
            return filename
        except Exception as e:
            logger.error(f"Failed to capture screenshot: {e}")
            return None
    
    def wait_for_data_extraction(self, data_source, timeout=600, check_interval=10):
        """Wait until data extraction is finished"""
        logger.info("Waiting for data extraction to complete...")
        start_time = time.time()
        
        while time.time() - start_time < timeout:
            if hasattr(data_source, 'target_descriptions') and data_source.target_descriptions:
                logger.info(f"Data extraction completed with {len(data_source.target_descriptions)} descriptions")
                return True
            
            logger.info("Data not ready yet, waiting...")
            time.sleep(check_interval)
        
        logger.error(f"Timeout waiting for data extraction after {timeout} seconds")
        return False
    
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
    
    def click_source_button(self):
        """Click the Source button in CKEditor toolbar"""
        try:
            logger.info("Attempting to click the Source button in CKEditor")
            
            # Try multiple selector strategies for better reliability
            selectors = [
                "a.cke_button__source",                
                ".cke_button__source",
                "#cke_1_toolbox .cke_button__source"
            ]
            
            for selector in selectors:
                try:
                    # Try to find the element with a short timeout
                    source_button = WebDriverWait(self.driver, 2).until(
                        EC.element_to_be_clickable((By.CSS_SELECTOR, selector))
                    )
                    
                    if source_button:
                        # Try a normal click first
                        source_button.click()
                        logger.info(f"Successfully clicked Source button using selector: {selector}")
                        time.sleep(0.5)  # Brief pause to let the editor switch modes
                        return True
                except Exception:
                    continue  # Try next selector
            
            # If regular clicks failed, try JavaScript click as fallback
            logger.info("Regular click methods failed, trying JavaScript click")
            script = "document.querySelector('a.cke_button__source').click();"
            self.driver.execute_script(script)
            logger.info("Clicked Source button via JavaScript")
            time.sleep(0.5)
            return True
                
        except Exception as e:
            logger.error(f"Error clicking Source button after all attempts: {e}")
            return False
    
    def select_other_name(self, other_name):
        """Select the 'Other name' option using autocomplete"""
        try:
            logger.info(f"Attempting to select Other name: '{other_name}'")
            
            # Capture initial state
            self.capture_screenshot("before_other_name_selection")
            
            # First try to find the select element itself
            select_element = self.wait_for_element((By.ID, "id_other_name"))
            if not select_element:
                self.capture_screenshot("other_name_element_not_found")
                logger.error("Could not find the id_other_name element")
                return False
                
            # Wait a moment for the page to stabilize
            time.sleep(2)
            
            # Try different approaches to interact with the dropdown
            
            # Approach 1: Try using Select class if it's a regular dropdown
            try:
                from selenium.webdriver.support.ui import Select
                dropdown = Select(select_element)
                dropdown.select_by_visible_text(other_name)
                logger.info(f"Selected Other name '{other_name}' using Select class")
                return True
            except Exception as e:
                logger.info(f"Select class approach failed: {e}")
                self.   ("select_class_failed")
            
            # Approach 2: Try clicking the dropdown using JavaScript
            try:
                logger.info("Trying JavaScript click on the dropdown")
                self.driver.execute_script("document.getElementById('id_other_name').click();")
                time.sleep(1)
                self.capture_screenshot("after_js_click")
                
                # Now try to find the search field
                search_field = self.driver.find_element(By.XPATH, "//input[contains(@class, 'select2-search__field')]")
                search_field.send_keys(other_name)
                time.sleep(1)
                self.capture_screenshot("after_search_text")
                
                # Try to find and click an option containing our text
                option = self.driver.find_element(By.XPATH, f"//li[contains(text(), '{other_name}')]")
                option.click()
                logger.info(f"Selected Other name '{other_name}' using JavaScript and XPath")
                return True
            except Exception as e:
                logger.info(f"JavaScript approach failed: {e}")
                self.capture_screenshot("js_approach_failed")
            
            # Approach 3: Direct option selection by JavaScript
            try:
                logger.info("Trying direct option selection by JavaScript")
                script = f"""
                var select = document.getElementById('id_other_name');
                for (var i = 0; i < select.options.length; i++) {{
                    if (select.options[i].text.includes('{other_name}')) {{
                        select.selectedIndex = i;
                        var event = new Event('change');
                        select.dispatchEvent(event);
                        return true;
                    }}
                }}
                return false;
                """
                result = self.driver.execute_script(script)
                if result:
                    logger.info(f"Selected Other name '{other_name}' using direct JavaScript option selection")
                    return True
                else:
                    logger.warning(f"No option found for '{other_name}' using JavaScript")
                    self.capture_screenshot("no_option_found")
            except Exception as e:
                logger.info(f"Direct JavaScript selection failed: {e}")
                self.capture_screenshot("direct_js_failed")
            
            # Approach 4: Try finding the element by alternative means
            try:
                logger.info("Trying alternative element finding approach")
                
                # Try direct XPath to the Select2 container
                dropdown_container = self.driver.find_element(By.CSS_SELECTOR, ".select2-container")
                dropdown_container.click()
                time.sleep(1)
                self.capture_screenshot("after_container_click")
                
                # Try to find search input
                search_input = self.driver.find_element(By.CSS_SELECTOR, ".select2-search__field")
                search_input.send_keys(other_name)
                time.sleep(1)
                
                # Try to select first option
                first_option = self.driver.find_element(By.CSS_SELECTOR, ".select2-results__option")
                first_option.click()
                logger.info("Selected option using alternative approach")
                return True
            except Exception as e:
                logger.info(f"Alternative approach failed: {e}")
                self.capture_screenshot("alternative_approach_failed")
            
            # Final fallback: Print the page source for debugging
            try:
                with open("page_source.html", "w", encoding="utf-8") as f:
                    f.write(self.driver.page_source)
                logger.info("Saved page source to page_source.html")
            except Exception as e:
                logger.error(f"Failed to save page source: {e}")
            
            logger.error(f"All approaches failed to select Other name: '{other_name}'")
            return False
            
        except Exception as e:
            self.capture_screenshot("error_in_select_other_name")
            logger.error(f"Error in select_other_name: {e}")
            return False
    
    def select_reset_info(self, device_name):
        """Select the 'Reset info' option using autocomplete"""
        try:
            logger.info(f"Attempting to select Reset info: '{device_name}'")
            
            # Capture initial state
            self.capture_screenshot("before_reset_info_selection")
            
            # First try to find the select element itself
            select_element = self.wait_for_element((By.ID, "id_reset_info"))
            if not select_element:
                self.capture_screenshot("reset_info_element_not_found")
                logger.error("Could not find the id_reset_info element")
                return False
                
            # Wait a moment for the page to stabilize
            time.sleep(2)
            
            # Try different approaches to interact with the dropdown
            
            # Approach 1: Try using Select class if it's a regular dropdown
            try:
                from selenium.webdriver.support.ui import Select
                dropdown = Select(select_element)
                dropdown.select_by_visible_text(device_name)
                logger.info(f"Selected Reset info '{device_name}' using Select class")
                return True
            except Exception as e:
                logger.info(f"Select class approach failed: {e}")
                self.capture_screenshot("select_class_failed_reset_info")
            
            # Approach 2: Try clicking the dropdown using JavaScript
            try:
                logger.info("Trying JavaScript click on the dropdown")
                self.driver.execute_script("document.getElementById('id_reset_info').click();")
                time.sleep(1)
                self.capture_screenshot("after_js_click_reset_info")
                
                # Now try to find the search field
                search_field = self.driver.find_element(By.XPATH, "//input[contains(@class, 'select2-search__field')]")
                search_field.send_keys(device_name)
                time.sleep(1)
                self.capture_screenshot("after_search_text_reset_info")
                
                # Try to find and click an option containing our text
                option = self.driver.find_element(By.XPATH, f"//li[contains(text(), '{device_name}')]")
                option.click()
                logger.info(f"Selected Reset info '{device_name}' using JavaScript and XPath")
                return True
            except Exception as e:
                logger.info(f"JavaScript approach failed: {e}")
                self.capture_screenshot("js_approach_failed_reset_info")
            
            # Approach 3: Direct option selection by JavaScript
            try:
                logger.info("Trying direct option selection by JavaScript")
                script = f"""
                var select = document.getElementById('id_reset_info');
                for (var i = 0; i < select.options.length; i++) {{
                    if (select.options[i].text.includes('{device_name}')) {{
                        select.selectedIndex = i;
                        var event = new Event('change');
                        select.dispatchEvent(event);
                        return true;
                    }}
                }}
                return false;
                """
                result = self.driver.execute_script(script)
                if result:
                    logger.info(f"Selected Reset info '{device_name}' using direct JavaScript option selection")
                    return True
                else:
                    logger.warning(f"No option found for '{device_name}' using JavaScript")
                    self.capture_screenshot("no_option_found_reset_info")
            except Exception as e:
                logger.info(f"Direct JavaScript selection failed: {e}")
                self.capture_screenshot("direct_js_failed_reset_info")
            
            # Approach 4: Try finding the element by alternative means
            try:
                logger.info("Trying alternative element finding approach")
                
                # Try direct XPath to the Select2 container
                dropdown_containers = self.driver.find_elements(By.CSS_SELECTOR, ".select2-container")
                if len(dropdown_containers) > 1:
                    dropdown_containers[1].click()  # Second container should be the reset_info dropdown
                time.sleep(1)
                self.capture_screenshot("after_container_click_reset_info")
                
                # Try to find search input
                search_input = self.driver.find_element(By.CSS_SELECTOR, ".select2-search__field")
                search_input.send_keys(device_name)
                time.sleep(1)
                
                # Try to select first option
                first_option = self.driver.find_element(By.CSS_SELECTOR, ".select2-results__option")
                first_option.click()
                logger.info("Selected option using alternative approach")
                return True
            except Exception as e:
                logger.info(f"Alternative approach failed: {e}")
                self.capture_screenshot("alternative_approach_failed_reset_info")
            
            logger.error(f"All approaches failed to select Reset info: '{device_name}'")
            return False
            
        except Exception as e:
            self.capture_screenshot("error_in_select_reset_info")
            logger.error(f"Error in select_reset_info: {e}")
            return False
    
    def publish_description(self, description_name, content):
        """Publish a single description"""
        try:
            logger.info(f"Publishing description: '{description_name}'")
            
            # Navigate to add description page
            self.driver.get(self.urls["add_description"])
            
            # 1. Select description type using autocomplete
            if not self.select_other_name(description_name):
                logger.error(f"Failed to select Other name: '{description_name}'")
                return False
            
            # 2. Select target device using autocomplete
            if not self.select_reset_info(self.target_device):
                logger.error(f"Failed to select Reset info: '{self.target_device}'")
                return False
            
            # 3. Click source button
            if not self.click_source_button():
                logger.error(f"Failed to click source button for '{description_name}'")
                return False
            
            # 4. Paste the content
            # Wait for textarea to appear after switching to source mode
            textarea = self.wait_for_element((By.XPATH, "//textarea[contains(@class, 'cke_source')]"))
            if textarea:
                textarea.clear()
                textarea.send_keys(content)
                logger.info(f"Content pasted for '{description_name}'")
            else:
                logger.error(f"Textarea not found for '{description_name}'")
                return False
            
            # 5. Click Save and add another
            save_button = self.wait_for_clickable((By.XPATH, "//input[@value='Save and add another']"))
            if save_button:
                save_button.click()
                logger.info(f"Saved description: '{description_name}'")
                
                # Wait for the page to reload
                time.sleep(2)
                return True
            else:
                logger.error(f"Save button not found for '{description_name}'")
                return False
                
        except Exception as e:
            logger.error(f"Error publishing description '{description_name}': {e}")
            return False
    
    def publish_all_descriptions(self, descriptions_dict):
        """Publish all descriptions in the dictionary"""
        logger.info(f"Publishing {len(descriptions_dict)} descriptions")
        success_count = 0
        
        try:
            for description_name, message in descriptions_dict.items():
                # Extract content from message object (adjust based on your actual structure)
                if hasattr(message, 'content'):
                    content = message.content[0].text
                else:
                    # If message is already a string
                    content = message
                
                success = self.publish_description(description_name, content)
                if success:
                    success_count += 1
            
            logger.info(f"Published {success_count} of {len(descriptions_dict)} descriptions")
            return success_count
        except Exception as e:
            logger.error(f"Error in publish_all_descriptions: {e}")
            return success_count
    
    def run(self, data_source):
        """Main execution method"""
        try:
            logger.info("Starting content publisher")
            self.setup_driver()
            
            # 1. Wait for data extraction to complete
            if not self.wait_for_data_extraction(data_source):
                logger.error("Data extraction did not complete in time")
                return False
            
            # 2. Authenticate
            if not self.authenticate():
                logger.error("Authentication failed")
                return False
            
            # 3-8. Publish all descriptions
            publish_count = self.publish_all_descriptions(data_source.target_descriptions)
            
            logger.info(f"Content publishing completed. Published {publish_count} descriptions")
            return True
            
        except Exception as e:
            logger.error(f"Error during execution: {e}")
            return False
        finally:
            # Ensure driver is quit properly
            if self.driver:
                logger.info("Closing WebDriver")
                self.driver.quit()


# Add this part to test the script when run directly
if __name__ == "__main__":
    print("Starting ContentPublisher test")
    
    # Create a test instance with your credentials
    publisher = ContentPublisher(
        username="Istomin", 
        password="VnXJ7i47n4tjWj&g",
        target_device="HUAWEI Mate 70 Pro Premium"
    )
    
    # Create test data
    class MockDataSource:
        def __init__(self):
            self.target_descriptions = {
                "Hard Reset": "This is a sample reset description for testing.",
                "Developer Options": "This is how to enable developer options."
            }
    
    # Run with the test data
    test_data = MockDataSource()
    print("Running publisher with test data...")
    publisher.run(test_data)
    print("Publisher test complete")