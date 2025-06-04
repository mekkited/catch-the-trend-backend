import re
import requests
from flask import Flask, jsonify, request
from bs4 import BeautifulSoup
from flask_cors import CORS

# Initialize Flask App
app = Flask(__name__)
# Enable CORS to allow your website to call this API
CORS(app)

# --- Data Definitions ---
# Define the keywords we want to track for each category.
# You can expand this list as much as you want.
TREND_KEYWORDS = {
    "USA": {
        "coloring": ["Vintage Floral Coloring Book", "Anime Character Coloring Book"],
        "journal": ["Kids' Mindfulness Journal", "Daily Stoic Journal Prompts"],
        "logbook": ["Workout & Fitness Logbook", "Reading Logbook"],
        "activity": ["Brain Teasers for Seniors", "Toddler Scissor Skills Book"]
    },
    "FR": {
        "coloring": ["Livre de coloriage Mandalas Zen", "Coloriage Mystère Disney"],
        "journal": ["Mon Journal Intime Fille", "Bullet Journal à Points"],
        "logbook": ["Carnet de Suivi Sportif", "Journal de Bord de Lecture"],
        "activity": ["Cahier d'Activités Montessori", "Jeux de Logique et Énigmes"]
    }
}

# --- Amazon Scraping Function ---
def get_amazon_competition(keyword, market):
    """
    Scrapes Amazon for a given keyword and returns the number of search results.
    """
    market_config = {
        "USA": {"domain": "amazon.com"},
        "FR": {"domain": "amazon.fr"}
    }

    if market not in market_config:
        return 0

    domain = market_config[market]["domain"]
    url = f"https://www.{domain}/s?k={keyword.replace(' ', '+')}"

    # IMPORTANT: Set a User-Agent header to mimic a real browser
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
    }

    try:
        response = requests.get(url, headers=headers, timeout=10)
        response.raise_for_status()  # Raise an exception for bad status codes (4xx or 5xx)

        soup = BeautifulSoup(response.content, 'html.parser')

        # Find the element containing the result count.
        # NOTE: Amazon's HTML can change. This selector might need updating in the future.
        result_span = soup.find('div', {'data-component-type': 's-result-info-bar'})
        
        if not result_span:
            return 0 # Element not found

        result_text = result_span.get_text(strip=True)

        # Use regex to find numbers in the text (e.g., "1-16 of over 3,000 results")
        # This looks for numbers that might have commas.
        matches = re.findall(r'[\d,]+', result_text)
        
        if matches:
            # The last number is usually the total count.
            # Remove commas and convert to an integer.
            competition_number = int(matches[-1].replace(',', ''))
            return competition_number
        else:
            return 0 # No number found in the text

    except requests.exceptions.RequestException as e:
        print(f"Error fetching {url}: {e}")
        return 0
    except Exception as e:
        print(f"An error occurred during scraping: {e}")
        return 0

# --- API Endpoint ---
@app.route('/api/trends', methods=['GET'])
def get_trends():
    # Get parameters from the request URL (e.g., /api/trends?market=USA&bookType=coloring)
    market = request.args.get('market', 'USA')
    book_type = request.args.get('bookType', 'all')

    if market not in TREND_KEYWORDS:
        return jsonify({"error": "Invalid market specified"}), 400

    trends_to_fetch = []
    if book_type == 'all':
        for btype in TREND_KEYWORDS[market]:
            trends_to_fetch.extend(TREND_KEYWORDS[market][btype])
    elif book_type in TREND_KEYWORDS[market]:
        trends_to_fetch = TREND_KEYWORDS[market][book_type]
    else:
        return jsonify({"error": "Invalid bookType specified"}), 400

    # Process each keyword to build the final trend data
    final_trends = []
    for keyword in trends_to_fetch:
        competition = get_amazon_competition(keyword, market)
        
        # Determine competition level based on result count
        if competition == 0:
            comp_level = "N/A"
        elif competition < 1000:
            comp_level = "Low"
        elif competition < 5000:
            comp_level = "Medium"
        else:
            comp_level = "High"

        # Create a dictionary that matches the frontend's expected format
        final_trends.append({
            "name": keyword,
            "searchVolume": "N/A",  # You could integrate another API for this
            "competition": comp_level,
            "trendPercentage": competition # Using the raw number here for now
        })

    return jsonify(final_trends)

# --- Health Check Endpoint ---
@app.route('/')
def index():
    return "Catch the Trend Backend is running!"

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000)