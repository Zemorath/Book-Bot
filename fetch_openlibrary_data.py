import requests

BASE_URL = "https://openlibrary.org"

def search_openlibrary(book_title):
    query = book_title.replace(' ', '+')
    URL = f"{BASE_URL}/search.json?title={query}"
    
    try:
        response = requests.get(URL)
        response.raise_for_status()
        data = response.json()

        if 'docs' not in data or not data['docs']:
            print("No listings found.")
            return None

        search_results = []
        for book in data['docs'][:5]:
            title = book.get("title", "N/A")
            isbn_list = book.get("isbn", ["N/A"])
            isbn = isbn_list[0]
            cover_id = book.get("cover_i")
            image_url = f"https://covers.openlibrary.org/b/id/{cover_id}-L.jpg" if cover_id else "N/A"
            search_results.append((title, isbn, image_url))
        
        return search_results

    except Exception as e:
        print(f"An error occurred: {e}")
        return None


