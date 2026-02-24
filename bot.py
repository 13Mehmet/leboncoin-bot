import os
import json
import requests
from bs4 import BeautifulSoup
from datetime import datetime

# ── Ayarlar ──────────────────────────────────────────────

TELEGRAM_TOKEN = os.environ[“TELEGRAM_TOKEN”]
TELEGRAM_CHAT_ID = os.environ[“TELEGRAM_CHAT_ID”]
SEEN_FILE = “seen_ids.json”

# Leboncoin filtreler — istediğin gibi düzenle

SEARCH_URL = (
“https://www.leboncoin.fr/recherche”
“?category=2”
“&locations=Lyon”
“&price=min-8000,max-11000”
“&mileage=min-0,max-190000”
“&year=min-2018”
“&sort=time”
“&owner_type=all”
)

HEADERS = {
“User-Agent”: (
“Mozilla/5.0 (Windows NT 10.0; Win64; x64) “
“AppleWebKit/537.36 (KHTML, like Gecko) “
“Chrome/120.0.0.0 Safari/537.36”
),
“Accept-Language”: “fr-FR,fr;q=0.9”,
“Accept”: “text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8”,
}

# ── Yardımcı Fonksiyonlar ─────────────────────────────────

def load_seen_ids():
if os.path.exists(SEEN_FILE):
with open(SEEN_FILE, “r”) as f:
return set(json.load(f))
return set()

def save_seen_ids(ids: set):
with open(SEEN_FILE, “w”) as f:
json.dump(list(ids), f)

def send_telegram(message: str):
url = f”https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage”
payload = {
“chat_id”: TELEGRAM_CHAT_ID,
“text”: message,
“parse_mode”: “HTML”,
“disable_web_page_preview”: False,
}
r = requests.post(url, json=payload, timeout=10)
r.raise_for_status()

def scrape_listings():
“”“Leboncoin’dan ilanları çek ve parse et.”””
session = requests.Session()
session.headers.update(HEADERS)

```
resp = session.get(SEARCH_URL, timeout=15)
resp.raise_for_status()

soup = BeautifulSoup(resp.text, "html.parser")

listings = []

# Leboncoin ilanları data-qa-id="aditem_container" içinde
items = soup.select('[data-qa-id="aditem_container"]')

if not items:
    # Alternatif selector dene
    items = soup.select('article[data-reactid]') or soup.select('li[itemtype*="Offer"]')

for item in items:
    try:
        # ID
        ad_id = item.get("data-id") or item.get("id") or ""

        # Başlık
        title_el = item.select_one('[data-qa-id="aditem_title"]') or item.select_one('h2')
        title = title_el.get_text(strip=True) if title_el else "Başlık yok"

        # Fiyat
        price_el = item.select_one('[data-qa-id="aditem_price"]') or item.select_one('[class*="price"]')
        price = price_el.get_text(strip=True) if price_el else "Fiyat belirtilmemiş"

        # Konum
        location_el = item.select_one('[data-qa-id="aditem_location"]') or item.select_one('[class*="location"]')
        location = location_el.get_text(strip=True) if location_el else ""

        # Link
        link_el = item.select_one('a')
        link = ""
        if link_el and link_el.get("href"):
            href = link_el["href"]
            link = f"https://www.leboncoin.fr{href}" if href.startswith("/") else href

        # Tarih
        date_el = item.select_one('[data-qa-id="aditem_date"]') or item.select_one('time')
        date = date_el.get_text(strip=True) if date_el else ""

        if ad_id and title:
            listings.append({
                "id": ad_id,
                "title": title,
                "price": price,
                "location": location,
                "link": link,
                "date": date,
            })
    except Exception as e:
        print(f"  ⚠️ İlan parse hatası: {e}")
        continue

return listings
```

# ── Ana Akış ─────────────────────────────────────────────

def main():
print(f”🚗 Leboncoin Bot başladı — {datetime.now().strftime(’%Y-%m-%d %H:%M’)}”)

```
seen_ids = load_seen_ids()
print(f"📋 Daha önce görülen ilan sayısı: {len(seen_ids)}")

try:
    listings = scrape_listings()
except Exception as e:
    send_telegram(f"⚠️ <b>Leboncoin Bot Hatası</b>\n{e}")
    raise

print(f"📦 Bulunan toplam ilan: {len(listings)}")

new_listings = [l for l in listings if l["id"] not in seen_ids]
print(f"🆕 Yeni ilan sayısı: {len(new_listings)}")

if not new_listings:
    print("✅ Yeni ilan yok.")
    send_telegram("✅ <b>Leboncoin Tarama Tamamlandı</b>\nYeni ilan bulunamadı.")
    return

# Telegram'a gönder
header = f"🚗 <b>{len(new_listings)} Yeni İlan Bulundu!</b> — {datetime.now().strftime('%d/%m/%Y %H:%M')}\n\n"
send_telegram(header)

for listing in new_listings[:20]:  # Max 20 ilan gönder
    msg = (
        f"📌 <b>{listing['title']}</b>\n"
        f"💶 {listing['price']}\n"
        f"📍 {listing['location']}\n"
        f"🕐 {listing['date']}\n"
        f"🔗 <a href='{listing['link']}'>İlanı Gör</a>"
    )
    try:
        send_telegram(msg)
    except Exception as e:
        print(f"  ❌ Telegram gönderim hatası: {e}")

    seen_ids.add(listing["id"])

save_seen_ids(seen_ids)
print("✅ Tamamlandı, seen_ids güncellendi.")
```

if **name** == “**main**”:
main()
