import requests
import os
import smtplib
from email.mime.text import MIMEText

# --- CONFIGURATION ---

API_KEY = os.getenv("TRAVELPAYOUTS_API_KEY")
EMAIL_PASSWORD = os.getenv("EMAIL_PASSWORD")  # Gmail app password

FROM_EMAIL = "tom.scire@gmail.com"
TO_EMAIL = "tom.scire@gmail.com"
SMS_EMAIL = "8327256861@vtext.com"  # Verizon SMS gateway

ORIGINS = ["IAH", "HOU"]
DESTINATION = "BZE"

DEPART_DATE = "2027-01-30"
RETURN_DATE = "2027-02-07"

THRESHOLD = 500


# --- EMAIL FUNCTIONS ---

def send_email(subject, message, recipients):
    msg = MIMEText(message)
    msg["Subject"] = subject
    msg["From"] = FROM_EMAIL
    msg["To"] = ", ".join(recipients)

    with smtplib.SMTP_SSL("smtp.gmail.com", 465) as server:
        server.login(FROM_EMAIL, EMAIL_PASSWORD)
        server.sendmail(FROM_EMAIL, recipients, msg.as_string())


def send_alert(message):
    send_email("Flight Price Alert", message, [TO_EMAIL, SMS_EMAIL])


def send_daily_summary(message):
    send_email("Daily Flight Price Summary", message, [TO_EMAIL])


# --- ONE-WAY PRICE CHECK (NON-STOP ONLY + SAFE JSON LOADER) ---

def check_one_way(origin, destination, date):
    url = "https://api.travelpayouts.com/aviasales/v3/prices_for_dates"
    params = {
        "origin": origin,
        "destination": destination,
        "depart_date": date,
        "currency": "usd",
        "token": API_KEY
    }

    r = requests.get(url, params=params)

    try:
        data = r.json()
    except ValueError:
        print(f"Non-JSON response for {origin} → {destination}:")
        print(r.text)
        return None

    offers = data.get("data", [])

    if not offers:
        print(f"No offers returned for {origin} → {destination}.")
        return None

    nonstop = [o for o in offers if o.get("number_of_changes", 99) == 0]

    if not nonstop:
        print(f"No NON-STOP flights for {origin} → {destination}.")
        return None

    return nonstop[0]["value"]


# --- MAIN LOGIC ---

results = {}

for origin in ORIGINS:
    outbound = check_one_way(origin, DESTINATION, DEPART_DATE)
    inbound = check_one_way(DESTINATION, origin, RETURN_DATE)

    if outbound is None or inbound is None:
        results[origin] = None
    else:
        results[origin] = outbound + inbound

print("\n--- Round-Trip Price Results (One-Way Combined) ---")
for origin, price in results.items():
    print(f"{origin}: {price}")

valid_prices = {o: p for o, p in results.items() if p is not None}

# Build daily summary email
summary = "Daily Flight Price Summary (One-Way Combined)\n\n"
summary += f"Route: {ORIGINS} → {DESTINATION}\n"
summary += f"Depart: {DEPART_DATE}\nReturn: {RETURN_DATE}\n\n"

for origin, price in results.items():
    summary += f"{origin}: {price}\n"

if valid_prices:
    best_origin = min(valid_prices, key=valid_prices.get)
    best_price = valid_prices[best_origin]
    summary += f"\nLowest NON-STOP round-trip price: ${best_price} from {best_origin}\n"
else:
    summary += "\nNo valid NON-STOP round-trip prices found today.\n"

print("Sending daily summary email...")
send_daily_summary(summary)

# Alerts
if valid_prices:
    best_origin = min(valid_prices, key=valid_prices.get)
    best_price = valid_prices[best_origin]

    if best_price < THRESHOLD:
        alert_msg = (
            f"🔥 Price Alert!\n\n"
            f"{best_origin} → {DESTINATION}\n"
            f"Depart: {DEPART_DATE}\nReturn: {RETURN_DATE}\n"
            f"NON-STOP round-trip price: ${best_price}\n\n"
            f"Below your threshold of ${THRESHOLD}."
        )
        print("Sending email + SMS alert...")
        send_alert(alert_msg)
