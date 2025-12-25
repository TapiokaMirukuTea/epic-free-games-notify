import requests, json, os
from datetime import datetime, timezone, timedelta

WEBHOOK = os.environ["DISCORD_WEBHOOK"]
STATE_FILE = "last_games.json"

URL = "https://store-site-backend-static.ak.epicgames.com/freeGamesPromotions?locale=ja&country=JP"

JST = timezone(timedelta(hours=9))


# =========================
# 時刻関連
# =========================
def format_end_time(end_iso):
    if not end_iso:
        return None

    end_utc = datetime.fromisoformat(end_iso.replace("Z", "+00:00"))
    end_jst = end_utc.astimezone(JST)

    week = ["月", "火", "水", "木", "金", "土", "日"][end_jst.weekday()]
    return f"{end_jst.month}/{end_jst.day}【{week}】{end_jst.hour}:00まで"


def remaining_time(end_iso):
    if not end_iso:
        return None

    end_utc = datetime.fromisoformat(end_iso.replace("Z", "+00:00"))
    end_jst = end_utc.astimezone(JST)
    now = datetime.now(JST)

    diff = end_jst - now
    hours = int(diff.total_seconds() // 3600)

    if hours < 0:
        return None
    if hours < 24:
        return f"残り {hours} 時間"
    return f"残り {hours // 24} 日"


# =========================
# 価格取得（最重要）
# =========================
def get_original_price(g):
    price = g.get("price", {})
    total = price.get("totalPrice", {})
    fmt = total.get("fmtPrice", {})

    original = fmt.get("originalPrice")

    # 正常に取れた場合
    if original and original not in ["0", "¥0", "$0"]:
        return f"~~{original}~~"

    # 取れなかった場合
    return "通常価格 不明"


# =========================
# 状態保存
# =========================
def load_last():
    if os.path.exists(STATE_FILE):
        with open(STATE_FILE, encoding="utf-8") as f:
            return json.load(f)
    return []


def save_last(titles):
    with open(STATE_FILE, "w", encoding="utf-8") as f:
        json.dump(titles, f, ensure_ascii=False)


# =========================
# メイン処理
# =========================
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

    # 無料配布期間（promotions から取得）
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

    end_text = format_end_time(end_date)

    # 価格
    price_text = get_original_price(g)

    # URL
    slug = g.get("productSlug")
    url = f"https://store.epicgames.com/ja/p/{slug}" if slug else ""

    # 画像（横長優先）
    img = None
    for i in g.get("keyImages", []):
        if i["type"] in ["OfferImageWide", "DieselStoreFrontWide"]:
            img = i["url"]
            break
    if not img and g.get("keyImages"):
        img = g["keyImages"][0]["url"]

    free_games.append({
        "title": g["title"],
        "price": price_text,
        "remain": remain,
        "end": end_text,
        "url": url,
        "image": img
    })


# =========================
# 通知
# =========================
last = load_last()
current_titles = [g["title"] for g in free_games]

if free_games and current_titles != last:
    embeds = []

    for g in free_games:
        embeds.append({
            "title": f"🎮 {g['title']}",
            "url": g["url"],
            "description": (
                f"💰 価格：{g['price']} → **無料**\n"
                f"📅 割引期間：{g['end']}\n"
                f"⏳ {g['remain']}"
            ),
            "image": {"url": g["image"]},
            "color": 0x00ADEF
        })

    requests.post(WEBHOOK, json={
        "content": "🎁 **Epic Games 無料配布中！**",
        "embeds": embeds
    })

    save_last(current_titles)
