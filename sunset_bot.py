import os
from datetime import datetime
import requests

LAT = float(os.environ["LAT"])
LON = float(os.environ["LON"])
CHAT_ID = os.environ["TELEGRAM_CHAT_ID"]
BOT_TOKEN = os.environ["TELEGRAM_BOT_TOKEN"]

THRESHOLD = int(os.environ.get("THRESHOLD", "70"))
TIMEZONE = os.environ.get("TIMEZONE", "Europe/Tallinn")

def send_telegram(text: str):
    url = f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage"
    r = requests.post(url, json={
        "chat_id": CHAT_ID,
        "text": text,
        "disable_web_page_preview": True
    }, timeout=30)
    r.raise_for_status()

def score_sunset(total, low, high, visibility):
    score = 0

    if 20 <= total <= 70:
        score += 25
    elif 10 <= total < 20 or 70 < total <= 85:
        score += 10

    if low < 20:
        score += 30
    elif low < 35:
        score += 20
    elif low < 50:
        score += 10

    if 10 <= high <= 50:
        score += 30
    elif 5 <= high < 10 or 50 < high <= 70:
        score += 15

    if visibility >= 15000:
        score += 15
    elif visibility >= 10000:
        score += 10

    return min(100, max(0, score))

def main():
    weather_url = "https://api.open-meteo.com/v1/forecast"
    params = {
        "latitude": LAT,
        "longitude": LON,
        "timezone": TIMEZONE,
        "forecast_days": 7,
        "hourly": "cloud_cover,cloud_cover_low,cloud_cover_high,visibility",
        "daily": "sunset"
    }

    r = requests.get(weather_url, params=params, timeout=30)
    r.raise_for_status()
    data = r.json()

    hourly_time = data["hourly"]["time"]
    total_cloud = data["hourly"]["cloud_cover"]
    low_cloud = data["hourly"]["cloud_cover_low"]
    high_cloud = data["hourly"]["cloud_cover_high"]
    visibility = data["hourly"]["visibility"]
    sunsets = data["daily"]["sunset"]

    hourly_index = {t: i for i, t in enumerate(hourly_time)}

    best = None

    for sunset in sunsets:
        dt = datetime.fromisoformat(sunset)
        rounded = dt.replace(minute=0, second=0, microsecond=0)
        if dt.minute >= 30:
            from datetime import timedelta
            rounded = rounded + timedelta(hours=1)

        key = rounded.strftime("%Y-%m-%dT%H:%M")
        if key not in hourly_index:
            continue

        i = hourly_index[key]
        score = score_sunset(
            total_cloud[i],
            low_cloud[i],
            high_cloud[i],
            visibility[i]
        )

        item = {
            "date": sunset[:10],
            "sunset": sunset,
            "score": score,
            "total": total_cloud[i],
            "low": low_cloud[i],
            "high": high_cloud[i],
            "visibility": visibility[i],
        }

        if best is None or item["score"] > best["score"]:
            best = item

    if best and best["score"] >= THRESHOLD:
        msg = (
            f"Sunset alert\n"
            f"Date: {best['date']}\n"
            f"Sunset: {best['sunset']}\n"
            f"Score: {best['score']}/100\n"
            f"Total cloud: {best['total']}%\n"
            f"Low cloud: {best['low']}%\n"
            f"High cloud: {best['high']}%\n"
            f"Visibility: {best['visibility']} m"
        )
        send_telegram(msg)

if __name__ == "__main__":
    main()
