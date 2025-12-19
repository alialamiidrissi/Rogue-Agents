
import os
import textwrap
import requests
from langchain_google_genai import ChatGoogleGenerativeAI

def wrap_text(text: str, width: int = 25) -> str:
    """Wraps text to a specified width using newlines."""
    return "\n".join(textwrap.wrap(text, width=width))

def add_retry(llm):
    """Adds exponential backoff retry to an LLM instance."""
    return llm.with_retry(exponential_jitter_params={"initial": 3})

def fetch_comicgen_asset(url: str, output_path: str) -> bool:
    """Fetches a ComicGen asset from a URL and saves it to a path."""
    try:
        response = requests.get(url)
        if response.status_code == 200:
            with open(output_path, "wb") as f:
                f.write(response.content)
            return True
        else:
            print(f"Error fetching asset: {response.status_code}")
            return False
    except Exception as e:
        print(f"Error fetching asset: {e}")
        return False

def load_guidelines(guidelines_path: str) -> str:
    if os.path.exists(guidelines_path):
        with open(guidelines_path, "r") as f:
            return f.read()
    return ""
