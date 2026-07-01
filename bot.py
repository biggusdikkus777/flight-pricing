import requests
import smtplib
from email.mime.text import MIMEText

API_KEY = "YOUR_IGNAV_API_KEY"

ORIGIN = "IAH"
DEST = "BOS"
DATE = "2024-09-12"
THRESHOLD = 220

EMAIL_FROM = "your_email@gmail.com"
EMAIL_TO = "your_email@gmail.com"
EMAIL_PASSWORD = "your_app_password"  # Gmail app password

def check_price():
    url = "https://api.ignav.com/flights/search"
    params = {
        "origin": ORIGIN,
        "destination": DEST,
        "departureDate": DATE,
        "adults": 1
    }
    headers = {"Authorization": f"Bearer {API_KEY}"}

    r = requests.get(url, params=params, headers=headers)
    data = r.json()

    lowest = data["results"][0]["price"]
    return lowest

def send_email(price):
    msg = MIMEText(f"🔥 Flight price dropped to ${price}!")
    msg["Subject"] = "Flight Price Alert"
    msg["From"] = EMAIL_FROM
    msg["To"] = EMAIL_TO

    with smtplib.SMTP_SSL("smtp.gmail.com", 465) as server:
        server.login(EMAIL_FROM, EMAIL_PASSWORD)
        server.sendmail(EMAIL_FROM, EMAIL_TO, msg.as_string())

price = check_price()

if price < THRESHOLD:
    send_email(price)
    print("Alert sent!")
else:
    print(f"Current price ${price} is above threshold.")
