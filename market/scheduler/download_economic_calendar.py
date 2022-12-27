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
def get_eco_data():
    converted = pytz.timezone('Asia/Kolkata')
    original = pytz.timezone('US/Eastern')

    engine = get_db_engine()
    news_day = date.today() + timedelta(days=1)
    sun_offset = (news_day.weekday() + 1) % 7
    sunday = news_day - timedelta(days=sun_offset)
    saturday = sunday + timedelta(days=6)
    url_yf = 'https://finance.yahoo.com/calendar/economic?from=' + sunday.strftime('%Y-%m-%d') + '&to=' + saturday.strftime('%Y-%m-%d') + '&day=' + news_day.strftime('%Y-%m-%d')
    print(url_yf)
    headers = {"User-Agent": "Mozilla/5.0 (X11; U; Linux i686) Gecko/20071127 Firefox/2.0.0.11"}
    response = requests.get(url_yf, headers=headers)
    soup = BeautifulSoup(response.text, 'html.parser')
    rows = soup.find_all("table", {"class": "W(100%)"})[0].find_all('tr')
    records = []
    for row in rows[1:]:
        rec = {}
        rec['event'] = row.find_all('td')[0].get_text().strip()
        rec['country'] = row.find_all('td')[1].get_text().strip()
        rec['time'] = row.find_all('td')[2].get_text().strip()
        tm = rec['time'].split('EST')[0]

        hr = int(tm.split('AM')[0].split(":")[0]) if 'AM' in tm else int(tm.split('PM')[0].split(":")[0])
        hr = 0 if hr == 12 else hr
        hr = hr if 'AM' in tm else hr + 12
        min = int(tm.split('AM')[0].split(":")[1] if 'AM' in tm else tm.split('PM')[0].split(":")[1])
        print(hr,min)
        dt_tmp = datetime.combine(news_day,time(hr, min))
        conv_time = original.localize(dt_tmp).astimezone(converted)
        rec['time'] = conv_time.strftime('%Y-%m-%d %H:%M')
        rec['period'] = row.find_all('td')[3].get_text().strip()
        rec['actual'] = row.find_all('td')[4].get_text().strip()
        rec['exp'] = row.find_all('td')[5].get_text().strip()
        rec['prev'] = row.find_all('td')[6].get_text().strip()
        rec['rev_from'] = row.find_all('td')[7].get_text().strip()
        records.append(rec)
    df = pd.DataFrame(records)
    df['news_date'] = news_day
    conn = engine.connect()
    df.to_sql('economic_calendar', conn, if_exists="append", index=False, dtype={'news_date': DATE})
    conn.close()
    return df[df.country.isin(['IN', 'US'])]

def email(df):
    print(df)
    if df.shape[0] > 0:
        sender_address = 'insightfunnel01@gmail.com'
        receiver_address = "basant@essenvia.com"
        sender_pass = 'xafwofkjrfchitpl'
        message = MIMEMultipart()
        message['From'] = sender_address
        message['To'] = receiver_address
        message['Subject'] = "Economic calendar for " + df['news_date'].to_list()[0].strftime('%Y-%m-%d')
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
    df = get_eco_data()
    email(df)
