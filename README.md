# Long-Only Intraday Breakout Trading Strategy

## 1. Project Overview

This project is a Python-based script that implements a systematic, long-only trading strategy designed for intraday breakouts. The script is built to interface with the Zerodha Kite Connect API, allowing it to fetch historical data and (in a live environment) place trades automatically.

The core of the project is a simulation engine that allows for backtesting the strategy's logic on historical data to verify its behavior before any real capital is deployed.

## 2. Strategy Rules (Features)

The script follows a precise set of rules for trade entry, stop-loss, target, and position sizing.

*   **Entry Trigger:** A long position is initiated when a 3-minute candle closes **above** a manually pre-defined breakout level for a stock.
*   **Stop-Loss Placement:** The stop-loss is automatically calculated and set to the **LOWER** of two values to ensure tight risk management:
    1.  The lowest price (`low`) reached in the two 3-minute candles immediately preceding the breakout candle.
    2.  2% below the entry price.
*   **Target:** The take-profit target is set at a 1:2 Risk/Reward ratio. The target is calculated as: `Entry Price + 2 * (Entry Price - Stop-Loss Price)`.
*   **Position Sizing:** The trade size is calculated based on a fixed risk amount per trade (e.g., ₹1,000), defined in the configuration file. The formula is: `Position Size = Risk Amount / (Entry Price - Stop-Loss Price)`.
*   **Intraday Only:** All positions are intended to be squared off by the end of the trading day. The simulation includes logic to exit positions at a pre-defined time.
*   **Leverage:** The script is designed to use intraday (`MIS`) products, which allows the broker to apply the available leverage automatically.

## 3. File Descriptions

*   `strategy.py`: This is the main engine of the project. It contains all the core logic for the trading strategy, including connecting to the API, fetching data, calculating trade parameters, and running the simulation.
*   `config.py`: A user-configurable file to store all your settings, such as API credentials, the list of stocks to track, their breakout levels, and risk parameters.
*   `test_strategy.py`: Contains unit tests to verify that the core calculation functions (`calculate_stoploss`, `calculate_position_size`, etc.) are working correctly.
*   `requirements.txt`: Lists all the necessary Python libraries required to run the project.

## 4. Setup and Installation

To get the project running, follow these steps:

1.  **Clone the repository** or download the source code.
2.  **Install dependencies:** Open a terminal or command prompt in the project's root directory and run the following command:
    ```bash
    pip install -r requirements.txt
    ```

## 5. Configuration

Before running the script, you must edit the `config.py` file:

1.  **API Credentials:** Fill in your Zerodha `API_KEY` and `API_SECRET`. You will also need to generate a valid `ACCESS_TOKEN` daily to run the simulation, as it needs to fetch data.
2.  **Stocks and Breakout Levels:**
    *   Update the `STOCKS` list with the stock symbols you want to track (e.g., `"RELIANCE"`, `"TCS"`).
    *   Update the `BREAKOUT_LEVELS` dictionary to map each stock symbol to its manually identified breakout level.
3.  **Risk Parameters:** Adjust `RISK_PER_TRADE` to your desired risk amount in your currency (e.g., `1000` for ₹1000).

## 6. How to Run the Simulation

The script is currently set up to run a historical simulation, not place live trades.

1.  Ensure your `config.py` is set up correctly, including a valid access token.
2.  Run the main strategy file from your terminal:
    ```bash
    python strategy.py
    ```
3.  The script will run a simulation for the first stock listed in your `config.py` file and print out any trade signals it finds based on the historical data.

## 7. API Documentation

For more advanced details on the Zerodha Kite Connect API and the `pykiteconnect` library used in this project, please refer to the official documentation:

*   **[Kite Connect API Documentation (v4)](https://kite.trade/docs/pykiteconnect/v4/)**