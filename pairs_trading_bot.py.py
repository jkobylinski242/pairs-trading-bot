import yfinance as yf
import pandas as pd
import statsmodels.api as sm
from statsmodels.tsa.stattools import adfuller
import time
import requests
from datetime import datetime
import warnings

warnings.filterwarnings('ignore')

# --- CONFIGURATION ---
WEBHOOK_URL = "PASTE_WEHBOOK_URL_HERE"
DISCORD_PING = "@everyone"

PAIRS = [
    ("MA", "V"),
    ("PEP", "KO"),
    ("MSFT", "AMZN"),
    ("GOOGL", "META"),
    ("JPM", "BAC")
]


class MultiPairArbitrageBot:
    def __init__(self, pairs):
        self.pairs = pairs
        self.models = {}

    def calibrate_models(self):
        """Calibrating OLS models and testing cointegration (ADF) on historical 1-year data."""
        print(
            f"[{datetime.now().strftime('%H:%M:%S')}] Calibrating models and ADF testing for {len(self.pairs)} pairs...")

        for ticker1, ticker2 in self.pairs:
            try:
                df1 = yf.download(ticker1, period="1y", interval="1d", progress=False)
                df2 = yf.download(ticker2, period="1y", interval="1d", progress=False)

                close1 = df1['Close'].rename(columns={'Close': ticker1})
                close2 = df2['Close'].rename(columns={'Close': ticker2})
                data = pd.concat([close1, close2], axis=1).dropna()

                y = data.iloc[:, 0].squeeze()
                x = data.iloc[:, 1].squeeze()

                x_with_const = sm.add_constant(x)
                model = sm.OLS(y, x_with_const).fit()

                intercept = float(model.params.iloc[0])
                hedge_ratio = float(model.params.iloc[1])

                spread = y - (hedge_ratio * x) - intercept
                std = float(spread.std())

                # --- ADF TEST (Cointegration) ---
                adf_result = adfuller(spread.dropna())
                p_value = float(adf_result[1])

                self.models[(ticker1, ticker2)] = {
                    "intercept": intercept,
                    "hedge_ratio": hedge_ratio,
                    "std": std,
                    "p_value": p_value
                }

                cointegrated = "YES (Stationary)" if p_value < 0.05 else "NO (Non-stationary)"
                print(f"   [OK] {ticker1} vs {ticker2} | p-value: {p_value:.4f} -> Cointegration: {cointegrated}")

            except Exception as e:
                print(f"   [ERROR] Couldn't calibrate {ticker1} vs {ticker2}: {e}")

        print("-" * 60)

    def send_discord_message(self, message):
        """Sending a Discord message."""
        if WEBHOOK_URL == "PASTE_WEHBOOK_URL_HERE":
            return
        try:
            requests.post(WEBHOOK_URL, json={"content": message})
        except Exception as e:
            print(f"Error in sending message: {e}")

    def run_monitor(self):
        """Main loop - checking spreads and verifying cointegration before sending an alert."""
        print("Starting monitoring of the stock market...")

        while True:
            try:
                current_time = datetime.now().strftime('%H:%M:%S')
                print(f"\n[{current_time}] Market scanning...")

                report_lines = [f"📊 **Market report at {current_time} (with ADF test)**"]

                for (ticker1, ticker2), params in self.models.items():
                    df1 = yf.download(ticker1, period="1d", interval="1m", progress=False)
                    df2 = yf.download(ticker2, period="1d", interval="1m", progress=False)

                    if not df1.empty and not df2.empty:
                        price1 = float(df1['Close'].iloc[-1].iloc[0])
                        price2 = float(df2['Close'].iloc[-1].iloc[0])

                        current_spread = price1 - (params['hedge_ratio'] * price2) - params['intercept']

                        upper_band = 2 * params['std']
                        lower_band = -2 * params['std']
                        p_val = params['p_value']

                        print(f"   -> [{ticker1} vs {ticker2}] Spread: {current_spread:.2f} | p-val: {p_val:.3f}")

                        # Adding p-value information
                        status_icon = "🟢" if p_val < 0.05 else "⚠️"
                        report_lines.append(
                            f"• `{ticker1} vs {ticker2}`: Spread = **{current_spread:.2f}** | p-val: {p_val:.3f} {status_icon}")

                        # Sending alert if spread breaches upper or lower STD band and is cointegrated (p-value < 0.05)
                        if current_spread > upper_band:
                            if p_val < 0.05:
                                alert_msg = (f"{DISCORD_PING} 🔴 **ALERT SHORT (Cointegrated)** 🔴\n"
                                             f"Pair: `{ticker1} vs {ticker2}`\n"
                                             f"Spread breached +2 STD! (Current: **{current_spread:.2f}**)\n"
                                             f"ADF Test confirms cointegration (p={p_val:.4f}).\n"
                                             f"Action: Sell {ticker1}, Buy {ticker2}")
                                self.send_discord_message(alert_msg)
                            else:
                                print(
                                    f"      [ALERT SKIPPED] {ticker1} vs {ticker2} breached +2 STD, but p-value ({p_val:.3f}) is too high!")

                        elif current_spread < lower_band:
                            if p_val < 0.05:
                                alert_msg = (f"{DISCORD_PING} 🟢 **ALERT LONG (Cointegrated)** 🟢\n"
                                             f"Pair: `{ticker1} vs {ticker2}`\n"
                                             f"Spread breached -2 STD! (Current: **{current_spread:.2f}**)\n"
                                             f"ADF Test confirms cointegration (p={p_val:.4f}).\n"
                                             f"Action: Buy {ticker1}, Sell {ticker2}")
                                self.send_discord_message(alert_msg)
                            else:
                                print(
                                    f"      [ALERT SKIPPED] {ticker1} vs {ticker2} breached -2 STD, but p-value ({p_val:.3f}) is too high!")

                self.send_discord_message("\n".join(report_lines))

                print("Scan completed. Waiting 1 hour until the next report...")
                time.sleep(3600)

            except Exception as e:
                print(f"Error in monitoring loop: {e}")
                time.sleep(60)


if __name__ == "__main__":
    bot = MultiPairArbitrageBot(PAIRS)
    bot.calibrate_models()
    bot.run_monitor()