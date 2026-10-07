import time
import requests
import smtplib
from email.message import EmailMessage
from datetime import datetime, timedelta, timezone
import os
from dotenv import load_dotenv

load_dotenv()


# ============================================================
# QCC API
# ============================================================

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


# ============================================================
# MONITOR SETTINGS
# ============================================================

# API is checked every 10 seconds
CHECK_EVERY_SECONDS = 10

# Each interval is exactly 3 minutes
INTERVAL_MINUTES = 3

# Send email if interval volume is >= 20 QCC
VOLUME_ALERT_THRESHOLD = 20


# ============================================================
# GMAIL SETTINGS
# ============================================================

SMTP_HOST = "smtp.gmail.com"
SMTP_PORT = 587

EMAIL_FROM = os.environ.get("QCC_EMAIL_FROM")
EMAIL_PASSWORD = os.environ.get("QCC_EMAIL_PASSWORD")
EMAIL_TO = os.environ.get("QCC_EMAIL_TO")


# ============================================================
# GET CURRENT UTC TIME
# ============================================================

def get_current_utc():

    return datetime.now(timezone.utc).replace(tzinfo=None)


# ============================================================
# SEND EMAIL
# ============================================================

def send_email(
    volume,
    buy_volume,
    sell_volume,
    price,
    trade_count,
    interval_start,
    interval_end
):

    if not EMAIL_FROM or not EMAIL_PASSWORD or not EMAIL_TO:

        print()
        print("❌ ERROR: Gmail environment variables are missing.")
        print()

        return False


    msg = EmailMessage()

    msg["Subject"] = "🚨 QCC High Volume Alert"

    msg["From"] = EMAIL_FROM

    msg["To"] = EMAIL_TO


    body = f"""
QCC HIGH VOLUME ALERT

3-minute interval volume: {volume:.6f} QCC

Buy volume:      {buy_volume:.6f} QCC
Sell volume:     {sell_volume:.6f} QCC

Latest price:    {price}

Trades:          {trade_count}

Interval start:  {interval_start}
Interval end:    {interval_end}

Alert threshold: {VOLUME_ALERT_THRESHOLD} QCC
"""


    msg.set_content(body)


    try:

        print()
        print("📧 Sending Gmail alert...")


        with smtplib.SMTP(
            SMTP_HOST,
            SMTP_PORT,
            timeout=20
        ) as server:

            server.starttls()

            server.login(
                EMAIL_FROM,
                EMAIL_PASSWORD
            )

            server.send_message(msg)


        print("✅ EMAIL ALERT SENT SUCCESSFULLY")
        print()

        return True


    except Exception as e:

        print()
        print("❌ EMAIL ERROR:", repr(e))
        print()

        return False


# ============================================================
# GET TRADES FROM QCC
# ============================================================

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

        raise Exception(
            "QCC API returned success=false"
        )


    return data["data"]["transactions"]


# ============================================================
# CONVERT API TRADE
# ============================================================

def convert_trade(t):

    return {

        "time": datetime.strptime(
            t["time"],
            "%Y-%m-%d %H:%M:%S"
        ),

        "amount": float(
            t["amount"]
        ),

        "price": float(
            t["price"]
        ),

        "total": float(
            t["total"]
        ),

        "side": t[
            "price_order_type"
        ].lower(),
    }


# ============================================================
# MAIN MONITOR
# ============================================================

def main():

    print(
        "=============================================="
    )

    print(
        "QCC FIXED 3-MINUTE VOLUME MONITOR"
    )

    print(
        "=============================================="
    )

    print(
        "Alert threshold:",
        VOLUME_ALERT_THRESHOLD,
        "QCC"
    )

    print(
        "Interval:",
        INTERVAL_MINUTES,
        "minutes"
    )

    print(
        "Checking every:",
        CHECK_EVERY_SECONDS,
        "seconds"
    )

    print(
        "Email:",
        EMAIL_TO
    )

    print()


    # ========================================================
    # IMPORTANT:
    # The moment the script starts becomes the beginning
    # of the FIRST interval.
    # ========================================================

    interval_start = get_current_utc()

    interval_end = (
        interval_start
        + timedelta(
            minutes=INTERVAL_MINUTES
        )
    )


    print(
        "Monitoring started."
    )

    print()

    print(
        "First interval:"
    )

    print(
        interval_start,
        "→",
        interval_end
    )

    print()

    print(
        "Trades before the script started will be ignored."
    )

    print(
        "Volume resets after every 3-minute interval."
    )

    print()

    print(
        "Press Ctrl+C to stop."
    )

    print()


    # ========================================================
    # MAIN LOOP
    # ========================================================

    while True:

        try:

            current_time = get_current_utc()


            # =================================================
            # CHECK WHETHER CURRENT INTERVAL HAS ENDED
            # =================================================

            if current_time >= interval_end:

                print()
                print(
                    "=============================================="
                )

                print(
                    "⏱️ 3-MINUTE INTERVAL FINISHED"
                )

                print(
                    "=============================================="
                )

                print(
                    "Interval:",
                    interval_start,
                    "→",
                    interval_end
                )


                # =============================================
                # FETCH TRADES FOR COMPLETED INTERVAL
                # =============================================

                trades = get_trades()


                converted_trades = [

                    convert_trade(t)

                    for t in trades

                ]


                # =============================================
                # ONLY TRADES INSIDE THIS INTERVAL
                # =============================================

                interval_trades = [

                    t

                    for t in converted_trades

                    if interval_start
                    <= t["time"]
                    < interval_end

                ]


                # =============================================
                # CALCULATE VOLUME
                # =============================================

                volume = sum(

                    t["amount"]

                    for t in interval_trades

                )


                buy_volume = sum(

                    t["amount"]

                    for t in interval_trades

                    if t["side"] == "buy"

                )


                sell_volume = sum(

                    t["amount"]

                    for t in interval_trades

                    if t["side"] == "sell"

                )


                trade_count = len(
                    interval_trades
                )


                # =============================================
                # LATEST PRICE
                # =============================================

                if interval_trades:

                    interval_trades.sort(
                        key=lambda x: x["time"]
                    )

                    latest_trade = (
                        interval_trades[-1]
                    )

                    latest_price = (
                        latest_trade["price"]
                    )

                    latest_trade_time = (
                        latest_trade["time"]
                    )

                else:

                    latest_price = 0

                    latest_trade_time = None


                # =============================================
                # SHOW INTERVAL RESULT
                # =============================================

                print()

                print(
                    f"Interval volume: "
                    f"{volume:.6f} QCC"
                )

                print(
                    f"Buy volume:      "
                    f"{buy_volume:.6f} QCC"
                )

                print(
                    f"Sell volume:     "
                    f"{sell_volume:.6f} QCC"
                )

                print(
                    f"Trades:          "
                    f"{trade_count}"
                )

                print(
                    f"Latest price:    "
                    f"{latest_price}"
                )

                print(
                    f"Latest trade:    "
                    f"{latest_trade_time}"
                )


                # =============================================
                # ALERT
                # =============================================

                if volume >= VOLUME_ALERT_THRESHOLD:

                    print()

                    print(
                        "🚨🚨🚨 HIGH VOLUME ALERT 🚨🚨🚨"
                    )

                    print(
                        f"3-minute volume = "
                        f"{volume:.6f} QCC"
                    )

                    print(
                        "Threshold =",
                        VOLUME_ALERT_THRESHOLD,
                        "QCC"
                    )

                    print(
                        "🚨🚨🚨🚨🚨🚨🚨🚨🚨🚨🚨"
                    )


                    send_email(

                        volume,

                        buy_volume,

                        sell_volume,

                        latest_price,

                        trade_count,

                        interval_start,

                        interval_end

                    )


                else:

                    print()

                    print(
                        "✅ Volume below threshold."
                    )

                    print(
                        f"{volume:.6f} QCC "
                        f"< "
                        f"{VOLUME_ALERT_THRESHOLD} QCC"
                    )


                # =================================================
                # IMPORTANT:
                #
                # OLD INTERVAL IS NOW COMPLETELY FINISHED.
                #
                # We do NOT carry its volume forward.
                # We do NOT use a rolling window.
                #
                # Start a completely NEW interval.
                # =================================================

                interval_start = interval_end

                interval_end = (

                    interval_start

                    + timedelta(
                        minutes=INTERVAL_MINUTES
                    )

                )


                print()

                print(
                    "🔄 VOLUME COUNT RESET"
                )

                print(
                    "New interval:"
                )

                print(
                    interval_start,
                    "→",
                    interval_end
                )

                print()


                # Continue immediately
                # without sleeping unnecessarily.

                continue


            # =================================================
            # CURRENT INTERVAL IS STILL RUNNING
            # =================================================

            else:

                remaining = (
                    interval_end
                    - current_time
                )


                remaining_seconds = int(
                    remaining.total_seconds()
                )


                # ---------------------------------------------
                # Fetch current trades
                # ---------------------------------------------

                trades = get_trades()


                converted_trades = [

                    convert_trade(t)

                    for t in trades

                ]


                # ---------------------------------------------
                # Count ONLY trades that happened
                # during the CURRENT interval.
                # ---------------------------------------------

                interval_trades = [

                    t

                    for t in converted_trades

                    if interval_start
                    <= t["time"]
                    <= current_time

                ]


                current_volume = sum(

                    t["amount"]

                    for t in interval_trades

                )


                # ---------------------------------------------
                # Display current progress
                # ---------------------------------------------

                print(

                    f"\rCurrent interval volume: "
                    f"{current_volume:.6f} QCC"
                    f" | Trades: {len(interval_trades)}"
                    f" | Remaining: "
                    f"{remaining_seconds}s",

                    end="",

                    flush=True

                )


        except requests.RequestException as e:

            print()

            print(
                "❌ Network/API error:",
                e
            )


        except Exception as e:

            print()

            print(
                "❌ Error:",
                e
            )


        # =====================================================
        # WAIT BEFORE NEXT API CHECK
        # =====================================================

        time.sleep(
            CHECK_EVERY_SECONDS
        )


# ============================================================
# START PROGRAM
# ============================================================

if __name__ == "__main__":

    main()