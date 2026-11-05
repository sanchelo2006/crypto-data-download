"""
GUI module for Crypto Data Fetcher - Bybit & Coinbase
Includes OHLCV, Fundamentals (OI/Funding/LS/FearGreed), News RSS, Trading Records, Data Bundle (3 coins)
"""

import sys
import tkinter as tk
from tkinter import ttk, messagebox, filedialog
from datetime import datetime, timedelta
import threading
import os
import shutil
import time
from pathlib import Path
import pandas as pd
import numpy as np
import requests
import config
import fetcher
from indicators import TechnicalIndicators
from logger import ErrorLogger
from bybit_fundamentals import BybitFundamentals
from news_fetcher import NewsAggregator
import subprocess


import winsound  # Для Windows
# Или для кроссплатформенности:
try:
    import winsound
    SOUND_AVAILABLE = True
except ImportError:
    SOUND_AVAILABLE = False
    print("Sound notifications only available on Windows")

def find_bybit_cmd() -> list[str]:
    """Возвращает команду для вызова bybit-history."""
    exe = shutil.which("bybit-history")
    if exe:
        return [exe]
    # fallback: запускаем модуль напрямую через текущий интерпретатор
    return [sys.executable, "-m", "bybit_history.bybit_data_downloader"]

class BybitGUI:
    def __init__(self, root):
        self.root = root
        self.root.title("Crypto Data Fetcher - Bybit & Coinbase")
        self.root.geometry(f"{config.WINDOW_WIDTH}x{config.WINDOW_HEIGHT}")
        self.root.resizable(True, True)

        # Logger
        self.logger = ErrorLogger()
        self.logger.log_info("Application started")

        # Exchange selection for OHLCV tab
        self.exchange_var = tk.StringVar(value=config.DEFAULT_EXCHANGE)

        # OHLCV fetcher
        self.fetcher = None
        self.data = None
        self.data_with_indicators = None
        self.fetch_cancelled = False
        self.fetch_thread = None

        # Indicators
        self.include_rsi = tk.BooleanVar(value=True)
        self.include_adx = tk.BooleanVar(value=True)
        self.include_ema_21 = tk.BooleanVar(value=True)
        self.include_ema_50 = tk.BooleanVar(value=True)
        self.include_ema_200 = tk.BooleanVar(value=False)
        self.include_macd = tk.BooleanVar(value=False)
        self.include_bb = tk.BooleanVar(value=False)

        # UI placeholders
        self.symbol_combo = None
        self.symbol_example = None
        self.market_var = None
        self.timeframe_var = None
        self.start_date_entry = None
        self.end_date_entry = None
        self.fetch_button = None
        self.cancel_button = None
        self.save_button = None
        self.clear_button = None
        self.test_button = None
        self.progress = None
        self.progress_label = None
        self.status_label = None
        self.connection_status = None
        self.exchange_info_label = None
        self.tree = None
        self.console_text = None

        # Fundamentals tab widgets
        self.fund_symbol = None
        self.fund_interval = None
        self.fund_start = None
        self.fund_end = None
        self.fund_fetch_btn = None
        self.fund_tree = None
        self.fund_save_btn = None
        self.fund_df = None
        self.fund_status = None

        # News tab widgets
        self.news_symbol = None
        self.news_limit = None
        self.news_age = None
        self.news_fetch_btn = None
        self.news_tree = None
        self.news_save_btn = None
        self.news_df = None
        self.news_status = None

        # Trading Records tab widgets
        self.tr_symbol = None
        self.tr_category = None
        self.tr_limit = None
        self.tr_fetch_btn = None
        self.tr_tree = None
        self.tr_save_btn = None
        self.tr_df = None
        self.tr_status = None

        # Data Bundle – для трёх монет
        self.bundle_symbols = []      # список Entry
        self.bundle_days = []         # список Spinbox
        self.bundle_folders = []      # список Entry
        self.init_snapshot_btns = []  # список кнопок
        self.current_data_btns = []   # список кнопок
        self.clear_folder_btns = [] 
        self.bundle_latest_candles_count = []
        self.bundle_latest_btns = []  
        self.bundle_status = None
        self.bundle_progress = None

        #auto mode and cancel flag
        self.current_fetch_thread = None
        self.fetch_cancelled_flag = False
        self.auto_mode_enabled = False
        self.auto_mode_thread = None
        self.auto_mode_idx = None

        # В __init__ добавьте:
        self.sound_enabled = tk.BooleanVar(value=True)
        self.sound_file = tk.StringVar(value="SystemAsterisk")  # Стандартный звук Windows

        # Setup UI with notebook
        self.setup_ui()
        self.setup_menu()
        self.setup_console()

        self.init_fetcher()

    # ----------------------------------------------------------------------
    # UI Construction with Notebook Tabs
    # ----------------------------------------------------------------------
    def setup_ui(self):
        main_frame = ttk.Frame(self.root, padding="10")
        main_frame.grid(row=0, column=0, sticky="nsew")
        self.root.columnconfigure(0, weight=1)
        self.root.rowconfigure(0, weight=1)
        main_frame.columnconfigure(0, weight=1)
        main_frame.rowconfigure(0, weight=1)

        self.notebook = ttk.Notebook(main_frame)
        self.notebook.grid(row=0, column=0, sticky="nsew")

        # Tab 1: OHLCV
        ohlcv_frame = ttk.Frame(self.notebook)
        self.notebook.add(ohlcv_frame, text="OHLCV Data")
        self._build_ohlcv_tab(ohlcv_frame)

        # Tab 2: Fundamentals (Bybit OI, Funding, LS, FearGreed)
        fund_frame = ttk.Frame(self.notebook)
        self.notebook.add(fund_frame, text="Fundamentals")
        self._build_fundamentals_tab(fund_frame)

        # Tab 3: News (RSS)
        news_frame = ttk.Frame(self.notebook)
        self.notebook.add(news_frame, text="Crypto News")
        self._build_news_tab(news_frame)

        # Tab 4: Trading Records (Bybit)
        trading_frame = ttk.Frame(self.notebook)
        self.notebook.add(trading_frame, text="Trading Records")
        self._build_trading_records_tab(trading_frame)

        # Tab 5: Data Bundle (3 coins)
        bundle_frame = ttk.Frame(self.notebook)
        self.notebook.add(bundle_frame, text="Data Bundle")
        self._build_data_bundle_tab(bundle_frame)

        # Tab : Order Book
        orderbook_frame = ttk.Frame(self.notebook)
        self.notebook.add(orderbook_frame, text="📖 Order Book")
        self._build_orderbook_tab(orderbook_frame)

        # Tab 6: Help / Guide
        help_frame = ttk.Frame(self.notebook)
        self.notebook.add(help_frame, text="📘 Help & Guide")
        self._build_help_tab(help_frame)
        # Tab 7: Public Trades (bybit-history)
        trades_frame = ttk.Frame(self.notebook)
        self.notebook.add(trades_frame, text="Public Trades")
        self._build_public_trades_tab(trades_frame)

    # ----------------------------- OHLCV Tab ---------------------------------
    def _build_ohlcv_tab(self, parent):
        parent.columnconfigure(1, weight=1)

        exchange_frame = ttk.LabelFrame(parent, text="Select Exchange", padding="5")
        exchange_frame.grid(row=0, column=0, columnspan=3, sticky="ew", pady=5)
        ttk.Radiobutton(exchange_frame, text="Bybit (Global, USDT) - Recommended",
                        variable=self.exchange_var, value=config.EXCHANGE_BYBIT,
                        command=self.on_exchange_change).pack(side=tk.LEFT, padx=10)
        ttk.Radiobutton(exchange_frame, text="Coinbase (USA, USD)",
                        variable=self.exchange_var, value=config.EXCHANGE_COINBASE,
                        command=self.on_exchange_change).pack(side=tk.LEFT, padx=10)
        self.exchange_info_label = ttk.Label(exchange_frame, text="", foreground="blue")
        self.exchange_info_label.pack(side=tk.LEFT, padx=20)

        status_frame = ttk.LabelFrame(parent, text="Connection Status", padding="5")
        status_frame.grid(row=1, column=0, columnspan=3, sticky="ew", pady=5)
        self.connection_status = ttk.Label(status_frame, text="Not connected", foreground="red")
        self.connection_status.pack(side=tk.LEFT, padx=10)
        self.test_button = ttk.Button(status_frame, text="Test Connection", command=self.test_connection)
        self.test_button.pack(side=tk.LEFT, padx=5)

        self._create_input_fields(parent, start_row=2)
        self._create_indicator_options(parent, start_row=7)
        self._create_buttons(parent, start_row=8)
        self._create_progress_indicators(parent, start_row=9)
        self._create_data_preview(parent, start_row=10)

        ttk.Label(parent, text="Bybit works globally with USDT pairs | Coinbase works in USA with USD pairs",
                  foreground="gray", font=("Arial", 8)).grid(row=11, column=0, columnspan=3, pady=5)

    def _create_input_fields(self, parent, start_row):
        row = start_row
        ttk.Label(parent, text="Coin Symbol:").grid(row=row, column=0, sticky=tk.W, pady=5)
        symbol_frame = ttk.Frame(parent)
        symbol_frame.grid(row=row, column=1, sticky="ew", pady=5)
        self.symbol_combo = ttk.Combobox(symbol_frame, width=28, state="normal")
        self.symbol_combo.pack(side=tk.LEFT, fill=tk.X, expand=True)
        self.symbol_combo.bind('<<ComboboxSelected>>', self.on_symbol_selected)
        self.symbol_example = ttk.Label(parent, text="(e.g., BTCUSDT)", foreground="gray")
        self.symbol_example.grid(row=row, column=2, sticky=tk.W, padx=5)
        row += 1

        ttk.Label(parent, text="Market:").grid(row=row, column=0, sticky=tk.W, pady=5)
        self.market_var = tk.StringVar(value=config.DEFAULT_MARKET)
        market_frame = ttk.Frame(parent)
        market_frame.grid(row=row, column=1, sticky=tk.W, pady=5)
        ttk.Radiobutton(market_frame, text="Spot", variable=self.market_var, value="spot").pack(side=tk.LEFT)
        ttk.Radiobutton(market_frame, text="Futures", variable=self.market_var, value="linear").pack(side=tk.LEFT)
        row += 1

        ttk.Label(parent, text="Timeframe:").grid(row=row, column=0, sticky=tk.W, pady=5)
        tf_frame = ttk.Frame(parent)
        tf_frame.grid(row=row, column=1, sticky="ew", pady=5)
        self.timeframe_var = tk.StringVar(value=config.DEFAULT_TIMEFRAME)
        self.timeframe_combo = ttk.Combobox(tf_frame, textvariable=self.timeframe_var,
                                            values=list(config.INTERVAL_SECONDS.keys()),
                                            state="readonly", width=20)
        self.timeframe_combo.pack(side=tk.LEFT)
        ttk.Button(tf_frame, text="ℹ", width=3, command=self.show_timeframe_info).pack(side=tk.LEFT, padx=5)
        self.timeframe_limit_label = ttk.Label(parent, text="", foreground="gray")
        self.timeframe_limit_label.grid(row=row, column=2, sticky=tk.W, padx=5)
        row += 1

        ttk.Label(parent, text="Start Date (YYYY-MM-DD):").grid(row=row, column=0, sticky=tk.W, pady=5)
        self.start_date_entry = ttk.Entry(parent, width=30)
        self.start_date_entry.grid(row=row, column=1, sticky="ew", pady=5)
        self.start_date_entry.insert(0, (datetime.now() - timedelta(days=config.DEFAULT_DAYS_BACK)).strftime("%Y-%m-%d"))
        row += 1

        ttk.Label(parent, text="End Date (YYYY-MM-DD):").grid(row=row, column=0, sticky=tk.W, pady=5)
        self.end_date_entry = ttk.Entry(parent, width=30)
        self.end_date_entry.grid(row=row, column=1, sticky="ew", pady=5)
        self.end_date_entry.insert(0, datetime.now().strftime("%Y-%m-%d"))

        date_frame = ttk.Frame(parent)
        date_frame.grid(row=row, column=2, sticky=tk.W, padx=5)
        for days, txt in [(7,"7d"),(30,"30d"),(90,"90d"),(365,"365d")]:
            ttk.Button(date_frame, text=txt, command=lambda d=days: self.set_quick_date(d)).pack(side=tk.LEFT, padx=2)
        row += 1

        self.update_coin_list()
        self.update_timeframe_info()

    def _create_indicator_options(self, parent, start_row):
        frame = ttk.LabelFrame(parent, text="Technical Indicators", padding="5")
        frame.grid(row=start_row, column=0, columnspan=3, sticky="ew", pady=10)
        checks = [("RSI (14)", self.include_rsi), ("ADX (14)", self.include_adx),
                  ("EMA 21", self.include_ema_21), ("EMA 50", self.include_ema_50),
                  ("EMA 200", self.include_ema_200), ("MACD", self.include_macd),
                  ("Bollinger Bands", self.include_bb)]
        for txt, var in checks:
            ttk.Checkbutton(frame, text=txt, variable=var).pack(side=tk.LEFT, padx=10)

    def _create_buttons(self, parent, start_row):
        frame = ttk.Frame(parent)
        frame.grid(row=start_row, column=0, columnspan=3, pady=10)
        self.fetch_button = ttk.Button(frame, text="Fetch OHLCV", command=self.fetch_data_thread)
        self.fetch_button.pack(side=tk.LEFT, padx=5)
        self.cancel_button = ttk.Button(frame, text="Cancel", command=self.cancel_fetch, state=tk.DISABLED)
        self.cancel_button.pack(side=tk.LEFT, padx=5)
        self.save_button = ttk.Button(frame, text="Save Data", command=self.save_data, state=tk.DISABLED)
        self.save_button.pack(side=tk.LEFT, padx=5)
        self.clear_button = ttk.Button(frame, text="Clear Data", command=self.clear_data)
        self.clear_button.pack(side=tk.LEFT, padx=5)

    def _create_progress_indicators(self, parent, start_row):
        self.progress = ttk.Progressbar(parent, mode='determinate')
        self.progress.grid(row=start_row, column=0, columnspan=3, sticky="ew", pady=10)
        self.progress_label = ttk.Label(parent, text="")
        self.progress_label.grid(row=start_row+1, column=0, columnspan=3, pady=2)
        self.status_label = ttk.Label(parent, text="Ready", relief=tk.SUNKEN, anchor=tk.W)
        self.status_label.grid(row=start_row+2, column=0, columnspan=3, sticky="ew", pady=5)

    def _create_data_preview(self, parent, start_row):
        frame = ttk.LabelFrame(parent, text="Data Preview (First 100 rows)", padding="5")
        frame.grid(row=start_row, column=0, columnspan=3, sticky="nsew", pady=10)
        frame.columnconfigure(0, weight=1)
        frame.rowconfigure(0, weight=1)
        self.tree = ttk.Treeview(frame, show="headings", height=config.PREVIEW_HEIGHT)
        self.tree.grid(row=0, column=0, sticky="nsew")
        v_scroll = ttk.Scrollbar(frame, orient="vertical", command=self.tree.yview)
        v_scroll.grid(row=0, column=1, sticky="ns")
        self.tree.configure(yscrollcommand=v_scroll.set)
        parent.rowconfigure(start_row, weight=1)

    # ----------------------------- Fundamentals Tab (Bybit) -----------------
    def _build_fundamentals_tab(self, parent):
        parent.columnconfigure(0, weight=1)
        parent.columnconfigure(1, weight=1)
        parent.rowconfigure(3, weight=1)

        ttk.Label(parent, text="Symbol:").grid(row=0, column=0, padx=5, pady=5, sticky="w")
        self.fund_symbol = ttk.Entry(parent, width=15)
        self.fund_symbol.grid(row=0, column=1, padx=5, pady=5, sticky="w")
        self.fund_symbol.insert(0, "BTCUSDT")

        ttk.Label(parent, text="Interval (OI/LS):").grid(row=0, column=2, padx=5, pady=5, sticky="w")
        self.fund_interval = ttk.Combobox(parent, values=["5min","15min","30min","1h","4h","1d"], width=8)
        self.fund_interval.set("1h")
        self.fund_interval.grid(row=0, column=3, padx=5, pady=5, sticky="w")

        ttk.Label(parent, text="Start Date:").grid(row=1, column=0, padx=5, pady=5, sticky="w")
        self.fund_start = ttk.Entry(parent, width=12)
        self.fund_start.insert(0, (datetime.now() - timedelta(days=7)).strftime("%Y-%m-%d"))
        self.fund_start.grid(row=1, column=1, padx=5, pady=5, sticky="w")

        ttk.Label(parent, text="End Date:").grid(row=1, column=2, padx=5, pady=5, sticky="w")
        self.fund_end = ttk.Entry(parent, width=12)
        self.fund_end.insert(0, datetime.now().strftime("%Y-%m-%d"))
        self.fund_end.grid(row=1, column=3, padx=5, pady=5, sticky="w")

        self.fund_fetch_btn = ttk.Button(parent, text="Fetch All Fundamentals", command=self.fetch_all_fundamentals)
        self.fund_fetch_btn.grid(row=2, column=0, columnspan=4, pady=10)

        columns = ("timestamp", "Open_Interest", "Funding_Rate", "Long_Short_Ratio",
                   "Fear_Greed_Value", "Market_Sentiment")
        self.fund_tree = ttk.Treeview(parent, columns=columns, show="headings", height=15)
        for col in columns:
            self.fund_tree.heading(col, text=col.replace("_"," "))
            self.fund_tree.column(col, width=100)
        self.fund_tree.grid(row=3, column=0, columnspan=4, padx=5, pady=5, sticky="nsew")
        scroll = ttk.Scrollbar(parent, orient="vertical", command=self.fund_tree.yview)
        scroll.grid(row=3, column=4, sticky="ns")
        self.fund_tree.configure(yscrollcommand=scroll.set)

        self.fund_save_btn = ttk.Button(parent, text="Save Fundamentals as CSV", command=self.save_fundamentals)
        self.fund_save_btn.grid(row=4, column=0, columnspan=2, pady=5, sticky="w")
        self.fund_save_btn.grid_remove()

    # ----------------------------- News Tab (RSS) ---------------------------
    def _build_news_tab(self, parent):
        parent.columnconfigure(0, weight=1)
        parent.columnconfigure(1, weight=1)
        parent.rowconfigure(4, weight=1)

        ttk.Label(parent, text="Coin Symbol:").grid(row=0, column=0, padx=5, pady=5, sticky="w")
        self.news_symbol = ttk.Entry(parent, width=15)
        self.news_symbol.grid(row=0, column=1, padx=5, pady=5, sticky="w")
        self.news_symbol.insert(0, "BTC")

        ttk.Label(parent, text="Limit:").grid(row=0, column=2, padx=5, pady=5, sticky="w")
        self.news_limit = ttk.Spinbox(parent, from_=5, to=50, width=10)
        self.news_limit.set(20)
        self.news_limit.grid(row=0, column=3, padx=5, pady=5, sticky="w")

        ttk.Label(parent, text="Max Age (days):").grid(row=1, column=0, padx=5, pady=5, sticky="w")
        self.news_age = ttk.Combobox(parent, values=["1","3","7","14","30","All"], width=8)
        self.news_age.set("7")
        self.news_age.grid(row=1, column=1, padx=5, pady=5, sticky="w")

        self.news_fetch_btn = ttk.Button(parent, text="Get News", command=self.fetch_news)
        self.news_fetch_btn.grid(row=2, column=0, columnspan=4, pady=10)

        self.news_status = ttk.Label(parent, text="", foreground="blue")
        self.news_status.grid(row=3, column=0, columnspan=4, pady=5)

        columns = ("date", "title", "summary", "url")
        self.news_tree = ttk.Treeview(parent, columns=columns, show="headings", height=15)
        for col in columns:
            self.news_tree.heading(col, text=col.capitalize())
            self.news_tree.column(col, width=200)
        self.news_tree.grid(row=4, column=0, columnspan=4, padx=5, pady=5, sticky="nsew")
        scroll = ttk.Scrollbar(parent, orient="vertical", command=self.news_tree.yview)
        scroll.grid(row=4, column=4, sticky="ns")
        self.news_tree.configure(yscrollcommand=scroll.set)

        self.news_save_btn = ttk.Button(parent, text="Save News as CSV", command=self.save_news)
        self.news_save_btn.grid(row=5, column=0, columnspan=2, pady=5, sticky="w")
        self.news_save_btn.grid_remove()

    # ----------------------------- Trading Records Tab (Bybit) --------------
    def _build_trading_records_tab(self, parent):
        parent.columnconfigure(0, weight=1)
        parent.columnconfigure(1, weight=1)
        parent.rowconfigure(4, weight=1)

        ttk.Label(parent, text="Symbol:").grid(row=0, column=0, padx=5, pady=5, sticky="w")
        self.tr_symbol = ttk.Entry(parent, width=15)
        self.tr_symbol.grid(row=0, column=1, padx=5, pady=5, sticky="w")
        self.tr_symbol.insert(0, "BTCUSDT")

        ttk.Label(parent, text="Category:").grid(row=0, column=2, padx=5, pady=5, sticky="w")
        self.tr_category = ttk.Combobox(parent, values=["spot", "linear"], width=10)
        self.tr_category.set("linear")
        self.tr_category.grid(row=0, column=3, padx=5, pady=5, sticky="w")

        ttk.Label(parent, text="Limit (max 1000):").grid(row=1, column=0, padx=5, pady=5, sticky="w")
        self.tr_limit = ttk.Spinbox(parent, from_=1, to=1000, width=10)
        self.tr_limit.set(200)
        self.tr_limit.grid(row=1, column=1, padx=5, pady=5, sticky="w")

        self.tr_fetch_btn = ttk.Button(parent, text="Get Trading Records", command=self.fetch_trading_records)
        self.tr_fetch_btn.grid(row=2, column=0, columnspan=4, pady=10)

        self.tr_status = ttk.Label(parent, text="", foreground="blue")
        self.tr_status.grid(row=3, column=0, columnspan=4, pady=5)

        columns = ("timestamp", "price", "volume", "side")
        self.tr_tree = ttk.Treeview(parent, columns=columns, show="headings", height=15)
        for col in columns:
            self.tr_tree.heading(col, text=col.capitalize())
            self.tr_tree.column(col, width=150 if col=="timestamp" else 100)
        self.tr_tree.grid(row=4, column=0, columnspan=4, padx=5, pady=5, sticky="nsew")
        scroll = ttk.Scrollbar(parent, orient="vertical", command=self.tr_tree.yview)
        scroll.grid(row=4, column=4, sticky="ns")
        self.tr_tree.configure(yscrollcommand=scroll.set)

        self.tr_save_btn = ttk.Button(parent, text="Save as CSV", command=self.save_trading_records)
        self.tr_save_btn.grid(row=5, column=0, columnspan=2, pady=5, sticky="w")
        self.tr_save_btn.grid_remove()

    # ----------------------------- Data Bundle Tab (3 coins) ----------------
    def _build_data_bundle_tab(self, parent):
        parent.columnconfigure(0, weight=1)
        parent.columnconfigure(1, weight=1)
        parent.columnconfigure(2, weight=1)
        parent.rowconfigure(1, weight=1)

        headers = ["Coin 1", "Coin 2", "Coin 3"]
        for col, header in enumerate(headers):
            ttk.Label(parent, text=header, font=('Arial', 10, 'bold')).grid(row=0, column=col, padx=5, pady=5)

        for i in range(3):
            frame = ttk.Frame(parent)
            frame.grid(row=1, column=i, padx=5, pady=5, sticky="nsew")
            self._create_bundle_row(frame, i)

        self.bundle_status = ttk.Label(parent, text="", foreground="blue")
        self.bundle_status.grid(row=2, column=0, columnspan=3, pady=5)
        self.bundle_progress = ttk.Progressbar(parent, mode='indeterminate')
        self.bundle_progress.grid(row=3, column=0, columnspan=3, sticky="ew", pady=5)
        self.bundle_progress.grid_remove()

    def _create_bundle_row(self, parent, idx):
        """Создаёт набор виджетов для одной монеты (для Data Bundle)"""
        # Символ монеты
        ttk.Label(parent, text="Symbol:").grid(row=0, column=0, sticky="w", pady=2)
        sym_entry = ttk.Entry(parent, width=12)
        sym_entry.insert(0, "BTCUSDT")
        sym_entry.grid(row=1, column=0, padx=2, pady=2, sticky="ew")
        self.bundle_symbols.append(sym_entry)

        # Количество дней
        ttk.Label(parent, text="Days back:").grid(row=2, column=0, sticky="w", pady=2)
        days_spin = ttk.Spinbox(parent, from_=1, to=365, width=10)
        days_spin.set(30)
        days_spin.grid(row=3, column=0, padx=2, pady=2, sticky="ew")
        self.bundle_days.append(days_spin)

        # Путь для сохранения
        ttk.Label(parent, text="Output folder:").grid(row=4, column=0, sticky="w", pady=2)
        folder_entry = ttk.Entry(parent, width=20)
        folder_entry.insert(0, str(Path.home() / "Desktop" / f"crypto_data_{idx+1}"))
        folder_entry.grid(row=5, column=0, padx=2, pady=2, sticky="ew")
        self.bundle_folders.append(folder_entry)

        # Кнопка выбора папки
        browse_btn = ttk.Button(parent, text="Browse", command=lambda i=idx: self._browse_bundle_folder(i))
        browse_btn.grid(row=5, column=1, padx=2, pady=2)

        # Кнопка очистки папки
        clear_btn = ttk.Button(parent, text="🗑️ Clear Folder", command=lambda i=idx: self.clear_output_folder(i))
        clear_btn.grid(row=6, column=0, columnspan=2, pady=2)
        self.clear_folder_btns.append(clear_btn)

        # Кнопка Initial Snapshot
        init_btn = ttk.Button(parent, text="📸 Initial Snapshot", command=lambda i=idx: self.fetch_initial_snapshot(i))
        init_btn.grid(row=7, column=0, columnspan=2, pady=2)
        self.init_snapshot_btns.append(init_btn)

        # Кнопка Current Data
        curr_btn = ttk.Button(parent, text="🔄 Current Data", command=lambda i=idx: self.fetch_current_data(i))
        curr_btn.grid(row=8, column=0, columnspan=2, pady=2)
        self.current_data_btns.append(curr_btn)

        # Количество свечей для "Latest Candles"
        ttk.Label(parent, text="Latest candles count:").grid(row=9, column=0, sticky="w", pady=2)
        candles_spin = ttk.Spinbox(parent, from_=5, to=200, width=8)
        candles_spin.set(20)
        candles_spin.grid(row=10, column=0, padx=2, pady=2, sticky="ew")
        self.bundle_latest_candles_count.append(candles_spin)

        # Кнопка "Latest Candles"
        latest_btn = ttk.Button(parent, text="🆕 Latest Candles", command=lambda i=idx: self.fetch_latest_candles(i))
        latest_btn.grid(row=11, column=0, columnspan=2, pady=2)
        self.bundle_latest_btns.append(latest_btn)

        # Кнопка отмены
        cancel_btn = ttk.Button(parent, text="⏹ Cancel", command=lambda i=idx: self.cancel_fetch_bundle(i))
        cancel_btn.grid(row=12, column=0, columnspan=2, pady=2)

        # Индикатор авторежима
        self.auto_indicator = ttk.Label(parent, text="⚪ Auto OFF", foreground="gray")
        self.auto_indicator.grid(row=13, column=0, columnspan=2, pady=2)

        # Кнопки управления авторежимом
        auto_frame = ttk.Frame(parent)
        auto_frame.grid(row=14, column=0, columnspan=2, pady=2)
        auto_start_btn = ttk.Button(auto_frame, text="▶ Auto Start", command=lambda i=idx: self.start_auto_mode(i))
        auto_start_btn.pack(side=tk.LEFT, padx=2)
        auto_stop_btn = ttk.Button(auto_frame, text="⏸ Auto Stop", command=lambda i=idx: self.stop_auto_mode(i))
        auto_stop_btn.pack(side=tk.LEFT, padx=2)

        # Настройки звука (только для первой карточки, чтобы не дублировать)
        if idx == 0:
            sound_frame = ttk.LabelFrame(parent, text="Sound Settings", padding="5")
            sound_frame.grid(row=15, column=0, columnspan=2, pady=5, sticky="ew")
            
            ttk.Checkbutton(sound_frame, text="Enable Sound Alert", variable=self.sound_enabled).pack(anchor=tk.W)
            
            sound_file_frame = ttk.Frame(sound_frame)
            sound_file_frame.pack(fill=tk.X, pady=2)
            ttk.Label(sound_file_frame, text="Sound:").pack(side=tk.LEFT)
            self.sound_file_combo = ttk.Combobox(sound_file_frame, textvariable=self.sound_file, 
                                                values=["SystemAsterisk", "SystemExclamation", "SystemHand", "SystemQuestion", "SystemDefault"],
                                                width=20)
            self.sound_file_combo.pack(side=tk.LEFT, padx=5)
            ttk.Button(sound_frame, text="Browse WAV", command=self.browse_sound_file).pack(pady=2)

        # Настройка растяжения колонки
        parent.columnconfigure(0, weight=1)

    def update_auto_status(self, idx, is_active):
        """Обновление индикатора авторежима"""
        if is_active:
            self.auto_indicator.config(text="🟢 Auto mode ON", foreground="green")
        else:
            self.auto_indicator.config(text="⚪ Auto mode OFF", foreground="gray")

    # ----------------------------- Helper Methods ---------------------------
    def setup_console(self):
        console_frame = ttk.LabelFrame(self.root, text="Log", padding="5")
        console_frame.grid(row=1, column=0, sticky="nsew", padx=10, pady=5)
        console_frame.columnconfigure(0, weight=1)
        console_frame.rowconfigure(0, weight=1)
        self.console_text = tk.Text(console_frame, height=config.CONSOLE_HEIGHT,
                                    wrap=tk.WORD, font=("Courier", 9))
        self.console_text.grid(row=0, column=0, sticky="nsew")
        scroll = ttk.Scrollbar(console_frame, orient="vertical", command=self.console_text.yview)
        scroll.grid(row=0, column=1, sticky="ns")
        self.console_text.configure(yscrollcommand=scroll.set)
        self.root.rowconfigure(1, weight=1)

    def setup_menu(self):
        menubar = tk.Menu(self.root)
        self.root.config(menu=menubar)
        file_menu = tk.Menu(menubar, tearoff=0)
        menubar.add_cascade(label="File", menu=file_menu)
        file_menu.add_command(label="Fetch OHLCV", command=self.fetch_data_thread)
        file_menu.add_command(label="Save Data", command=self.save_data)
        file_menu.add_separator()
        file_menu.add_command(label="Exit", command=self.root.quit)

        # Настройки
        settings_menu = tk.Menu(menubar, tearoff=0)
        menubar.add_cascade(label="Settings", menu=settings_menu)
        settings_menu.add_checkbutton(label="Enable Sound Alerts", variable=self.sound_enabled)
        settings_menu.add_separator()
        settings_menu.add_command(label="Select Sound File", command=self.browse_sound_file)


        help_menu = tk.Menu(menubar, tearoff=0)
        menubar.add_cascade(label="Help", menu=help_menu)
        help_menu.add_command(label="Indicator Information", command=self.show_indicator_info)
        help_menu.add_command(label="Timeframe Limits", command=self.show_timeframe_limits)
        help_menu.add_command(label="View Error Log", command=self.view_error_log)
        help_menu.add_command(label="About", command=self.show_about)

    def log_to_console(self, message):
        timestamp = datetime.now().strftime("%H:%M:%S")
        self.console_text.insert(tk.END, f"[{timestamp}] {message}\n")
        self.console_text.see(tk.END)
        self.root.update_idletasks()

    # ---------- OHLCV methods ----------
    def init_fetcher(self):
        try:
            exchange = self.exchange_var.get()
            self.fetcher = fetcher.get_fetcher(exchange, self.logger)
            exchange_name = config.EXCHANGES.get(exchange, {}).get('name', exchange)
            self.status_label.config(text=f"Ready - {exchange_name}")
            self.log_to_console(f"{exchange_name} fetcher initialized")
            if exchange == config.EXCHANGE_BYBIT:
                self.exchange_info_label.config(text="✓ Bybit works globally with USDT pairs", foreground="green")
            else:
                self.exchange_info_label.config(text="✓ Coinbase works in USA with USD pairs", foreground="green")
        except Exception as e:
            self.log_to_console(f"ERROR initializing fetcher: {str(e)}")
            messagebox.showerror("Error", f"Failed to initialize fetcher:\n{str(e)}")

    def update_coin_list(self):
        exchange = self.exchange_var.get()
        coins = config.EXCHANGES.get(exchange, {}).get('common_coins', [])
        if self.symbol_combo:
            self.symbol_combo['values'] = coins
            default = "BTCUSDT" if exchange == config.EXCHANGE_BYBIT else "BTC-USD"
            self.symbol_combo.set(default)
            self.update_symbol_example()

    def update_symbol_example(self):
        exchange = self.exchange_var.get()
        if exchange == config.EXCHANGE_BYBIT:
            self.symbol_example.config(text="(e.g., BTCUSDT, ETHUSDT, SOLUSDT)")
        else:
            self.symbol_example.config(text="(e.g., BTC-USD, ETH-USD, SOL-USD)")

    def on_exchange_change(self):
        self.update_coin_list()
        self.update_symbol_example()
        self.update_timeframe_info()
        self.clear_data()
        self.connection_status.config(text="Not connected", foreground="red")
        self.init_fetcher()

    def on_symbol_selected(self, event):
        self.log_to_console(f"Selected symbol: {self.symbol_combo.get()}")

    def get_symbol(self):
        return self.symbol_combo.get().strip().upper()

    def update_timeframe_info(self):
        exchange = self.exchange_var.get()
        tf = self.timeframe_var.get()
        if exchange == config.EXCHANGE_COINBASE:
            limits = {"1m":"⚠ Max 24h","5m":"⚠ Max 7d","15m":"⚠ Max 30d",
                      "1h":"✓ Up to 90d","4h":"✓ Up to 180d","1d":"✓ Up to 365d"}
            txt = limits.get(tf, "✓ Standard limits")
            self.timeframe_limit_label.config(text=txt, foreground="orange" if "⚠" in txt else "green")
        else:
            self.timeframe_limit_label.config(text="✓ No strict limits", foreground="green")

    def show_timeframe_info(self):
        exchange = self.exchange_var.get()
        if exchange == config.EXCHANGE_COINBASE:
            msg = "Coinbase limits:\n1m:24h\n5m:7d\n15m:30d\n1h:90d\n4h:180d\n1d:365d"
        else:
            msg = "Bybit: no fixed date limit, up to 1000 candles per request."
        messagebox.showinfo("Timeframe Limits", msg)

    def show_timeframe_limits(self):
        self.show_timeframe_info()

    def set_quick_date(self, days):
        end = datetime.now()
        start = end - timedelta(days=days)
        self.start_date_entry.delete(0, tk.END)
        self.start_date_entry.insert(0, start.strftime("%Y-%m-%d"))
        self.end_date_entry.delete(0, tk.END)
        self.end_date_entry.insert(0, end.strftime("%Y-%m-%d"))

    def test_connection(self):
        exchange = self.exchange_var.get()
        self.log_to_console("="*50)
        self.log_to_console(f"Testing connection to {exchange.upper()}...")
        self.connection_status.config(text=f"Testing {exchange.upper()}...", foreground="orange")
        self.root.update()
        try:
            if exchange == config.EXCHANGE_BYBIT:
                r = requests.get("https://api.bybit.com/v5/market/tickers?category=spot&symbol=BTCUSDT", timeout=10)
                if r.status_code==200 and r.json().get("retCode")==0:
                    price = r.json()["result"]["list"][0]["lastPrice"]
                    self.log_to_console(f"✓ Connected to Bybit! BTCUSDT: ${price}")
                    self.connection_status.config(text=f"Connected to Bybit - BTC: ${price}", foreground="green")
                else:
                    raise Exception("Invalid response")
            else:
                r = requests.get("https://api.exchange.coinbase.com/products/BTC-USD/ticker", timeout=10)
                if r.status_code==200:
                    price = r.json()["price"]
                    self.log_to_console(f"✓ Connected to Coinbase! BTC-USD: ${price}")
                    self.connection_status.config(text=f"Connected to Coinbase - BTC: ${price}", foreground="green")
                else:
                    raise Exception("HTTP error")
        except Exception as e:
            self.log_to_console(f"✗ Connection failed: {str(e)}")
            self.connection_status.config(text="Connection failed", foreground="red")

    def fetch_data_thread(self):
        if self.fetch_thread and self.fetch_thread.is_alive():
            messagebox.showwarning("Warning", "Fetch already in progress")
            return
        self.fetch_cancelled = False
        self.cancel_button.config(state=tk.NORMAL)
        self.fetch_thread = threading.Thread(target=self.fetch_data)
        self.fetch_thread.daemon = True
        self.fetch_thread.start()

    def fetch_data(self):
        try:
            self.console_text.delete(1.0, tk.END)
            self.fetch_button.config(state=tk.DISABLED)
            self.save_button.config(state=tk.DISABLED)
            self.progress['value'] = 0
            self.status_label.config(text="Fetching data...")
            self.root.update()

            symbol = self.get_symbol()
            exchange = self.exchange_var.get()
            market = self.market_var.get()
            timeframe = self.timeframe_var.get()
            if not symbol:
                messagebox.showerror("Error", "Enter coin symbol")
                return

            if hasattr(self.fetcher, 'validate_symbol'):
                valid, msg, _, _ = self.fetcher.validate_symbol(symbol, market)
                if not valid:
                    messagebox.showwarning("Symbol Validation", msg)
                    return

            try:
                start = datetime.strptime(self.start_date_entry.get(), "%Y-%m-%d")
                end = datetime.strptime(self.end_date_entry.get(), "%Y-%m-%d")
                end = end.replace(hour=23, minute=59, second=59)
            except ValueError:
                messagebox.showerror("Date Error", "Invalid date format")
                return
            if start > end:
                messagebox.showerror("Error", "Start date > end date")
                return

            self.log_to_console(f"Fetching OHLCV from {exchange.upper()}, {symbol} ({market}), {timeframe}")
            self.data = self.fetcher.fetch_ohlcv(symbol, timeframe, start, end, market,
                                                  progress_callback=self.update_progress)
            if self.fetch_cancelled:
                self.status_label.config(text="Fetch cancelled")
                return
            if self.data is not None and not self.data.empty:
                # Принудительная сортировка от старых к новым (важно для индикаторов)
                self.data = self.data.sort_values('timestamp').reset_index(drop=True)

                self.log_to_console("Calculating indicators...")
                ind = TechnicalIndicators(self.data)
                self.data_with_indicators = self.data.copy()
                if self.include_rsi.get():
                    self.data_with_indicators['RSI'] = ind.calculate_rsi(14)
                if self.include_adx.get():
                    self.data_with_indicators['ADX'] = ind.calculate_adx(14)
                if self.include_ema_21.get():
                    self.data_with_indicators['EMA_21'] = ind.calculate_ema(21)
                if self.include_ema_50.get():
                    self.data_with_indicators['EMA_50'] = ind.calculate_ema(50)
                if self.include_ema_200.get():
                    self.data_with_indicators['EMA_200'] = ind.calculate_ema(200)
                if self.include_macd.get():
                    macd = ind.calculate_macd()
                    self.data_with_indicators['MACD'] = macd['macd']
                    self.data_with_indicators['MACD_Signal'] = macd['signal']
                    self.data_with_indicators['MACD_Histogram'] = macd['histogram']
                if self.include_bb.get():
                    bb = ind.calculate_bollinger_bands()
                    self.data_with_indicators['BB_Upper'] = bb['upper']
                    self.data_with_indicators['BB_Middle'] = bb['middle']
                    self.data_with_indicators['BB_Lower'] = bb['lower']

                self.status_label.config(text=f"Fetched {len(self.data_with_indicators)} records")
                self.save_button.config(state=tk.NORMAL)
                self.update_preview()
                self.log_to_console(f"Success: {len(self.data)} candles")
                summary = self._create_summary(symbol, timeframe, market)
                messagebox.showinfo("Data Summary", summary)
            else:
                self.status_label.config(text="No data")
                self.log_to_console("No data found")
        except Exception as e:
            self.logger.log_exception(e, "fetch_data")
            self.log_to_console(f"ERROR: {str(e)}")
            messagebox.showerror("Error", str(e))
        finally:
            self.progress['value'] = 0
            self.progress_label.config(text="")
            self.fetch_button.config(state=tk.NORMAL)
            self.cancel_button.config(state=tk.DISABLED)

    def update_progress(self, progress, current, total):
        if not self.fetch_cancelled:
            self.progress['value'] = progress
            self.progress_label.config(text=f"Fetched {current}/{total} candles ({progress}%)")
            self.root.update_idletasks()

    def update_preview(self):
        for item in self.tree.get_children():
            self.tree.delete(item)
        if self.data_with_indicators is not None and not self.data_with_indicators.empty:
            cols = list(self.data_with_indicators.columns)
            self.tree["columns"] = cols
            for c in cols:
                self.tree.heading(c, text=c)
                self.tree.column(c, width=150 if c=='timestamp' else 80, anchor=tk.CENTER)
            for _, row in self.data_with_indicators.head(100).iterrows():
                self.tree.insert("", tk.END, values=list(row))

    def clear_data(self):
        self.data = None
        self.data_with_indicators = None
        self.save_button.config(state=tk.DISABLED)
        for item in self.tree.get_children():
            self.tree.delete(item)
        self.status_label.config(text="Data cleared")
        self.log_to_console("Data cleared")

    def save_data(self):
        if self.data_with_indicators is None or self.data_with_indicators.empty:
            messagebox.showwarning("No Data", "No data to save")
            return
        exchange = self.exchange_var.get()
        symbol = self.get_symbol()
        tf = self.timeframe_var.get()
        fname = filedialog.asksaveasfilename(defaultextension=".csv",
            filetypes=[("CSV","*.csv")],
            initialfile=f"{exchange}_{symbol}_{tf}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv")
        if fname:
            df_to_save = self.data_with_indicators.copy()
            if 'turnover' in df_to_save.columns:
                df_to_save.drop(columns=['turnover'], inplace=True)
            df_to_save.to_csv(fname, index=False)
            self.log_to_console(f"Saved to {fname}")
            messagebox.showinfo("Success", "Data saved")

    def _create_summary(self, symbol, tf, market):
        df = self.data_with_indicators
        s = f"Symbol: {symbol}\nTimeframe: {tf}\nMarket: {market}\n"
        s += f"Date range: {df['timestamp'].min()} to {df['timestamp'].max()}\n"
        s += f"Records: {len(df)}\nPrice range: ${df['low'].min():.2f} - ${df['high'].max():.2f}"
        ind = []
        if self.include_rsi.get(): ind.append("RSI")
        if self.include_adx.get(): ind.append("ADX")
        if self.include_ema_21.get(): ind.append("EMA21")
        if self.include_ema_50.get(): ind.append("EMA50")
        if self.include_ema_200.get(): ind.append("EMA200")
        if self.include_macd.get(): ind.append("MACD")
        if self.include_bb.get(): ind.append("BB")
        if ind: s += f"\nIndicators: {', '.join(ind)}"
        return s

    def show_indicator_info(self):
        msg = """RSI(14): first 14 NaN
ADX(14): first ~28 NaN
EMA21: first 21 NaN
EMA50: first 50 NaN
EMA200: first 200 NaN
MACD: first 26 NaN
BB(20): first 20 NaN
Fetch extra data beyond target range."""
        messagebox.showinfo("Indicator Info", msg)

    def cancel_fetch(self):
        self.fetch_cancelled = True
        self.status_label.config(text="Cancelling...")
        self.log_to_console("Fetch cancelled by user")

    def view_error_log(self):
        log_file = Path("logs") / "error.log"
        if log_file.exists():
            os.startfile(log_file) if sys.platform == 'win32' else os.system(f'open "{log_file}"')
        else:
            messagebox.showinfo("Info", "No error log")

    def show_about(self):
        about = """Crypto Data Fetcher v7.0
- OHLCV: Bybit (global) & Coinbase (USA)
- Fundamentals: OI, Funding Rate, Long/Short, Fear&Greed
- News: RSS feeds (cointelegraph, coindesk, decrypt)
- Trading Records: recent trades from Bybit
- Data Bundle: one-click export for 3 coins (prices+indicators+fundamentals+news)
Built with Python, tkinter, pybit, pandas"""
        messagebox.showinfo("About", about)

    # ---------- Fundamentals (Bybit) ----------
    def fetch_all_fundamentals(self):
        symbol = self.fund_symbol.get().strip().upper()
        interval = self.fund_interval.get()
        try:
            start = datetime.strptime(self.fund_start.get(), "%Y-%m-%d")
            end = datetime.strptime(self.fund_end.get(), "%Y-%m-%d")
            end = end.replace(hour=23, minute=59, second=59)
        except ValueError:
            messagebox.showerror("Date Error", "Invalid date")
            return
        start_ts = int(start.timestamp()*1000)
        end_ts = int(end.timestamp()*1000)
        self.fund_fetch_btn.config(state=tk.DISABLED)
        self.fund_status = ttk.Label(self.fund_tree.master, text="Fetching...", foreground="blue")
        self.fund_status.grid(row=5, column=0, columnspan=4, pady=5)
        self.root.update()
        try:
            fb = BybitFundamentals()
            df = fb.fetch_all_fundamentals(symbol, start_time=start_ts, end_time=end_ts,
                                            interval=interval, limit=1000)
            if df.empty:
                raise Exception("No data")
            for col in ["Open_Interest","Funding_Rate","Long_Short_Ratio","Fear_Greed_Value"]:
                if col in df.columns:
                    df[col] = pd.to_numeric(df[col], errors='coerce')
            df = df[(df["timestamp"]>=start) & (df["timestamp"]<=end)]
            self.fund_df = df.copy()
            for row in self.fund_tree.get_children():
                self.fund_tree.delete(row)
            for _, r in df.iterrows():
                self.fund_tree.insert("", "end", values=(
                    r["timestamp"].strftime("%Y-%m-%d %H:%M"),
                    f"{r.get('Open_Interest','N/A'):.2f}" if pd.notna(r.get('Open_Interest')) else "N/A",
                    f"{r.get('Funding_Rate','N/A'):.6f}" if pd.notna(r.get('Funding_Rate')) else "N/A",
                    f"{r.get('Long_Short_Ratio','N/A'):.3f}" if pd.notna(r.get('Long_Short_Ratio')) else "N/A",
                    f"{r.get('Fear_Greed_Value','N/A'):.0f}" if pd.notna(r.get('Fear_Greed_Value')) else "N/A",
                    r.get("Market_Sentiment", "N/A")
                ))
            self.fund_save_btn.grid()
            self.fund_status.config(text=f"Loaded {len(df)} records", foreground="green")
            self.log_to_console(f"Fundamentals fetched for {symbol}")
        except Exception as e:
            self.logger.log_exception(e, "fetch_all_fundamentals")
            self.fund_status.config(text=f"Error: {str(e)}", foreground="red")
        finally:
            self.fund_fetch_btn.config(state=tk.NORMAL)

    def save_fundamentals(self):
        if not hasattr(self, 'fund_df') or self.fund_df.empty:
            messagebox.showwarning("No Data", "No fundamentals data")
            return
        fname = filedialog.asksaveasfilename(defaultextension=".csv",
            filetypes=[("CSV","*.csv")],
            initialfile=f"fundamentals_{self.fund_symbol.get()}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv")
        if fname:
            self.fund_df.to_csv(fname, index=False)
            self.log_to_console(f"Saved to {fname}")

    # ---------- News ----------
    def fetch_news(self):
        symbol = self.news_symbol.get().strip().upper()
        try:
            limit = int(self.news_limit.get())
        except ValueError:
            messagebox.showerror("Error", "Limit must be integer")
            return
        age_str = self.news_age.get()
        max_age_days = int(age_str) if age_str.isdigit() else (None if age_str.lower()=="all" else 7)
        self.news_fetch_btn.config(state=tk.DISABLED)
        self.news_status.config(text="Fetching news...", foreground="blue")
        self.root.update()
        try:
            agg = NewsAggregator()
            df = agg.fetch_news(coin_symbol=symbol, source="rss", limit=limit, max_age_days=max_age_days)
            if df.empty:
                raise Exception("No news found")
            self.news_df = df.copy()
            for row in self.news_tree.get_children():
                self.news_tree.delete(row)
            for _, r in df.iterrows():
                self.news_tree.insert("", "end", values=(
                    r.get("date",""), r.get("title",""), r.get("summary",""), r.get("url","")
                ))
            self.news_save_btn.grid()
            self.news_status.config(text=f"Loaded {len(df)} news articles", foreground="green")
            self.log_to_console(f"News fetched for {symbol}")
        except Exception as e:
            self.logger.log_exception(e, "fetch_news")
            self.news_status.config(text=f"Error: {str(e)}", foreground="red")
        finally:
            self.news_fetch_btn.config(state=tk.NORMAL)

    def save_news(self):
        if not hasattr(self, 'news_df') or self.news_df.empty:
            messagebox.showwarning("No Data", "No news data")
            return
        fname = filedialog.asksaveasfilename(defaultextension=".csv",
            filetypes=[("CSV","*.csv")],
            initialfile=f"news_{self.news_symbol.get()}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv")
        if fname:
            self.news_df.to_csv(fname, index=False)
            self.log_to_console(f"News saved to {fname}")

    # ---------- Trading Records ----------
    def fetch_trading_records(self):
        if self.exchange_var.get() != config.EXCHANGE_BYBIT:
            messagebox.showerror("Error", "Trading Records only available for Bybit")
            return
        symbol = self.tr_symbol.get().strip().upper()
        category = self.tr_category.get()
        try:
            limit = int(self.tr_limit.get())
        except ValueError:
            messagebox.showerror("Error", "Limit must be integer")
            return
        self.tr_fetch_btn.config(state=tk.DISABLED)
        self.tr_status.config(text="Fetching trading records...", foreground="blue")
        self.root.update()
        try:
            if not self.fetcher:
                raise Exception("Fetcher not initialized")
            df = self.fetcher.get_public_trading_records(category=category, symbol=symbol, limit=limit)
            if df.empty:
                raise Exception("No trading records found")
            self.tr_df = df.copy()
            for row in self.tr_tree.get_children():
                self.tr_tree.delete(row)
            for _, r in df.iterrows():
                ts_str = r['timestamp'].strftime("%Y-%m-%d %H:%M:%S") if not pd.isna(r['timestamp']) else "N/A"
                self.tr_tree.insert("", "end", values=(
                    ts_str,
                    f"{r['price']:.2f}",
                    f"{r['volume']:.4f}",
                    r['side']
                ))
            self.tr_save_btn.grid()
            self.tr_status.config(text=f"Loaded {len(df)} records", foreground="green")
            self.log_to_console(f"Trading records fetched for {symbol} ({category})")
        except Exception as e:
            self.logger.log_exception(e, "fetch_trading_records")
            self.tr_status.config(text=f"Error: {str(e)}", foreground="red")
        finally:
            self.tr_fetch_btn.config(state=tk.NORMAL)

    def save_trading_records(self):
        if not hasattr(self, 'tr_df') or self.tr_df.empty:
            messagebox.showwarning("No Data", "No trading records to save")
            return
        fname = filedialog.asksaveasfilename(defaultextension=".csv",
            filetypes=[("CSV","*.csv")],
            initialfile=f"trading_records_{self.tr_symbol.get()}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv")
        if fname:
            self.tr_df.to_csv(fname, index=False)
            self.log_to_console(f"Saved to {fname}")

    # ---------- Data Bundle (3 coins) ----------
    def _browse_bundle_folder(self, idx):
        folder = filedialog.askdirectory()
        if folder:
            self.bundle_folders[idx].delete(0, tk.END)
            self.bundle_folders[idx].insert(0, folder)

    def clear_output_folder(self, idx):
        folder = self.bundle_folders[idx].get().strip()
        if not folder:
            messagebox.showerror("Error", "No folder selected")
            return
        if not os.path.exists(folder):
            return
        try:
            deleted_count = 0
            for filename in os.listdir(folder):
                file_path = os.path.join(folder, filename)
                if os.path.isfile(file_path):
                    os.remove(file_path)
                    deleted_count += 1
            if deleted_count:
                self.log_to_console(f"Cleared folder: {folder} (deleted {deleted_count} file(s))")
        except Exception as e:
            self.logger.log_exception(e, "clear_output_folder")
            messagebox.showerror("Error", f"Failed to clear folder:\n{str(e)}")

    def _prepare_and_save_price_data(self, df_full, symbol, timeframe, folder, suffix, indicators_list, trim_start=None):
        """
        Рассчитывает индикаторы на расширенных данных, затем обрезает до trim_start.
        Если trim_start=None, сохраняет весь df_full.
        """
        if df_full is None or df_full.empty:
            return
        df_full = df_full.sort_values('timestamp').reset_index(drop=True)
        if 'turnover' in df_full.columns:
            df_full.drop(columns=['turnover'], inplace=True)
        
        # Рассчитываем индикаторы на всём df_full
        ind = TechnicalIndicators(df_full)
        for name, period in indicators_list:
            if name == 'RSI':
                df_full[name] = ind.calculate_rsi(period=period)
            elif name == 'MACD':
                macd = ind.calculate_macd()
                df_full['MACD'] = macd['macd']
                df_full['MACD_Signal'] = macd['signal']
                df_full['MACD_Histogram'] = macd['histogram']
            elif name.startswith('EMA'):
                df_full[name] = ind.calculate_ema(period=period)
        
        # Обрезаем до нужного периода
        if trim_start is not None:
            df_result = df_full[df_full['timestamp'] >= trim_start].copy()
            if df_result.empty:
                self.log_to_console(f"Warning: No data after trimming for {symbol}")
                return
        else:
            df_result = df_full.copy()
        
        filename = f"{symbol}_{timeframe}_{suffix}_prices.csv"
        filepath = Path(folder) / filename
        df_result.to_csv(filepath, index=False)
        self.log_to_console(f"Saved: {filepath}")

    def fetch_initial_snapshot(self, idx):
        symbol = self.bundle_symbols[idx].get().strip().upper()
        try:
            days = int(self.bundle_days[idx].get())
        except ValueError:
            messagebox.showerror("Error", "Days must be an integer")
            return
        folder = self.bundle_folders[idx].get().strip()
        if not folder:
            messagebox.showerror("Error", "Please select output folder")
            return
        os.makedirs(folder, exist_ok=True)

        self.init_snapshot_btns[idx].config(state=tk.DISABLED)
        self.current_data_btns[idx].config(state=tk.DISABLED)
        self.bundle_status.config(text=f"Fetching snapshot for {symbol}...", foreground="blue")
        self.bundle_progress.grid()
        self.bundle_progress.start()
        self.root.update()
        
        # Сброс флага отмены
        self.fetch_cancelled_flag = False

        def task():
            try:
                from fetcher import get_fetcher
                from bybit_fundamentals import BybitFundamentals
                bybit_fetcher = get_fetcher(config.EXCHANGE_BYBIT, self.logger)

                end_date = datetime.now()
                start_date = end_date - timedelta(days=days)
                
                # Для корректного расчёта индикаторов берём расширенный период (максимальный период индикатора = 200 для EMA200)
                extended_start = start_date - timedelta(days=200 * 1.5 / 24)  # ~13 дней запаса для 1h EMA200
                if self.fetch_cancelled_flag:
                    return

                # 1. OHLCV с индикаторами
                timeframes = [("15m", 200), ("1h", 200)]
                for tf, buffer_days in timeframes:
                    tf_start = start_date - timedelta(days=buffer_days * 1.5 / 24)
                    df_full = bybit_fetcher.fetch_ohlcv(symbol, tf, tf_start, end_date, category="linear")
                    if df_full is not None and not df_full.empty:
                        df_full = df_full.sort_values('timestamp').reset_index(drop=True)
                        if 'turnover' in df_full.columns:
                            df_full.drop(columns=['turnover'], inplace=True)
                        
                        # Расчёт индикаторов на полных данных
                        ind = TechnicalIndicators(df_full)
                        if tf == "15m":
                            df_full['RSI'] = ind.calculate_rsi(14)
                            macd = ind.calculate_macd()
                            df_full['MACD'] = macd['macd']
                            df_full['MACD_Signal'] = macd['signal']
                            df_full['MACD_Histogram'] = macd['histogram']
                            df_full['EMA_21'] = ind.calculate_ema(21)
                            df_full['EMA_50'] = ind.calculate_ema(50)
                        else:  # 1h
                            df_full['RSI'] = ind.calculate_rsi(14)
                            macd = ind.calculate_macd()
                            df_full['MACD'] = macd['macd']
                            df_full['MACD_Signal'] = macd['signal']
                            df_full['MACD_Histogram'] = macd['histogram']
                            df_full['EMA_50'] = ind.calculate_ema(50)
                            df_full['EMA_200'] = ind.calculate_ema(200)
                        
                        # Обрезаем до целевого периода
                        df = df_full[(df_full['timestamp'] >= start_date) & (df_full['timestamp'] <= end_date)].copy()
                        if not df.empty:
                            suffix = f"{start_date.strftime('%Y%m%d')}_{end_date.strftime('%Y%m%d')}"
                            filename = f"{symbol}_{tf}_{suffix}_prices.csv"
                            filepath = Path(folder) / filename
                            df.to_csv(filepath, index=False)
                            self.log_to_console(f"Saved: {filepath}")
                    
                    if self.fetch_cancelled_flag:
                        return

                # 2. Фундаментальные данные (с расширенным периодом)
                fb = BybitFundamentals()
                intervals = ["15min", "1h"]
                fund_start = start_date - timedelta(days=7)  # Запас для фундаментала
                fund_start_ts = int(fund_start.timestamp() * 1000)
                end_ts = int(end_date.timestamp() * 1000)
                
                for interval in intervals:
                    if self.fetch_cancelled_flag:
                        return
                    df_full = fb.fetch_all_fundamentals(symbol, start_time=fund_start_ts, end_time=end_ts,
                                                        interval=interval, limit=1000)
                    if df_full is not None and not df_full.empty:
                        df_full = df_full.sort_values('timestamp').reset_index(drop=True)
                        df = df_full[(df_full['timestamp'] >= start_date) & (df_full['timestamp'] <= end_date)].copy()
                        if not df.empty:
                            if 'timestamp' in df.columns:
                                df['timestamp'] = df['timestamp'].dt.strftime('%Y-%m-%d %H:%M:%S')
                            filename = f"{symbol}_{interval}_fundamentals_{start_date.strftime('%Y%m%d')}_{end_date.strftime('%m%d')}.csv"
                            filepath = Path(folder) / filename
                            df.to_csv(filepath, index=False)
                            self.log_to_console(f"Saved: {filepath}")

                if self.fetch_cancelled_flag:
                    return

                # 3. ORDERBOOK (глубина 25)
                orderbook = bybit_fetcher.session.get_orderbook(
                    category="linear",
                    symbol=symbol,
                    limit=25
                )
                if orderbook and orderbook.get("retCode") == 0:
                    result = orderbook["result"]
                    bids_df = pd.DataFrame(result["b"], columns=["price", "size"])
                    bids_df["side"] = "bid"
                    asks_df = pd.DataFrame(result["a"], columns=["price", "size"])
                    asks_df["side"] = "ask"
                    orderbook_df = pd.concat([bids_df, asks_df], ignore_index=True)
                    orderbook_df["price"] = orderbook_df["price"].astype(float)
                    orderbook_df["size"] = orderbook_df["size"].astype(float)
                    orderbook_df["timestamp"] = pd.to_datetime(result["ts"], unit="ms").strftime('%Y-%m-%d %H:%M:%S')
                    filename = f"{symbol}_orderbook_depth25_{start_date.strftime('%Y%m%d')}_{end_date.strftime('%Y%m%d')}.csv"
                    filepath = Path(folder) / filename
                    orderbook_df.to_csv(filepath, index=False)
                    self.log_to_console(f"Saved orderbook: {filepath}")

                if self.fetch_cancelled_flag:
                    return

                # 4. TRADING RECORDS (последние 100 сделок)
                trading_records = bybit_fetcher.get_public_trading_records(
                    category="linear",
                    symbol=symbol,
                    limit=100
                )
                if trading_records is not None and not trading_records.empty:
                    if 'timestamp' in trading_records.columns:
                        trading_records['timestamp'] = pd.to_datetime(trading_records['timestamp']).dt.strftime('%Y-%m-%d %H:%M:%S')
                    tr_filename = f"{symbol}_trading_records_{start_date.strftime('%Y%m%d')}_{end_date.strftime('%Y%m%d')}.csv"
                    tr_filepath = Path(folder) / tr_filename
                    trading_records.to_csv(tr_filepath, index=False)
                    self.log_to_console(f"Saved trading records: {tr_filepath}")

                self.log_to_console(f"✅ Snapshot for {symbol} completed.")
                self.bundle_status.config(text=f"Snapshot for {symbol} completed", foreground="green")
            except Exception as e:
                self.logger.log_exception(e, "fetch_initial_snapshot")
                self.bundle_status.config(text=f"Error for {symbol}: {str(e)}", foreground="red")
            finally:
                self.bundle_progress.stop()
                self.bundle_progress.grid_remove()
                self.init_snapshot_btns[idx].config(state=tk.NORMAL)
                self.current_data_btns[idx].config(state=tk.NORMAL)
                self.fetch_cancelled_flag = False
                self.root.update()

        threading.Thread(target=task, daemon=True).start()

    #специальный метод для коректного отображения индикаторов в current data
    def _prepare_and_save_price_data_with_trim(self, df_full, symbol, timeframe, folder, suffix, indicators_list, trim_start):
        """Рассчитывает индикаторы на полных данных, затем обрезает до trim_start и сохраняет."""
        if df_full is None or df_full.empty:
            return
        df_full = df_full.sort_values('timestamp').reset_index(drop=True)
        if 'turnover' in df_full.columns:
            df_full.drop(columns=['turnover'], inplace=True)
        ind = TechnicalIndicators(df_full)

        for name, period in indicators_list:
            if name == 'RSI':
                df_full[name] = ind.calculate_rsi(period=period)
            elif name == 'MACD':
                macd = ind.calculate_macd()
                df_full['MACD'] = macd['macd']
                df_full['MACD_Signal'] = macd['signal']
                df_full['MACD_Histogram'] = macd['histogram']
            elif name.startswith('EMA'):
                df_full[name] = ind.calculate_ema(period=period)

        # Обрезаем до нужной даты
        df_trimmed = df_full[df_full['timestamp'] >= trim_start].copy()
        if df_trimmed.empty:
            self.log_to_console(f"Warning: No data after trimming for {symbol}")
            return

        filename = f"{symbol}_{timeframe}_{suffix}_prices.csv"
        filepath = Path(folder) / filename
        df_trimmed.to_csv(filepath, index=False)
        self.log_to_console(f"Saved: {filepath}")

    def fetch_current_data(self, idx):
        symbol = self.bundle_symbols[idx].get().strip().upper()
        folder = self.bundle_folders[idx].get().strip()
        if not folder:
            messagebox.showerror("Error", "Please select output folder")
            return
        os.makedirs(folder, exist_ok=True)

        self.init_snapshot_btns[idx].config(state=tk.DISABLED)
        self.current_data_btns[idx].config(state=tk.DISABLED)
        self.bundle_status.config(text=f"Fetching current data for {symbol}...", foreground="blue")
        self.bundle_progress.grid()
        self.bundle_progress.start()
        self.root.update()
        
        self.fetch_cancelled_flag = False

        def task():
            try:
                from fetcher import get_fetcher
                from bybit_fundamentals import BybitFundamentals
                bybit_fetcher = get_fetcher(config.EXCHANGE_BYBIT, self.logger)

                today_start = datetime.now().replace(hour=0, minute=0, second=0, microsecond=0)
                today_end = datetime.now()
                
                # Для корректного расчёта индикаторов берём данные за последние 3 дня
                extended_start = today_start - timedelta(days=3)
                
                if self.fetch_cancelled_flag:
                    return

                # Цены 15m с индикаторами
                df_prices_full = bybit_fetcher.fetch_ohlcv(symbol, "15m", extended_start, today_end, category="linear")
                if df_prices_full is not None and not df_prices_full.empty:
                    df_prices_full = df_prices_full.sort_values('timestamp').reset_index(drop=True)
                    if 'turnover' in df_prices_full.columns:
                        df_prices_full.drop(columns=['turnover'], inplace=True)
                    
                    ind = TechnicalIndicators(df_prices_full)
                    df_prices_full['RSI'] = ind.calculate_rsi(14)
                    macd = ind.calculate_macd()
                    df_prices_full['MACD'] = macd['macd']
                    df_prices_full['MACD_Signal'] = macd['signal']
                    df_prices_full['MACD_Histogram'] = macd['histogram']
                    df_prices_full['EMA_21'] = ind.calculate_ema(21)
                    df_prices_full['EMA_50'] = ind.calculate_ema(50)
                    
                    df_prices = df_prices_full[df_prices_full['timestamp'] >= today_start].copy()
                    if not df_prices.empty:
                        suffix = f"current_{today_start.strftime('%Y%m%d')}"
                        filename = f"{symbol}_15m_{suffix}_prices.csv"
                        filepath = Path(folder) / filename
                        df_prices.to_csv(filepath, index=False)
                        self.log_to_console(f"Saved: {filepath}")

                if self.fetch_cancelled_flag:
                    return

                # Фундаментальные данные 15min
                fb = BybitFundamentals()
                fund_start = today_start - timedelta(days=3)
                start_ts = int(fund_start.timestamp() * 1000)
                end_ts = int(today_end.timestamp() * 1000)
                df_fund_full = fb.fetch_all_fundamentals(symbol, start_time=start_ts, end_time=end_ts,
                                                        interval="15min", limit=1000)
                if df_fund_full is not None and not df_fund_full.empty:
                    df_fund_full = df_fund_full.sort_values('timestamp').reset_index(drop=True)
                    df_fund = df_fund_full[df_fund_full['timestamp'] >= today_start].copy()
                    if not df_fund.empty:
                        if 'timestamp' in df_fund.columns:
                            df_fund['timestamp'] = df_fund['timestamp'].dt.strftime('%Y-%m-%d %H:%M:%S')
                        filename = f"{symbol}_15min_fundamentals_current_{today_start.strftime('%Y%m%d')}.csv"
                        filepath = Path(folder) / filename
                        df_fund.to_csv(filepath, index=False)
                        self.log_to_console(f"Saved: {filepath}")

                if self.fetch_cancelled_flag:
                    return

                # ORDERBOOK (глубина 25)
                orderbook = bybit_fetcher.session.get_orderbook(
                    category="linear",
                    symbol=symbol,
                    limit=25
                )
                if orderbook and orderbook.get("retCode") == 0:
                    result = orderbook["result"]
                    bids_df = pd.DataFrame(result["b"], columns=["price", "size"])
                    bids_df["side"] = "bid"
                    asks_df = pd.DataFrame(result["a"], columns=["price", "size"])
                    asks_df["side"] = "ask"
                    orderbook_df = pd.concat([bids_df, asks_df], ignore_index=True)
                    orderbook_df["price"] = orderbook_df["price"].astype(float)
                    orderbook_df["size"] = orderbook_df["size"].astype(float)
                    orderbook_df["timestamp"] = pd.to_datetime(result["ts"], unit="ms").strftime('%Y-%m-%d %H:%M:%S')
                    ob_filename = f"{symbol}_orderbook_depth25_current_{today_start.strftime('%Y%m%d_%H%M%S')}.csv"
                    ob_filepath = Path(folder) / ob_filename
                    orderbook_df.to_csv(ob_filepath, index=False)
                    self.log_to_console(f"Saved orderbook: {ob_filepath}")

                if self.fetch_cancelled_flag:
                    return

                # TRADING RECORDS
                trading_records = bybit_fetcher.get_public_trading_records(
                    category="linear",
                    symbol=symbol,
                    limit=100
                )
                if trading_records is not None and not trading_records.empty:
                    if 'timestamp' in trading_records.columns:
                        trading_records['timestamp'] = pd.to_datetime(trading_records['timestamp']).dt.strftime('%Y-%m-%d %H:%M:%S')
                    tr_filename = f"{symbol}_trading_records_current_{today_start.strftime('%Y%m%d')}.csv"
                    tr_filepath = Path(folder) / tr_filename
                    trading_records.to_csv(tr_filepath, index=False)
                    self.log_to_console(f"Saved trading records: {tr_filepath}")

                self.log_to_console(f"✅ Current data for {symbol} completed.")
                self.bundle_status.config(text=f"Current data for {symbol} completed", foreground="green")
            except Exception as e:
                self.logger.log_exception(e, "fetch_current_data")
                self.bundle_status.config(text=f"Error for {symbol}: {str(e)}", foreground="red")
            finally:
                self.bundle_progress.stop()
                self.bundle_progress.grid_remove()
                self.init_snapshot_btns[idx].config(state=tk.NORMAL)
                self.current_data_btns[idx].config(state=tk.NORMAL)
                self.fetch_cancelled_flag = False
                self.root.update()

        threading.Thread(target=task, daemon=True).start()

    def fetch_latest_candles(self, idx):
        symbol = self.bundle_symbols[idx].get().strip().upper()
        try:
            count = int(self.bundle_latest_candles_count[idx].get())
        except ValueError:
            messagebox.showerror("Error", "Candles count must be integer")
            return
        folder = self.bundle_folders[idx].get().strip()
        if not folder:
            messagebox.showerror("Error", "Please select output folder")
            return
        os.makedirs(folder, exist_ok=True)

        self.bundle_latest_btns[idx].config(state=tk.DISABLED)
        self.bundle_status.config(text=f"Fetching latest {count} candles for {symbol}...", foreground="blue")
        self.bundle_progress.grid()
        self.bundle_progress.start()
        self.root.update()
        
        self.fetch_cancelled_flag = False

        def task():
            nonlocal count
            try:
                from fetcher import get_fetcher
                from bybit_fundamentals import BybitFundamentals
                bybit_fetcher = get_fetcher(config.EXCHANGE_BYBIT, self.logger)

                # Для корректного расчёта индикаторов берём данные за последние 7 дней
                end_date = datetime.now()
                start_date = end_date - timedelta(days=7)
                df_prices_full = bybit_fetcher.fetch_ohlcv(symbol, "15m", start_date, end_date, category="linear")
                if df_prices_full is None or df_prices_full.empty:
                    self.log_to_console(f"Warning: No price data for {symbol}")
                    return

                if self.fetch_cancelled_flag:
                    return

                df_prices_full = df_prices_full.sort_values('timestamp').reset_index(drop=True)
                if len(df_prices_full) < count:
                    self.log_to_console(f"Warning: Only {len(df_prices_full)} candles available, requested {count}")
                    count = len(df_prices_full)

                # 1. Подготовка ценового файла с индикаторами
                df_prices = df_prices_full.copy()
                if 'turnover' in df_prices.columns:
                    df_prices.drop(columns=['turnover'], inplace=True)
                ind = TechnicalIndicators(df_prices)

                df_prices['RSI'] = ind.calculate_rsi(14)
                macd = ind.calculate_macd()
                df_prices['MACD'] = macd['macd']
                df_prices['MACD_Signal'] = macd['signal']
                df_prices['MACD_Histogram'] = macd['histogram']
                df_prices['EMA_21'] = ind.calculate_ema(21)
                df_prices['EMA_50'] = ind.calculate_ema(50)

                # Берём последние 'count' свечей
                df_prices_result = df_prices.tail(count).copy()
                price_filename = f"{symbol}_15m_latest_{count}candles_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv"
                price_filepath = Path(folder) / price_filename
                df_prices_result.to_csv(price_filepath, index=False)
                self.log_to_console(f"Saved price data: {price_filepath}")

                if self.fetch_cancelled_flag:
                    return

                # 2. Фундаментальные данные за те же последние N свечей
                if not df_prices_result.empty:
                    start_ts = int(df_prices_result['timestamp'].min().timestamp() * 1000)
                    end_ts = int(df_prices_result['timestamp'].max().timestamp() * 1000)
                else:
                    start_ts = int((datetime.now() - timedelta(days=1)).timestamp() * 1000)
                    end_ts = int(datetime.now().timestamp() * 1000)

                fb = BybitFundamentals()
                df_fund_full = fb.fetch_all_fundamentals(symbol,
                                                        start_time=start_ts - 7*24*3600*1000,
                                                        end_time=end_ts,
                                                        interval="15min",
                                                        limit=1000)
                if df_fund_full is not None and not df_fund_full.empty:
                    df_fund_trimmed = df_fund_full[
                        (df_fund_full['timestamp'] >= df_prices_result['timestamp'].min()) &
                        (df_fund_full['timestamp'] <= df_prices_result['timestamp'].max())
                    ]
                    if not df_fund_trimmed.empty:
                        if 'timestamp' in df_fund_trimmed.columns:
                            df_fund_trimmed['timestamp'] = df_fund_trimmed['timestamp'].dt.strftime('%Y-%m-%d %H:%M:%S')
                        fund_filename = f"{symbol}_15m_fundamentals_latest_{count}candles_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv"
                        fund_filepath = Path(folder) / fund_filename
                        df_fund_trimmed.to_csv(fund_filepath, index=False)
                        self.log_to_console(f"Saved fundamentals data: {fund_filepath}")

                if self.fetch_cancelled_flag:
                    return

                # 3. ORDERBOOK (текущий снапшот)
                orderbook = bybit_fetcher.session.get_orderbook(
                    category="linear",
                    symbol=symbol,
                    limit=25
                )
                if orderbook and orderbook.get("retCode") == 0:
                    result = orderbook["result"]
                    bids_df = pd.DataFrame(result["b"], columns=["price", "size"])
                    bids_df["side"] = "bid"
                    asks_df = pd.DataFrame(result["a"], columns=["price", "size"])
                    asks_df["side"] = "ask"
                    orderbook_df = pd.concat([bids_df, asks_df], ignore_index=True)
                    orderbook_df["price"] = orderbook_df["price"].astype(float)
                    orderbook_df["size"] = orderbook_df["size"].astype(float)
                    orderbook_df["timestamp"] = pd.to_datetime(result["ts"], unit="ms").strftime('%Y-%m-%d %H:%M:%S')
                    ob_filename = f"{symbol}_orderbook_depth25_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv"
                    ob_filepath = Path(folder) / ob_filename
                    orderbook_df.to_csv(ob_filepath, index=False)
                    self.log_to_console(f"Saved orderbook: {ob_filepath}")

                if self.fetch_cancelled_flag:
                    return

                # 4. TRADING RECORDS (последние 100 сделок)
                trading_records = bybit_fetcher.get_public_trading_records(
                    category="linear",
                    symbol=symbol,
                    limit=100
                )
                if trading_records is not None and not trading_records.empty:
                    if 'timestamp' in trading_records.columns:
                        trading_records['timestamp'] = pd.to_datetime(trading_records['timestamp']).dt.strftime('%Y-%m-%d %H:%M:%S')
                    tr_filename = f"{symbol}_trading_records_latest_100_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv"
                    tr_filepath = Path(folder) / tr_filename
                    trading_records.to_csv(tr_filepath, index=False)
                    self.log_to_console(f"Saved trading records: {tr_filepath}")

                self.bundle_status.config(text=f"Latest {count} candles for {symbol} saved", foreground="green")
            except Exception as e:
                self.logger.log_exception(e, "fetch_latest_candles")
                self.bundle_status.config(text=f"Error for {symbol}: {str(e)}", foreground="red")
            finally:
                self.bundle_progress.stop()
                self.bundle_progress.grid_remove()
                self.bundle_latest_btns[idx].config(state=tk.NORMAL)
                self.fetch_cancelled_flag = False
                self.root.update()

        threading.Thread(target=task, daemon=True).start()

    def _build_orderbook_tab(self, parent):
        """Интерфейс для просмотра стакана ордеров."""
        parent.columnconfigure(1, weight=1)
        parent.columnconfigure(3, weight=1)

        # Символ
        ttk.Label(parent, text="Symbol:").grid(row=0, column=0, padx=5, pady=5, sticky="w")
        self.ob_symbol = ttk.Entry(parent, width=15)
        self.ob_symbol.grid(row=0, column=1, padx=5, pady=5, sticky="ew")
        self.ob_symbol.insert(0, "BTCUSDT")

        # Категория
        ttk.Label(parent, text="Category:").grid(row=0, column=2, padx=5, pady=5, sticky="w")
        self.ob_category = ttk.Combobox(parent, values=["spot", "linear", "inverse", "option"], width=10)
        self.ob_category.set("linear")
        self.ob_category.grid(row=0, column=3, padx=5, pady=5, sticky="ew")

        # Глубина (лимит)
        ttk.Label(parent, text="Limit (depth):").grid(row=1, column=0, padx=5, pady=5, sticky="w")
        self.ob_limit = ttk.Spinbox(parent, from_=1, to=1000, width=10)
        self.ob_limit.set(25)
        self.ob_limit.grid(row=1, column=1, padx=5, pady=5, sticky="ew")

        # Кнопка
        self.ob_fetch_btn = ttk.Button(parent, text="Get Order Book", command=self.fetch_orderbook)
        self.ob_fetch_btn.grid(row=2, column=0, columnspan=4, pady=10)

        # Статус
        self.ob_status = ttk.Label(parent, text="", foreground="blue")
        self.ob_status.grid(row=3, column=0, columnspan=4, pady=5)

        # Treeview для отображения стакана
        columns = ("bid_price", "bid_size", "ask_price", "ask_size")
        self.ob_tree = ttk.Treeview(parent, columns=columns, show="headings", height=20)
        self.ob_tree.heading("bid_price", text="Bid Price")
        self.ob_tree.heading("bid_size", text="Bid Size")
        self.ob_tree.heading("ask_price", text="Ask Price")
        self.ob_tree.heading("ask_size", text="Ask Size")
        self.ob_tree.column("bid_price", width=120, anchor=tk.CENTER)
        self.ob_tree.column("bid_size", width=100, anchor=tk.CENTER)
        self.ob_tree.column("ask_price", width=120, anchor=tk.CENTER)
        self.ob_tree.column("ask_size", width=100, anchor=tk.CENTER)
        self.ob_tree.grid(row=4, column=0, columnspan=4, padx=5, pady=5, sticky="nsew")

        # Scrollbar
        scroll = ttk.Scrollbar(parent, orient="vertical", command=self.ob_tree.yview)
        scroll.grid(row=4, column=4, sticky="ns")
        self.ob_tree.configure(yscrollcommand=scroll.set)

        parent.rowconfigure(4, weight=1)


    def fetch_orderbook(self):
        """Получение и отображение стакана ордеров."""
        if self.exchange_var.get() != config.EXCHANGE_BYBIT:
            messagebox.showerror("Error", "Order Book is only available for Bybit exchange.\nPlease switch to Bybit in the OHLCV tab.")
            return

        symbol = self.ob_symbol.get().strip().upper()
        category = self.ob_category.get()
        try:
            limit = int(self.ob_limit.get())
        except ValueError:
            messagebox.showerror("Error", "Limit must be integer")
            return

        self.ob_fetch_btn.config(state=tk.DISABLED)
        self.ob_status.config(text="Fetching order book...", foreground="blue")
        self.root.update()

        try:
            if not self.fetcher:
                raise Exception("Fetcher not initialized")
            result = self.fetcher.get_orderbook(category=category, symbol=symbol, limit=limit)
            if not result:
                raise Exception("Empty response from API")

            bids = result.get("b", [])
            asks = result.get("a", [])
            # Ограничим отображение до лимита (API уже вернуло limit уровней, но на всякий случай)
            max_levels = max(len(bids), len(asks))
            # Строим таблицу: для каждого уровня выводим bid и ask (если есть)
            rows = []
            for i in range(max_levels):
                bid_price = bids[i][0] if i < len(bids) else ""
                bid_size = bids[i][1] if i < len(bids) else ""
                ask_price = asks[i][0] if i < len(asks) else ""
                ask_size = asks[i][1] if i < len(asks) else ""
                rows.append((bid_price, bid_size, ask_price, ask_size))

            # Очищаем treeview
            for row in self.ob_tree.get_children():
                self.ob_tree.delete(row)

            # Вставляем данные
            for row in rows:
                self.ob_tree.insert("", tk.END, values=row)

            self.ob_status.config(text=f"Order book loaded ({len(rows)} levels)", foreground="green")
            self.log_to_console(f"Order book fetched for {symbol} ({category}), depth={limit}")
        except Exception as e:
            self.logger.log_exception(e, "fetch_orderbook")
            self.ob_status.config(text=f"Error: {str(e)}", foreground="red")
        finally:
            self.ob_fetch_btn.config(state=tk.NORMAL)

    def start_auto_mode(self, idx):
        """Запуск автоматического обновления для выбранной монеты"""
        if self.auto_mode_enabled and self.auto_mode_idx == idx:
            return
        
        # Останавливаем предыдущий режим
        self.stop_auto_mode(idx)
        
        self.auto_mode_enabled = True
        self.auto_mode_idx = idx
        
        # Обновляем индикатор
        if hasattr(self, 'auto_indicator'):
            self.auto_indicator.config(text="🟢 Auto ON", foreground="green")
        
        symbol = self.bundle_symbols[idx].get().strip().upper()
        count = int(self.bundle_latest_candles_count[idx].get())
        folder = self.bundle_folders[idx].get().strip()
        
        if not folder:
            messagebox.showerror("Error", "Please select output folder")
            self.stop_auto_mode(idx)
            return
        
        self.log_to_console(f"🔄 Auto mode STARTED for {symbol} (updates every 15 min)")
        self.bundle_status.config(text=f"Auto mode active for {symbol}", foreground="green")
        
        def auto_task():
            while self.auto_mode_enabled and self.auto_mode_idx == idx:
                now = datetime.now()
                minutes = now.minute
                # Следующий запуск в 00:01, 00:16, 00:31, 00:46
                next_minute = ((minutes // 15) + 1) * 15
                if next_minute == 60:
                    next_minute = 0
                    next_hour = now.hour + 1
                else:
                    next_hour = now.hour
                
                next_run = now.replace(hour=next_hour, minute=next_minute, second=1, microsecond=0)
                if next_run <= now:
                    next_run += timedelta(hours=1)
                
                sleep_seconds = (next_run - now).total_seconds()
                self.log_to_console(f"⏰ Next auto-update for {symbol} at {next_run.strftime('%H:%M:%S')}")
                
                # Ждём до следующего запуска
                for _ in range(int(sleep_seconds)):
                    if not self.auto_mode_enabled or self.auto_mode_idx != idx:
                        return
                    time.sleep(1)
                
                # Выполняем обновление
                if self.auto_mode_enabled and self.auto_mode_idx == idx:
                    self.log_to_console(f"🔄 Auto-updating {symbol}...")
                    self.clear_output_folder(idx)
                    self.fetch_latest_candles(idx)
                    # Воспроизводим звук после обновления
                    self.play_notification_sound()
                    self.log_to_console(f"🔔 Sound notification played for {symbol}")
        
        self.auto_mode_thread = threading.Thread(target=auto_task, daemon=True)
        self.auto_mode_thread.start()

    def stop_auto_mode(self, idx):
        """Остановка автоматического обновления"""
        if self.auto_mode_enabled and self.auto_mode_idx == idx:
            self.auto_mode_enabled = False
            symbol = self.bundle_symbols[idx].get().strip().upper()
            self.log_to_console(f"🛑 Auto mode STOPPED for {symbol}")
            self.bundle_status.config(text=f"Auto mode stopped", foreground="blue")
            
            # Обновляем индикатор
            if hasattr(self, 'auto_indicator'):
                self.auto_indicator.config(text="⚪ Auto OFF", foreground="gray")

    def update_auto_status(self, idx, is_active):
        """Обновление индикатора авторежима"""
        if hasattr(self, 'auto_indicator'):
            if is_active:
                self.auto_indicator.config(text="🟢 Auto ON", foreground="green")
            else:
                self.auto_indicator.config(text="⚪ Auto OFF", foreground="gray")

    def cancel_fetch_bundle(self, idx):
        """Отмена текущей загрузки для конкретной монеты"""
        self.fetch_cancelled_flag = True
        self.bundle_status.config(text=f"Cancelling fetch for {self.bundle_symbols[idx].get()}...", foreground="orange")
        self.log_to_console(f"🛑 Cancelling fetch for {self.bundle_symbols[idx].get()}")

    def browse_sound_file(self):
        """Выбор пользовательского WAV файла для оповещения"""
        filename = filedialog.askopenfilename(
            title="Select Sound File",
            filetypes=[("WAV files", "*.wav"), ("All files", "*.*")]
        )
        if filename:
            self.sound_file.set(filename)
            self.sound_file_combo.set(filename)
            self.log_to_console(f"Sound file selected: {filename}")

    def play_notification_sound(self):
        """Воспроизведение звукового оповещения"""
        if not self.sound_enabled.get():
            return
        
        sound = self.sound_file.get()
        try:
            if sound.endswith('.wav') and os.path.exists(sound):
                winsound.PlaySound(sound, winsound.SND_FILENAME | winsound.SND_ASYNC)
            elif sound in ["SystemAsterisk", "SystemExclamation", "SystemHand", "SystemQuestion", "SystemDefault"]:
                winsound.PlaySound(sound, winsound.SND_ALIAS | winsound.SND_ASYNC)
            else:
                # Звук по умолчанию
                winsound.PlaySound("SystemAsterisk", winsound.SND_ALIAS | winsound.SND_ASYNC)
        except Exception as e:
            self.log_to_console(f"Sound error: {e}")

    # ---------- Help Tab ----------
    def _build_help_tab(self, parent):
        parent.columnconfigure(0, weight=1)
        parent.rowconfigure(0, weight=1)
        text_widget = tk.Text(parent, wrap=tk.WORD, font=("Segoe UI", 10), bg="#f9f9f9")
        text_widget.grid(row=0, column=0, sticky="nsew", padx=5, pady=5)
        scrollbar = ttk.Scrollbar(parent, orient="vertical", command=text_widget.yview)
        scrollbar.grid(row=0, column=1, sticky="ns")
        text_widget.configure(yscrollcommand=scrollbar.set)
        help_text = self._get_help_text()
        text_widget.insert(tk.END, help_text)
        text_widget.configure(state=tk.DISABLED)

    def _build_public_trades_tab(self, parent):
        """Вкладка для загрузки public trades через bybit-history."""
        parent.columnconfigure(1, weight=1)

        # Символ
        ttk.Label(parent, text="Symbol (e.g. BTCUSDT):").grid(row=0, column=0, padx=5, pady=5, sticky="w")
        self.trades_symbol = ttk.Entry(parent, width=20)
        self.trades_symbol.grid(row=0, column=1, padx=5, pady=5, sticky="ew")
        self.trades_symbol.insert(0, "BTCUSDT")

        # Дата начала
        ttk.Label(parent, text="Start Date (YYYY-MM-DD):").grid(row=1, column=0, padx=5, pady=5, sticky="w")
        self.trades_start_date = ttk.Entry(parent, width=15)
        self.trades_start_date.grid(row=1, column=1, padx=5, pady=5, sticky="w")
        self.trades_start_date.insert(0, (datetime.now() - timedelta(days=7)).strftime("%Y-%m-%d"))

        # Дата окончания
        ttk.Label(parent, text="End Date (YYYY-MM-DD):").grid(row=2, column=0, padx=5, pady=5, sticky="w")
        self.trades_end_date = ttk.Entry(parent, width=15)
        self.trades_end_date.grid(row=2, column=1, padx=5, pady=5, sticky="w")
        self.trades_end_date.insert(0, datetime.now().strftime("%Y-%m-%d"))

        # Папка для сохранения
        ttk.Label(parent, text="Output Folder:").grid(row=3, column=0, padx=5, pady=5, sticky="w")
        self.trades_output_folder = ttk.Entry(parent, width=40)
        self.trades_output_folder.grid(row=3, column=1, padx=5, pady=5, sticky="ew")
        self.trades_output_folder.insert(0, str(Path.home() / "Desktop" / "bybit_trades"))
        ttk.Button(parent, text="Browse", command=self._browse_trades_folder).grid(row=3, column=2, padx=5, pady=5)

        # Кнопка старта
        self.trades_start_btn = ttk.Button(parent, text="Start Download", command=self.start_public_trades_download)
        self.trades_start_btn.grid(row=4, column=0, columnspan=3, pady=15)

        # Статус
        self.trades_status = ttk.Label(parent, text="", foreground="blue")
        self.trades_status.grid(row=5, column=0, columnspan=3, pady=5)

        # Лог (текстовое поле)
        log_frame = ttk.LabelFrame(parent, text="Download Log", padding="5")
        log_frame.grid(row=6, column=0, columnspan=3, sticky="nsew", pady=5)
        parent.rowconfigure(6, weight=1)
        log_frame.columnconfigure(0, weight=1)
        log_frame.rowconfigure(0, weight=1)

        self.trades_log = tk.Text(log_frame, height=15, wrap=tk.WORD, font=("Courier", 9))
        self.trades_log.grid(row=0, column=0, sticky="nsew")
        scroll = ttk.Scrollbar(log_frame, orient="vertical", command=self.trades_log.yview)
        scroll.grid(row=0, column=1, sticky="ns")
        self.trades_log.configure(yscrollcommand=scroll.set)

    def _browse_trades_folder(self):
        folder = filedialog.askdirectory()
        if folder:
            self.trades_output_folder.delete(0, tk.END)
            self.trades_output_folder.insert(0, folder)

    def start_public_trades_download(self):
        """Запускает bybit-history в отдельном потоке."""
        symbol = self.trades_symbol.get().strip().upper()
        start_date = self.trades_start_date.get().strip()
        end_date = self.trades_end_date.get().strip()
        output_dir = self.trades_output_folder.get().strip()

        if not symbol:
            messagebox.showerror("Error", "Please enter a symbol (e.g. BTCUSDT)")
            return
        if not start_date or not end_date:
            messagebox.showerror("Error", "Please enter start and end dates (YYYY-MM-DD)")
            return
        if not output_dir:
            messagebox.showerror("Error", "Please select an output folder")
            return

        # Создаём папку, если её нет
        os.makedirs(output_dir, exist_ok=True)

        self.trades_start_btn.config(state=tk.DISABLED)
        self.trades_status.config(text="Downloading...", foreground="blue")
        self.trades_log.delete(1.0, tk.END)
        self.root.update()

        def task():
            try:
                # Формируем команду
                cmd = find_bybit_cmd() + [
                    "--start-date", start_date,
                    "--end-date", end_date,
                    "--coins", symbol,
                    "--data-types", "trading",
                    "--output-dir", output_dir
                ]
                self.trades_log.insert(tk.END, f"Running: {' '.join(cmd)}\n\n")
                self.trades_log.see(tk.END)
                self.root.update()

                # Запускаем процесс
                process = subprocess.Popen(
                    cmd,
                    stdout=subprocess.PIPE,
                    stderr=subprocess.STDOUT,
                    text=True,
                    encoding="utf-8",
                    errors="replace",
                    creationflags=subprocess.CREATE_NO_WINDOW if sys.platform == "win32" else 0
                )

                # Читаем вывод построчно
                for line in process.stdout:
                    self.trades_log.insert(tk.END, line)
                    self.trades_log.see(tk.END)
                    self.root.update()

                process.wait()

                if process.returncode == 0:
                    self.trades_status.config(text="Download completed successfully", foreground="green")
                    self.trades_log.insert(tk.END, "\n✅ Download finished.\n")
                else:
                    self.trades_status.config(text=f"Download failed (exit code {process.returncode})", foreground="red")
                    self.trades_log.insert(tk.END, f"\n❌ Process exited with code {process.returncode}\n")

            except FileNotFoundError:
                self.trades_status.config(text="bybit-history not found. Install: pip install bybit-history", foreground="red")
                self.trades_log.insert(tk.END, "Error: 'bybit-history' command not found.\nPlease install it: pip install bybit-history\n")
            except Exception as e:
                self.trades_status.config(text=f"Error: {str(e)[:80]}", foreground="red")
                self.trades_log.insert(tk.END, f"Exception: {e}\n")
            finally:
                self.trades_start_btn.config(state=tk.NORMAL)
                self.root.update()

        threading.Thread(target=task, daemon=True).start()

    def _get_help_text(self) -> str:
        return """
╔════════════════════════════════════════════════════════════════════════════════════════════════╗
    ║                         CRYPTO DATA FETCHER – ПОЛНОЕ РУКОВОДСТВО                               ║
    ╚════════════════════════════════════════════════════════════════════════════════════════════════╝

    Это приложение позволяет загружать, анализировать и сохранять исторические и реальные данные
    криптовалют с бирж Bybit и Coinbase. Ниже описаны все вкладки и их возможности.

    ────────────────────────────────────────────────────────────────────────────────────────────────
    📊 1. ВКЛАДКА «OHLCV DATA»
    ────────────────────────────────────────────────────────────────────────────────────────────────
    Назначение: загрузка свечных данных (Open, High, Low, Close, Volume) за выбранный период.

    Параметры:
    • Coin Symbol – торговая пара. Примеры:
        - Для Bybit: BTCUSDT, ETHUSDT, SOLUSDT
        - Для Coinbase: BTC-USD, ETH-USD, SOL-USD
    • Market – Spot (спот) или Futures (фьючерсы). Доступно только для Bybit.
    • Timeframe – период одной свечи: 1m, 5m, 1h, 4h, 1d и т.д.
    • Start Date / End Date – диапазон дат (YYYY-MM-DD).
    • Кнопка «Test Connection» – проверяет доступность выбранной биржи.
    • Кнопка «Fetch OHLCV» – запускает загрузку данных.
    • Кнопка «Save Data» – сохраняет таблицу (с индикаторами) в CSV.
    • Technical Indicators – можно включить расчёт RSI, ADX, EMA 21/50, MACD, Bollinger Bands.

    Пример:
    1) Выберите Bybit, символ BTCUSDT, Market=Futures, Timeframe=1h.
    2) Укажите Start Date = 2025-04-01, End Date = 2025-04-07.
    3) Нажмите «Fetch OHLCV».
    4) После загрузки включите RSI и EMA 21, затем «Save Data».

    ────────────────────────────────────────────────────────────────────────────────────────────────
    📈 2. ВКЛАДКА «FUNDAMENTALS» (только Bybit)
    ────────────────────────────────────────────────────────────────────────────────────────────────
    Назначение: получение фундаментальных показателей фьючерсного рынка.

    Что вы получите:
    • Open Interest – открытый интерес (общее количество контрактов).
    • Funding Rate – текущая ставка финансирования (положительная = лонги платят шортам).
    • Long/Short Ratio – отношение длинных позиций к коротким.
    • Fear & Greed Index – индекс страха и жадности из alternative.me (0 – экстремальный страх, 100 – экстремальная жадность).

    Параметры:
    • Symbol – например BTCUSDT.
    • Interval – таймфрейм для OI и L/S (5min, 15min, 1h, 1d и т.д.).
    • Start Date / End Date – диапазон.
    • «Fetch All Fundamentals» – загружает все четыре показателя и объединяет их по времени в одну таблицу.
    • «Save Fundamentals as CSV» – сохраняет таблицу.

    Пример:
    Установите Interval = 1h, даты – последние 7 дней, нажмите «Fetch All Fundamentals».
    Вы увидите колонки: Timestamp, Open_Interest, Funding_Rate, Long_Short_Ratio,
    Fear_Greed_Value, Market_Sentiment. Это поможет оценить настроение рынка.

    ────────────────────────────────────────────────────────────────────────────────────────────────
    📰 3. ВКЛАДКА «CRYPTO NEWS»
    ────────────────────────────────────────────────────────────────────────────────────────────────
    Агрегация новостей из RSS-лент (CoinTelegraph, CoinDesk, Decrypt) с фильтром по монете.

    Параметры:
    • Coin Symbol – базовый символ монеты (например BTC, ETH, XRP). Допустим ввод без USDT.
    • Limit – максимальное количество новостей (5–50).
    • Max Age (days) – за какой период брать новости (1, 3, 7, 14, 30 дней или All).
    • «Get News» – ищет новости, содержащие в заголовке введённый символ.
    • «Save News as CSV» – сохраняет таблицу (дата, заголовок, краткое содержание, ссылка).

    Пример:
    Введите «SOL», Limit=20, Max Age=7 дней. Нажмите «Get News».
    Получите список последних новостей о Solana. Кликните на ссылку, чтобы открыть в браузере.

    ────────────────────────────────────────────────────────────────────────────────────────────────
    💱 4. ВКЛАДКА «TRADING RECORDS» (только Bybit)
    ────────────────────────────────────────────────────────────────────────────────────────────────
    Отображает последние реальные сделки (трейды) на рынке – кто, когда, по какой цене и в каком объёме купил/продал.

    Параметры:
    • Symbol – торговая пара, например BTCUSDT.
    • Category – spot или linear (фьючерсы).
    • Limit – количество записей (до 1000).
    • «Get Trading Records» – загружает последние сделки.
    • «Save as CSV» – сохраняет таблицу.

    Пример:
    Выберите Symbol = ETHUSDT, Category = linear, Limit = 100, нажмите «Get Trading Records».
    Вы увидите таблицу с временем, ценой, объёмом и стороной (Buy/Sell). Крупные объёмы могут указывать на активность институционалов.

    ────────────────────────────────────────────────────────────────────────────────────────────────
    📦 5. ВКЛАДКА «DATA BUNDLE» (МАССОВАЯ ВЫГРУЗКА)
    ────────────────────────────────────────────────────────────────────────────────────────────────
    Позволяет одной кнопкой сохранить сразу несколько файлов: цены, фундаментальные данные и новости.

    Кнопка 1 – «Initial Snapshot (History)»:
        - Загружает цены (таймфреймы 15m и 1h)
        - Фундаментальные данные (интервалы 15min и 1h)
        - Новости (за указанное количество дней)
        - Все файлы сохраняются в выбранную папку.

    Кнопка 2 – «Current Data (Today only)»:
        - Загружает только цены (15m) и фундамент (15min) за сегодняшний день.

    Настройки:
    • Coin Symbol – торговая пара (например BTCUSDT).
    • Days back – глубина истории для Snapshot (максимум 365).
    • Output folder – папка для сохранения. Можно выбрать через кнопку Browse.

    Пример использования (ежедневный отчёт на 30 дней):
    1) Укажите BTCUSDT, Days back = 30, выберите папку D:\\Reports\BTC.
    2) Нажмите «Initial Snapshot» – через несколько минут в папке появятся 5–7 CSV-файлов.
    3) Каждый день нажимайте «Current Data» – будут добавляться файлы с данными за сегодня.

    ────────────────────────────────────────────────────────────────────────────────────────────────
    ⚙️ ОБЩИЕ СОВЕТЫ
    ────────────────────────────────────────────────────────────────────────────────────────────────
    • Все длительные операции выполняются в фоновом потоке – интерфейс не зависает.
    • Если вы переключаете биржу (Bybit ↔ Coinbase), некоторые вкладки могут стать недоступными – приложение предупредит.
    • Лог-файлы ошибок хранятся в папке logs (создаётся автоматически).
    • Для работы фундаментальных данных и Fear&Greed нужен API-ключ Coinalyze (прописывается в .env).
    • Если не хотите использовать фундаментал, просто не открывайте вкладку – ошибки не будет.

    ────────────────────────────────────────────────────────────────────────────────────────────────
    📞 ПОМОЩЬ И ПОДДЕРЖКА
    ────────────────────────────────────────────────────────────────────────────────────────────────
    • При возникновении ошибок просмотрите консоль (вкладка «Log»).
    • Если данные не загружаются, проверьте интернет‑соединение.
    • Для Bybit может потребоваться VPN (встроенного нет, но вы можете использовать внешний).
    • При проблемах с датами – убедитесь, что формат YYYY-MM-DD.

    Спасибо, что пользуетесь нашим приложением! Удачной торговли! 🚀
"""

# Compatibility alias
CryptoDataFetcherGUI = BybitGUI