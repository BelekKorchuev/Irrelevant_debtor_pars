from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options
from selenium import webdriver
from webdriver_manager.chrome import ChromeDriverManager
import logging

# Функция для создания WebDriver
def create_webdriver():
    try:
        chrome_options = Options()
        chrome_service = Service(ChromeDriverManager().install())
        driver = webdriver.Chrome(service=chrome_service, options=chrome_options)
        return driver
    except Exception as e:
        logging.error(f"Ошибка при создании WebDriver: {e}")
        return None

# Перезапуск драйвера
def restart_driver(driver):
    try:
        driver.quit()
    except Exception as e:
        logging.error(f"Ошибка при завершении WebDriver: {e}")
    return create_webdriver()

# Проверка состояния браузера
def is_browser_alive(driver):
    try:
        driver.title
        return True
    except Exception as e:
        logging.warning(f"Браузер не отвечает: {e}")
        return False
