from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options
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

driver.get("https://www.hardreset.info/admin/")

def text_field_interaction(url, class_name, text_to_enter=None, wait_time = 10):
    try:
        driver.get(url)
        
        try:
            element = WebDriverWait(driver, wait_time).until(EC.presence_of_element_located((By.CLASS_NAME, class_name)))
            
            if element.tag_name in ["input", "textarea"]:
                if text_to_enter:
                    element.clear() 
                    element.send_keys(text_to_enter)
                    
                current_value = element.get_attribute("value")
                return current_value
            else:
                print(f"Найденный элемент не является текстовым полем. Тег: {element.tag_name}")
                return None
                
        except TimeoutException:
            print(f"Текстовое поле с классом '{class_name}' не найдено за {wait_time} секунд")
            
            text_fields = driver.find_elements(By.XPATH, "//input[@type='text'] | //textarea")
            
            if text_fields:
                print(f"Найдено {len(text_fields)} текстовых полей на странице. Их классы:")
                for idx, field in enumerate(text_fields):
                    print(f"{idx + 1}. Класс: '{field.get_attribute('class')}', ID: '{field.get_attribute('id')}', Имя: '{field.get_attribute('name')}'")
            else:
                print("Текстовых полей на странице не обнаружено")
            
            return None
    
    finally:
        time.sleep(10)
        driver.quit()

if __name__ == "__main__": pass

driver.quit() 