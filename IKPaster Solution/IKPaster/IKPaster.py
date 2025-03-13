from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options
from selenium.webdriver import Keys, ActionChains
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import TimeoutException, NoSuchElementException
import time
import TelegramInteraction
import AnthropicAPI

telgrambot = TelegramInteraction
haiku = AnthropicAPI
driver = webdriver.Chrome()

auth_url = "https://www.hardreset.info/admin/"
username = "Istomin"
password = "VnXJ7i47n4tjWj&g"
usnm_textarea = "id_username"
pswd_textarea = "id_password"


def text_field_interaction_id(class_name, text_to_enter=None, wait_time = 10):
    try:        
        element = WebDriverWait(driver, wait_time).until(EC.presence_of_element_located((By.ID, class_name))) # make's driver wait until object is located

        if element.tag_name in ["input", "textarea"]:
            if text_to_enter:
                    element.clear()
                    element.send_keys(text_to_enter)
        else:
            print(f"Not a textarea")
                
    except TimeoutException:
            print(f"Textarea is not finded")
            
            text_fields = driver.find_elements(By.XPATH, "//input[@type='text'] | //textarea")
            
            if text_fields:
                print(f"Найдено {len(text_fields)} текстовых полей на странице. Их классы:")
                for idx, field in enumerate(text_fields):
                    print(f"{idx + 1}. Класс: '{field.get_attribute('class')}', ID: '{field.get_attribute('id')}', Имя: '{field.get_attribute('name')}'")
            else:
                print("Текстовых полей на странице не обнаружено")
            
            return None 
    

def click(xpath, wait_time = 10):
     element = WebDriverWait(driver, wait_time).until(EC.presence_of_element_located((By.XPATH, xpath)))
     element.click()




if __name__ == "__main__": 
    driver.get(auth_url)
    text_field_interaction_id(usnm_textarea, username)
    text_field_interaction_id(pswd_textarea, password)
    time.sleep(5)
    click("//input[@value='Log in']")
    time.sleep(100)
driver.quit() 