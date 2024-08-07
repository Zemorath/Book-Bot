import requests
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def search_openlibrary(query):
    base_url = "http://openlibrary.org/search.json"
    cover_base_url = "http://covers.openlibrary.org/b/ISBN/"
    params = {
        "title": query,
        "limit": 10
    }
    try:
        response = requests.get(base_url, params=params, timeout=10)
        response.raise_for_status()
        data = response.json()

        if 'docs' not in data:
            logger.info("No 'docs' field found in response")
            return []

        search_results = []
        for doc in data["docs"]:
            title = doc.get("title", "N/A")
            author = ", ".join(doc.get("author_name", ["N/A"]))
            isbn_list = doc.get("isbn", [])
            isbn = isbn_list[0] if isbn_list else "N/A"
            image_url = f"{cover_base_url}{isbn}-L.jpg" if isbn_list else None
            search_results.append((title, author, isbn, image_url))

        if not search_results:
            logger.info("No search results found")
        else:
            logger.info(f"Found {len(search_results)} results")

        return search_results

    except requests.exceptions.RequestException as e:
        logger.error(f"An error occurred: {e}")
        return []

# Example usage
if __name__ == "__main__":
    results = search_openlibrary("The Way of Kings")
    for result in results:
        print(result)
