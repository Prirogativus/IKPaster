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
import TelegramInteraction
import AnthropicAPI

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler("scraper.log"),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

class DataExtractorClass:
    def __init__(self, username, password):
        self.username = username
        self.password = password
        self.telegram_bot = TelegramInteraction
        self.ai_model = AnthropicAPI
        
        # Initialize attributes
        self.driver = None
        self.example_model = "HUAWEI Mate 60 Pro" #self.telegram_bot.example_model
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
        """Find a clickable link containing the device name"""
        try:
            xpath = f"//a[contains(text(), '{device_name}')]"
            return self.wait_for_clickable((By.XPATH, xpath))
        except Exception as e:
            logger.error(f"Error finding device link for '{device_name}': {e}")
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
    
    """def extract_textarea_content(self):
        try:
            # First find the iframe (CKEditor uses iframes for the editable area)
            iframe = self.driver.find_element(By.CSS_SELECTOR, ".cke_wysiwyg_frame")
            
            # Switch to the iframe context
            self.driver.switch_to.frame(iframe)
            
            # Now we can access the content
            content = self.driver.find_element(By.TAG_NAME, "body").get_attribute("innerHTML")
            
            # Switch back to the main document
            self.driver.switch_to.default_content()
            
            return content
        except Exception as e:
            logger.error(f"Error extracting textarea content: {e}")
            return ""  # Return empty string instead of None to avoid type errors" """

    def click_reset_description(self, descriptions_dict, name_to_click):
        """Click on a reset description by name"""
        try:
            if name_to_click in descriptions_dict and descriptions_dict[name_to_click]:
                descriptions_dict[name_to_click].click()
                logger.info(f"Clicked on '{name_to_click}'")
                return True
            else:
                logger.error(f"Reset description '{name_to_click}' not found")
                return False
        except Exception as e:
            logger.error(f"Error clicking reset description '{name_to_click}': {e}")
            return False
        
    def go_back(self):
        """
        Navigate back to the previous page in the browser history
        """
        try:
            self.driver.back()
            logger.info("Navigated back to the previous page")
            
            

            WebDriverWait(self.driver, 10).until(
                EC.presence_of_element_located((By.TAG_NAME, "body"))
            )
            
            return True
        except Exception as e:
            logger.error(f"Error navigating back: {e}")
            return False
    
    def extract_textarea_content(self):
        """
        Extract content from CKEditor in either WYSIWYG or source mode
        Returns the HTML content as a string
        """
        content = ""
        
        # Try source mode first (direct textarea)
        try:
            logger.info("Attempting to extract content from source mode textarea")
            # Check if we're in source mode
            textarea = self.wait_for_element((By.XPATH, "/html/body/div[1]/div[3]/div/form/div/fieldset/div[6]/div/div[1]/div/div/textarea"), timeout=3)
            
            if textarea:
                content = textarea.get_attribute("value")
                logger.info("Successfully extracted content from source mode textarea")
                return content
        except Exception as e:
            logger.info(f"Textarea not found in source mode: {e}")
        
        # If source mode failed, try WYSIWYG mode (iframe)
        if not content:
            try:
                logger.info("Attempting to extract content from WYSIWYG mode (iframe)")
                # Find the iframe
                iframe = self.wait_for_element((By.CSS_SELECTOR, ".cke_wysiwyg_frame"), timeout=3)
                
                if iframe:
                    # Switch to the iframe context
                    self.driver.switch_to.frame(iframe)
                    
                    # Get content from the body
                    body_element = self.wait_for_element((By.TAG_NAME, "body"), timeout=3)
                    if body_element:
                        content = body_element.get_attribute("innerHTML")
                    
                    # Switch back to the main document
                    self.driver.switch_to.default_content()
                    
                    logger.info("Successfully extracted content from WYSIWYG iframe")
            except Exception as e:
                logger.error(f"Error extracting content from WYSIWYG iframe: {e}")
                # Always make sure to switch back to default content if there was an error
                try:
                    self.driver.switch_to.default_content()
                except:
                    pass
        
        return content
    

    def click_source_button(self):
        """Click the Source button in CKEditor toolbar"""
        try:
            logger.info("Attempting to click the Source button in CKEditor")
            
            # Try multiple selector strategies for better reliability
            selectors = [
                "a.cke_button__source",                          # CSS selector (preferred)
                "#cke_52\\.cke_button\\.cke_button__source",     # ID-based selector from screenshot
                ".cke_button__source"                           # Class-based selector
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
            
            # One last attempt - try the original XPath from your locators
            try:
                original_button = self.wait_for_element(self.locators["source_button"], timeout=3)
                if original_button:
                    original_button.click()
                    logger.info("Clicked Source button using original locator")
                    time.sleep(0.5)
                    return True
            except:
                pass
                
            return False


    def get_example_content(self):
        """Search for example model and get its content"""
        try:
            logger.info(f"Getting content for example model: {self.example_model}")
            
            # Navigate to reset info page
            self.driver.get(self.urls["reset_info"])
            
            # Search for the example model
            self.fill_text_field(self.locators["search_field"], self.example_model)
            self.click_element(self.locators["search_button"])
            
            # Find and click the device link
            device_link = self.find_device_link(self.example_model)
            if not device_link:
                logger.error(f"Device link for '{self.example_model}' not found")
                return False
                
            device_link.click()
            logger.info(f"Clicked on device link for '{self.example_model}'")
            
            # Click on the "Other Description" button
            if not self.click_element(self.locators["other_desc_btn"]):
                logger.error("Failed to click 'Other Description' button")
                return False
                
            logger.info("Clicked on 'Other Description' button")
            
            # Initialize content dictionary
            content_dict = {}
            
            # Get all description names first
            description_names = []
            try:
                # Wait for the table to load
                self.wait_for_element((By.XPATH, "//table"))
                
                # Find all description links
                links = self.driver.find_elements(By.XPATH, "//th/a")
                for link in links:
                    name = link.text.strip()
                    if name:
                        description_names.append(name)
                        
                logger.info(f"Found {len(description_names)} reset descriptions: {description_names}")
            except Exception as e:
                logger.error(f"Error finding description names: {e}")
                return False
            
            # Process each description by navigating directly to it
            for description_name in description_names:
                logger.info(f"Processing reset description: '{description_name}'")
                
                # For each description, we need to:
                # 1. Find the current page's links (to avoid stale references)
                # 2. Click on the link with matching text
                # 3. Process the content
                # 4. Navigate back
                
                try:
                    # Find the link with this description name
                    link_xpath = f"//th/a[contains(text(), '{description_name}')]"
                    link = WebDriverWait(self.driver, 10).until(
                        EC.element_to_be_clickable((By.XPATH, link_xpath))
                    )
                    
                    # Click on the link
                    link.click()
                    logger.info(f"Clicked on '{description_name}' link")
                    
                    # Wait for page to load
                    time.sleep(1)
                    
                    # Click source button to switch to source mode
                    try:
                        # Try different selectors for the source button
                        selectors = [
                            "a.cke_button__source",
                            ".cke_button__source",
                            "#cke_1_toolbox .cke_button__source"
                        ]
                        
                        source_clicked = False
                        for selector in selectors:
                            try:
                                source_button = WebDriverWait(self.driver, 3).until(
                                    EC.element_to_be_clickable((By.CSS_SELECTOR, selector))
                                )
                                source_button.click()
                                logger.info(f"Clicked source button using selector: {selector}")
                                source_clicked = True
                                time.sleep(1)  # Wait for editor to switch modes
                                break
                            except Exception:
                                continue
                        
                        if not source_clicked:
                            # Try JavaScript as a fallback
                            self.driver.execute_script(
                                "document.querySelector('a.cke_button__source').click();"
                            )
                            logger.info("Used JavaScript to click source button")
                            time.sleep(1)
                    
                    except Exception as e:
                        logger.error(f"Error clicking source button: {e}")
                    
                    # Try to get content from textarea (source mode)
                    content = ""
                    try:
                        # Try multiple selectors for the textarea
                        textarea_selectors = [
                            "//textarea[contains(@class, 'cke_source')]",
                            "/html/body/div[1]/div[3]/div/form/div/fieldset/div[6]/div/div[1]/div/div/textarea",
                            "textarea.cke_source"
                        ]
                        
                        for textarea_selector in textarea_selectors:
                            try:
                                if textarea_selector.startswith("//"):
                                    textarea = WebDriverWait(self.driver, 3).until(
                                        EC.presence_of_element_located((By.XPATH, textarea_selector))
                                    )
                                else:
                                    textarea = WebDriverWait(self.driver, 3).until(
                                        EC.presence_of_element_located((By.CSS_SELECTOR, textarea_selector))
                                    )
                                
                                content = textarea.get_attribute("value")
                                if content:
                                    logger.info(f"Got content using selector: {textarea_selector}")
                                    break
                            except Exception:
                                continue
                    
                    except Exception as e:
                        logger.error(f"Error getting textarea content: {e}")
                    
                    # If no content from textarea, try iframe
                    if not content:
                        try:
                            iframe = self.driver.find_element(By.CSS_SELECTOR, ".cke_wysiwyg_frame")
                            self.driver.switch_to.frame(iframe)
                            
                            body = self.driver.find_element(By.TAG_NAME, "body")
                            content = body.get_attribute("innerHTML")
                            
                            self.driver.switch_to.default_content()
                            logger.info("Got content from iframe")
                        except Exception as e:
                            logger.error(f"Error getting iframe content: {e}")
                            # Make sure we switch back to default content
                            try:
                                self.driver.switch_to.default_content()
                            except:
                                pass
                    
                    # Store content if we got it
                    if content:
                        content_dict[description_name] = content
                        logger.info(f"Successfully extracted content for '{description_name}'")
                    else:
                        logger.warning(f"No content extracted for '{description_name}'")
                    
                    # Go back to the descriptions list
                    self.driver.back()
                    
                    # Wait for the list page to load again
                    WebDriverWait(self.driver, 10).until(
                        EC.presence_of_element_located((By.XPATH, "//table"))
                    )
                    
                except Exception as e:
                    logger.error(f"Error processing '{description_name}': {e}")
                    # Try to go back to the list page
                    try:
                        self.driver.back()
                        WebDriverWait(self.driver, 10).until(
                            EC.presence_of_element_located((By.XPATH, "//table"))
                        )
                    except:
                        # If going back fails, try to navigate directly to the other description page
                        self.driver.get(self.urls["other_descriptions"])
                        self.fill_text_field(self.locators["search_field"], self.example_model)
                        self.click_element(self.locators["search_button"])
            
            # Store the content dictionary
            self.example_descriptions = content_dict
            
            logger.info(f"Successfully extracted content for {len(content_dict)} descriptions")
            return True
            
        except Exception as e:
            logger.error(f"Error in get_example_content: {e}")
            return False
        
    
    def run(self):
        """Main execution method"""
        try:
            self.setup_driver()
            
            if self.authenticate():
                self.get_example_content()
                # Additional methods can be called here
                
            else:
                logger.error("Could not proceed due to authentication failure")
        except Exception as e:
            logger.error(f"Error during execution: {e}")
        finally:
            # Ensure driver is quit properly
            if self.driver:
                logger.info("Closing WebDriver")
                time.sleep(10)
                self.driver.quit()


if __name__ == "__main__":
    # Create and run the scraper
    scraper = DataExtractorClass(username="Istomin", password="VnXJ7i47n4tjWj&g")
    scraper.run()
