from datetime import datetime,timedelta
import matplotlib.pyplot as plt
import pandas as pd
from pandas.plotting import register_matplotlib_converters
register_matplotlib_converters()
import MetaTrader5 as mt5
import time
import mplfinance as mpf
import numpy as np
import threading

if not mt5.initialize():
    print("initialize() failed")
    mt5.shutdown()

class mt5_ea_conductor():
    pd.set_option('display.max_columns',10)
    pd.set_option('display.width',1000)
    
    def __init__(self, symbol,timeframe,past_time=50,test = False,test_pass_time=1):
        self.timeframe = timeframe
        self.past_time = past_time
        if test == True:
            self.test_past_time = test_past_time * 365
        self.symbol = symbol
        self.rates_frame = []
        self.extra_lines = []
        self.stats = {}
        self.rates_frame = self.get_past_data()
        self.rates_frame = self.add_ema(self.rates_frame)

    def get_past_data(self,from_days=None,symbol=None):
        if symbol == None:
            symbol =self.symbol
        if from_days is None:
            req_time = datetime.today() - timedelta(days=36)
        else:
            req_time = datetime.today() - timedelta(days=from_days)
        data = mt5.copy_rates_range(symbol,
                                           self.timeframe,
                                           req_time,
                                           datetime.today() )
        if len(data) == 0:
            print("Couldn't get the data")
            return None

        refined_data = self.convert_to_pd(data)
        refined_data = self.add_ema(refined_data)
        return refined_data 

    def getTimeOpts(self,key):
        data =   {mt5.TIMEFRAME_M1:2,
                mt5.TIMEFRAME_M2:2,
                mt5.TIMEFRAME_M3:2,
                mt5.TIMEFRAME_M4:2,
                mt5.TIMEFRAME_M5:2,
                mt5.TIMEFRAME_M6:3,
                mt5.TIMEFRAME_M10:3,
                mt5.TIMEFRAME_M12:3,
                mt5.TIMEFRAME_M15:3,
                mt5.TIMEFRAME_M20:3,
                mt5.TIMEFRAME_M30:3,
                mt5.TIMEFRAME_H1:10,
                mt5.TIMEFRAME_H2:15,
                mt5.TIMEFRAME_H3:17,
                mt5.TIMEFRAME_H4:20,
                mt5.TIMEFRAME_H6:20,
                mt5.TIMEFRAME_H8:20,
                mt5.TIMEFRAME_H12:20,
                mt5.TIMEFRAME_D1:20,
                mt5.TIMEFRAME_W1:20,
                }
        return data[key]
    def convert_to_pd(self,data):
        refined_data = pd.DataFrame(data)
        refined_data['time'] = pd.to_datetime(refined_data['time'], unit='s')
        return refined_data

    def plot_ohlc(self,pd_data=None):
        if pd_data is None:
            pd_data = self.rates_frame
        if len(pd_data) != 0:
            mpl_data = self.conv(pd_data)
            extra_lines = self.graph_add_all(conv_data =pd_data)
            
            if extra_lines == []:
                mpf.plot(mpl_data, type='candlestick')
                
            else:
                mpf.plot(mpl_data, type='candlestick',addplot=extra_lines)

        else:
            print("No data in past data")

    def add_ema(self,data):
        
        data['EMA'] =data.iloc[:,4].ewm(span=50 ,adjust=False).mean()
        return data

    def get_curr_tr(self,data):
        return max(abs(data[1]['high'] - data[1]['low']),
                    abs(data[1]['high']-data[0]['close']),
                    abs(data[1]['low']-data[0]['close'])) * 10000

    def set_tr(self,data):
        tr_loc = data.columns.get_loc('tr')
        
        
        for i in range(1,len(data)):
	        data.iloc[i,tr_loc] = self.get_curr_tr([data.iloc[i-1],data.iloc[i]])
        
        return data

    def set_atr(self,data):
        atr_loc = data.columns.get_loc('atr')
        tr_loc = data.columns.get_loc('tr')
        data.iloc[14,atr_loc]  = self.get_first_atr(data)
        for i in range(15,len(data)):
            last_atr = data.iloc[i-1,atr_loc]
            curr_tr = data.iloc[i,tr_loc]
            data.iloc[i,atr_loc] = self.get_curr_atr(last_atr, curr_tr)
        return data

    def get_first_atr(self,data):

        tr_loc = data.columns.get_loc('tr')   
        tr_mean = data.iloc[:13,tr_loc].mean()
        last_tr = data.iloc[14,tr_loc]
        first_atr = ((tr_mean*13)+last_tr)/14
        return first_atr
    
    def get_curr_atr(self,last_atr,curr_tr):
        return ((last_atr * 13) + curr_tr) / 14

    def get_col_index(self,data,name):
        return list(data.columns).index(name)

    def graph_add_all(self,conv_data = None):
        if conv_data is None:
            conv_data = self.rates_frame
        default_cols = ['time', 'open', 'high', 'low', 'close', 'tick_volume', 'spread', 'real_volume']
        extra_lines = []
        extra = list(set(conv_data.columns.values) - set(default_cols))
        
        if len(extra) > 0:
            extra_lines = mpf.make_addplot(conv_data[[symb for symb in extra]])
        return extra_lines
        

    def refresh_data(self):
        curr_data = get_current_data()
        self.rates_frame = self.rates_frame.drop(self.rates_frame.index[0])
        self.rates_frame.append.curr_data
        self.analyser()
        
        
        
    def get_current_data(self):
        data = mt5.copy_rates_from_pos(self.symbol,
                                           self.timeframe,
                                           0,
                                           1)
        if len(data) == 0:
            raise Exception("Couldn't update the data")

        data = self.convert_to_pd(data)
        data = self.add_ema(data)

        return data
        

    def get_lower_low(self,timespan,pd_data = None):
        if pd_data is None:
            pd_data = self.rates_frame
            
        return min(pd_data.iloc[:-timespan]['close'])

    def get_higher_high(self,timespan,pd_data = None):
        if pd_data is None:
            pd_data = self.rates_frame
            
        return max(pd_data.iloc[:-timespan]['close'])


    def conv(self,data):
        reformatted_data = {}
        reformatted_data['Date'] = []
        reformatted_data['Open'] = []
        reformatted_data['High'] = []
        reformatted_data['Low'] = []
        reformatted_data['Close'] = []
        reformatted_data['Volume'] = []
        reformatted_data['Date'] = data['time']
        reformatted_data['Open']= data['open']
        reformatted_data['High']=data['high']
        reformatted_data['Low']=data['low']
        reformatted_data['Close']=data['close']
        reformatted_data['Volume']=data['tick_volume']
        reformatted_data = pd.DataFrame(reformatted_data)
        reformatted_data.index = reformatted_data.Date
        return reformatted_data

    def test_get_working_frame(self,data):
        return data.iloc[:50].copy()


    def plot_with_lower(self,data):
        conv_data = trader.conv(data)
        mpf.plot(conv_data,type='candlestick',addplot=[mpf.make_addplot(data['low_breaker'],type='scatter',markersize=50,marker='^'),
                                                       mpf.make_addplot(data['EMA'])])


if __name__ == '__main__':
    trader = mt5_ea_conductor('EURCAD',16385)
    trader.trade_signal('buy')
    trader.trade_signal('sell')
    
