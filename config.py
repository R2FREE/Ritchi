# configuration

# telegram TOKEN chat_id
TOKEN = "746132186:AAFaInEvPk3iZGvzQIYMpGV4CsHRyqg8CwE"
chat_id = 768693322

'''IMPORTANT PART!IMPORTANT PART!IMPORTANT PART!IMPORTANT PART!'''
testing = False  # test in test-BM or not
backtesting = True  # backtesting or not
isLocal = True

# BitMEX API real live
API_KEY = "Co7RMTSJJvIK09I_DgoScm8M"
API_SECRET = "EhiZ1vmavWcQ_wxX__DjGXESDDFrtCxIKMlAB-QoQVmin_zf"

# trading in N min period
N_min = 5

# strategy windows
EMA_fast = 5
EMA_fast_v2 = 4
EMA_slow = 8

WMA_fast = 5
WMA_fast_v2 = 4
WMA_slow = 8

# stoploss
stoploss = -0.07

# jump and slump Threshold Value
jnp_tv = 0.3 / 100

# skip narrow gap Threshold Value
sng_tv = 0.8 / 10_000

'''IMPORTANT PART!IMPORTANT PART!IMPORTANT PART!IMPORTANT PART!'''
# limit order 1_000 is 1 second
# wait_time = 30_000
wait_time = 10_000 if backtesting else 30_000


'''IMPORTANT PART!IMPORTANT PART!IMPORTANT PART!IMPORTANT PART!'''
# place percent: to make sure place successful
percent = 0.95 / 4 / 19
float_percent = 0.25

'''IMPORTANT PART!IMPORTANT PART!IMPORTANT PART!IMPORTANT PART!'''
# rest time in MIN
rest_time = 90
