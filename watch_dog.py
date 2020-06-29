import datetime
import config
import logging
import numpy
from time import sleep
from bitmex_api import BitMEX_API
from telegram_bot import send_any_msg

price_pre = 0
pnl = 0

bm = BitMEX_API()
logger = logging.getLogger(__name__)

def watch_pnl(cv_wd, q_wd_finish, q_wd_data, q_wd_notify_printer):
    """q_wd_data: get price first, then get trend_pos"""
    global price_pre, pnl

    while 1:
        with cv_wd:
            cv_wd.wait()

        price_entry = q_wd_data.get()
        los = q_wd_data.get()
        logger.info('WATCH_DOG WORKING')
        logger.info('get entry price:' + str(price_entry))
        logger.info('trend: :' + str(los))

        # make sure the price_pre will not be None
        while price_pre == 0:
            startTime = datetime.datetime.utcnow().replace(microsecond=0)
            price_now = bm.fetch_current_price(startTime=str(startTime))
            if price_now:
                price_pre = price_now[0]['price']
            else:
                sleep(5)

        while 1:
            if not q_wd_finish.empty():
                q_wd_finish.get()
                break

            startTime = datetime.datetime.utcnow().replace(microsecond=0)
            price_now = bm.fetch_current_price(startTime=str(startTime))

            if price_now:
                price_now = price_now[0]['price']
                price_pre = price_now
            else:
                price_now = price_pre

            pnl = (price_now - price_entry)/price_entry * los * 20
            pnl = numpy.around(pnl, decimals=4)
            if datetime.datetime.utcnow().minute % 2 == 0:
                logger.info('PNL for now: ' + str(pnl) + ', price: ' + str(price_now))

            # FORCE CLOSE
            if pnl < config.stoploss:
                bm.order_closePosition()
                logger.info('Loss too much, FORCE CLOSE')
                q_wd_finish.put(1)
                send_any_msg('FORCE CLOSE POS')
                q_wd_notify_printer.put(1)

            sleep(5)


if __name__ == '__main__':
    from threading import Thread, Condition
    from queue import Queue
    c = Condition()
    q_f = Queue()
    q_data = Queue()

    Thread(target=watch_pnl, name='watch_pnl', args=(c, q_f, q_data)).start()

    sleep(2)
    with c:
        c.notify()
        q_data.put(8100)
        q_data.put(1)

    sleep(15)
    q_f.put(1)
    print("close")

    sleep(5)
    print("start again")
    with c:
        c.notify()
        q_data.put(8700)
        q_data.put(1)