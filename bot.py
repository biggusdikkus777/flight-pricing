import os
import json
import smtplib
from email.mime.text import MIMEText
from playwright.sync_api import sync_playwright

# --- CONFIGURATION ---

EMAIL_PASSWORD = os.getenv("EMAIL_PASSWORD")  # Gmail app password

FROM_EMAIL = "tom.scire@gmail.com"
TO_EMAIL = "tom.scire@gmail.com"
SMS_EMAIL = "8327256861@vtext.com"  # Verizon SMS gateway

THRESHOLD = 500

IAH_URL = "https://www.google.com/travel/flights/search?tfs=CBwQAhoeEgoyMDI3LTAxLTMwagcIARIDSUFIcgcIARIDQlpFGh4SCjIwMjctMDItMDdqBwgBEgNCWkVyBwgBEgNJQUhAAUgBcAGCAQsI____________AZgBAQ&hl=en-US&gl=US"
HOU_URL = "https://www.google.com/travel/flights/search?tfs=CBwQAhoeEgoyMDI3LTAxLTMwagcIARIDSE9VcgcIARIDQlpFGh4SCjIwMjctMDItMDdqBwgBEgNCWkVyBwgBEgNIT1VAAUgBcAGCAQsI____________AZgBAQ&tfu=EgYIABAAGAA&hl=en-US&gl=US"


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


# --- GOOGLE FLIGHTS JSON INTERCEPT ---

def get_nonstop_price(url):
    from playwright.sync_api import sync_playwright

    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        page = browser.new_page()

        # Block heavy resources to speed up Google Flights
        page.route("**/*", lambda route, request: (
            route.abort()
            if request.resource_type in ["image", "media", "font", "stylesheet"]
            else route.continue_()
        ))

        page.goto(url, wait_until="domcontentloaded")

        # Wait for flight cards to appear
        try:
            page.wait_for_selector('div[role="listitem"]', timeout=15000)
        except Exception:
            browser.close()
            return None

        cards = page.query_selector_all('div[role="listitem"]')
        prices = []

        for card in cards:
            # Check if this card contains "Nonstop"
            if not card.query_selector(':has-text("Nonstop")'):
                continue

            # Extract price inside this card
            price_el = card.query_selector(':has-text("$")')
            if not price_el:
                continue

            text = price_el.inner_text().strip().replace(",", "")
            # Find the first $### in the text
            import re
            match = re.search(r"\$(\d+)", text)
            if match:
                prices.append(int(match.group(1)))

        browser.close()

        if not prices:
            return None

        return min(prices)
    return min(prices)


# --- MAIN LOGIC ---

results = {}

iah_price = get_nonstop_price(IAH_URL)
hou_price = get_nonstop_price(HOU_URL)

results["IAH"] = iah_price
results["HOU"] = hou_price

print("\n--- Non-Stop Round-Trip Price Results (Google Flights JSON) ---")
for origin, price in results.items():
    print(f"{origin}: {price}")

valid_prices = {o: p for o, p in results.items() if p is not None}

summary = "Daily Flight Price Summary (Google Flights Non-Stop)\n\n"
summary += "Route: IAH/HOU → BZE\n"
summary += "Depart: 2027-01-30\nReturn: 2027-02-07\n\n"

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

if valid_prices:
    best_origin = min(valid_prices, key=valid_prices.get)
    best_price = valid_prices[best_origin]

    if best_price < THRESHOLD:
        alert_msg = (
            f"🔥 Price Alert!\n\n"
            f"{best_origin} → BZE\n"
            f"Depart: 2027-01-30\nReturn: 2027-02-07\n"
            f"NON-STOP round-trip price: ${best_price}\n\n"
            f"Below your threshold of ${THRESHOLD}."
        )
        print("Sending email + SMS alert...")
        send_alert(alert_msg)
