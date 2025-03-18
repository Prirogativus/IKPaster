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

class HardResetScraper:
    def __init__(self, username, password):
        self.username = username
        self.password = password
        self.telegram_bot = TelegramInteraction
        self.ai_model = AnthropicAPI
        
        # Initialize attributes
        self.driver = None
        self.example_model = "HUAWEI Mate 60 Pro" #self.telegram_bot.example_model
        self.target_model = "HUAWEI Mate 70 Pro Premium"#self.telegram_bot.target_model
        self.example_descriptions = {}
        self.target_descriptions = {}
        
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
            "source_button": (By.XPATH, "/html/body/div[1]/div[3]/div/form/div/fieldset/div[6]/div/div[1]/div/span[1]/span[2]/span[10]/span[3]/a[1]"),
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
    
    def extract_textarea_content(self):
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
            return ""  # Return empty string instead of None to avoid type errors

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
            if device_link:
                device_link.click()
                
                # Click on the "Other Description" button
                self.click_element(self.locators["other_desc_btn"])
                
                # Extract reset descriptions
                self.example_descriptions = self.extract_reset_descriptions()
                
                # Click on "Hard Reset" if it exists
                for description in self.example_descriptions:
                    self.click_reset_description(self.example_descriptions, description)
                    self.wait_for_element((By.XPATH, self.locators["source_button"]))
                    self.click_element(self.locators["source_button"])
                    self.wait_for_element(By.XPATH, "/html/body/div[1]/div[3]/div/form/div/fieldset/div[6]/div/div[1]/div/div/textarea")
                    try:
                        self.example_descriptions[description] = self.extract_textarea_content()
                        logger.error("Text copy: Succes")
                    except:
                        logger.error("Text copy: Failure")
                    self.go_back()
            else:
                logger.error(f"Device link for '{self.example_model}' not found")
            
            return False
        except Exception as e:
            logger.error(f"Error getting example content: {e}")
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
                time.sleep(100)
                self.driver.quit()


if __name__ == "__main__":
    # Create and run the scraper
    scraper = HardResetScraper(username="Istomin", password="VnXJ7i47n4tjWj&g")
    scraper.run()
