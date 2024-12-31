from flask import Flask, jsonify, request
import uuid
import requests
import os
import sys
from datetime import datetime

# Retrieve the API key from the environment variable
api_key = os.getenv("API_KEY")
if not api_key:
    print("Error: API_KEY not set in environment variables.", file=sys.stderr)
    sys.exit(1)  # Exit with a non-zero status code to indicate an error

app = Flask(__name__)

# In-memory storage for stocks
stocks = {}


# Helper function to validate required fields
def validate_required_fields(data, required_fields):
    """
    Validate that all required fields are present in the data.
    Returns a tuple (is_valid, error_response).
    """
    if not all(field in data for field in required_fields):
        return False, {"error": "Malformed data"}

    if 'purchase_price' in data and not isinstance(data['purchase_price'], (float, int)):
        return False, {"error": "Malformed data"}
    if 'shares' in data and not isinstance(data['shares'], int):
        return False, {"error": "Malformed data"}
    if 'purchase_date' in data and not validate_date_format(data['purchase_date']):
        return False, {"error": "Malformed data"}  # 'purchase_date' must be in DD-MM-YYYY format

    return True, None


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


# Helper function to validate date format
def validate_date_format(date_str):
    try:
        datetime.strptime(date_str, "%d-%m-%Y")
        return True
    except ValueError:
        return False


@app.route('/stocks', methods=['GET'])
def get_stocks():
    try:
        query_params = request.args
        if not query_params:
            return jsonify(list(stocks.values())), 200

        filtered_stocks = []
        for stock in stocks.values():
            match = all(str(stock.get(key, '')).lower() == value.lower()
                        for key, value in query_params.items())
            if match:
                filtered_stocks.append(stock)

        return jsonify(filtered_stocks), 200
    except Exception as e:
        return jsonify({"server error": str(e)}), 500


@app.route('/stocks', methods=['POST'])
def add_stock():
    try:
        content_type = request.headers.get('Content-Type')
        if content_type != 'application/json':
            return jsonify({"error": "Expected application/json media type"}), 415

        data = request.get_json()
        for stock in stocks.values():
            if stock['symbol'].lower() == data['symbol'].lower():
                return jsonify({"error": "Malformed data"}), 400

        required_fields = ['symbol', 'purchase_price', 'shares']
        is_valid, error_response = validate_required_fields(data, required_fields)
        if not is_valid:
            return jsonify(error_response), 400

        new_id = str(uuid.uuid4())
        stock = {
            'id': new_id,
            'name': data.get('name', 'NA'),
            'symbol': data['symbol'].upper(),
            'purchase_price': round(data['purchase_price'], 2),
            'purchase_date': data.get('purchase_date', 'NA'),
            'shares': data['shares']
        }

        stocks[new_id] = stock
        return jsonify({"id": new_id}), 201
    except Exception as e:
        return jsonify({"server error": str(e)}), 500


@app.route('/stocks/<stock_id>', methods=['GET'])
def get_stock(stock_id):
    try:
        return jsonify(stocks[stock_id]), 200
    except KeyError:
        return jsonify({"error": "Not found"}), 404
    except Exception as e:
        return jsonify({"server error": str(e)}), 500


@app.route('/stocks/<stock_id>', methods=['DELETE'])
def delete_stock(stock_id):
    try:
        del stocks[stock_id]
        return '', 204
    except KeyError:
        return jsonify({"error": "Not found"}), 404
    except Exception as e:
        return jsonify({"server error": str(e)}), 500


@app.route('/stocks/<stock_id>', methods=['PUT'])
def update_stock(stock_id):
    try:
        # Check if the stock exists
        if stock_id not in stocks:
            return jsonify({"error": "Not found"}), 404

        # Validate content type
        content_type = request.headers.get('Content-Type')
        if content_type != 'application/json':
            return jsonify({"error": "Expected application/json media type"}), 415

        # Get the request data
        data = request.get_json()

        # Ensure the 'id' field is present and matches the stock_id in the URL
        if "id" not in data or data["id"] != stock_id:
            return jsonify({"error": "Malformed data"}), 400

        # Validate required fields
        required_fields = ['id', 'symbol', 'purchase_price', 'shares']
        is_valid, error_response = validate_required_fields(data, required_fields)
        if not is_valid:
            return jsonify(error_response), 400

        # Update the stock with provided data, keeping existing values for missing fields
        stock = stocks[stock_id]
        stock.update({
            'id': data['id'],  # Ensure the ID matches
            'name': data.get('name', stock['name']),  # Keep existing value if not provided
            'symbol': data['symbol'].upper(),
            'purchase_price': round(data['purchase_price'], 2),
            'purchase_date': data.get('purchase_date', stock['purchase_date']),  # Keep existing value
            'shares': data['shares']
        })

        return jsonify({"id": stock_id}), 200
    except Exception as e:
        return jsonify({"server error": str(e)}), 500


@app.route('/stock-value/<stock_id>', methods=['GET'])
def get_stock_value(stock_id):
    try:
        stock = stocks.get(stock_id)
        if not stock:
            return jsonify({"error": "Not found"}), 404

        symbol = stock['symbol']
        shares = stock['shares']
        ticker_price, error_response = fetch_ticker_price(symbol)
        if error_response:
            return jsonify(error_response), 500

        stock_value = round(shares * ticker_price, 2)
        return jsonify({
            "symbol": symbol,
            "ticker": round(ticker_price, 2),
            "stock_value": stock_value
        }), 200
    except Exception as e:
        return jsonify({"server error": str(e)}), 500


@app.route('/portfolio-value', methods=['GET'])
def get_portfolio_value():
    try:
        total_value = 0
        for stock in stocks.values():
            stock_symbol = stock['symbol']
            stock_number_of_shares = stock['shares']

            ticker_price, error_response = fetch_ticker_price(stock_symbol)
            if error_response:
                return jsonify(error_response), 500

            stock_value = round(stock_number_of_shares * ticker_price, 2)
            total_value += stock_value

        current_date = datetime.now().strftime("%Y-%m-%d")
        return jsonify({"date": current_date, "portfolio_value": round(total_value, 2)}), 200
    except Exception as e:
        return jsonify({"server error": str(e)}), 500


if __name__ == '__main__':
    app.run(host="0.0.0.0", port=5001)
