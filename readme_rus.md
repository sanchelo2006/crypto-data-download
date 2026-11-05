<div align="center">

# 📊 Crypto Data Fetcher

**Настольное приложение для сбора и анализа криптовалютных данных с Bybit и Coinbase**

![Python](https://img.shields.io/badge/Python-3.13+-3776AB?style=for-the-badge&logo=python&logoColor=white)
![Tkinter](https://img.shields.io/badge/GUI-Tkinter-blue?style=for-the-badge)
![Bybit](https://img.shields.io/badge/Bybit-Spot%20%26%20Futures-F7A600?style=for-the-badge)
![Coinbase](https://img.shields.io/badge/Coinbase-USA-0052FF?style=for-the-badge)
![Platform](https://img.shields.io/badge/Platform-Windows-0078D4?style=for-the-badge&logo=windows)

Один инструмент для загрузки OHLCV, фундаментальных метрик, стакана заявок, публичных сделок и новостей — с расчётом технических индикаторов и экспортом в CSV.
Основное предназначение - выгрузка данных биржи для нейросети для последующего ее анализа

</div>

---

## ✨ Возможности

| Вкладка | Что делает |
|---|---|
| 📊 **OHLCV Data** | Свечи Open/High/Low/Close/Volume с Bybit (Spot & Futures) и Coinbase. До 1000 свечей за запрос, автоматическая батчизация. |
| 📈 **Fundamentals** | Open Interest, Funding Rate, Long/Short Ratio, Fear & Greed Index — всё в одной таблице. |
| 📰 **Crypto News** | Агрегатор новостей из RSS: CoinTelegraph, CoinDesk, Decrypt, The Block, CryptoPanic и ещё 10+ источников. |
| 💱 **Trading Records** | Последние публичные сделки (до 1000) с указанием стороны Buy/Sell. |
| 📦 **Data Bundle** | Массовая выгрузка для **3 монет одновременно**: цены + индикаторы + фундамент + стакан + сделки. Одна кнопка — 6–8 CSV-файлов. |
| 📖 **Order Book** | Снапшот стакана заявок (глубина до 1000 уровней). |
| 📥 **Public Trades** | Загрузка исторических данных через CLI `bybit-history` с возобновлением и дедупликацией. |
| 🤖 **Auto Mode** | Автообновление данных каждые 15 минут (в 00:01, 00:16, 00:31, 00:46) со звуковым уведомлением. |
| 📘 **Help & Guide** | Встроенное руководство пользователя. |

---

## 🧮 Технические индикаторы

Все индикаторы рассчитываются по методологии Bybit:

- 📉 **RSI (14)** — с использованием EMA (а не SMA)
- 📊 **ADX (14)** — с Wilder's smoothing
- 📈 **EMA 21 / 50 / 200**
- 🌊 **MACD (12, 26, 9)** — линия, сигнальная, гистограмма
- 🎯 **Bollinger Bands (20, 2σ)**

Приложение корректно обрабатывает «прогрев» индикаторов: загружает расширенный период, чтобы значения EMA200 на часовике были валидными с первой строки целевого диапазона.

---

## 📦 Требования

- **Python** 3.13 или выше
- **ОС:** Windows 10/11 (протестировано), Linux/macOS — должны работать, но с оговорками по шрифтам
- **Интернет** — для доступа к API бирж и RSS-лентам
- **~50 МБ** на диске (без учёта скачанных данных)

---

## 🚀 Установка

### 1. Клонируйте репозиторий

```cmd
git clone https://github.com/yourusername/crypto-data-fetcher.git
cd crypto-data-fetcher
```

### 2. Создайте виртуальное окружение

```
python -m venv .venv
.venv\Scripts\activate
```

### 3. Установите зависимости

```
python -m pip install --upgrade pip
python -m pip install -r requirements.txt
```

`requirements.txt` содержит:

```
pybit>=5.0.0
pandas>=1.3.0
numpy>=1.21.0
requests>=2.28.0
python-dotenv>=0.19.0
feedparser>=6.0.0
python-dateutil>=2.8.0
bybit-history>=0.1.3
```

### 4. Запустите приложение

```
python main.py
```

---

## 🎯 Быстрый старт

1. **Выберите биржу** во вкладке OHLCV Data — Bybit или Coinbase.
2. **Введите символ:** `BTCUSDT` (Bybit) или `BTC-USD` (Coinbase).
3. **Укажите период** и нажмите «Fetch OHLCV».
4. **Включите индикаторы** (RSI, EMA, MACD и т.д.) через чекбоксы.
5. **Сохраните данные** — получите CSV со всеми колонками.

Для загрузки целого набора данных (цены + фундамент + стакан + сделки) для **трёх монет сразу** — используйте вкладку **Data Bundle**.

---

## 📁 Структура проекта

```
OHLC_APP/
├── main.py                  # Точка входа
├── gui.py                   # Интерфейс (Tkinter, вкладки, логика UI)
├── fetcher.py               # Фабрика фетчеров бирж + Bybit fetcher
├── coinbase_fetcher.py      # Фетчер Coinbase
├── bybit_fundamentals.py    # OI, Funding Rate, Long/Short, Fear & Greed
├── indicators.py            # RSI, ADX, EMA, MACD, Bollinger Bands
├── news_fetcher.py          # RSS-агрегатор новостей
├── config.py                # Константы, таймфреймы, настройки GUI
├── logger.py                # Логирование с ротацией
├── requirements.txt
├── README.md                # ← этот файл (RU)
└── README.en.md             # английская версия
```

---

## ⚙️ Конфигурация

Приложение не требует API-ключей для публичных данных. Если вы планируете расширять функционал (приватные эндпоинты Coinalyze и т.п.), создайте файл `.env` в корне:

```
COINALYZE_API_KEY="ваш_ключ"
```

Файл `.env` не должен попадать в git — добавьте его в `.gitignore`.

---

## 🔧 Логи и отладка

- Логи пишутся в папку `logs/` рядом с приложением.
- В окне есть встроенная консоль внизу — там видно прогресс загрузки и ошибки в реальном времени.
- Меню **Help → View Error Log** открывает `logs/error.log`.

---

## 🐛 Решение типичных проблем
<details>
<summary><b>❌ «No module named 'X'» после установки</b></summary>
Скорее всего, активирован не тот venv. Проверьте:

```
where python
where pip
python -c "import sys; print(sys.executable)"
```

Все три пути должны указывать внутрь `.venv\Scripts\`. Если нет — пересоздайте venv:

```
deactivate
rmdir /s /q .venv
python -m venv .venv
.venv\Scripts\activate
python -m pip install -r requirements.txt
```
</details><details>
<summary><b>❌ «'bybit-history' command not found»</b></summary>
Пакет `bybit-history` — это CLI, а не библиотека. Команда может не попасть в PATH внутри venv.

Проверьте:

```
where bybit-history
python -m bybit_history.bybit_data_downloader --help
```

Второй вариант работает всегда — приложение использует его как fallback.
</details><details>
<summary><b>⏱ Долгая загрузка на 1m-таймфрейме с Coinbase</b></summary>
Coinbase ограничивает историю для мелких таймфреймов:

| Таймфрейм ↕▾ | Максимум истории ↕▾ |
|---|---|
| −1m | 24 часа |
| −5m | 7 дней |
| −15m | 30 дней |
| −1h | 90 дней |
| −1d | 365 дней |
⚙

Для больших периодов используйте Bybit или крупный таймфрейм.
</details><details>
<summary><b>🔌 Bybit не отвечает</b></summary>
Из некоторых регионов API Bybit недоступен. Встроенный VPN в приложении был удалён — используйте внешний VPN/прокси или переключитесь на Coinbase.
</details>
---

## 🤝 Вклад в проект

Pull requests приветствуются. По багам — открывайте Issue с указанием:

1. Версии Python и ОС
2. Полного текста ошибки из лога
3. Символа, таймфрейма и диапазона дат, при которых воспроизводится

---

## 📄 Лицензия

MIT License — см. файл `LICENSE.txt`.

---
<div align="center">
**⭐ Если проект оказался полезен — поставьте звезду на GitHub!**

Сделано с ❤️ на Python + Tkinter + PyBit
</div>
