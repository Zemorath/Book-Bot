import requests
from bs4 import BeautifulSoup

URL = "https://www.hpb.com/search?q=the+daily+stoic&search-button=&lang=en_US"
page = requests.get(URL)

soup = BeautifulSoup(page.content, "html.parser")

results = soup.find(id="product-search-results")
# print(results.prettify())

item_list = results.find_all("div", class_="product")

for item in item_list:
    title = item.find("a", class_="link")
    if title:
        print(title.text.strip())
        price_class = item.find("div", class_="price")
        price_range = price_class.find_all("span", class_="value")
        for price in price_range:
            print("Price: ", price.text.strip())
        print()
        