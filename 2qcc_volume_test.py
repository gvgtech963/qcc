import time
import requests
import smtplib
from email.message import EmailMessage
from datetime import datetime, timedelta, timezone

API_URL = "https://admin.qccex.com/api/get-exchange-market-trades-app"

PARAMS = {
    "base_coin_id": "28",
    "trade_coin_id": "4",
    "dashboard_type": "dashboard",
    "per_page": "50",
}

HEADERS = {
    "User-Agent": "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 "
                  "(KHTML, like Gecko) Chrome/154.0.0.0 Safari/537.36",
    "Accept": "application/json, text/plain, */*",
    "Referer": "https://qccex.com/",
    "Origin": "https://qccex.com",
}

CHECK_EVERY_SECONDS = 10
WINDOW_MINUTES = 1

# TESTING
VOLUME_ALERT_THRESHOLD = 20

# After testing, change to:
# VOLUME_ALERT_THRESHOLD = 20

SMTP_HOST = "smtp.gmail.com"
SMTP_PORT = 587

EMAIL_FROM = __import__("os").environ.get("QCC_EMAIL_FROM")
EMAIL_PASSWORD = __import__("os").environ.get("QCC_EMAIL_PASSWORD")
EMAIL_TO = __import__("os").environ.get("QCC_EMAIL_TO")


def send_email(volume, buy_volume, sell_volume, price, trade_count, trade_time):

    if not EMAIL_FROM or not EMAIL_PASSWORD or not EMAIL_TO:
        print("ERROR: Gmail environment variables are missing.")
        return

    msg = EmailMessage()

    msg["Subject"] = "🚨 QCC High Volume Alert"
    msg["From"] = EMAIL_FROM
    msg["To"] = EMAIL_TO

    body = f"""
QCC HIGH VOLUME ALERT

1-minute volume: {volume:.6f} QCC

Buy volume:      {buy_volume:.6f} QCC
Sell volume:     {sell_volume:.6f} QCC

Latest price:    {price}
Trades:          {trade_count}

Latest trade:    {trade_time}

Alert threshold: {VOLUME_ALERT_THRESHOLD} QCC
"""

    msg.set_content(body)

    try:
        with smtplib.SMTP(SMTP_HOST, SMTP_PORT, timeout=20) as server:
            server.starttls()
            server.login(EMAIL_FROM, EMAIL_PASSWORD)
            server.send_message(msg)

        print()
        print("📧 EMAIL ALERT SENT SUCCESSFULLY")
        print()

    except Exception as e:
        print()
        print("❌ EMAIL ERROR:", e)
        print()


def get_trades():

    response = requests.get(
        API_URL,
        params=PARAMS,
        headers=HEADERS,
        timeout=15
    )

    response.raise_for_status()

    data = response.json()

    if not data.get("success"):
        raise Exception("QCC API returned success=false")

    return data["data"]["transactions"]


def convert_trade(t):

    return {
        "time": datetime.strptime(
            t["time"],
            "%Y-%m-%d %H:%M:%S"
        ),
        "amount": float(t["amount"]),
        "price": float(t["price"]),
        "total": float(t["total"]),
        "side": t["price_order_type"].lower(),
    }


def analyse(trades):

    global alert_active

    trades = [convert_trade(t) for t in trades]

    if not trades:
        return

    trades.sort(key=lambda x: x["time"])

    # Use the computer's actual current time.
    # This prevents an old transaction from being treated
    # as a new 1-minute volume event.
    current_time = datetime.now(timezone.utc).replace(tzinfo=None)

    start_time = current_time - timedelta(
        minutes=WINDOW_MINUTES
    )

    # Only include trades that actually happened
    # during the current rolling 1-minute window.
    recent = [
        t for t in trades
        if start_time < t["time"] <= current_time
    ]

    volume = sum(
        t["amount"]
        for t in recent
    )

    buy_volume = sum(
        t["amount"]
        for t in recent
        if t["side"] == "buy"
    )

    sell_volume = sum(
        t["amount"]
        for t in recent
        if t["side"] == "sell"
    )

    if recent:
        latest_trade = recent[-1]
        latest_price = latest_trade["price"]
        latest_trade_time = latest_trade["time"]
    else:
        latest_price = trades[-1]["price"]
        latest_trade_time = None

    print("\n" + "=" * 55)
    print("QCC VOLUME MONITOR")
    print("=" * 55)

    print("Current time :", current_time)

    if latest_trade_time:
        print("Latest trade :", latest_trade_time)
    else:
        print("Latest trade : No trade in current 1-minute window")

    print("Latest price :", latest_price)

    print(f"1-min volume : {volume:.6f} QCC")
    print(f"Buy volume   : {buy_volume:.6f} QCC")
    print(f"Sell volume  : {sell_volume:.6f} QCC")
    print("Trades       :", len(recent))

    if volume >= VOLUME_ALERT_THRESHOLD:

        print()
        print("🚨🚨🚨 HIGH VOLUME ALERT 🚨🚨🚨")
        print(f"1-minute volume: {volume:.6f} QCC")
        print(f"Buy volume:      {buy_volume:.6f} QCC")
        print(f"Sell volume:     {sell_volume:.6f} QCC")
        print(f"Price:           {latest_price}")
        print("🚨🚨🚨🚨🚨🚨🚨🚨🚨🚨🚨")

        if not alert_active:

            send_email(
                volume,
                buy_volume,
                sell_volume,
                latest_price,
                len(recent),
                latest_trade_time
            )

            alert_active = True

    else:

        # Once volume falls below the threshold,
        # allow a new alert later.
        alert_active = False

    print("=" * 55)


def main():

    print("==============================================")
    print("QCC 1-MINUTE VOLUME + GMAIL ALERT MONITOR")
    print("==============================================")

    print(
        "Alert threshold:",
        VOLUME_ALERT_THRESHOLD,
        "QCC"
    )

    print(
        "Checking every:",
        CHECK_EVERY_SECONDS,
        "seconds"
    )

    print("Email:", EMAIL_TO)

    print()
    print("Press Ctrl+C to stop.")

    while True:

        try:

            trades = get_trades()
            analyse(trades)

        except requests.RequestException as e:

            print("\nNetwork/API error:", e)

        except Exception as e:

            print("\nError:", e)

        time.sleep(CHECK_EVERY_SECONDS)


alert_active = False


if __name__ == "__main__":
    main()