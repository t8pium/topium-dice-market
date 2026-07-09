# Topium Dice Market

A lightweight Python market simulator that turns coin flips and dice rolls into an interactive candlestick chart.

The project is built around one simple idea: randomness can still form structure. Every raw candle starts as five small coin-and-dice moves, then the app aggregates those 1-minute candles into higher timeframes and displays them with a clean dark chart interface.

## What it does

Topium Dice Market generates fake OHLC candles locally and visualizes them in a chart window. It is not connected to real market data. The purpose is to experiment with market-like movement, timeframe aggregation, chart navigation, and simple technical indicators without relying on an external data feed.

## Features

- Coin-flip and dice-roll candle engine
- Dark candlestick chart UI
- Start, stop, step, reset, and quick-generate controls
- TradingView-style timeframe buttons:
  - `1m`, `3m`, `5m`, `15m`, `30m`, `45m`
  - `1h`, `2h`, `4h`
  - `1D`, `1W`, `1M`
- Pan and zoom navigation
- VWAP indicator
- VWAP deviation bands:
  - Band 1: VWAP ± 1σ
  - Band 2: VWAP ± 2σ
  - Band 3: VWAP ± 3σ
- Subtle starting-price reference line
- Dice scale control
- Coin bias control
- Speed control
- Visible bars control
- CSV export

## Candle engine

Each generated candle represents one simulated minute.

For each 1-minute candle:

1. The app creates five internal moves.
2. Each move flips a coin to choose direction.
3. Each move rolls a dice from 1 to 6.
4. Price movement is calculated as:

```text
movement = direction × dice_roll × dice_scale
```

A positive coin bias increases the chance of upward movement. A negative coin bias increases the chance of downward movement.

## Timeframe aggregation

The app always generates raw `1m` candles first. Higher timeframes are built from those candles:

- Open = first candle open
- High = highest high
- Low = lowest low
- Close = last candle close
- Volume = summed internal fake volume

This keeps the engine simple while allowing the chart to behave like a basic multi-timeframe terminal.

## Requirements

- Python 3.10+
- Matplotlib

Install dependencies:

```bash
pip install -r requirements.txt
```

## Run

```bash
python topium_dice_market.py
```

## Controls

| Control | Purpose |
|---|---|
| Start / Stop | Runs or pauses live candle generation |
| Step | Generates one 1-minute candle |
| +10 | Generates ten candles instantly |
| Reset | Clears the simulation |
| Reset View | Jumps the chart back to the newest candles |
| Dice Scale | Controls the size of each dice-based move |
| Coin Bias | Tilts the probability of upward or downward movement |
| Speed | Controls how quickly live candles are generated |
| Visible Bars | Controls how many candles are shown on screen |

## Chart navigation

- Drag left/right to pan through chart history.
- Use the mouse wheel to zoom in or out.
- Use Reset View to return to the latest candles.

## Why this exists

This started as a small experiment in turning simple randomness into something that feels market-like. The point was not to predict real prices, but to build a clear, local, understandable charting prototype that can later grow into a more complete backtesting tool.

## Future ideas

- Import OHLC CSV files
- Add paper trading
- Add stop-loss and take-profit lines
- Add strategy testing
- Add more indicators
- Package as a desktop app
