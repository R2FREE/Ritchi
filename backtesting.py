from strategy import Printer_strategy
import logging
import pandas
import threading
import datetime
from time import sleep

logging.getLogger(__name__)
logging.basicConfig(filename='backtesting.log', format='%(asctime)s: %(name)s: %(levelname)s: %(message)s', level=logging.INFO)

printer = Printer_strategy()
ohlc = pandas.read_csv('test_data.csv', index_col=0)

def data_feeder(count):
    column = 89 + 25 + 28 + count
    feed = ohlc.iloc[0:column]
    return feed

def thr_nme():
    while 1:
        print(threading.enumerate())
        sleep(1)


while 1:
    for i in range(300):
        data = data_feeder(i)
        logging.info(data.index[-1])
        print(data.index[-1])
        # print(threading.enumerate())
        printer.printer(data)
        sleep(6.5)


