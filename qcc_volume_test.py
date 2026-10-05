import time
import requests
from datetime import datetime, timedelta

API_URL = "https://admin.qccex.com/api/get-exchange-market-trades-app"

PARAMS = {
    "base_coin_id": "28",
    "trade_coin_id": "4",
    "dashboard_type": "dashboard",
    "per_page": "50",
}

CHECK_EVERY_SECONDS = 10
WINDOW_MINUTES = 5


def get_trades():
    headers = {
        "User-Agent": "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/154.0.0.0 Safari/537.36",
        "Accept": "application/json, text/plain, */*",
        "Referer": "https://qccex.com/",
        "Origin": "https://qccex.com",
    }
    response = requests.get(
        API_URL,
        params=PARAMS,
        headers=headers,
        timeout=15
    )
    response.raise_for_status()

    data = response.json()

    if not data.get("success"):
        raise Exception("QCC API returned success=false")

    return data["data"]["transactions"]


def convert_trade(t):
    return {
        "time": datetime.strptime(t["time"], "%Y-%m-%d %H:%M:%S"),
        "amount": float(t["amount"]),
        "price": float(t["price"]),
        "total": float(t["total"]),
        "side": t["price_order_type"].lower(),
    }


def analyse(trades):
    trades = [convert_trade(t) for t in trades]
    trades.sort(key=lambda x: x["time"])

    if not trades:
        return

    newest_time = trades[-1]["time"]
    start_time = newest_time - timedelta(minutes=WINDOW_MINUTES)

    recent = [
        t for t in trades
        if start_time < t["time"] <= newest_time
    ]

    volume = sum(t["amount"] for t in recent)
    buy_volume = sum(
        t["amount"] for t in recent if t["side"] == "buy"
    )
    sell_volume = sum(
        t["amount"] for t in recent if t["side"] == "sell"
    )

    print("\n" + "=" * 55)
    print("QCC VOLUME MONITOR")
    print("=" * 55)
    print("Latest trade :", newest_time)
    print("Latest price :", trades[-1]["price"])
    print(f"5-min volume : {volume:.6f} QCC")
    print(f"Buy volume   : {buy_volume:.6f} QCC")
    print(f"Sell volume  : {sell_volume:.6f} QCC")
    print("Trades       :", len(recent))
    print("=" * 55)


def main():
    print("QCC monitor started.")
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


if __name__ == "__main__":
    main()
