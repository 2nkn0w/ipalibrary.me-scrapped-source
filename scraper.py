import requests
from bs4 import BeautifulSoup
import base64
import json
import re
import os
from datetime import datetime
from concurrent.futures import ThreadPoolExecutor

# --- CONFIGURATION ---
SITEMAP_URL = "https://ipalibrary.me/post-sitemap.xml"
# Garantiza que el JSON se guarde en la misma carpeta que el script
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
OUTPUT_FILE = os.path.join(BASE_DIR, "ipalibrary_source.json")

MAX_THREADS = 12 
HEADERS = {
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/119.0.0.0 Safari/537.36'
}

# ... (resto de funciones decode_download_url y scrape_app_page quedan exactamente igual) ...

def run_scraper():
    print("--- 🛠️ IPALibrary AltStore Source Generator ---")
    
    try:
        print("🔍 Fetching URLs from sitemap...")
        r = requests.get(SITEMAP_URL, headers=HEADERS)
        # Asegurarse de usar lxml para parsear XML
        sitemap_soup = BeautifulSoup(r.content, 'lxml-xml')
        urls = [loc.text for loc in sitemap_soup.find_all('loc') if "ipalibrary.me/" in loc.text]
        urls = [u for u in urls if u != "https://ipalibrary.me/" and not u.endswith('.xml')]
    except Exception as e:
        print(f"❌ Failed to read sitemap: {e}")
        return

    total_urls = len(urls)
    print(f"📦 Found {total_urls} potential apps. Starting multi-threaded extraction...")

    with ThreadPoolExecutor(max_workers=MAX_THREADS) as executor:
        results = list(executor.map(scrape_app_page, urls))

    apps_list = [app for app in results if app is not None]

    source_data = {
        "name": "IPALibrary Source",
        "identifier": "me.ipalibrary.source",
        "subtitle": f"Last Update: {datetime.now().strftime('%b %d, %Y')}",
        "description": "Custom AltStore source for IPALibrary apps.",
        "iconURL": "https://ipalibrary.me/favicon.ico",
        "website": "https://ipalibrary.me",
        "apps": apps_list
    }

    with open(OUTPUT_FILE, 'w', encoding='utf-8') as f:
        json.dump(source_data, f, indent=4, ensure_ascii=False)

    print("\n" + "="*40)
    print(f"✨ SUCCESS: {len(apps_list)} apps added to source.")
    print(f"📁 Output file: {OUTPUT_FILE}")
    print("="*40)

if __name__ == "__main__":
    run_scraper()
