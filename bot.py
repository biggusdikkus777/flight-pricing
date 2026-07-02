import os
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


# --- GOOGLE FLIGHTS SCRAPING (NON-STOP ONLY) ---

def extract_price_from_page(page):
    # This selector targets price text in the main results list.
    # You may need to tweak it if Google changes layout.
    elements = page.query_selector_all('div[aria-label*="Nonstop"] span[aria-label^="$"]')
    prices = []

    for el in elements:
        text = el.get_attribute("aria-label") or el.inner_text()
        if not text:
            continue
        text = text.replace(",", "").strip()
        if text.startswith("$"):
            try:
                prices.append(int(text[1:]))
            except ValueError:
                continue

    if not prices:
        return None

    return min(prices)


def get_nonstop_price(url):
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        page = browser.new_page()
        page.goto(url, wait_until="networkidle")

        price = extract_price_from_page(page)

        browser.close()

    return price


# --- MAIN LOGIC ---

results = {}

iah_price = get_nonstop_price(IAH_URL)
hou_price = get_nonstop_price(HOU_URL)

results["IAH"] = iah_price
results["HOU"] = hou_price

print("\n--- Non-Stop Round-Trip Price Results (Google Flights) ---")
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
