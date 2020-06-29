from requests.auth import AuthBase
import pandas
import config
import json
import hashlib
import hmac
import requests
import urllib.parse
import datetime
import time
import numpy

pandas.set_option('expand_frame_repr', False)
pandas.set_option('display.max_row', 1000)

REAL_BASE = 'https://www.bitmex.com/api/v1'
TEST_BASE = 'https://testnet.bitmex.com/api/v1'
UTC_FORMAT = "%Y-%m-%dT%H:%M:%S.%fZ"
MIN_FORMAT = "%Y-%m-%d %H:%M"  # for fetch OHLC data without sencond and ms

"""
ERROR 400: Parameter Error

ERROR 401: Unauthorized

ERROR 403: Access Denied

ERROR 404: Not Found
"""


class APIKeyAuthWithExpires(AuthBase):
    """Attaches API Key Authentication to the given Request object. This implementation uses `expires`."""

    def __init__(self, apiKey, apiSecret):
        """Init with Key & Secret."""
        self.apiKey = apiKey
        self.apiSecret = apiSecret

    def __call__(self, r):
        """
        Called when forming a request - generates api key headers. This call uses `expires` instead of nonce.
        This way it will not collide with other processes using the same API Key if requests arrive out of order.
        For more details, see https://www.bitmex.com/app/apiKeys
        """
        # modify and return the request
        # 5s grace period in case of clock skew
        expires = int(round(time.time()) + 13)
        r.headers['api-expires'] = str(expires)
        r.headers['api-key'] = self.apiKey
        r.headers['api-signature'] = self.generate_signature(self.apiSecret, r.method, r.url, expires, r.body or '')
        return r

    @staticmethod
    def generate_signature(secret, verb, url, nonce, data):
        """Generate a request signature compatible with BitMEX."""
        # Parse the url so we can remove the base and extract just the path.
        parsedURL = urllib.parse.urlparse(url)
        path = parsedURL.path
        if parsedURL.query:
            path = path + '?' + parsedURL.query

        message = verb + path + str(nonce) + data

        signature = hmac.new(
            bytes(secret, 'utf8'), bytes(message, 'utf8'), digestmod=hashlib.sha256).hexdigest()
        return signature


class BitMEX_API(object):
    """
    testing=False means using the real trading
    """

    def __init__(
            self,
            testing=config.testing,
            api_key=config.API_KEY,
            api_secret=config.API_SECRET):
        self.BASE_URL = REAL_BASE if not testing else TEST_BASE
        self.API_KEY = api_key,
        self.API_SECRET = api_secret

    def authenticator(self):
        auth = APIKeyAuthWithExpires(self.API_KEY, self.API_SECRET)
        auth.apiKey = str(auth.apiKey[0])
        return auth

    # """private"""
    # balance
    def execution(self, proxies=None):
        """get the wallet balance of yesterday and the day before yesterday"""
        auth = self.authenticator()
        url = self.BASE_URL + '/execution'
        payload = {
            'symbol': 'XBTUSD',
            'columns': (

            ),
            'count': 1,
        }

        r = requests.get(url, params=payload, auth=auth, proxies=proxies)

        wallet_info = json.loads(r.text)

        return wallet_info

    # wallet
    def user_wallet(self, proxies=None):
        """get the wallet balance of yesterday and the day before yesterday"""
        auth = self.authenticator()
        url = self.BASE_URL + '/user/wallet'
        payload = {
            'currency': 'XBt'
        }

        r = requests.get(url, params=payload, auth=auth, proxies=proxies)

        wallet_info = json.loads(r.text)

        return wallet_info

    def user_wallet_summary(self, proxies=None):
        """get the wallet balance"""
        auth = self.authenticator()
        url = self.BASE_URL + '/user/walletSummary'
        payload = {
            'currency': 'XBt'
        }

        r = requests.get(url, params=payload, auth=auth, proxies=proxies)

        wallet_info = json.loads(r.text)

        return wallet_info

    def user_wallet_balance(self, proxies=None):
        """get the wallet balance"""
        auth = self.authenticator()
        url = self.BASE_URL + '/user/walletHistory'
        payload = {
            'currency': 'XBt',
            'count': 1,
        }

        r = requests.get(url, params=payload, auth=auth, proxies=proxies)

        # from the walletHistory get the current wallet balance in XBT form
        wallet_balance = json.loads(r.text)[0]['walletBalance'] * 1e-8
        balance = numpy.around(wallet_balance, decimals=8)
        return balance

    # order
    def order_get(self, proxies=None):
        """to get the open orders info --- get"""
        auth = self.authenticator()
        url = self.BASE_URL + '/order'
        payload = {
            'symbol': 'XBTUSD',
            'columns': ('side',
                        'ordType',
                        'ordStatus',
                        'price',
                        'leavesQty'
                        ),
            'count': 1,
            'reverse': 'true'
        }

        r = requests.get(url, params=payload, auth=auth, proxies=proxies)

        order_info = json.loads(r.text)

        return order_info

    def order_limit_post(self, price, Qty, proxies=None):
        """
        creat new limit order --- post
        the negative Qty means short
        """
        auth = self.authenticator()
        url = self.BASE_URL + '/order'
        payload = {
            'symbol': 'XBTUSD',
            'price': price,
            'orderQty': Qty,  # Qty must be int and negative Qty means short
            'ordType': 'Limit'
        }

        r = requests.post(url, params=payload, auth=auth, proxies=proxies)

        return r

    def order_market_post(self, Qty, proxies=None):
        """creat new market order --- post"""
        auth = self.authenticator()
        url = self.BASE_URL + '/order'
        payload = {
            'symbol': 'XBTUSD',
            'orderQty': Qty,  # Qty must be int and negative Qty means short
            'ordType': 'Market',
        }

        r = requests.post(url, params=payload, auth=auth, proxies=proxies)

        return r

    def order_cancel_all(self, proxies=None):
        """cancel all of the order --- delete"""
        auth = self.authenticator()
        url = self.BASE_URL + '/order/all'
        payload = {
            'symbol': 'XBTUSD',
        }

        r = requests.delete(url, params=payload, auth=auth, proxies=proxies)

        return r

    def order_cancelAllAfter(self, proxies=None, timeout=15_000):
        """
        cancel all of the order after a timeout --- post
        will cancel all order if not be took after XXX ms
        """
        auth = self.authenticator()

        url = self.BASE_URL + '/order/cancelAllAfter'
        payload = {
            'timeout': timeout  # in ms
        }

        r = requests.post(url, params=payload, auth=auth, proxies=proxies)

        return r

    def order_closePosition(self, proxies=None, limit_price=None):
        """
        close position --- post
        if the limit_price was None means close position by market order
        """
        auth = self.authenticator()
        url = self.BASE_URL + '/order/closePosition'
        payload = {
            'symbol': 'XBTUSD',
            'price': limit_price
        }

        r = requests.post(url, params=payload, auth=auth, proxies=proxies)

        return r

    # position
    def position_get(self, proxies=None):
        """get position"""
        auth = self.authenticator()
        url = self.BASE_URL + '/position'
        payload = {
            'symbol': 'XBTUSD',
            'columns': (
                        'leverage',
                        'realisedPnl',  # 24h total pnl reset at UTC 12:00
                        'isOpen',   # get a Pos or not for now
                        'execQty',  # the Qty for the Pos now
                        'avgEntryPrice',    # execPrice
                        'prevRealisedPnl',  # the pnl of last pos
                        # 'unrealisedPnlPcnt'
                        ),
            'count': 2,
        }

        r = requests.get(url, params=payload, auth=auth, proxies=proxies)

        order_info = json.loads(r.text)

        return order_info[0]

    # """public"""
    def fetchOHLC(self, binSize, count, startTime, reverse='false', proxies=None):
        """
        for 1min candle:there is nothing need to be noticed
        for 5min candle:the startTime's minuter par between 1-4 will return the X5,
                        the startTime's minuter part between 6-9 will return the X0,
                        the startTime's minuter part is X0 and X5 will return exactly the time's candle data

        :binSize: 1m,5m,1h,1d
        :count: the number of bars to fetch
        :startTime: then time begin to fetch
        :reverse: reverse or not
        :proxies: need the proxies or not
        """
        global num_min
        url = self.BASE_URL + '/trade/bucketed'

        if binSize == '5m':
            num_min = 5
        elif binSize == '1m':
            num_min = 1

        startTime = str(startTime + datetime.timedelta(minutes=num_min))
        payload = {
            'binSize': binSize,  # 1m,5m,1h,1d
            'partial': 'false',
            'symbol': 'XBTUSD',
            'count': count,
            'reverse': reverse,
            'startTime': startTime,
        }
        r = requests.get(url, params=payload, proxies=proxies)
        candle = json.loads(r.text)

        OHLC_data = pandas.DataFrame(candle, columns=['timestamp', 'open', 'high', 'low', 'close'])  # deleted 'volume'
        OHLC_data['timestamp'] = pandas.to_datetime(OHLC_data['timestamp'], format=UTC_FORMAT) - pandas.Timedelta(
            num_min, unit='min')
        OHLC_data = OHLC_data.set_index(['timestamp'])

        return OHLC_data

    def fetch_current_price(self, startTime, proxies=None):
        """startTime format: 2019-10-01 16:10:00"""
        url = self.BASE_URL + '/trade'
        payload = {
            'symbol': 'XBTUSD',
            # 'columns': 'price',
            'count': 1,
            'startTime': startTime,
        }

        r = requests.get(url, params=payload, proxies=proxies)

        # price = json.loads(r.text)[0]['price']
        price = json.loads(r.text)

        return price

    # tool
    def time_format(self):
        """"""
        pass


if __name__ == '__main__':
    import datetime
    import time
    import numpy

    # proxy = {
    #     'http': 'http://127.0.0.1:1080',
    #     'https': 'http://127.0.0.1:1080'
    # }
    # proxy = None

    bm = BitMEX_API()
    #
    # startTime = datetime.datetime.strptime('2019-10-21 00:15:00', "%Y-%m-%d %H:%M:%S")
    # ohlc = bm.fetchOHLC(binSize='5m', count=500, startTime=startTime)
    # print(ohlc)
    # ohlc.to_csv('test_data.csv')

    # bm.order_market_post(Qty=-1)
    # bm.order_market_post(Qty=1)

    # print(bm.user_wallet_balance())
    print(bm.fetch_current_price('2019-10-01 16:10:00'))

    pos = bm.position_get()
    print(pos)

    order = bm.order_get()[0]
    print(order)

    Qty = bm.user_wallet_balance()
    print(Qty)

    # time_fuck = datetime.datetime.utcnow().replace(microsecond=0, second=0)
    # print(5 % 5)

    # startTime = datetime.datetime.utcnow().replace(microsecond=0, second=0)
    # print(bm.fetch_current_price(str(startTime)))

    # a = -0.15111111
    # a = numpy.around(a*100, decimals=2)
    # print(a)
    # wallet = str(a) + '%'
    # print(wallet)
