import psutil
import os
import subprocess
import logging
import time
import numpy
import config
import asyncio
from bitmex_api import BitMEX_API
from aiogram import Bot, Dispatcher, executor, types
from pair import CNY2USD, XBT2USD

API_TOKEN = '987504537:AAFQZTiHG4VmtdkVoNIRBrDF0CaQ7wZvoas'
chat_id = '768693322'
PROXY_URL = 'http://127.0.0.1:7890'

# Configure logging
logging.basicConfig(level=logging.INFO)

# Initialize bot and dispatcher
bot = Bot(token=API_TOKEN, proxy=PROXY_URL) if config.isLocal else Bot(token=API_TOKEN)
dp = Dispatcher(bot)

bm = BitMEX_API()

PID_controller = os.getpid()
PID_main = None


def killProcess(pid):
    subprocess.Popen('taskkill /F /PID {0}'.format(pid), shell=True)


def runScript():
    subprocess.Popen(['python', 'main.py'], shell=True)
    filtrate_pid()


def filtrate_pid():
    global PID_main
    time.sleep(5)
    pids = psutil.pids()
    for pid in pids:
        p = psutil.Process(pid)
        if p.name() == 'python.exe' and pid != PID_controller:
            PID_main = pid
            logging.info('The main loop PID is: %d' % pid)
            # print(" MAIN LOOP PID: pid-%d pname-%s" % (pid, p.name()))


@dp.message_handler(commands=['help'])
async def reply_wallet_balance(message: types.Message):
    await message.answer('/start\n'
                         '/stop\n'
                         '/forceclose\n'
                         '/pos\n'
                         '/wallet')

@dp.message_handler(commands=['start'])
async def run_loop(message):
    runScript()
    await message.answer('COPY THAT\nSTART NOW')


@dp.message_handler(commands=['stop'])
async def end_loop(message):
    global PID_main
    killProcess(PID_main)
    await message.answer('COPY THAT\nSTOP RUNNING')


@dp.message_handler(commands=['forceclose'])
async def reply_wallet_balance(message: types.Message):
    bm.order_closePosition()
    await message.answer('FORCE CLOSE POS DONE')


@dp.message_handler(commands=['wallet'])
async def reply_wallet_balance(message: types.Message):
    XBT = bm.user_wallet_balance()
    await message.answer('Wallet: ' + str(XBT) + ' XBT\n' +
                         'CNY: ' + str(numpy.around(XBT * CNY2USD() * XBT2USD(), decimals=2)) + ' 💴')


@dp.message_handler(commands=['pos'])
async def reply_pos_info(message: types.Message):
    POS = bm.position_get()
    isOpen = POS['isOpen']
    currentQty = POS['currentQty']
    realisedPnl = POS['realisedPnl']
    avgEntryPrice = POS['avgEntryPrice']
    prevRealisedPnl = POS['prevRealisedPnl']
    if not isOpen:
        await message.answer('NO POS NOW')
    elif isOpen:
        await message.answer('currentQty: ' + str(currentQty) +
                             '\nrealisedPnl: ' + str(realisedPnl) +
                             '\navgEntryPrice: ' + str(avgEntryPrice) +
                             '\nprevRealisedPnl: ' + str(prevRealisedPnl))


if __name__ == '__main__':
    executor.start_polling(dp, skip_updates=True)