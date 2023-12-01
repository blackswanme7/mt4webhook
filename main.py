from flask import Flask, request, jsonify, abort
import json
import grpc
from mt4grpc.sdk.python3 import mt4_pb2_grpc
from mt4grpc.sdk.python3.mt4_pb2 import *
import logging
from datetime import datetime, timedelta

# Set up logging
logging.basicConfig(filename='server.log', level=logging.DEBUG)

# Flask application setup
app = Flask(__name__)

# # TradingView IP addresses
# allowed_ips = ["52.89.214.238", "34.212.75.30", "54.218.53.128", "52.32.178.7"]

# # Decorator to limit access to allowed IPs
# def limit_ips(allowed_ips):
#     def decorator(f):
#         def decorated_function(*args, **kwargs):
#             if request.remote_addr not in allowed_ips:
#                 abort(403)  # Forbidden access
#             return f(*args, **kwargs)
#         return decorated_function
#     return decorator

# A dictionary to store tokens for each user
# Format: { user_id: {"token": <token>, "last_updated": <datetime>} }
token_cache = {}

# Read configuration from a file for multiple users
with open('config.json', 'r') as config_file:
    config = json.load(config_file)

# Function to connect to MT4 and update the token for a specific user
def connect_to_mt4(user_id):
    user_config = config[str(user_id)]
    try:
        channel = grpc.secure_channel('mt4grpc.mtapi.io:443', grpc.ssl_channel_credentials())
        connection = mt4_pb2_grpc.ConnectionStub(channel)
        req = ConnectRequest(user=user_config["user"], password=user_config["pass"], host=user_config["host"], port=443)
        res = connection.Connect(req)
        if res.error.message:
            logging.error(f"Error for user {user_id}: {res.error.message}")
            raise Exception(res.error.message)
        token_cache[user_id] = {
            "token": res.result,
            "last_updated": datetime.now()
        }
        logging.info(f"Token refreshed for user {user_id}")
        return res.result, mt4_pb2_grpc.TradingStub(channel)
    except Exception as e:
        logging.error(f"MT4 connection error for user {user_id}: {str(e)}")
        raise

# Function to refresh the token if needed for a specific user
def refresh_token_if_needed(user_id):
    now = datetime.now()
    if (user_id not in token_cache or
        token_cache[user_id]["last_updated"] is None or
        now - token_cache[user_id]["last_updated"] > timedelta(hours=6)):
        connect_to_mt4(user_id)
# Function to close all orders for a given symbol
def close_all_orders(symbol, token):
    channel = grpc.secure_channel('mt4grpc.mtapi.io:443', grpc.ssl_channel_credentials())
    mt4 = mt4_pb2_grpc.MT4Stub(channel)

    req = OpenedOrderRequest(id=token)
    res = mt4.OpenedOrders(req)
    if res.error.message:
        logging.error(f"Error retrieving open orders: {res.error.message}")
        raise Exception(res.error.message)

    tickets_to_close = [order.Ticket for order in res.result if order.Symbol == symbol]
    
    trading = mt4_pb2_grpc.TradingStub(channel)
    for ticket in tickets_to_close:
        order_close_req = OrderCloseRequest(id=token, ticket=ticket)
        order_close_res = trading.OrderClose(order_close_req)
        if order_close_res.error.message:
            logging.error(f"Error closing order {ticket}: {order_close_res.error.message}")
        else:
            logging.info(f"Successfully closed order {ticket}")
# Webhook endpoint
@app.route('/<int:user_id>', methods=['POST'])
# @limit_ips(allowed_ips)
def webhook(user_id):
    try:
        if str(user_id) not in config:
            return jsonify({'error': 'Invalid user'}), 403

        # Refresh the token if needed
        refresh_token_if_needed(user_id)

        data = request.get_json()
        logging.info(f"Webhook received data for user {user_id}: {data}")  # Log the POST data

        # Use the token from the cache
        token = token_cache[user_id]["token"]
        trading = mt4_pb2_grpc.TradingStub(grpc.secure_channel('mt4grpc.mtapi.io:443', grpc.ssl_channel_credentials()))

        for order in data:
            symbol = order["symbol"]
            
            # If 'exit' is 0, close all orders for the symbol and continue to the next order
            if order.get('exit') == '0':
                close_all_orders(symbol, token)
                logging.info(f"Closed all orders for {symbol} for user {user_id}")
                continue

            # If 'exit' is true, process the order and then close all orders for the symbol
            if order.get('exit') == 'true':
                close_all_orders(symbol, token)
                logging.info(f"Processed and closed all orders for {symbol} for user {user_id}")
                continue

            # Otherwise, just process the order
            process_order(order, token, trading)


        return jsonify({'status': 'orders processed'}), 200
    except Exception as e:
        logging.error(f"Webhook error for user {user_id}: {str(e)}")
        return jsonify({'error': str(e)}), 500
    
def process_order(order, token, trading_stub):
    # Function to process buy or sell order
    symbol = order["symbol"]
    lot = round(float(order["lot"]), 2)
    side = order["side"]
    operation = 0 if side == "buy" else 1

    order_send_req = OrderSendRequest(
        id=token,
        symbol=symbol,
        operation=operation,
        volume=lot,
        price=0,
        slippage=0,
        stoploss=0,
        takeprofit=0,
        placedType=0
    )
    order_send_res = trading_stub.OrderSend(order_send_req)
    # Log the response from the trading call
    logging.info(f"Trading response , order {order}: {order_send_res}")

    if order_send_res.error.message:
        logging.error(f"Order error for : {order_send_res.error.message}")


if __name__ == '__main__':
    app.run(debug=True)
