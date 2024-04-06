import unittest
from omega.fetchers.tushare import fetch_stock_bars_daily
import tushare as ts
import os
import datetime
import cfg4py
from tests import get_config_dir, init_calendar


class TestFetchStockBarsDaily(unittest.TestCase):
    def setUp(self) -> None:
        cfg4py.init(get_config_dir())
        init_calendar()
        return super().setUp()
    
    def test_fetch_stock_bars_daily(self):
        token = os.environ["TUSHARE_TOKEN"]
        ts.set_token(token)

        codes = ["000001.SZ", "600000.SH"]
        start = datetime.date(2024, 3, 13)
        end = datetime.date(2024, 3, 25)

        df = fetch_stock_bars_daily(codes, start, end)
        print(df)
