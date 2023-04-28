import argparse
import threading
import logging
from binance.client import Client
from binance.enums import *

# Параметры API
api_key = "YOUR_API_KEY"
api_secret = "YOUR_API_SECRET"

# Инициализация клиента Binance
client = Client(api_key, api_secret)

# Настройка логирования
logging.basicConfig(filename='monitoring_logs.log', level=logging.INFO, format='%(asctime)s - %(message)s', datefmt='%Y-%m-%d %H:%M:%S')

# ... (остальные функции те же самые) ...
def calculate_quantity(symbol, risk_percent):
    # Здесь должна быть ваша логика расчета размера позиции с учетом риск-менеджмента
    return 1  # Возвращает примерное количество (например, 1)

def create_order(symbol, side, entry_price, take_profits, stop_loss):
    risk_percent = 0.01
    total_quantity = calculate_quantity(symbol, risk_percent)
    quantity_parts = [total_quantity / 3] * 3
    order_type = "LIMIT" if side.upper() == "LONG" else "STOP_MARKET"

    order = client.create_order(
        symbol=symbol,
        side=SIDE_BUY if side.upper() == "LONG" else SIDE_SELL,
        type=order_type,
        timeInForce=TIME_IN_FORCE_GTC,
        quantity=total_quantity,
        price=entry_price
    )

    order_id = order["orderId"]

    for i, tp in enumerate(take_profits):
        client.create_order(
            symbol=symbol,
            side=SIDE_SELL if side.upper() == "LONG" else SIDE_BUY,
            type="LIMIT",
            timeInForce=TIME_IN_FORCE_GTC,
            quantity=quantity_parts[i],
            price=tp
        )

    stop_loss_order = client.create_order(
        symbol=symbol,
        side=SIDE_SELL if side.upper() == "LONG" else SIDE_BUY,
        type="STOP_MARKET",
        timeInForce=TIME_IN_FORCE_GTC,
        quantity=total_quantity - sum(quantity_parts[:2]),
        stopPrice=stop_loss
    )

    monitor_orders(symbol)

def process_order(args):
    symbol = args.symbol
    side = args.side
    entry_price = args.entry_price
    take_profits = args.take_profits
    stop_loss = args.stop_loss

    create_order(symbol, side, entry_price, take_profits, stop_loss)

def monitor_orders(symbol):
    stop_loss_modified = False
    first_tp_filled = False
    second_tp_filled = False

    while True:
        time.sleep(5)

        open_orders = client.get_open_orders(symbol=symbol)

        for order in open_orders:
            if order["type"] == "STOP_MARKET" and not stop_loss_modified:
                if first_tp_filled and second_tp_filled:
                    new_stop_loss_quantity = order["origQty"] - (order["origQty"] / 3)
                    client.cancel_order(symbol=symbol, orderId=order["orderId"])
                    client.create_order(
                        symbol=symbol,
                        side=order["side"],
                        type=order["type"],
                        timeInForce=TIME_IN_FORCE_GTC,
                        quantity=new_stop_loss_quantity,
                        stopPrice=order["stopPrice"]
                    )
                    logging.info(f'Stop loss modified for {symbol}: New quantity = {new_stop_loss_quantity}')
                    stop_loss_modified = True
            elif order["type"] == "LIMIT":
                if order["price"] == take_profits[0]:
                    if order["status"] == "FILLED":
                        first_tp_filled = True
                        logging.info(f'First take profit filled for {symbol}')
                elif order["price"] == take_profits[1]:
                    if order["status"] == "FILLED":
                        second_tp_filled = True
                        logging.info(f'Second take profit filled for {symbol}')

        if not open_orders:
            logging.info(f'All orders closed for {symbol}')
            break

def main():
    parser = argparse.ArgumentParser(description="Binance Futures Trading Bot")
    parser.add_argument("symbol", type=str, help="Trading symbol (e.g., BTCUSDT)")
    parser.add_argument("side", type=str, help="LONG or SHORT")
    parser.add_argument("entry_price", type=float, help="Entry price")
    parser.add_argument("take_profits", type=float, nargs=3, help="Three take profit levels")
    parser.add_argument("stop_loss", type=float, help="Stop loss level")

    while True:
        print("Enter your order:")
        args = parser.parse_args(input().split())
        order_thread = threading.Thread(target=process_order, args=(args,))
        order_thread.start()

if __name__ == "__main__":
    main()

