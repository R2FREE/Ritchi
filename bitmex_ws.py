from bitmex_websocket import BitMEXWebsocket
from initializer import *
import pandas
import datetime


pandas.set_option('expand_frame_repr', False)
pandas.set_option('display.max_row', 1000)

endpoint_real = "https://www.bitmex.com/api/v1"
endpoint_test = "https://testnet.bitmex.com/api/v1"

UTC_FORMAT = "%Y-%m-%dT%H:%M:%S.%fZ"

timedelta_1min = datetime.timedelta(minutes=1)


def setup_logger():
    # Prints logger info to terminal
    logger_setup = logging.getLogger()
    logger_setup.setLevel(logging.INFO)  # Change this to DEBUG if you want a lot more info
    ch = logging.StreamHandler()
    # create formatter
    formatter = logging.Formatter(" %(message)s")
    # add formatter to ch
    ch.setFormatter(formatter)
    logger_setup.addHandler(ch)
    return logger_setup


def run_ws(queue, evt_init_1min, testing=config.testing):
    setup_logger()
    endpoint = endpoint_real if not testing else endpoint_test

    ws = BitMEXWebsocket(
        endpoint=endpoint, symbol="XBTUSD",
        # api_key='',
        # api_secret='')
    )

    df_tick_null = pandas.DataFrame(columns=['timestamp', 'price'])

    df_tick = df_tick_null

    time_now = datetime.datetime.strptime(ws.get_ticker()[0], UTC_FORMAT)  # get the timestamp return with WS
    time_init = (time_now + timedelta_1min).replace(microsecond=0, second=0)  # get the time which add 1min
    time_cyc = time_init + timedelta_1min  # get the time added 2min
    '''may got some bug in this sleep, could cause sleep less'''
    sleep((time_init - datetime.datetime.strptime(ws.get_ticker()[0], UTC_FORMAT)).total_seconds())

    evt_init_1min.set()

    while 1:
    # while ws.ws.sock.connected:
    #     if ws.api_key:
    #         logger.info("Funds: %s" % ws.funds())

        price = ws.get_ticker()[1]
        time_now = datetime.datetime.strptime(ws.get_ticker()[0], UTC_FORMAT)

        # '>=' will contain the whole point time situation
        if time_now >= time_cyc:
            df_1min = df_tick.set_index(['timestamp'])  # get all the tick in 1 min by DataFrame form
            # convert to 1_min ohlc
            df_1min = df_1min['price'].resample(rule='1Min').ohlc()

            # # if got 2 row, delete first row
            # if df_1min.shape[0] == 2:
            #     df_1min = df_1min.iloc[1:]

            queue.put(df_1min)
            logging.debug(df_1min)
            # logging.info('******WS put 1-min kline******')

            time_cyc = time_cyc + timedelta_1min  # rest the time used for judge
            time_init = time_init + timedelta_1min
            df_tick = df_tick_null  # reset the df_tick for the next LOOP
            df_temp = pandas.DataFrame([[time_now, price]], columns=['timestamp', 'price'])  # to put the time_now's data to df
            df_tick = df_tick.append(df_temp)  # append the last tick to the temporary df

        elif time_now >= time_init:
            df_temp = pandas.DataFrame([[time_now, price]], columns=['timestamp', 'price'])
            df_tick = df_tick.append(df_temp)  # append the last tick to the temporary df

        sleep(0.5)


if __name__ == "__main__":
    # from telegram_bot import *
    from initializer import *
    # from strategy import Printer_strategy

    # printer = Printer_strategy()

    cv = Condition()
    cv_printer = Condition()
    q_ws = Queue()
    q_loop = Queue()
    q_keeper = Queue()
    q_printer = Queue()
    evt_init_1min = Event()
    evt_first_5min = Event()
    evt_loop = Event()

    # def algorithm(q_printer, cv_printer):
    #     while 1:
    #         with cv_printer:
    #             cv_printer.wait()
    #             print("calculating")
    #             printer.printer(df_ohlc=q_printer.get())

    Thread(target=run_ws, name='ws', args=(q_ws, evt_init_1min,), daemon=True).start()
    Thread(target=data_keeper, name='data_keeper', args=(q_keeper, q_printer, cv_printer), daemon=True).start()
    Thread(target=init_klines_1min, name='init_klines_1min', args=(q_ws, q_loop, q_keeper, cv, evt_init_1min, evt_first_5min, evt_loop,)).start()
    # Thread(target=algorithm, name='printer', args=(q_printer, cv_printer), daemon=True).start()
    # Thread(target=bot.polling, name='telebot', daemon=True).start()

    # while 1:
    #     sleep(2)
    #     print('-------------thread num-------------')
    #     print(threading.active_count())
    #     print('\n')
    #     print(threading.enumerate())
    #     print('-------------thread num-------------\n')



