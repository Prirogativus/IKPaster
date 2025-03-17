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
        self.example_model = self.telegram_bot.example_model
        self.target_model = self.telegram_bot.target_model
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
        """
        Extract 'Other name' column values into a dictionary as keys and store the clickable elements.
        Returns: Dictionary with 'Other name' as keys and corresponding clickable elements as values
        """
        try:
            # Wait for the table to load
            self.wait_for_element(self.locators["table"])
            
            # Extract all rows from the table (excluding header row)
            rows = self.driver.find_elements(*self.locators["table_rows"])
            
            reset_descriptions = {}
            
            # Loop through each row to extract data
            for row in rows:
                # Get all columns in the row
                columns = row.find_elements(*self.locators["table_cells"])
                
                # Check for the "Other name" column (adjust index if needed)
                if len(columns) > 3:
                    other_name = columns[2].text.strip()
                    
                    if other_name:
                        # Find the link element within the "Other name" column
                        link_elements = columns[2].find_elements(By.TAG_NAME, "a")
                        link_element = link_elements[0] if link_elements else None
                        
                        # Store the element with the other_name as key
                        reset_descriptions[other_name] = link_element
            
            logger.info(f"Extracted {len(reset_descriptions)} reset descriptions")
            return reset_descriptions
        except Exception as e:
            logger.error(f"Error extracting reset descriptions: {e}")
            return {}
    
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
                if "Hard Reset" in self.example_descriptions:
                    self.click_reset_description(self.example_descriptions, "Hard Reset")
                    return True
                else:
                    logger.warning("'Hard Reset' description not found")
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
                self.driver.quit()


if __name__ == "__main__":
    # Create and run the scraper
    scraper = HardResetScraper(username="Istomin", password="VnXJ7i47n4tjWj&g")
    scraper.run()
