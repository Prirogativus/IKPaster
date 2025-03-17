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

#telgrambot = TelegramInteraction
#haiku = AnthropicAPI
driver = webdriver.Chrome()

#Authentification
username = "Istomin"
password = "VnXJ7i47n4tjWj&g"

# URL-s
auth_url = "https://www.hardreset.info/admin/"

# Elements
usnm_textarea = "id_username"
pswd_textarea = "id_password"
search_field ="/html/body/div/div[3]/div/div/div[1]/form/div/input[1]"
search_button = "/html/body/div/div[3]/div/div/div[1]/form/div/input[2]"
other_desc_btn = "/html/body/div/div[3]/div/ul/li[1]/a"

#Example devices
example_dev = "HUAWEI Mate 60 Pro"
target_dev = "HUAWEI Mate 70"


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


def text_field_interaction_xpath(xpath, text_to_enter=None, wait_time = 10):
    try:        
        element = WebDriverWait(driver, wait_time).until(EC.presence_of_element_located((By.XPATH, xpath))) # make's driver wait until object is located

        if element.tag_name in ["input", "textarea"]:
            if text_to_enter:
                    element.clear()
                    element.send_keys(text_to_enter)
     
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


def find_and_click(xpath, wait_time = 10):
     element = WebDriverWait(driver, wait_time).until(EC.presence_of_element_located((By.XPATH, xpath)))
     element.click()


def find_element_with_name_included(name):
    try:
         element = WebDriverWait(driver, 10).until(EC.presence_of_element_located((By.XPATH, f"//tr[.//a[normalize-space(text())='{name}']]")))
         print("exact object wasn't founded")
    except:
         element = WebDriverWait(driver, 10).until(EC.presence_of_element_located((By.XPATH, f"//td[text()='{name}']/parent::tr")))
    return element


def find_clickable_device_name(device_name, timeout=10):
    try:
        link = WebDriverWait(driver, timeout).until(
            EC.element_to_be_clickable((By.XPATH, f"//a[contains(., '{device_name}')]"))
        )
        return link 
    except TimeoutException:
        try:
            cell = WebDriverWait(driver, timeout).until(
                EC.presence_of_element_located((By.XPATH, f"//td[contains(., '{device_name}')]"))
            )
            link = cell.find_element(By.TAG_NAME, "a")
            return link
        except:
            return None
        

def authentification():
    driver.get(auth_url)
    text_field_interaction_id(usnm_textarea, username)
    text_field_interaction_id(pswd_textarea, password)
    find_and_click("//input[@value='Log in']")

    
def get_example_text():
    driver.get("https://www.hardreset.info/admin/reset/resetinfo/")
    text_field_interaction_xpath(search_field, example_dev)
    find_and_click(search_button)
    find_clickable_device_name(example_dev).click()
    find_and_click(other_desc_btn)

if __name__ == "__main__": 
    authentification()
    get_example_text()
    time.sleep(100)
    driver.quit() 

