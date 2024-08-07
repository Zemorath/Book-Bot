import requests
from bs4 import BeautifulSoup

BASE_URL = "https://www.hpb.com"

def fetch_listing_details(listing_url):
    page = requests.get(listing_url)
    soup = BeautifulSoup(page.content, 'html.parser')

    # Scrape ISBN
    isbn_element = soup.find("span", class_="product-id")
    isbn = isbn_element.text.strip() if isbn_element else "N/A"

    # Scrape image URL
    image_element = soup.find(id="zoom")
    image_url = image_element['src'] if image_element else "N/A"

    return isbn, image_url

def search_book(book_title):
    query = book_title.replace(' ', '+')
    URL = f"{BASE_URL}/search?q={query}&search-button=&lang=en_US"
    page = requests.get(URL)
    soup = BeautifulSoup(page.content, 'html.parser')

    results = soup.find(id="product-search-results")
    item_list = results.find_all("div", class_="product")

    for item in item_list:
        title_element = item.find("a", class_="link")
        if title_element:
            title_text = title_element.text.strip()
            if title_text.lower() == book_title.lower():
                listing_url = BASE_URL + title_element['href']
                isbn, image_url = fetch_listing_details(listing_url)
                price_class = item.find("div", class_="price")
                price_range = price_class.find_all("span", class_="value")
                prices = [price.text.strip() for price in price_range]
                return [(title_text, listing_url, isbn, image_url, prices)]

    return []
