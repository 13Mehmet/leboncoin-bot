import os
import json
import requests
from datetime import datetime

TELEGRAM_TOKEN = os.environ["TELEGRAM_TOKEN"]
TELEGRAM_CHAT_ID = os.environ["TELEGRAM_CHAT_ID"]
SEEN_FILE = "seen_ids.json"

def load_seen_ids():
    if os.path.exists(SEEN_FILE):
        with open(SEEN_FILE, "r") as f:
            return set(json.load(f))
    return set()

def save_seen_ids(ids):
    with open(SEEN_FILE, "w") as f:
        json.dump(list(ids), f)

def send_telegram(message):
    url = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage"
    payload = {
        "chat_id": TELEGRAM_CHAT_ID,
        "text": message,
        "parse_mode": "HTML",
        "disable_web_page_preview": False,
    }
    r = requests.post(url, json=payload, timeout=10)
    r.raise_for_status()

def scrape_listings():
    api_url = "https://api.leboncoin.fr/finder/search"
    headers = {
        "User-Agent": "LeBonCoin/9.0.0 (iPhone; iOS 16.0)",
        "Content-Type": "application/json",
        "Accept": "application/json",
        "api_key": "ba0c2dad52b3585d5d6b3b0a5f0d5a8a",
    }
    payload = {
        "filters": {
            "category": {"id": "2"},
            "location": {
                "city_zipcodes": [{"city": "Lyon", "zipcode": "69000"}]
            },
            "keywords": {},
            "ranges": {
                "price": {"min": 8000, "max": 11000},
                "mileage": {"min": 0, "max": 190000},
                "regdate": {"min": 2018},
            },
        },
        "limit": 35,
        "sort_by": "time",
        "sort_order": "desc",
        "offset": 0,
    }
    resp = requests.post(api_url, json=payload, headers=headers, timeout=15)
    resp.raise_for_status()
    data = resp.json()

    listings = []
    for ad in data.get("ads", []):
        ad_id = str(ad.get("list_id", ""))
        title = ad.get("subject", "Baslik yok")
        price_val = ad.get("price", [None])[0] if ad.get("price") else None
        price = f"{price_val} EUR" if price_val else "Fiyat belirtilmemis"
        location = ad.get("location", {}).get("city", "")
        link = ad.get("url", "")
        date = ad.get("first_publication_date", "")[:10] if ad.get("first_publication_date") else ""
        if ad_id:
            listings.append({
                "id": ad_id,
                "title": title,
                "price": price,
                "location": location,
                "link": link,
                "date": date,
            })
    return listings

def main():
    print(f"Bot basladi - {datetime.now().strftime('%Y-%m-%d %H:%M')}")
    seen_ids = load_seen_ids()
    print(f"Daha once gorulen ilan: {len(seen_ids)}")

    try:
        listings = scrape_listings()
    except Exception as e:
        send_telegram(f"HATA: {e}")
        raise

    print(f"Bulunan ilan: {len(listings)}")
    new_listings = [l for l in listings if l["id"] not in seen_ids]
    print(f"Yeni ilan: {len(new_listings)}")

    if not new_listings:
        send_telegram("Leboncoin tarama tamamlandi. Yeni ilan bulunamadi.")
        return

    send_telegram(f"<b>{len(new_listings)} Yeni Araba Ilani!</b>")

    for listing in new_listings[:20]:
        msg = (
            f"<b>{listing['title']}</b>\n"
            f"{listing['price']}\n"
            f"{listing['location']} - {listing['date']}\n"
            f"<a href='{listing['link']}'>Ilani Gor</a>"
        )
        try:
            send_telegram(msg)
        except Exception as e:
            print(f"Telegram hatasi: {e}")
        seen_ids.add(listing["id"])

    save_seen_ids(seen_ids)
    print("Tamamlandi.")

if __name__ == "__main__":
    main()