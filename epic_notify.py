import requests, json, os
from datetime import datetime, timezone

WEBHOOK = os.environ["DISCORD_WEBHOOK"]
STATE_FILE = "last_games.json"

URL = "https://store-site-backend-static.ak.epicgames.com/freeGamesPromotions?locale=ja&country=JP"

def remaining_time(end_iso):
    if not end_iso:
        return None
    end = datetime.fromisoformat(end_iso.replace("Z", "+00:00"))
    now = datetime.now(timezone.utc)
    diff = end - now
    hours = int(diff.total_seconds() // 3600)
    if hours < 0:
        return None
    if hours < 24:
        return f"残り {hours} 時間"
    return f"残り {hours // 24} 日"


def load_last():
    if os.path.exists(STATE_FILE):
        return json.load(open(STATE_FILE, encoding="utf-8"))
    return []

def save_last(titles):
    json.dump(titles, open(STATE_FILE, "w", encoding="utf-8"), ensure_ascii=False)

data = requests.get(URL).json()
games = data["data"]["Catalog"]["searchStore"]["elements"]

free_games = []

for g in games:
    price_info = g.get("price", {}).get("totalPrice")
    if not price_info:
        continue

    if price_info.get("discountPrice") != 0:
        continue

    # ★ ここに入れる
    print(
        g["title"],
        "discount:", price_info.get("discountPrice"),
        "original:", price_info.get("originalPrice"),
        "validUntil:", price_info.get("priceValidUntil")
    )

    end_date = price_info.get("priceValidUntil")
    if not end_date:
        continue

    remain = remaining_time(end_date)
    if not remain:
        continue


    price = price_info["fmtPrice"]["originalPrice"]
    img = g["keyImages"][0]["url"]
    slug = g.get("productSlug")
    url = f"https://store.epicgames.com/ja/p/{slug}" if slug else ""

    free_games.append({
        "title": g["title"],
        "price": price,
        "remain": remain,
        "url": url,
        "image": img
    })


last = load_last()
current_titles = [g["title"] for g in free_games]

if free_games and current_titles != last:
    embeds = []
    for g in free_games:
        embeds.append({
            "title": g["title"],
            "url": g["url"],
            "description": f"💰 通常 {g['price']}\n⏳ {g['remain']}",
            "thumbnail": {"url": g["image"]},
            "color": 0x00ADEF
        })

    requests.post(WEBHOOK, json={
        "content": "🎁 **Epic Games 無料配布中！**",
        "embeds": embeds
    })

    save_last(current_titles)

