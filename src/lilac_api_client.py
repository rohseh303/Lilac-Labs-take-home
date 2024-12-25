import requests
from constants import API_BASE_URL, API_TOKEN
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry
import time

class LilacApiClient:
    def __init__(self, location="ben-franks"):
        self.api_token = API_TOKEN
        self.base_url = API_BASE_URL
        self.location = location

        # Configure retry strategy
        retry_strategy = Retry(
            total=3,  # number of retries
            backoff_factor=1,  # wait 1, 2, 4 seconds between retries
            status_forcelist=[500, 502, 503, 504]
        )
        
        # Create session with retry strategy
        self.session = requests.Session()
        adapter = HTTPAdapter(max_retries=retry_strategy)
        self.session.mount("https://", adapter)

    def start_order(self):
        """Start a new order session."""
        url = f"{self.base_url}/start"
        headers = {
            "x-api-key": f"Bearer {self.api_token}",
            "Content-Type": "application/json",
        }
        data = {"location": self.location}
        resp = requests.post(url, json=data, headers=headers)
        resp.raise_for_status()
        return resp.json()["orderId"]

    def send_chat_message(self, order_id, message):
        """Send a chat message to Lilac's order-taking agent."""
        url = f"{self.base_url}/chat"
        headers = {
            "x-api-key": f"Bearer {self.api_token}",
            "Content-Type": "application/json",
        }
        data = {
            "orderId": order_id,
            "input": message,
            "location": self.location
        }
        
        max_retries = 3
        for attempt in range(max_retries):
            try:
                resp = self.session.post(url, json=data, headers=headers)
                resp.raise_for_status()
                return resp.json()
            except requests.exceptions.ConnectionError as e:
                if attempt == max_retries - 1:
                    raise
                time.sleep(2 ** attempt)  # exponential backoff

    def retrieve_order(self, order_id):
        """Retrieve the current order state."""
        url = f"{self.base_url}/order/{order_id}"
        headers = {
            "x-api-key": f"Bearer {self.api_token}",
            "Content-Type": "application/json",
        }
        resp = requests.get(url, headers=headers)
        resp.raise_for_status()
        return resp.json()
