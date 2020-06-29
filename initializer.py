from threading import Thread, Event, Condition
from time import sleep
from queue import Queue
from pandas import DataFrame
import config
import datetime
import logging
from bitmex_api import BitMEX_API

logger = logging.getLogger(__name__)

convert_rule = {'open': 'first',
                'high': 'max',
                'low': 'min',
                'close': 'last'}

N = config.N_min

def init_klines_Nmin():
    """init step 1"""
    bm = BitMEX_API(testing=config.testing, api_key=config.API_KEY, api_secret=config.API_SECRET)
    num_bars = config.EMA_slow + 75
    trading_period = str(N) + 'm'
    startTime = datetime.datetime.utcnow().replace(microsecond=0, second=0) - datetime.timedelta(minutes=num_bars * 5)
    ohlc_history_Nmin = bm.fetchOHLC(binSize=trading_period, count=num_bars, startTime=startTime)
    return ohlc_history_Nmin

def avoid_bad_timing():
    current_minute = datetime.datetime.utcnow().minute
    current_second = datetime.datetime.utcnow().second
    if ((current_minute+1) % 10 == 0) or ((current_minute+1) % 5 == 0):
        if current_second > 30:
            sleep(45)

def init_klines_1min(q_ws, q_loop, q_keeper, cv, evt_init_1min, evt_first_Nmin, evt_loop):
    """init step 1, !!!attention if the start time just pass the :00 and :05 will put an empty DataFrame"""
    # because the bug in ws, the sleep time may be less than real, so sleep more in here
    evt_init_1min.wait()
    sleep(5)

    bm = BitMEX_API(testing=config.testing, api_key=config.API_KEY, api_secret=config.API_SECRET)
    startTime = datetime.datetime.utcnow().replace(microsecond=0, second=0)
    num_bars = startTime.minute % 5 + 1
    startTime = startTime - datetime.timedelta(minutes=(num_bars - 1))

    sleep(15)
    ohlc_history_1min = bm.fetchOHLC(binSize='1m', count=num_bars, startTime=startTime)
    q_ws.put(ohlc_history_1min)

    logger.info('******init 1-min klines******   DONE')
    logger.debug(ohlc_history_1min)

    Thread(target=init_first_Nmin, name='init_first_Nmin', args=(q_ws, q_loop, q_keeper, cv, evt_first_Nmin, evt_loop,)).start()

    evt_first_Nmin.set()


def init_first_Nmin(q_ws, q_loop, q_keeper, cv, evt_first_Nmin, evt_loop):
    """init step 1"""
    evt_first_Nmin.wait()

    df_1min = q_ws.get()
    row = df_1min.shape[0]

    if row == N:

        logger.info('******init N-min klines******   DONE')
        logger.debug(df_1min)

        q_loop.put(df_1min)

        # start convert 5min OHLC
        Thread(target=convert_1_to_N, name='convert_1_to_N', args=(q_loop, q_keeper, cv, evt_loop,)).start()
        Thread(target=data_provider, name='data_provider', args=(q_ws, q_loop, cv, evt_loop,)).start()
        evt_loop.set()

    else:
        while row < N:
            df_temp = q_ws.get()
            df_1min = df_1min.append(df_temp)
            row = row + 1

        logger.info('******init N-min klines******   DONE')
        logger.debug(df_1min)

        q_loop.put(df_1min)

        # start convert 5min OHLC
        Thread(target=convert_1_to_N, name='convert_1_to_N', args=(q_loop, q_keeper, cv, evt_loop,)).start()
        Thread(target=data_provider, name='data_provider', args=(q_ws, q_loop, cv, evt_loop,)).start()
        evt_loop.set()


def data_provider(q_ws, q_loop, cv, evt_loop):
    """
    run forever,
    provide N 1-min kline for convert N-min kline in loop
    """
    evt_loop.wait()

    df_1min = DataFrame()
    sleep(30)
    while 1:
        df_temp = q_ws.get()
        df_1min = df_1min.append(df_temp)
        if df_1min.shape[0] == N:
            q_loop.put(df_1min)
            df_1min = DataFrame()
            with cv:
                cv.notify()


def convert_1_to_N(q_loop, q_keeper, cv, evt_loop):
    """
    init step 2,
    run forever,
    after init, this function will work for loop,
    and will be notified when new N 1-min kline generated
    """
    evt_loop.wait()

    while 1:
        with cv:
            data = q_loop.get()
            resample_sign = str(N)+'Min'
            df_Nmin_lastest = data.resample(resample_sign).agg(convert_rule)

            logger.info('******convert N 1-min to N-min kline******')
            logger.debug(df_Nmin_lastest)

            q_keeper.put(df_Nmin_lastest)
            cv.wait()


def data_keeper(q_keeper, q_printer, cv_printer):
    """run forever"""
    df_Nmin = init_klines_Nmin()

    while 1:
        df_temp = q_keeper.get()
        df_Nmin = df_Nmin.append(df_temp)
        # notify the printer to work
        q_printer.put(df_Nmin)
        with cv_printer:
            cv_printer.notify()

        logger.info('******append the last N-min kline******')
        logger.info(str(df_Nmin.index[-1]) + '   close price: ' + str(df_Nmin['close'][-1]))
        # print(df_Nmin)

        # delete the first 45, when the df is too large
        if df_Nmin.shape[0] > 130:
            df_Nmin = df_Nmin.iloc[45:]
            logger.info('******delete some old kline******')


if __name__ == "__main__":
    # avoid_bad_timing()
    print(type(str(N) + 'm'))