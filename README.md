# Drive-Through Order Simulator

A sophisticated system that simulates realistic drive-through ordering conversations using AI. The simulator generates natural customer interactions while working to complete specific order goals.

## Features

- 🤖 Natural language conversation simulation using GPT-4
- 🔄 Multiple conversation styles and customer personalities
- 📋 Support for simple, medium, and complex order scenarios
- ⚡ Parallel simulation processing
- 📝 Comprehensive logging system
- 🔄 Automatic retry handling for API requests
- 🎯 Goal-oriented ordering system

## Prerequisites

- Python 3.8+
- OpenAI API key
- Lilac API credentials

## Installation

1. Clone the repository:
2. git clone [repository-url]
3. cd [repository-name]
4. Set up environment variables (Lilac API key, OpenAI API key)
5. Create virtual environment: python -m venv .venv
5. pip install -r requirements.txt

## Usage
1. Run the script:
2. python src/main.py

## Configuration

- Uncomment the desired simulation in main.py
- Set the desired order complexity in main.py
- Set the desired number of simulations in main.py
- Set the desired number of concurrent threads in main.py