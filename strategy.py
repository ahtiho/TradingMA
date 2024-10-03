from lumibot.brokers import Alpaca
from lumibot.backtesting import YahooDataBacktesting
from lumibot.strategies.strategy import Strategy
from lumibot.traders import Trader
from datetime import datetime 
from alpaca_trade_api import REST
from alpaca.data.historical import StockHistoricalDataClient
from timedelta import Timedelta 
from alpaca.data.requests import StockBarsRequest
from alpaca.data.timeframe import TimeFrame
from dotenv import load_dotenv
import os

load_dotenv()

API_KEY = os.getenv("API_KEY")
API_SECRET = os.getenv("API_SECRET")
BASE_URL = os.getenv("BASE_URL")

ALPACA_CREDS = {
    "API_KEY": API_KEY, 
    "API_SECRET": API_SECRET, 
    "PAPER": True
}
class MLTrader(Strategy): 
    def initialize(self, symbol:str="AAPL", cash_at_risk:float=.5): 
        self.symbol = symbol
        self.sleeptime = "24H" 
        self.last_trade = None 
        self.cash_at_risk = cash_at_risk
        self.api = REST(base_url=BASE_URL, key_id=API_KEY, secret_key=API_SECRET)
    
    def get_historical_data(self, current_date):
        client = StockHistoricalDataClient(API_KEY, API_SECRET)

        end_date = current_date.strftime('%Y-%m-%d')
        start_date = (current_date - Timedelta(days=201)).strftime('%Y-%m-%d')

        request_params = StockBarsRequest(
            symbol_or_symbols=[self.symbol],
            timeframe=TimeFrame.Day,
            start=start_date,
            end=end_date
        )
        stock_bars = client.get_stock_bars(request_params)

        return stock_bars.df
    
    def buy_signal(self, current_date): 
        historical_data = self.get_historical_data(current_date)
       
        historical_data['20_MA'] = historical_data['close'].rolling(window=20).mean()
        historical_data['50_MA'] = historical_data['close'].rolling(window=50).mean()
        if historical_data['20_MA'].iloc[-1] > historical_data['50_MA'].iloc[-1] and \
           historical_data['20_MA'].iloc[-2] <= historical_data['50_MA'].iloc[-2]:
            return True
        return False
    
    def sell_signal(self, current_date):
        historical_data = self.get_historical_data(current_date)
        historical_data['20_MA'] = historical_data['close'].rolling(window=20).mean()
        historical_data['50_MA'] = historical_data['close'].rolling(window=50).mean()
        
        if historical_data['20_MA'].iloc[-1] < historical_data['50_MA'].iloc[-1] and \
           historical_data['20_MA'].iloc[-2] >= historical_data['50_MA'].iloc[-2]:
            return True
        return False
    
    def position_sizing(self): 
        cash = self.get_cash() 
        last_price = self.get_last_price(self.symbol)
        quantity = round(cash * self.cash_at_risk / last_price,0)
        return cash, last_price, quantity
    
    def on_trading_iteration(self):
        current_date = self.get_datetime()
        cash, last_price, quantity = self.position_sizing()
        if cash > last_price:
            if self.buy_signal(current_date) and self.last_trade != 'buy':
                if self.last_trade == "sell": 
                        self.sell_all() 
                
                order = self.create_order(
                        self.symbol, 
                        quantity, 
                        "buy", 
                        type="bracket", 
                        take_profit_price=last_price*1.50, 
                        stop_loss_price=last_price*.95
                    )
                self.submit_order(order) 
                self.last_trade = 'buy'
            
            elif self.sell_signal(current_date) and self.last_trade != 'sell':
                if self.last_trade == "buy": 
                        self.sell_all() 
                order = self.create_order(
                        self.symbol, 
                        quantity, 
                        "sell", 
                        type="bracket", 
                        take_profit_price=last_price*0.8, 
                        stop_loss_price=last_price*1.05
                    )
                self.submit_order(order) 
                self.last_trade = 'sell'
            print(self.buy_signal(current_date), self.sell_signal(current_date))
            print(current_date)
            print(self.last_trade)
start_date = datetime(2022,1,1)
end_date = datetime(2022,12,31) 
broker = Alpaca(ALPACA_CREDS)
strategy = MLTrader(name='mlstrat', broker=broker, 
                    parameters={"symbol":"AAPL", 
                                "cash_at_risk":.5})
strategy.backtest(
    YahooDataBacktesting, 
    start_date, 
    end_date, 
    benchmark_asset='AAPL',
    parameters={"symbol":"AAPL", "cash_at_risk":.5}
)
