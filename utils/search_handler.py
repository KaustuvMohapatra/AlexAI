import os
from serpapi import GoogleSearch

REALTIME_KEYWORDS = [
    "weather", "price", "cost", "stock", "temperature", "temp", "news",
    "latest", "current", "how much", "what is the time", "capital of"
]


def is_realtime_query(text: str) -> bool:
    return any(keyword in text.lower() for keyword in REALTIME_KEYWORDS)


def fetch_realtime_info(query: str) -> str:
    print(f"-> EXECUTING MANUAL SEARCH for: '{query}'")
    try:
        api_key = os.getenv("SERPAPI_API_KEY")
        if not api_key:
            return "Error: SERPAPI_API_KEY is not set."
        params = {"q": query, "api_key": api_key, "engine": "google", "hl": "en"}
        search = GoogleSearch(params)
        results = search.get_dict()
        if "answer_box" in results and "answer" in results["answer_box"]:
            return results["answer_box"]["answer"]
        if "organic_results" in results and results["organic_results"] and "snippet" in results["organic_results"][0]:
            return results["organic_results"][0]["snippet"]
        return "No definitive real-time information found."
    except Exception as e:
        return f"Error fetching real-time info: {str(e)}"
