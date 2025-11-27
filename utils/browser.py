from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from webdriver_manager.chrome import ChromeDriverManager
from selenium.webdriver.chrome.service import Service
import time

class BrowserAutomation:
    def __init__(self):
        self.options = Options()
        self.options.add_argument('--headless')
        self.options.add_argument('--no-sandbox')
        self.options.add_argument('--disable-dev-shm-usage')
        self.options.add_argument('--disable-gpu')
    
    def fetch_page(self, url):
        """Fetch and render JavaScript page"""
        driver = webdriver.Chrome(
            service=Service(ChromeDriverManager().install()),
            options=self.options
        )
        
        try:
            driver.get(url)
            time.sleep(3)  # Wait for JS execution
            
            html = driver.page_source
            text = driver.find_element(By.TAG_NAME, 'body').text
            
            return html, text
        finally:
            driver.quit()