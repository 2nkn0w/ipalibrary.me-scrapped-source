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
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
OUTPUT_FILE = os.path.join(BASE_DIR, "ipalibrary_source.json")

MAX_THREADS = 12 
HEADERS = {
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/119.0.0.0 Safari/537.36'
}

def decode_download_url(encoded_href):
    """ Extracts and decodes the Base64 URL from the download button """
    try:
        encoded_data = encoded_href.split('data=')[1]
        decoded_str = base64.b64decode(encoded_data).decode('utf-8')
        
        match = re.search(r'url=([^&]+)', decoded_str)
        if match:
            return match.group(1)
    except Exception:
        pass
    return None

def scrape_app_page(url):
    """ Scrapes a single app page for its metadata and download link """
    try:
        response = requests.get(url, headers=HEADERS, timeout=15)
        if response.status_code != 200:
            return None
        
        soup = BeautifulSoup(response.text, 'html.parser')
        
        # 1. Get App Name
        name_tag = soup.find('h1')
        name = name_tag.text.strip() if name_tag else "Unknown App"

        # 2. Get App Icon
        icon_url = "https://ipalibrary.me/favicon.ico"
        img_tag = soup.find('img', {'class': lambda x: x and 'img-fluid' in x and 'rounded-5' in x})
        if img_tag:
            icon_url = img_tag.get('data-src') or img_tag.get('src')

        # 3. Get Developer and Version
        developer = "Unknown Developer"
        version = "1.0"
        dev_elements = soup.find_all('div', class_='ipa-developer')
        for el in dev_elements:
            text = el.get_text(strip=True)
            if "Version:" in text:
                version = text.replace("Version:", "").strip()
            elif "bi-person-fill" in str(el):
                developer = text.strip()

        # 4. Get Download Link
        download_url = None
        a_tag = soup.find('a', href=re.compile(r'/dl\?data='))
        if a_tag:
            download_url = decode_download_url(a_tag['href'])

        if download_url:
            bundle_id = f"me.ipalibrary.{re.sub(r'[^a-zA-Z0-9]', '', name.lower())}"
            
            print(f"✅ Processed: {name} (v{version})")
            return {
                "name": name,
                "bundleIdentifier": bundle_id,
                "developerName": developer,
                "version": version,
                "versionDate": datetime.now().strftime("%Y-%m-%d"),
                "downloadURL": download_url,
                "localizedDescription": f"App: {name}\nVersion: {version}\nSource: IPALibrary",
                "iconURL": icon_url,
                "size": 0
            }
    except Exception as e:
        print(f"⚠️ Error scraping {url}: {e}")
    return None

def run_scraper():
    print("--- 🛠️ IPALibrary AltStore Source Generator ---")
    
    try:
        print("🔍 Fetching URLs from sitemap...")
        r = requests.get(SITEMAP_URL, headers=HEADERS, timeout=20)
        r.raise_for_status() # Lanza error si la web devuelve 404, 500, etc.
        sitemap_soup = BeautifulSoup(r.content, 'lxml-xml')
        urls = [loc.text for loc in sitemap_soup.find_all('loc') if "ipalibrary.me/" in loc.text]
        urls = [u for u in urls if u != "https://ipalibrary.me/" and not u.endswith('.xml')]
    except Exception as e:
        print(f"❌ Failed to read sitemap: {e}")
        raise RuntimeError("Sitemap inaccessible or network error. Aborting run.")

    total_urls = len(urls)
    print(f"📦 Found {total_urls} potential apps. Starting multi-threaded extraction...")

    with ThreadPoolExecutor(max_workers=MAX_THREADS) as executor:
        results = list(executor.map(scrape_app_page, urls))

    apps_list = [app for app in results if app is not None]

    # --- CONTROL DE SEGURIDAD ---
    if not apps_list:
        print("❌ CRITICAL ERROR: 0 apps extracted. The web layout might have changed.")
        raise RuntimeError("No apps were successfully scraped. Aborting file update to prevent corrupted data.")

    # Formateo de fecha y hora completa (ejemplo: Aug 26, 2026 - 11:15:30 UTC)
    full_timestamp = datetime.now().strftime('%b %d, %Y - %H:%M:%S UTC')

    source_data = {
        "name": "IPALibrary Source",
        "identifier": "me.ipalibrary.source",
        "subtitle": f"Last Update: {full_timestamp}",
        "description": f"Custom AltStore source for IPALibrary apps. Updated at {full_timestamp}.",
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
