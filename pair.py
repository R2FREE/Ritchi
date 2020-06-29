import requests
import numpy
from currency_converter import CurrencyConverter


c = CurrencyConverter()

c.convert(1, 'EUR', 'USD')

def CNY2USD():
    return numpy.around(c.convert(1, 'USD', 'CNY'), decimals=0)

def XBT2USD():
    bitcoin_api_url = 'https://api.coinmarketcap.com/v1/ticker/bitcoin/'
    response = requests.get(bitcoin_api_url)
    response_json = response.json()
    type(response_json)  # The API returns a list
    return numpy.around(float(response_json[0]['price_usd']), decimals=0)


if __name__ == '__main__':
    CNY2USD()
    XBT2USD()