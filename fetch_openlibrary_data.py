import requests

def search_openlibrary(query):
    base_url = "http://openlibrary.org/search.json"
    params = {"title": query}
    response = requests.get(base_url, params=params)
    data = response.json()

    search_results = []
    for book in data.get("docs", [])[:10]:  # Limit to top 10 results
        title = book.get("title", "N/A")
        author = book.get("author_name", ["N/A"])[0]
        isbn = book.get("isbn", ["N/A"])[0]
        cover_id = book.get("cover_i", None)
        if cover_id:
            image_url = f"http://covers.openlibrary.org/b/id/{cover_id}-L.jpg"
        else:
            image_url = None
        search_results.append((title, author, isbn, image_url))
    return search_results
