from mt4grpc.sdk.python3 import mt4_pb2_grpc
from mt4grpc.sdk.python3.mt4_pb2 import *
from mt4grpc.sdk.python3.mt4_pb2_grpc import *

channel = grpc.secure_channel('mt4grpc.mtapi.io:443', grpc.ssl_channel_credentials())
service = mt4_pb2_grpc.ServiceStub(channel)
mt4 = mt4_pb2_grpc.MT4Stub(channel)
trading = mt4_pb2_grpc.TradingStub(channel)
connection = mt4_pb2_grpc.ConnectionStub(channel)


host="185.96.244.190"
user=45211733
passw="dIkbO1h2Czz1pE4"

req = ConnectRequest(
    # user = 500476959,
    # password = 'ehj4bod',
    # host="mt4-demo.roboforex.com", 
    # port=443
    user = user,
    password = passw,
    host=host, 
    port=443
    
    )
res = connection.Connect(req)
if res.error.message:
    print(res.error)
    exit()
token = res.result
print(token)

req = AccountSummaryRequest(
    id = token)
res = mt4.AccountSummary(req)
if res.error.message:
    print(res.error)
    exit()
print(res.result)


order_send_req = OrderSendRequest(
    id=token,  # Use the token obtained from the Connect response
    symbol="XAUUSD.HKT",
    operation=8,  # For example, 0 for buy , 1 for sell 
    volume=0.1,
    price=0,
    slippage=0,
    stoploss=0,
    takeprofit=0,
    placedType=0
)
# Sending the trading request
order_send_res = trading.OrderSend(order_send_req)
if order_send_res.error.message:
    print(order_send_res.error)
    exit()

print(f"Order Send Response: {order_send_res}")


print(f"Order Send Response: {order_send_res}")