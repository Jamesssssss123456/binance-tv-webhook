import hmac
import time
import hashlib
import requests
from flask import Flask, request, jsonify

app = Flask(__name__)

# === CONFIG ===
API_KEY = "YOUR_BINANCE_API_KEY"
API_SECRET = "YOUR_BINANCE_API_SECRET"
BASE_URL = "https://fapi.binance.com"  # Binance Futures endpoint

def send_order(symbol, side, quantity, leverage):
    # Set leverage first (required)
    lev_params = {
        "symbol": symbol,
        "leverage": leverage,
        "timestamp": int(time.time() * 1000)
    }
    query_string = "&".join([f"{k}={v}" for k, v in lev_params.items()])
    signature = hmac.new(API_SECRET.encode(), query_string.encode(), hashlib.sha256).hexdigest()
    lev_params["signature"] = signature
    headers = {"X-MBX-APIKEY": API_KEY}
    requests.post(f"{BASE_URL}/fapi/v1/leverage", params=lev_params, headers=headers)

    # Send market order
    order_params = {
        "symbol": symbol,
        "side": side,
        "type": "MARKET",
        "quantity": quantity,
        "timestamp": int(time.time() * 1000)
    }
    query_string = "&".join([f"{k}={v}" for k, v in order_params.items()])
    signature = hmac.new(API_SECRET.encode(), query_string.encode(), hashlib.sha256).hexdigest()
    order_params["signature"] = signature
    res = requests.post(f"{BASE_URL}/fapi/v1/order", params=order_params, headers=headers)
    return res.json()

def get_quantity(symbol, position_pct):
    # Get account balance USDT
    headers = {"X-MBX-APIKEY": API_KEY}
    timestamp = int(time.time() * 1000)
    query = f"timestamp={timestamp}"
    signature = hmac.new(API_SECRET.encode(), query.encode(), hashlib.sha256).hexdigest()
    res = requests.get(f"{BASE_URL}/fapi/v2/balance", params={"timestamp": timestamp, "signature": signature}, headers=headers)
    balance_data = res.json()
    usdt_balance = next((float(x['balance']) for x in balance_data if x['asset'] == 'USDT'), 0)
    
    # Get price for symbol
    price_res = requests.get(f"{BASE_URL}/fapi/v1/ticker/price", params={"symbol": symbol})
    price = float(price_res.json()['price'])
    
    # Calculate position size in contracts
    notional = usdt_balance * (position_pct / 100)
    qty = round(notional / price, 3)  # Round to 3 decimal places
    return qty

@app.route("/webhook", methods=["POST"])
def webhook():
    data = request.json
    symbol = data.get("symbol")
    side = data.get("side")
    leverage = data.get("leverage", 10)
    position_pct = data.get("position_size_pct", 5)

    qty = get_quantity(symbol, position_pct)
    result = send_order(symbol, side, qty, leverage)
    return jsonify(result)

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000)
