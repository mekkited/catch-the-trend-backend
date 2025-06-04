import re
import os
import time
import requests
from flask import Flask, jsonify, request
from bs4 import BeautifulSoup
from flask_cors import CORS

# Initialize Flask App
app = Flask(__name__)
CORS(app)

# Add a simple cache to store recent results and save API credits
CACHE = {}
CACHE_DURATION_SECONDS = 86400  # 24 hours

# Data Definitions (No changes)
TREND_KEYWORDS = {
    "USA": { "coloring": ["Vintage Floral Coloring Book", "Anime Character Coloring Book"], "journal": ["Kids' Mindfulness Journal", "Daily Stoic Journal Prompts"], "logbook": ["Workout & Fitness Logbook", "Reading Logbook"], "activity": ["Brain Teasers for Seniors", "Toddler Scissor Skills Book"] },
    "FR": { "coloring": ["Livre de coloriage Mandalas Zen", "Coloriage Mystère Disney"], "journal": ["Mon Journal Intime Fille", "Bullet Journal à Points"], "logbook": ["Carnet de Suivi Sportif", "Journal de Bord de Lecture"], "activity": ["Cahier d'Activités Montessori", "Jeux de Logique et Énigmes"] }
}

# Amazon Scraping Function
def get_amazon_competition(keyword, market):
    """
    Scrapes Amazon using scrape.do and includes caching.
    """
    # Check cache first
    if keyword in CACHE:
        cached_data, timestamp = CACHE[keyword]
        if time.time() - timestamp < CACHE_DURATION_SECONDS:
            print(f"CACHE HIT: Using cached data for '{keyword}'")
            return cached_data

    market_config = {"USA": {"domain": "amazon.com"}, "FR": {"domain": "amazon.fr"}}
    if market not in market_config: return 0

    domain = market_config[market]["domain"]
    amazon_url_to_scrape = f"https://www.{domain}/s?k={keyword.replace(' ', '+')}"

    scrape_do_api_key = os.environ.get('SCRAPER_API_KEY')
    if not scrape_do_api_key:
        print("ERROR: SCRAPER_API_KEY environment variable not set.")
        return 0

    scrape_do_api_url = f"http://api.scrape.do/"
    params = {
        'token': scrape_do_api_key,
        'url': amazon_url_to_scrape
    }

    try:
        # Send the request to scrape.do
        # The timeout for the requests library itself is set here.
        # Gunicorn's timeout (set in Render's start command) handles the overall worker timeout.
        response = requests.get(scrape_do_api_url, params=params, timeout=60) 
        response.raise_for_status() # Will raise an exception for HTTP errors (4xx or 5xx)
        
        # --- DEBUG LINE ADDED HERE ---
        print(f"DEBUG: scrape.do response for {amazon_url_to_scrape}: {response.text[:1000]}") # Print first 1000 chars
        # --- END DEBUG LINE ---

        soup = BeautifulSoup(response.content, 'html.parser')
        
        result_span = soup.find('div', {'data-component-type': 's-result-info-bar'})
        if not result_span:
            print(f"Could not find result span for keyword: {keyword} on {amazon_url_to_scrape}")
            return 0

        result_text = result_span.get_text(strip=True)
        matches = re.findall(r'[\d,]+', result_text)
        
        if matches:
            competition_number = int(matches[-1].replace(',', ''))
            CACHE[keyword] = (competition_number, time.time()) # Store in cache
            print(f"API CALL (scrape.do): Fetched and cached data for '{keyword}'")
            return competition_number
        else:
            print(f"Could not parse result number from text: '{result_text}' for keyword: {keyword}")
            return 0

    except requests.exceptions.RequestException as e:
        print(f"Error fetching via scrape.do: {e}")
        return 0
    except Exception as e:
        print(f"An error occurred during parsing: {e}")
        return 0

# API Endpoint (No changes)
@app.route('/api/trends', methods=['GET'])
def get_trends():
    market = request.args.get('market', 'USA')
    book_type = request.args.get('bookType', 'all')
    if market not in TREND_KEYWORDS: return jsonify({"error": "Invalid market specified"}), 400

    trends_to_fetch = []
    if book_type == 'all':
        for btype in TREND_KEYWORDS[market]: trends_to_fetch.extend(TREND_KEYWORDS[market][btype])
    elif book_type in TREND_KEYWORDS[market]: trends_to_fetch = TREND_KEYWORDS[market][book_type]
    else: return jsonify({"error": "Invalid bookType specified"}), 400

    final_trends = []
    for keyword in trends_to_fetch:
        competition = get_amazon_competition(keyword, market)
        if competition == 0: comp_level = "N/A"
        elif competition < 1000: comp_level = "Low"
        elif competition < 5000: comp_level = "Medium"
        else: comp_level = "High"
        final_trends.append({"name": keyword, "searchVolume": "N/A", "competition": comp_level, "trendPercentage": competition})
    return jsonify(final_trends)

# Health Check Endpoint (No changes)
@app.route('/')
def index():
    return "Catch the Trend Backend is running (with scrape.do)!"

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000)