import os
from dotenv import load_dotenv
import json

load_dotenv()

API_BASE_URL = os.getenv('LILAC_API_BASE_URL', "https://test.lilaclabs.ai/lilac-agent")
API_TOKEN = os.getenv('LILAC_API_TOKEN')

# Load the actual menu from the provided JSON file
with open('provided/menu.json', 'r') as f:
    MENU_JSON = json.load(f)
