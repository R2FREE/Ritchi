import talib
import numpy
from time import sleep
import logging
import datetime
from bitmex_api import BitMEX_API
from watch_dog import watch_pnl
from telebot_aio import *
from threading import Thread, Condition
from queue import Queue
# import config
# import pandas

TIME_FORMAT = "%Y-%m-%d %H:%M:%S"

timedelta_10min = datetime.timedelta(minutes=10)
logger = logging.getLogger(__name__)

Pos = 0  # own a position or not
Segmt = 0
Trend = 0  # for place order 1 or -1 and means long or short
Trend_pos = 0  # record the tend when place a order
trend_segmt = 0  # the trend for segmt place order
skip_cross = 0  # if skip the narrow gap, will set 1
Qty_order = 0
float_time = 0
float_price = 0
float_count = 1
wallet_balance = BitMEX_API().user_wallet_balance()  # update wallet_balance
time_work = 0  # the time used for how long should rest
price = 0

backtesting = config.backtesting

c_watch = Condition()  # for wake up watching
q_watch = Queue()  # for close the watching, cause by close pos or force sell
q_wd_data = Queue()  # for pass the los(long or short)
q_wd_notify_printer = Queue()  # to notify printer that need to update Pos and Trend after force sell

Thread(target=watch_pnl, name='watch_pnl', args=(c_watch, q_watch, q_wd_data, q_wd_notify_printer)).start()

def init_params():
    global Pos, Segmt, Trend, Trend_pos, trend_segmt, skip_cross, Qty_order, float_count, float_time, float_price, wallet_balance
    Pos = 0  # own a position or not
    Segmt = 0
    Trend = 0  # for place order 1 or -1 and means long or short
    Trend_pos = 0  # record the tend when place a order
    trend_segmt = 0  # the trend for segmt place order
    skip_cross = 0  # if skip the narrow gap, will set 1
    Qty_order = 0
    float_time = 0
    float_price = 0
    float_count = 1
    wallet_balance = BitMEX_API().user_wallet_balance()  # update wallet_balance

def WMA(ohlc_wma, timeperiod: int):
    return talib.WMA(ohlc_wma['close'].values, timeperiod=timeperiod)


def EMA(ohlc_ema, timeperiod: int):
    """
    timeperiod: Need larger than 80 when the timeperiod is 8, in this way EMA will be stable
    """
    return talib.EMA(ohlc_ema['close'].values, timeperiod=timeperiod)


def trend_judger(cross_result):
    if cross_result == 'long':
        return 1
    elif cross_result == 'short':
        return -1
    elif cross_result == 'wma crossed below' or cross_result == 'wma crossed over':
        return 0
    elif cross_result == 'wait':
        return None


class Printer_strategy(object):
    def __init__(self):
        self.ema_fast_window = config.EMA_fast
        self.ema_fast_v2_window = config.EMA_fast_v2
        self.ema_slow_window = config.EMA_slow

        self.wma_fast_window = config.WMA_fast
        self.wma_fast_v2_window = config.WMA_fast_v2
        self.wma_slow_window = config.WMA_slow
        """need to change when real trade"""
        self.bm = BitMEX_API()

    def checkPos(self):
        global Pos, Trend, Trend_pos, Qty_order, wallet_balance, float_time, float_price, float_count
        if str(self.check_position('isOpen')) == 'True':
            Pos = 1
            currentQty = self.check_position('currentQty')
            Qty_order = abs(currentQty)
            Trend = 1 if currentQty > 0 else -1
            Trend_pos = Trend

            time_base = datetime.datetime.utcnow().replace(microsecond=0, second=0)
            time_delta = 5 - time_base.minute % 5
            float_time = time_base + datetime.timedelta(minutes=time_delta)
            float_price = self.check_position('avgEntryPrice')
            float_count = int(abs(self.check_position('currentQty')) / int(
                float_price * wallet_balance * 20 * config.percent * config.float_percent))
            self.price_entry = self.check_position('avgEntryPrice')
            self.wake_dog(los=Trend)
            logger.info('Already got a Position, ' + 'Trend is ' + str(Trend))
            logger.info('float_time: ' + str(float_time) + ',' + 'float_price: ' + str(
                float_price) + ',' + 'float_count: ' + str(float_count))
            send_any_msg(msg='Already Got A Position')
        else:
            logger.info('No Position')

    def get_Qty(self):
        global wallet_balance
        wallet_balance = self.bm.user_wallet_balance()
        return wallet_balance

    # **********-----order related-----**********
    def place_market_order(self, los, action):
        """los is 1 or -1, means long or short. 'place' means open order"""
        global wallet_balance, Qty_order, float_count
        if action == 'place':
            Qty = wallet_balance
            Qty_market = int(self.close_price * Qty * 20 * config.percent * config.float_percent) * los
            logger.info('Market: place order')

            if float_count == 1:
                Qty_order = abs(Qty_market)
                # print(Qty_order)
            elif float_count > 1:
                Qty_order = Qty_order + abs(Qty_market)
                # print(Qty_order)

        elif action == 'close':
            Qty_market = Qty_order * los
            logger.info('Market: close order')

        self.bm.order_market_post(Qty=Qty_market)

    def place_limit_order(self, los, action):
        """los is 1 or -1, mean long or short"""
        global wallet_balance, Qty_order, float_count
        if action == 'place':
            Qty = wallet_balance
            self.Qty_limit = int(self.close_price * Qty * 20 * config.percent * config.float_percent) * los

            if float_count == 1:
                Qty_order = abs(self.Qty_limit)
                # print(Qty_order)
            elif float_count > 1:
                Qty_order = Qty_order + abs(self.Qty_limit)
                # print(Qty_order)

        elif action == 'close':
            self.Qty_limit = Qty_order * los
            logger.info('Limit: close order')

        if los == 1:
            order_price = self.close_price - 0.5
        elif los == -1:
            order_price = self.close_price + 0.5

        self.bm.order_limit_post(price=order_price, Qty=self.Qty_limit)

    def check_position(self, columns):
        """depend on what columns is given to return the message"""
        info = self.bm.position_get()
        return info[columns]

    def place_order(self, los, action):
        """
        try limit order first,then market order. when the order if filled set Pos
        action:'place' means using the wallet_balance, 'close' means using the Qty_order
        """
        global Pos, Trend_pos, float_count, Qty_order, wallet_balance
        # try limit order first
        logger.info('los: ' + str(los) + ', ' + 'action: ' + str(action))
        self.place_limit_order(los, action)

        self.bm.order_cancelAllAfter(timeout=config.wait_time)
        logger.info('begin waiting limit taken')

        sleep(config.wait_time / 1000 + 1)
        # make sure the Pos is empty
        ordStatus = self.bm.order_get()[0]['ordStatus']
        if ordStatus == 'Canceled' or ordStatus == 'Rejected':
            logger.info('limit order failed, place market order')
            if action == 'place':
                Qty_order = Qty_order - abs(self.Qty_limit)
            elif action == 'close':
                pass
            # print(Qty_order)
            self.place_market_order(los, action)
            sleep(0.5)

        # notify watch dog
        while self.bm.order_get()[0]['leavesQty'] != 0:
            sleep(1)

        if action == 'place':
            Pos = 1
            # set float time is not here, cause float place order will use this def here

        elif action == 'close':
            Pos = 0
            q_watch.put(1)
            float_count = 1
            # update the wallet_balance
            sleep(1)
            # every time close position will update the wallet
            wallet_balance = self.get_Qty()

    def force_close(self, limit_price=None):
        """close by market price if the price is not given"""
        self.bm.order_closePosition(limit_price=limit_price)

    def float_check(self):
        global float_count, float_time, timedelta_10min, backtesting
        avg_price = (self.close_price_penult + self.close_price_antepenult)/2

        if (self.close_price - avg_price) * Trend_pos > 0:
            logger.info('Continue place cause got float profit')
            # this float_count must be set before place order
            float_count = float_count + 1
            self.place_order(los=Trend_pos, action='place')
            self.send_float_message()

            float_time = datetime.datetime.strptime(self.ohlc_time, TIME_FORMAT) + timedelta_10min if \
                backtesting else self.ohlc_time + timedelta_10min
            logger.info('float_time: ' + str(float_time))

            # close WATCH DOG and wake again
            q_watch.put(1)
            sleep(0.5)
            self.wake_dog(los=Trend_pos)
        else:
            float_time = datetime.datetime.strptime(self.ohlc_time, TIME_FORMAT) + timedelta_10min if \
                backtesting else self.ohlc_time + timedelta_10min
            logger.info('float_time: ' + str(float_time))

    # **********-----detect def & indicator related-----**********
    def detect_cross(self, df_ohlc):
        """
        df_ohlc: need more than 80 klines if the timeperiod is 8
        position: None means no position, True means long, False means short
        v2 is faster than the fast one, which has a smaller window
        """
        global Pos

        # get the indicator value
        wma_fast = WMA(df_ohlc, self.wma_fast_window)
        wma_fast_v2 = WMA(df_ohlc, self.wma_fast_v2_window)
        wma_slow = WMA(df_ohlc, self.wma_slow_window)

        ema_fast = EMA(df_ohlc, self.ema_fast_window)
        ema_fast_v2 = EMA(df_ohlc, self.ema_fast_v2_window)
        ema_slow = EMA(df_ohlc, self.ema_slow_window)

        # get the close price & time for other def
        self.close_price = df_ohlc['close'][-1]
        self.open_price = df_ohlc['open'][-1]
        self.ohlc_time = df_ohlc.index[-1]
        self.close_price_penult = df_ohlc['close'][-2]
        self.open_price_penult = df_ohlc['open'][-2]
        self.close_price_antepenult = df_ohlc['close'][-3]
        # self.ohlc_time = datetime.datetime.strptime(df_ohlc.index[-1], "%Y-%m-%d %H:%M:%S")

        # get the new indicator of each
        # wma
        wma_fast_1 = numpy.around(wma_fast[-1], decimals=4)
        wma_fast_2 = numpy.around(wma_fast[-2], decimals=4)
        wma_fast_3 = numpy.around(wma_fast[-3], decimals=4)
        self.wma_fast = wma_fast_1

        wma_fast_v2_1 = numpy.around(wma_fast_v2[-1], decimals=4)
        wma_fast_v2_2 = numpy.around(wma_fast_v2[-2], decimals=4)
        wma_fast_v2_3 = numpy.around(wma_fast_v2[-3], decimals=4)

        wma_slow_1 = numpy.around(wma_slow[-1], decimals=4)
        wma_slow_2 = numpy.around(wma_slow[-2], decimals=4)
        wma_slow_3 = numpy.around(wma_slow[-3], decimals=4)
        self.wma_slow = wma_slow_1

        # ema
        ema_fast_1 = numpy.around(ema_fast[-1], decimals=4)
        ema_fast_2 = numpy.around(ema_fast[-2], decimals=4)

        ema_fast_v2_1 = numpy.around(ema_fast_v2[-1], decimals=4)
        ema_fast_v2_2 = numpy.around(ema_fast_v2[-2], decimals=4)

        ema_slow_1 = numpy.around(ema_slow[-1], decimals=4)
        ema_slow_2 = numpy.around(ema_slow[-2], decimals=4)

        # wma cross
        # cross over: means long
        # cross at the latest kline
        self.wma_cross_over_latest = wma_fast_1 > wma_slow_1 and wma_fast_2 < wma_slow_2
        self.wma_cross_over_v2_latest = wma_fast_v2_1 > wma_slow_1 and wma_fast_v2_2 < wma_slow_2
        # cross at the second from latest kline
        self.wma_cross_over_second = wma_fast_2 > wma_slow_2 and wma_fast_3 < wma_slow_3
        self.wma_cross_over_v2_second = wma_fast_v2_2 > wma_slow_2 and wma_fast_v2_3 < wma_slow_3

        # cross below: means short
        # cross at the latest kline
        self.wma_cross_below_latest = wma_fast_1 < wma_slow_1 and wma_fast_2 > wma_slow_2
        self.wma_cross_below_v2_latest = wma_fast_v2_1 < wma_slow_1 and wma_fast_v2_2 > wma_slow_2
        # cross at the second from latest kline
        self.wma_cross_below_second = wma_fast_2 < wma_slow_2 and wma_fast_3 > wma_slow_3
        self.wma_cross_below_v2_second = wma_fast_v2_2 < wma_slow_2 and wma_fast_v2_3 > wma_slow_3

        # ema cross
        # cross over
        # cross at the latest kline
        self.ema_cross_over_latest = ema_fast_1 > ema_slow_1 and ema_fast_2 < ema_slow_2
        self.ema_cross_over_v2_latest = ema_fast_v2_1 > ema_slow_1 and ema_fast_v2_2 < ema_slow_2

        # cross below
        # cross at the latest kline
        self.ema_cross_below_latest = ema_fast_1 < ema_slow_1 and ema_fast_2 > ema_slow_2
        self.ema_cross_below_v2_latest = ema_fast_v2_1 < ema_slow_1 and ema_fast_v2_2 > ema_slow_2

        if Pos == 0:
            # long signal for Pos==0
            if (self.wma_cross_over_latest or self.wma_cross_over_v2_latest) and (
                    self.ema_cross_over_latest or self.ema_cross_over_v2_latest):
                return "long"
            elif (self.wma_cross_over_second or self.wma_cross_over_v2_second) and (
                    self.ema_cross_over_latest or self.ema_cross_over_v2_latest):
                return "long"
            # short signal for Pos==0
            elif (self.wma_cross_below_latest or self.wma_cross_below_v2_latest) and (
                    self.ema_cross_below_latest or self.ema_cross_below_v2_latest):
                return "short"
            elif (self.wma_cross_below_second or self.wma_cross_below_v2_second) and (
                    self.ema_cross_below_latest or self.ema_cross_below_v2_latest):
                return "short"
            else:
                return "wait"
        elif Pos == 1:
            # long signal for Pos==1
            if self.wma_cross_over_latest and (self.ema_cross_over_latest or self.ema_cross_over_v2_latest):
                return "long"
            elif self.wma_cross_over_second and (self.ema_cross_over_latest or self.ema_cross_over_v2_latest):
                return "long"
            # short signal for Pos==1
            elif self.wma_cross_below_latest and (self.ema_cross_below_latest or self.ema_cross_below_v2_latest):
                return "short"
            elif self.wma_cross_below_second and (self.ema_cross_below_latest or self.ema_cross_below_v2_latest):
                return "short"
            # close or segmt signal
            elif self.wma_cross_over_latest:
                return "wma crossed over"
            elif self.wma_cross_below_latest:
                return "wma crossed below"
            # cancel segmt signal
            elif (self.ema_cross_below_latest or self.ema_cross_over_latest) or (
                    self.ema_cross_below_v2_latest or self.ema_cross_over_v2_latest):
                return "ema cross only"
            else:
                return "wait"

    def detect_seesaw(self):
        """The left hand is cross over and right hand is cross below, or exchanged"""
        pass

    def detect_needle(self):
        pass

    def detect_jns(self):
        """detect jump and slump"""
        if abs((self.close_price - self.open_price) / self.open_price) > config.jnp_tv or \
                abs((self.close_price_penult - self.open_price_penult) / self.open_price) > config.jnp_tv:
            logger.info('SKIP JNS')
            return False
        else:
            return True

    def detect_narrow_cross(self):
        gap = abs(self.wma_fast - self.wma_slow)
        gap_ratio = gap / self.close_price
        if gap_ratio <= config.sng_tv:
            return True
        elif gap_ratio > config.sng_tv:
            return False

    def skip_narrow_cross(self):
        global wallet_balance, Segmt, Trend_pos, Pos, skip_cross

        narrow_gap = self.detect_narrow_cross()
        logger.info('Meet the skip_narrow_cross condition')

        if (narrow_gap is False) and (self.cross_trend != Trend_pos):
            """when the gap is not narrow, close position"""
            logger.info('close position (cause the cross)')

            self.place_order(los=(-Trend_pos), action='close')

            sleep(0.5)
            # get new wallet_balance and set Segmt 1
            while str(self.check_position('isOpen')) == 'True':
                sleep(0.5)
                pass

            # prepare for the Segmt profit
            Segmt = 1

            # reset skip_cross
            skip_cross = 0

            # telebot send pnl message
            self.send_pnl_message()

            # Trend_pos = 1 if Trend == 1 else -1

        elif narrow_gap:
            skip_cross = 1
            logger.info('skip this cross, because the gap is narrow')

    # **********-----send message & watch def-----**********
    def send_pnl_message(self):
        """telebot send pnl message of last position"""
        global wallet_balance, time_work
        Qty = wallet_balance * 1e8  # to get XBt
        pnl = self.check_position('prevRealisedPnl')
        Qty_pre = Qty - pnl
        self.pnl_rate = numpy.around(pnl / Qty_pre * 100, decimals=2)
        pnl_rate_str = str(self.pnl_rate) + '%'
        # fetch the exit price
        close_price = self.bm.order_get()[0]['price']
        # send the pnl message by telebot
        send_pnl(pnl=pnl_rate_str, price=str(close_price))
        if 0.2 <= self.pnl_rate <= 0.45:
            time_work = self.ohlc_time + datetime.timedelta(minutes=config.rest_time)

    def send_place_message(self, signal):
        pos_info = self.bm.position_get()
        currentQty = str(pos_info['currentQty'])
        self.price_entry = numpy.around(pos_info['avgEntryPrice'], decimals=2)
        avgPrice = str(self.price_entry)
        if signal == 1:
            send_place_order(trend="LONG", execQty=currentQty, avgPrice=avgPrice)
            logger.info('place a' + '***LONG***' + 'order')
        elif signal == -1:
            send_place_order(trend="SHORT", execQty=currentQty, avgPrice=avgPrice)
            logger.info('place a' + '***SHORT***' + 'order')

    def send_float_message(self):
        global Trend_pos
        pos_info = self.bm.position_get()
        currentQty = str(pos_info['currentQty'])
        self.price_entry = numpy.around(pos_info['avgEntryPrice'], decimals=2)
        avgPrice = str(self.price_entry)

        if Trend_pos == 1:
            send_float_order("LONG", currentQty, avgPrice)
            logger.info('Continue' + '***LONG***')
        elif Trend_pos == -1:
            send_float_order("SHORT", currentQty, avgPrice)
            logger.info('Continue ' + '***SHORT***')

    def wake_dog(self, los):
        with c_watch:
            c_watch.notify()
        q_wd_data.put(self.price_entry)  # put price first
        q_wd_data.put(los)  # then, put the los

    # THE REAL LOGICAL PART
    def printer(self, df_ohlc):
        global wallet_balance, Trend, Trend_pos, trend_segmt, Pos, Segmt, skip_cross, float_time, float_count, backtesting
        self.cross_result = self.detect_cross(df_ohlc)

        if not q_wd_notify_printer.empty():
            q_wd_notify_printer.get()
            init_params()
            send_any_msg(msg="RESET ALL PARAMS\nSTART PRINTING AGAIN")
            logger.info("Have been throng FORCE SELL, reset all params!")

        # Pos = 1 if self.check_position('isOpen') else 0
        logger.info('cross result is ' + '***' + str.upper(self.cross_result) + '***')
        Trend = trend_judger(self.cross_result)
        logger.info('Trend is: ' + str(Trend))
        logger.info('Trend_pos is: ' + str(Trend_pos))

        # if Segmt ==1, need to confirm the trend. cross_trend is used to avoid accident close
        self.cross_trend = 0
        trend_segmt = 0  # reset first
        if self.cross_result == "wma crossed below" or self.cross_result == "short":
            self.cross_trend = -1
            if Segmt == 1 or skip_cross == 1:
                trend_segmt = -1
        elif self.cross_result == "wma crossed over" or self.cross_result == "long":
            self.cross_trend = 1
            if Segmt == 1 or skip_cross == 1:
                trend_segmt = 1
        logger.info("trend_segmt is: " + str(trend_segmt))

        # if double cross and the trend is same reset the skip_cross
        if trend_segmt == Trend_pos and skip_cross == 1:
            logger.info("Trend is still same, set the skip_cross = 0 ")
            skip_cross = 0

        # # if ema cross is true, stop Segmt situation
        # if self.cross_result == 'ema cross only' and Pos == 0:
        #     Segmt = 0

        # When No Pos
        if Pos == 0:
            logger.info('Meet the Pos==0 condition')
            if (Trend == 1 or Trend == -1) and self.detect_jns:
                self.place_order(los=Trend, action='place')

                # telebot send message
                sleep(1)
                self.send_place_message(signal=Trend)

                # set float_time for multiple place order and plus some min
                float_time = datetime.datetime.strptime(self.ohlc_time, TIME_FORMAT) + timedelta_10min if \
                    backtesting else self.ohlc_time + timedelta_10min
                logger.info('float_time: ' + str(float_time))

                float_count = 1

                # set Trend_pos for the Pos==1 case
                Trend_pos = Trend

                # wake up watch dog
                self.wake_dog(los=Trend_pos)

            # When no Pos but Segmt is 1
            elif Trend == 0 and Segmt == 1 and self.detect_jns:
                logger.info('Meet the Segmt condition')

                # get the pnl of last position
                make_profit = self.check_position('prevRealisedPnl')
                if make_profit > 0:
                    Trend = trend_segmt
                    if self.detect_jns:
                        self.place_order(los=Trend, action='place')

                        self.send_place_message(signal=Trend)
                        Segmt = 0
                        Trend_pos = Trend

                        # set float_time for multiple place order
                        float_time = datetime.datetime.strptime(self.ohlc_time, TIME_FORMAT) + timedelta_10min if \
                            backtesting else self.ohlc_time + timedelta_10min
                        logger.info('float_time: ' + str(float_time))

                        # wake up watch dog
                        self.wake_dog(los=Trend_pos)

        # When got a Pos
        elif Pos == 1:
            logger.info('Meet the Pos==1 condition')
            df_ohlc_time = datetime.datetime.strptime(self.ohlc_time, TIME_FORMAT) if \
                backtesting else self.ohlc_time

            if (Trend == 1 or Trend == -1) and (Trend_pos != Trend):
                logger.info('Meet the close and immediately open condition')

                # close first! try close by limit order, using the opposite Trend
                self.place_order(los=Trend, action='close')

                # make sure the position is closed
                while str(self.check_position('isOpen')) == 'True':
                    sleep(0.5)
                    pass

                # telebot send pnl message of last position
                self.send_pnl_message()

                if self.detect_jns:
                    # place new order, after the close
                    self.place_order(los=Trend, action='place')
                    logger.info('closed pos, and place a new order')
                    # telebot send place order message
                    sleep(0.5)
                    self.send_place_message(signal=Trend)

                    # update the Trend_pos
                    float_count = 1
                    Trend_pos = Trend

                    skip_cross = 0

                    # kill watch dog and wake up watch dog
                    q_watch.put(1)
                    sleep(0.5)
                    self.wake_dog(los=Trend_pos)

                    # set float_time for multiple place order
                    float_time = datetime.datetime.strptime(self.ohlc_time, TIME_FORMAT) + timedelta_10min if \
                        backtesting else self.ohlc_time + timedelta_10min
                    logger.info('float_time: ' + str(float_time))
                else:
                    Pos = 0

            # Trend == 0 means only wma crossed, will set skip_cross 1 if narrow gap
            elif Trend == 0 and skip_cross == 0:
                logger.info('Meet the Pos ==1 and wma cross, skip or close?')
                if skip_cross == 1:
                    skip_cross = 0
                else:
                    self.skip_narrow_cross()

            # When the cross is past, the the gap may grow in the opposite side
            elif Trend is None and skip_cross == 1:
                logger.info('Meet already skip cross, if close?')
                self.skip_narrow_cross()

            # Float place
            elif df_ohlc_time >= float_time and float_count < 4:
                logger.info('Meet the Float condition')
                self.float_check()

    def printer_with_rest(self, df_ohlc):
        global time_work
        if time_work == 0:
            time_work = df_ohlc.index[-1]
        if df_ohlc.index[-1] >= time_work:
            self.printer(df_ohlc)


if __name__ == '__main__':
    printer = Printer_strategy()
    # ohlc = pandas.read_csv('test_data_0.csv', index_col=0)
    # print(ohlc)
    # signal = strategy.detect_cross(ohlc)
    # print(signal)
    # print(ohlc['close'][-1])
    # printer.printer(df_ohlc=ohlc)

    # printer.checkPos()
    # print(Pos, Trend, Trend_pos, Qty_order, wallet_balance)

    printer.send_place_message(signal=1)
