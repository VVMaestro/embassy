from selenium import webdriver
from selenium.webdriver.chrome.options import Options


def init_chromium(headless=True):
    # Setup Chrome options
    options = Options()
    if headless:
        options.add_argument("--headless")
    options.add_argument("--no-sandbox")
    options.add_argument("--disable-dev-shm-usage")
    options.add_argument("--disable-gpu")
    options.add_argument("--window-size=1920,1080")

    # Create driver
    return webdriver.Chrome(options=options)
