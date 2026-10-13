# Quantitative Pairs Trading Strategy & Monitor

A statistical arbitrage (pairs trading) research project on **Visa (V)** and **Mastercard (MA)**, with a held-out backtest and a monitoring bot that sends spread alerts to Discord.

> **Disclaimer:** Educational project. The bot sends alerts only and does not place orders. Nothing here is financial advice.

## Project Structure

* `/docs/linear_regression_theory.pdf` - Theory of the OLS regression model: residual analysis, matrix algebra, autocorrelation tests (LaTeX).
* `/docs/regression_data_generation.nb` - Wolfram Mathematica notebook used to prototype the mathematical foundations and generate the 3D data distributions used in the documentation.
* `/research/pairs_trading_research.ipynb` - Exploratory analysis with `yfinance`: regression, spread and Z-score bands, ADF test. *Exploratory cells use the full sample and are not used for the reported results.*
* `/research/backtest_research.ipynb` - The train/test backtest that produces the results below.
* `pairs_trading_bot.py` - Monitoring bot that sends alerts to Discord when the spread breaches ±2σ (see "Alert Bot" below).

## Backtest Methodology

1. **Data:** daily closing prices from `yfinance`, 2019-01-01 to 2026-10-13. Data from Yahoo Finance can change slightly between downloads.
2. **Split:**
   * Training: 2019 - 2021 (used only to fit the hedge ratio and run the cointegration test).
   * Test 1: Jan 2022 - Oct 2024.
   * Test 2: Oct 2024 - Oct 2026.
3. **Hedge ratio:** OLS slope of MA on V, estimated on the training period only and then kept fixed.
4. **Spread:** `spread = MA - beta * V`.
5. **Signals:** Z-score computed from a 60-day rolling mean and standard deviation, **lagged by one day** so only past data is used. Enter short at Z > 2, long at Z < -2, exit when Z crosses 0. Signals are applied to the next day's return.
6. **Costs and metrics:** 10 bps of deployed capital per position change. No borrowing costs or bid-ask spread. Sharpe ratio uses a risk-free rate of 0 (a long-short pair is roughly self-financing). Return is measured on deployed capital (`|Y price| + |beta| x X price`).
7. **Parameters:** the 60-day window and ±2σ threshold were chosen in advance and not tuned on the test data.

## Results

| Period | Annualized return | Sharpe | Max drawdown | Position changes* | Time in market |
|---|---|---|---|---|---|
| Test 1: Jan 2022 - Oct 2024 | 3.54% | 0.89 | -2.34% | 25 | 64.3% |
| Test 2: Oct 2024 - Oct 2026 | 1.74% | 0.48 | -3.34% | 18 | 46.3% |

\*Counts entries and exits separately, so the number of round trips is roughly half. *(Re-run after any code change and update these numbers.)*

**Cointegration test (Engle-Granger, training period only):** p-value = **0.1302**. This is **not significant at the 5% level**, so the pair did not pass a cointegration test on the training data.

## Limitations

* **Weak statistical evidence for the pair.** The training-period cointegration test is not significant (p = 0.13).
* **Small sample.** One pair and roughly 9-12 round trips per test window. With so few trades, Sharpe ratios have a large standard error (about ±0.7 for Test 1) and are indicative only, not statistically significant.
* **The pair was chosen by economic reasoning** (two companies in the same payments duopoly) before testing, not by a systematic scan. *(Edit this line so it accurately describes the pairs you tried.)*
* **Static hedge ratio.** Beta is fixed from 2019-2021 and may become stale; Test 2 results are weaker, consistent with the relationship drifting after Oct 2024.
* **Simplified costs:** no short-borrow fees, slippage, or bid-ask spread.

## Alert Bot

`pairs_trading_bot.py` calibrates an OLS fit on a rolling 1-year window, monitors real-time prices, and sends an alert to Discord when the spread breaches ±2 standard deviations. It also applies an ADF stationarity filter (p < 0.05) before alerting.

Note that the bot's configuration (rolling 1-year OLS plus ADF filter) **differs from the backtest above** (fixed hedge ratio, no filter), and the bot has not been backtested in that configuration. It is a monitoring tool and does not execute trades.

The Discord webhook URL is read from an environment variable (never hard-coded in the repository).

## Tech Stack

* Python (Pandas, NumPy, Statsmodels, yfinance)
* Jupyter Notebook
* LaTeX / Wolfram Mathematica
* Discord Webhooks API

## How to Run

```bash
pip install pandas numpy statsmodels yfinance matplotlib
# Research and backtest: open the notebooks in /research with Jupyter
# Bot (set your own webhook first):
export DISCORD_WEBHOOK_URL="your-webhook-url"
python pairs_trading_bot.py
