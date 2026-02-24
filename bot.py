import os
import json
import requests
import time
from datetime import datetime

TELEGRAM_TOKEN = os.environ["TELEGRAM_TOKEN"]
TELEGRAM_CHAT_ID = os.environ["TELEGRAM_CHAT_ID"]
APIFY_TOKEN = os.environ["APIFY_TOKEN"]
SEEN_FILE = "seen_ids.json"

SEARCH_URL = "https://www.leboncoin.fr/recherche?category=2&locations=Lyon&price=min-8000,max-11000&mileage=min-0,max-190000&year=min-2018&sort=time"

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

def scrape_with_apify():
    run_url = f"https://api.apify.com/v2/acts/fatihtahta~leboncoin-fr-scraper/runs?token={APIFY_TOKEN}"
    input_data = {
        "startUrls": [{"url": SEARCH_URL}],
        "maxItems": 50,
    }
    resp = requests.post(run_url, json=input_data, timeout=30)
    resp.raise_for_status()
    run_id = resp.json()["data"]["id"]
    print(f"Apify run basladi: {run_id}")

    for i in range(24):
        time.sleep(10)
        status_url = f"https://api.apify.com/v2/actor-runs/{run_id}?token={APIFY_TOKEN}"
        status_resp = requests.get(status_url, timeout=10)
        status = status_resp.json()["data"]["status"]
        print(f"[{i+1}] Status: {status}")
        if status == "SUCCEEDED":
            dataset_id = status_resp.json()["data"]["defaultDatasetId"]
            break
        elif status in ["FAILED", "ABORTED", "TIMED-OUT"]:
            raise Exception(f"Apify run basarisiz: {status}")
    else:
        raise Exception("Apify run zaman asimi")

    items_url = f"https://api.apify.com/v2/datasets/{dataset_id}/items?token={APIFY_TOKEN}"
    items_resp = requests.get(items_url, timeout=15)
    items_resp.raise_for_status()
    items = items_resp.json()
    print(f"Apify'dan gelen ilan sayisi: {len(items)}")

    listings = []
    for item in items:
        ad_id = str(item.get("id", item.get("list_id", item.get("adId", ""))))
        title = item.get("title", item.get("subject", "Baslik yok"))
        price = item.get("price", "Fiyat belirtilmemis")
        if isinstance(price, dict):
            price = str(price.get("amount", price.get("display", ""))) + " EUR"
        elif isinstance(price, (int, float)):
            price = f"{price} EUR"
        location = item.get("location", "")
        if isinstance(location, dict):
            location = location.get("city", "")
        link = item.get("url", item.get("link", ""))
        date = str(item.get("first_publication_date", item.get("postedAt", item.get("date", ""))))[:10]

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
        listings = scrape_with_apify()
    except Exception as e:
        send_telegram(f"HATA: {e}")
        raise

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