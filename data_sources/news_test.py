#GET https://newsapi.org/v2/everything?q=keyword&apiKey=13c0ec61a462423fb8da21ee63a3a2de
"""

from requests.auth import HTTPBasicAuth
import requests

url = 'https://newsapi.org/v2/top-headlines?q=keyword&apiKey=13c0ec61a462423fb8da21ee63a3a2de'
headers = {'Accept': 'application/json'}
auth = HTTPBasicAuth('Authorization', '13c0ec61a462423fb8da21ee63a3a2de')

req = requests.get(url)
#print(req.content)

from newsapi import NewsApiClient

newsapi = NewsApiClient(api_key='13c0ec61a462423fb8da21ee63a3a2de')

top_headlines = newsapi.get_top_headlines(#category='business',
                                          sources="google-news-in",
                                          language='en',
                                          #country='in'
    )
#print(top_headlines)
# /v2/everything
all_articles = newsapi.get_everything(q='india',
                                      sources='bbc-news,the-verge',
                                      domains='bbc.co.uk,techcrunch.com',
                                      from_param='2022-04-01',
                                      to='2022-04-02',
                                      language='en',
                                      sort_by='relevancy',
                                      page=2)

# /v2/top-headlines/sources
sources = newsapi.get_sources( country= 'in')
#print(sources)

import requests

url = "https://latest-mutual-fund-nav.p.rapidapi.com/fetchLatestNAV"

headers = {
	"X-RapidAPI-Host": "latest-mutual-fund-nav.p.rapidapi.com",
	"X-RapidAPI-Key": "069f32cd56msh4ccbd589a35d581p1d233fjsn679aa9e3f89b"
}

response = requests.request("GET", url, headers=headers)

print(response.text)
"""

"""
import requests

url = "https://latest-stock-price.p.rapidapi.com/price"

querystring = {"Indices":"NIFTY 50"}

headers = {
	"X-RapidAPI-Host": "latest-stock-price.p.rapidapi.com",
	"X-RapidAPI-Key": "069f32cd56msh4ccbd589a35d581p1d233fjsn679aa9e3f89b"
}

response = requests.request("GET", url, headers=headers, params=querystring)

print(response.text)
"""
"""
from newsapi import NewsApiClient

newsapi = NewsApiClient(api_key='13c0ec61a462423fb8da21ee63a3a2de')

top_headlines = newsapi.get_top_headlines(#category='business',
                                          sources="Moneycontrol",
                                          language='en',
                                          #country='in'
)
print(top_headlines)
"""
"""
import requests

url = "https://scrapingant.p.rapidapi.com/get"

querystring = {"url":"https://www.nseindia.com/api/option-chain-indices?symbol=NIFTY"}

headers = {
	"X-RapidAPI-Host": "scrapingant.p.rapidapi.com",
	"X-RapidAPI-Key": "069f32cd56msh4ccbd589a35d581p1d233fjsn679aa9e3f89b"
}

response = requests.request("GET", url, headers=headers, params=querystring)

print(response.text)
"""
"""
import requests

url = "https://seeking-alpha.p.rapidapi.com/v2/auto-complete"

querystring = {"query":"apple","type":"people,symbols,pages","size":"5"}

headers = {
	"X-RapidAPI-Host": "seeking-alpha.p.rapidapi.com",
	"X-RapidAPI-Key": "069f32cd56msh4ccbd589a35d581p1d233fjsn679aa9e3f89b"
}

response = requests.request("GET", url, headers=headers, params=querystring)

print(response.text)
"""
"""
from newsapi import NewsApiClient

newsapi = NewsApiClient(api_key='13c0ec61a462423fb8da21ee63a3a2de')
top_headlines_1 = newsapi.get_top_headlines(category='business',
                                          language='en',
                                          country='in'
    )




top_headlines_2 = newsapi.get_top_headlines(#category='business',
                                          sources="google-news-in",
                                          language='en',
                                          #country='in'
    )
print([x['title'] for x in  top_headlines_1['articles']] + [x['title'] for x in  top_headlines_2['articles']] )
"""

key2 = 'pub_63158739be7d5f552ec47c06a8daaf4f445e'

from newsdataapi import NewsDataApiClient

# API key authorization, Initialize the client with your API key

api = NewsDataApiClient(key2)

# You can pass empty or with request parameters {ex. (country = "us")}

data = { "country": "in"}

response = api.news_api(  data )

