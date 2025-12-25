import requests, json, os
from datetime import datetime, timezone

WEBHOOK = os.environ["DISCORD_WEBHOOK"]
STATE_FILE = "last_games.json"

URL = "https://store-site-backend-static.ak.epicgames.com/freeGamesPromotions?locale=ja&country=JP"

# 残り時間表示
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

# 終了日時フォーマット（曜日付き）
def format_end_date(end_iso):
    dt = datetime.fromisoformat(end_iso.replace("Z", "+00:00")).astimezone()
    weeks = ["月", "火", "水", "木", "金", "土", "日"]
    w = weeks[dt.weekday()]
    return f"{dt.month}月{dt.day}日【{w}】{dt.hour:02d}:{dt.minute:02d}"

def load_last():
    if os.path.exists(STATE_FILE):
        return json.load(open(STATE_FILE, encoding="utf-8"))
    return []

def save_last(titles):
    json.dump(titles, open(STATE_FILE, "w", encoding="utf-8"), ensure_ascii=False)

# API取得
data = requests.get(URL).json()
games = data["data"]["Catalog"]["searchStore"]["elements"]

free_games = []

for g in games:
    price_info = g.get("price", {}).get("totalPrice")
    if not price_info:
        continue

    # 無料のみ
    if price_info.get("discountPrice") != 0:
        continue

    # 正しい無料配布期間の取得
    promotions = g.get("promotions")
    if not promotions:
        continue

    offers = promotions.get("promotionalOffers")
    if not offers:
        continue

    offer = offers[0]["promotionalOffers"][0]
    end_date = offer.get("endDate")
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
        "end_date": end_date,
        "url": url,
        "image": img
    })

last = load_last()
current_titles = [g["title"] for g in free_games]

# 変更があった時だけ通知
if free_games and current_titles != last:
    embeds = []

    for g in free_games:
        embeds.append({
            "title": f"🎮 {g['title']}",
            "url": g["url"],
            "description": (
                f"💰 **価　格**：~~{g['price']}~~ → **無料**\n"
                f"⏰ **割引期間**：{format_end_date(g['end_date'])} まで\n"
                f"⌛ {g['remain']}"
            ),
            "image": {   # 大きめバナー画像
                "url": g["image"]
            },
            "color": 0x00ADEF
        })

    requests.post(WEBHOOK, json={
        "content": "🎁 **Epic Games 無料配布中！**",
        "embeds": embeds
    })

    save_last(current_titles)
