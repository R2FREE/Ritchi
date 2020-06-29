import time
import config
from aiogram import Bot, Dispatcher, executor

API_TOKEN = '746132186:AAFaInEvPk3iZGvzQIYMpGV4CsHRyqg8CwE'
chat_id = '768693322'
PROXY_URL = 'http://127.0.0.1:7890'

# bot = Bot(token=API_TOKEN, proxy=PROXY_URL) if config.isLocal else Bot(token=API_TOKEN)
# dp = Dispatcher(bot)

def inst_bot(func):
    def wrapper(*args, **kw):
        bot = Bot(token=API_TOKEN, proxy=PROXY_URL) if config.isLocal else Bot(token=API_TOKEN)
        dp = Dispatcher(bot)
        func(dp, bot, *args, **kw)
    return wrapper


async def send_message(bot, text):
    await bot.send_message(chat_id=chat_id, text=text)


@inst_bot
def send_start(dp, bot):
    executor.start(dp, send_message(bot, text='START PRINTING NOW' + '\n'))


@inst_bot
def send_pnl(dp, bot, pnl, price):
    message = "PNL: " + pnl + '\n' + 'PRICE: ' + price
    executor.start(dp, send_message(bot, text=message))


@inst_bot
def send_place_order(dp, bot, trend, execQty, avgPrice):
    message = "PLACED: " + trend + '\n' +\
              'QTY: ' + execQty + '\n' +\
              'PRICE: ' + avgPrice
    executor.start(dp, send_message(bot, text=message))


@inst_bot
def send_float_order(dp, bot, trend, execQty, avgPrice):
    message = "CONTINUE: " + trend + '\n' +\
              'TOTAL QTY: ' + execQty + '\n' + \
              'PRICE: ' + avgPrice
    executor.start(dp, send_message(bot, text=message))


@inst_bot
def send_any_msg(dp, bot, msg):
    message = msg
    executor.start(dp, send_message(bot, text=message))


if __name__ == '__main__':
    # executor.start(dp, send_message())
    # time.sleep(5)
    # bot = Bot(token=API_TOKEN, proxy=PROXY_URL) if config.isLocal else Bot(token=API_TOKEN)
    # dp = Dispatcher(bot)
    # executor.start(dp, send_message())
    # send_pnl(pnl='100.5%', price='8551')
    # time.sleep(2)
    # send_place_order(trend='LONG', execQty='1000', avgPrice='8556.9')
    # time.sleep(2)
    # send_float_order(trend='LONG', execQty='1000', avgPrice='8556.9')
    # time.sleep(2)
    # send_any_msg(msg='END NOW')
    while 1:
        a = 1
        if a == 1 or 2:
            print("fuck")
        else:
            print('you')
        time.sleep(2)
        a = 3
        if a == 1 or 2:
            print("fuck")
        else:
            print('you')