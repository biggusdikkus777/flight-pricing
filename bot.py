import requests
import os
import smtplib
from email.mime.text import MIMEText

# --- CONFIGURATION ---

API_KEY = os.getenv("TRAVELPAYOUTS_API_KEY")
EMAIL_PASSWORD = os.getenv("EMAIL_PASSWORD")  # Gmail app password

FROM_EMAIL = "your_email_here@gmail.com"      # <-- update this
TO_EMAIL = "your_email_here@gmail.com"        # <-- daily summary email
SMS_EMAIL = "8327256861@vtext.com"            # Verizon SMS gateway (free SMS)

ORIGINS = ["IAH", "HOU"]                      # Multiple Houston airports
DESTINATION = "BZE"
DEPART_DATE = "2027-01-30"
RETURN_DATE = "2027-02-07"
THRESHOLD = 500                               # Updated threshold


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
    # Sends both email + SMS
    send_email("Flight Price Alert", message, [TO_EMAIL, SMS_EMAIL])


def send_daily_summary(message):
    # Sends only email
    send_email("Daily Flight Price Summary", message, [TO_EMAIL])


# --- PRICE CHECK FUNCTION (NON-STOP ONLY + SAFE JSON LOADER) ---

def check_price(origin):
    url = "https://api.travelpayouts.com/aviasales/v3/prices"
    params = {
        "origin": origin,
        "destination": DESTINATION,
        "depart_date": DEPART_DATE,
        "return_date": RETURN_DATE,
        "currency": "usd",
        "token": API_KEY
    }

    r = requests.get(url, params=params)

    # Safe JSON loader
    try:
        data = r.json()
    except ValueError:
        print(f"Non-JSON response received for {origin}:")
        print(r.text)
        return None

    offers = data.get("data", [])

    if not offers:
        print(f"No offers returned for {origin}.")
        return None

    # Filter for NON-STOP flights only
    nonstop_offers = [o for o in offers if o.get("number_of_changes", 99) == 0]

    if not nonstop_offers:
        print(f"No NON-STOP flights found for {origin}.")
        return None

    lowest = nonstop_offers[0]["value"]
    return lowest


# --- MAIN LOGIC ---

results = {}

for origin in ORIGINS:
    price = check_price(origin)
    results[origin] = price

print("\n--- Price Results ---")
for origin, price in results.items():
    print(f"{origin}: {price}")

valid_prices = {o: p for o, p in results.items() if p is not None}

# Build daily summary email
summary = "Daily Flight Price Summary\n\n"
summary += f"Route: {ORIGINS} → {DESTINATION}\n"
summary += f"Depart: {DEPART_DATE}\nReturn: {RETURN_DATE}\n\n"

for origin, price in results.items():
    summary += f"{origin}: {price}\n"

if valid_prices:
    best_origin = min(valid_prices, key=valid_prices.get)
    best_price = valid_prices[best_origin]
    summary += f"\nLowest NON-STOP price: ${best_price} from {best_origin}\n"
else:
    summary += "\nNo valid NON-STOP prices found today.\n"

# Send daily summary email
print("Sending daily summary email...")
send_daily_summary(summary)

# Send alert if below threshold
if valid_prices:
    best_origin = min(valid_prices, key=valid_prices.get)
    best_price = valid_prices[best_origin]

    if best_price < THRESHOLD:
        alert_msg = (
            f"🔥 Price Alert!\n\n"
            f"{best_origin} → {DESTINATION}\n"
            f"Depart: {DEPART_DATE}\nReturn: {RETURN_DATE}\n"
            f"NON-STOP price: ${best_price}\n\n"
            f"Below your threshold of ${THRESHOLD}."
        )
        print("Sending email + SMS alert...")
        send_alert(alert_msg)
