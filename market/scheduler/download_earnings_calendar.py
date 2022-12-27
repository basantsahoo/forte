from datetime import date, timedelta, datetime, time
from bs4 import BeautifulSoup
from db.db_engine import get_db_engine
from sqlalchemy.types import DATE
import requests
import json
import pandas as pd
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from email.mime.base import MIMEBase
from email import encoders
import smtplib
import pytz
def get_earning_data():
    engine = get_db_engine()
    url_yf = ' https://www.moneycontrol.com/earnings-widget?indexId=N&dur=TO&startDate=&endDate=&page=1&deviceType=web&classic=true'
    headers = {"User-Agent": "Mozilla/5.0 (X11; U; Linux i686) Gecko/20071127 Firefox/2.0.0.11"}
    response = requests.get(url_yf, headers=headers)
    #print(response.text)
    soup = BeautifulSoup(response.text, 'html.parser')
    rows = soup.find_all("table")[0].find_all('tr')
    records = []
    for row in rows[1:]:
        tds = row.find_all('td')
        rec = {}
        rec['date'] = tds[1].get_text().strip()
        rec['company'] = tds[2].get_text().strip()
        rec['result_type'] = tds[3].get_text().strip()
        rec['ltp'] = tds[4].get_text().strip()
        rec['time'] = tds[6].get_text().strip()
        records.append(rec)
    df = pd.DataFrame(records)
    conn = engine.connect()
    df.to_sql('earning_calendar', conn, if_exists="append", index=False, dtype={'news_date': DATE})
    conn.close()
    return df

def email(df):
    if df.shape[0] > 0:
        sender_address = 'insightfunnel01@gmail.com'
        receiver_address = "basant@essenvia.com"
        sender_pass = 'xafwofkjrfchitpl'
        message = MIMEMultipart()
        message['From'] = sender_address
        message['To'] = receiver_address
        message['Subject'] = "Earnings calendar for " + df['date'].to_list()[0]
        html = """\
        <html>
          <head></head>
          <body>
            {0}
          </body>
        </html>
        """.format(df.to_html())
        message.attach(MIMEText(html, 'html'))
        session = smtplib.SMTP('smtp.gmail.com', 587)  # use gmail with port
        session.starttls()  # enable security
        session.login(sender_address, sender_pass)
        session.sendmail(sender_address, receiver_address, message.as_string())
        session.quit()

def run():
    df = get_earning_data()
    email(df)
