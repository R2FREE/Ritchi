import threading
from telebot_aio import *
from initializer import *
import logging
import time
import os
import strategy
from bitmex_ws import *
from strategy import Printer_strategy
from threading import Event, Condition
from queue import Queue

logger = logging.getLogger(__name__)
logging.Formatter.converter = time.gmtime
logging.basicConfig(filename='printer.log', format='%(asctime)s: %(name)s: %(levelname)s: %(message)s',
                    level=logging.DEBUG)

printer = Printer_strategy()

cv = Condition()
cv_printer = Condition()
q_ws = Queue()
q_loop = Queue()
q_keeper = Queue()
q_printer = Queue()
evt_init_1min = Event()
evt_first_5min = Event()
evt_loop = Event()


def algorithm(q_p, cv_p):
    while 1:
        with cv_p:
            cv_p.wait()
            printer.printer_with_rest(df_ohlc=q_p.get())


def start_printer():
    send_start()

    avoid_bad_timing()

    printer.checkPos()
    logger.info('Pos:' + str(strategy.Pos))

    Thread(target=run_ws, name='ws', args=(q_ws, evt_init_1min), daemon=True).start()
    Thread(target=data_keeper, name='data_keeper', args=(q_keeper, q_printer, cv_printer), daemon=True).start()
    Thread(target=init_klines_1min, name='init_klines_1min',
           args=(q_ws, q_loop, q_keeper, cv, evt_init_1min, evt_first_5min, evt_loop)).start()
    Thread(target=algorithm, name='printer', args=(q_printer, cv_printer), daemon=True).start()


start_printer()

