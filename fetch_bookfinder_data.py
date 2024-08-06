from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC

BASE_URL = "https://www.bookfinder.com"
MAX_LISTINGS = 5

def search_bookfinder(book_isbn):
    query = book_isbn
    URL = f"{BASE_URL}/isbn/{query}/?st=sr&ac=qr&mode=basic&author=&title=&isbn={query}&lang=en&destination=us&currency=USD&binding=*&keywords=&publisher=&min_year=&max_year=&minprice=&maxprice="
    
    chrome_options = Options()
    chrome_options.add_argument("--no-sandbox")
    chrome_options.add_argument("--disable-dev-shm-usage")
    chrome_options.add_argument("user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36")
    
    service = Service("/usr/local/bin/chromedriver")  
    
    driver = webdriver.Chrome(service=service, options=chrome_options)
    driver.get(URL)
    
    try:
        WebDriverWait(driver, 20).until(
            EC.presence_of_element_located((By.XPATH, "//span[@class='results-price']/a"))
        )

        listings = driver.find_elements(By.XPATH, "//span[@class='results-price']/a")

        if len(listings) == 0:
            print("No listings found.")
            return None

        first_listing = listings[0] if len(listings) > 0 else None
        fifth_listing = listings[4] if len(listings) >= 5 else listings[-1] if len(listings) > 0 else None
        
        first_url = first_listing.get_attribute('href') if first_listing else "N/A"
        first_price = first_listing.text.strip() if first_listing else "N/A"
        first_store = first_listing.get_attribute("data-ga-pageview-bookstore")

        fifth_url = fifth_listing.get_attribute('href') if fifth_listing else "N/A"
        fifth_price = fifth_listing.text.strip() if fifth_listing else "N/A"
        fifth_store = fifth_listing.get_attribute("data-ga-pageview-bookstore")

        price_range = f"{first_price} - {fifth_price}"
        return {
            "price_range": price_range,
            "first_listing_url": first_url,
            "first_listing_price": first_price,
            "first_store": first_store,
            "fifth_listing_url": fifth_url,
            "fifth_listing_price": fifth_price,
            "fifth_store": fifth_store
        }

    except Exception as e:
        print(f"An error occurred: {e}")
    finally:
        driver.quit()
