from flask import Flask, jsonify, request
import requests
import os
import sys

# Retrieve the API key from the environment variable
api_key = os.getenv("API_KEY")
if not api_key:
    print("Error: API_KEY not set in environment variables.", file=sys.stderr)
    sys.exit(1)  # Exit with a non-zero status code to indicate an error

# Use the environment variable for the port, defaulting to 5003 if not provided
port = int(os.getenv("FLASK_RUN_PORT", 5003))

app = Flask(__name__)

STOCKS1_URL = os.getenv("STOCKS1_URL", "http://stocks1:8000")
STOCKS2_URL = os.getenv("STOCKS2_URL", "http://stocks2:8000")


def fetch_stocks_from_stock_service(service_url):
    """
    Fetch all stocks from the specified stocks service.
    """
    response = requests.get(service_url + "/stocks")

    if response.status_code == 200:
        return response.json()
    else:
        raise Exception(f"Failed to fetch stocks from {service_url}: {response.status_code}")


# Helper function for API calls
def fetch_ticker_price(symbol):
    """
    Fetch the ticker price for a given stock symbol using an external API.
    Returns a tuple (price, error_response).
    """
    api_url = f'https://api.api-ninjas.com/v1/stockprice?ticker={symbol}'
    response = requests.get(api_url, headers={'X-Api-Key': api_key})
    if response.status_code == requests.codes.ok:
        return response.json().get('price', 0), None
    return None, {"server error": "API response code " + str(response.status_code)}

@app.route('/kill', methods=['GET'])
def kill_container():
    os._exit(1)

@app.route("/capital-gains", methods=["GET"])
def get_capital_gains():
    try:
        query_params = request.args
        portfolio = query_params.get("portfolio")
        numsharesgt = query_params.get("numsharesgt")
        numshareslt = query_params.get("numshareslt")

        stocks = []
        if portfolio == "stocks1" or not portfolio:
            stocks += fetch_stocks_from_stock_service(STOCKS1_URL)
        if portfolio == "stocks2" or not portfolio:
            stocks += fetch_stocks_from_stock_service(STOCKS2_URL)  

        if numsharesgt:
            stocks = [stock for stock in stocks if stock["shares"] > int(numsharesgt)]

        if numshareslt: 
            stocks = [stock for stock in stocks if stock["shares"] < int(numshareslt)]
        
        total_capital_gain = 0
        for stock in stocks:
            symbol = stock['symbol']
            shares = stock['shares']
            purchase_price = stock['purchase_price']
            ticker_price, error_response = fetch_ticker_price(symbol)
            if error_response:
                return jsonify(error_response), 500

            current_stock_value = round(shares * ticker_price, 2)
            capital_gain = round((current_stock_value - purchase_price), 2)
            total_capital_gain += capital_gain

        return jsonify({"total_capital_gain": total_capital_gain}), 200
    except Exception as e:
        return jsonify({"error": str(e)}), 500
    

if __name__ == '__main__':
    app.run(host="0.0.0.0", port=port)