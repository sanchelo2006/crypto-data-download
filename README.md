# Bybit OHLCV Data Fetcher

A powerful desktop application to fetch historical OHLCV data from Bybit exchange with technical indicators.
Main usage - download market data and paste it for msg for neuronets for future analysis.

## Features

- 📊 **OHLCV Data**: Fetch Open, High, Low, Close, Volume data
- 🔄 **Batch Processing**: Automatically handles large date ranges (1000+ candles)
- 📈 **Technical Indicators**:
  - RSI (14) - Using EMA method
  - ADX (14) - Using Wilder's smoothing
  - EMA 21 & EMA 50
  - MACD (optional)
  - Bollinger Bands (optional)
- 💾 **Export to CSV**: Save data for further analysis
- 🐛 **Error Logging**: Automatic error logging with rotation
- 🎨 **User-Friendly GUI**: Easy to use interface

## System Requirements

- Windows 10/11 (64-bit)
- 2GB RAM minimum
- 100MB free disk space
- Internet connection

## Installation

### Installer (Recommended)

1. Download `BybitDataFetcher_Setup.exe`
2. Run the installer
3. Follow the installation wizard
4. Launch from Start Menu or Desktop

### Option 2: Portable Version

> Need to build the portable version yourself — due to size limit it can't be uploaded here.

1. Download `BybitDataFetcher.exe`
2. Run directly from any location
3. Creates logs folder automatically

## Usage Guide

### Basic Usage

1. **Enter Symbol**: BTCUSDT, ETHUSDT, etc.
2. **Select Market**: Spot or Futures (linear)
3. **Choose Timeframe**: 1m to 1M
4. **Set Date Range**: Start and end dates
5. **Select Indicators**: Check desired technical indicators
6. **Click "Fetch Data"**: Wait for data retrieval
7. **Save Data**: Click "Save Data" to export to CSV

### Batch Fetching

- Automatically fetches data in batches of 200 candles
- Progress bar shows current status
- Cancel button to stop long fetches
- Console log shows detailed batch information

### Technical Indicators

| Indicator         | Default Period | Notes                        |
|-------------------|----------------|------------------------------|
| RSI               | 14             | Uses EMA for averaging       |
| ADX               | 14             | Wilder's smoothing method    |
| EMA 21            | 21             | Exponential Moving Average   |
| EMA 50            | 50             | Exponential Moving Average   |
| MACD              | 12/26/9        | Optional indicator           |
| Bollinger Bands   | 20, 2σ         | Optional indicator           |

## Configuration

### config.ini

Located in the installation directory. Edit to change defaults:

```ini
[Defaults]
DefaultSymbol=BTCUSDT
DefaultMarket=spot
DefaultTimeframe=1h
DefaultDaysBack=30

[Indicators]
RSI=true
ADX=true
EMA21=true
EMA50=true
MACD=false
BollingerBands=false

[API]
Testnet=false
MaxRetries=3
RetryDelay=1

[Logging]
LogLevel=ERROR
MaxLogSizeMB=10
MaxBackupFiles=4
```

## Log Files

- **Location**: `%APPDATA%\BybitDataFetcher\logs\` or `\logs\` in the installation folder
- **Error Log**: `error.log` — Contains error messages and stack traces
- **Info Log**: `info.log` — Contains debug information
- **Rotation**: Logs rotate at 10MB, keeping 4 backups

## Troubleshooting

### Common Issues

**No data found**

- Check date range (older than 2020 may not be available)
- Verify symbol format (`BTCUSDT`, not `BTC/USDT`)
- Ensure market type is correct (spot vs linear)

**Indicator values don't match Bybit**

- Indicators are calculated using Bybit's standard methods
- First few values may be NaN (need sufficient data)

**API rate limiting**

- Built-in delays between batches
- Retry logic for failed requests
- Reduce date range if hitting limits

## Support

- **GitHub Issues**: Report bugs or request features
- **Email**: sanchelo2006@yandex.ru

## Uninstallation

### Windows

1. Open Control Panel
2. Go to Programs and Features
3. Find "Bybit OHLCV Data Fetcher"
4. Click Uninstall

### Manual

1. Delete installation folder
2. Remove Start Menu shortcuts
3. Delete logs folder (optional)

## License

MIT License — Free for personal and commercial use.

## Version History

### Version 3.0.0 (2024)

- Added technical indicators (RSI, ADX, EMA21, EMA50)
- Improved batch fetching algorithm
- Added error logging with rotation
- GUI improvements and console output
- Configurable defaults

### Version 2.0.0 (2024)

- Initial release
- Basic OHLCV fetching
- Batch processing support

## Credits

- Built with Python, tkinter, and PyBit
- Icon created with custom design
- Inno Setup for installer creation

## Disclaimer

This tool is for educational and informational purposes only. Cryptocurrency trading involves significant risk. Always verify data with official sources.

