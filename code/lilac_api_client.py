import requests
from constants import API_BASE_URL, API_TOKEN

class LilacApiClient:
    def __init__(self, location="ben-franks"):
        self.api_token = API_TOKEN
        self.base_url = API_BASE_URL
        self.location = location

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
        resp = requests.post(url, json=data, headers=headers)
        resp.raise_for_status()
        return resp.json()

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
