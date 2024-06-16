import MetaTrader5 as mt5
import pandas as pd
import numpy as np
from datetime import datetime, timedelta
import time
import threading
import PySimpleGUI as sg
import config

stop_event = threading.Event()
profit_total = 0
loss_total = 0
balance_total = 0
last_price_check = None  # Para evitar chequeos constantes fallidos del precio

def initialize_mt5():
    if not mt5.initialize():
        log_message("Error al inicializar MT5")
        return False
    if not mt5.login(config.MT5_LOGIN, password=config.MT5_PASSWORD, server=config.MT5_SERVER):
        log_message("Error al iniciar sesión en la cuenta de MT5")
        mt5.shutdown()
        return False
    log_message("Conexión exitosa a MT5")
    return True

def check_connection_and_symbol():
    if not mt5.initialize():
        log_message("Error al inicializar MT5")
        return False
    if not mt5.login(config.MT5_LOGIN, password=config.MT5_PASSWORD, server=config.MT5_SERVER):
        log_message("Error al iniciar sesión en la cuenta de MT5")
        mt5.shutdown()
        return False
    log_message("Conexión exitosa a MT5")

    symbol_info = mt5.symbol_info(config.SYMBOL)
    if symbol_info is None:
        log_message(f"El símbolo {config.SYMBOL} no existe.")
        mt5.shutdown()
        return False
    log_message(f"Símbolo {config.SYMBOL} disponible.")

    mt5.shutdown()
    return True

def get_market_data(symbol, timeframe, start, end):
    for attempt in range(5):  # Intentar varias veces
        rates = mt5.copy_rates_range(symbol, timeframe, start, end)
        if rates is not None and len(rates) > 0:
            data = pd.DataFrame(rates)
            log_message("Datos obtenidos:")
            log_message(str(data.head()))  # Añadido para depuración
            log_message("Columnas disponibles en los datos:")
            log_message(str(data.columns))  # Añadido para depuración
            data['time'] = pd.to_datetime(data['time'], unit='s')
            data.set_index('time', inplace=True)
            return data
        else:
            log_message(f"No se obtuvieron datos de mercado, intento {attempt + 1}/5...")
            time.sleep(5)  # Esperar antes de intentar nuevamente
    log_message(f"No se obtuvieron datos de mercado para {symbol} desde {start} hasta {end}.")
    return pd.DataFrame()  # Retornar un DataFrame vacío

def apply_strategy(data):
    short_window = 50
    long_window = 200

    # Calcular SMA50 y SMA200
    data['SMA50'] = data['close'].rolling(window=short_window).mean()
    data['SMA200'] = data['close'].rolling(window=long_window).mean()

    # Inicializar la columna de señales y posiciones
    data['signal'] = 0.0
    data.loc[data.index[short_window:], 'signal'] = np.where(
        data['SMA50'][short_window:] > data['SMA200'][short_window:], 1.0, 
        np.where(data['SMA50'][short_window:] < data['SMA200'][short_window:], -1.0, 0.0)
    )
    # Detalle: Cambiar la lógica de 'positions' para detectar cambios en la señal efectiva
    data['positions'] = data['signal'].diff().fillna(0)

    # Añadir más depuración
    log_message("Señales y posiciones calculadas:")
    log_message(str(data[['close', 'SMA50', 'SMA200', 'signal', 'positions']].tail(10)))  # Mostrar las últimas 10 filas

    return data

def send_order_with_risk_management(action, symbol, lot, price, deviation, sl_points, tp_points):
    if action == mt5.ORDER_TYPE_BUY:
        sl = price - sl_points * mt5.symbol_info(symbol).point
        tp = price + tp_points * mt5.symbol_info(symbol).point
    else:
        sl = price + sl_points * mt5.symbol_info(symbol).point
        tp = price - tp_points * mt5.symbol_info(symbol).point

    request = {
        "action": mt5.TRADE_ACTION_DEAL,
        "symbol": symbol,
        "volume": lot,
        "type": action,
        "price": price,
        "sl": sl,
        "tp": tp,
        "deviation": deviation,
        "magic": 234000,
        "comment": "Python script order",
        "type_time": mt5.ORDER_TIME_GTC,
        "type_filling": mt5.ORDER_FILLING_RETURN,
    }
    result = mt5.order_send(request)
    log_message(f"Order Send Result={result._asdict()}")
    return result

def log_transaction(action, result):
    global profit_total, loss_total, balance_total

    profit = result.profit
    if profit >= 0:
        profit_total += profit
    else:
        loss_total += abs(profit)
    
    balance_total = profit_total - loss_total

    # Actualizar valores en la interfaz
    window['PROFIT'].update(f"{profit_total:,.2f}")
    window['LOSS'].update(f"{loss_total:,.2f}")
    window['BALANCE'].update(f"{balance_total:,.2f}")

    log_entry = {
        "time": pd.Timestamp.now(),
        "action": "BUY" if action == mt5.ORDER_TYPE_BUY else "SELL",
        "volume": result.volume,
        "price": result.price,
        "sl": result.price - config.SL_POINTS * mt5.symbol_info(config.SYMBOL).point if action == mt5.ORDER_TYPE_BUY else result.price + config.SL_POINTS * mt5.symbol_info(config.SYMBOL).point,
        "tp": result.price + config.TP_POINTS * mt5.symbol_info(config.SYMBOL).point if action == mt5.ORDER_TYPE_BUY else result.price - config.TP_POINTS * mt5.symbol_info(config.SYMBOL).point,
        "profit": result.profit,
        "comment": result.comment
    }
    log_df = pd.DataFrame([log_entry])
    with open('transaction_log.csv', 'a') as f:
        log_df.to_csv(f, header=f.tell()==0, index=False)
    log_message(f"Transaction logged: {log_entry}")

def is_market_open():
    now = datetime.now()
    # Check if it's weekend
    if now.weekday() >= 5:  # Saturday and Sunday
        return False
    # Here we could add checks for specific market hours if needed
    return True

def log_message(message):
    window['LOG'].print(message)

def update_price():
    global last_price_check
    symbol = config.SYMBOL
    tick = mt5.symbol_info_tick(symbol)
    try:
        if tick is not None:
            price = tick.last
            window['SYMBOL'].update(f"Símbolo: {symbol}")
            window['PRICE'].update(f"Precio Actual: {price:.5f}")
        else:
            now = datetime.now()
            if last_price_check is None or (now - last_price_check).seconds > 60:
                log_message(f"No se pudo obtener el precio para el símbolo {symbol}")
            last_price_check = now
    except Exception as e:
        log_message(f"Error al obtener el precio: {str(e)}")
def main():
    if not check_connection_and_symbol():
        return

    if not initialize_mt5():
        return

    if not is_market_open():
        log_message("El mercado está cerrado. Por favor, inténtelo durante las horas de mercado.")
        return

    symbol = config.SYMBOL
    lot = config.LOT
    deviation = config.DEVIATION
    sl_points = config.SL_POINTS
    tp_points = config.TP_POINTS

    end = datetime.now()
    start = end - timedelta(days=7)  # Cambiar a una semana antes
    timeframe = eval(f"mt5.TIMEFRAME_{config.TIMEFRAME}")

    while not stop_event.is_set():
        if not is_market_open():
            log_message("El mercado está cerrado. Reintentando en 1 hora...")
            time.sleep(3600)  # Espera 1 hora
            continue

        market_data = get_market_data(symbol, timeframe, start, end)
        if market_data.empty:  
            log_message("No se obtuvieron datos de mercado, reintentando en 5 minutos...")
            time.sleep(300)
            continue

        market_data = apply_strategy(market_data)

        log_message("Última fila de market_data con señales y posiciones:")
        log_message(str(market_data.iloc[-1]))

        last_row = market_data.iloc[-1]

        update_price()

        if last_row['positions'] == 1.0:
            price = mt5.symbol_info_tick(symbol).ask
            log_message(f"Enviando orden de COMPRA. Precio: {price}")
            result = send_order_with_risk_management(mt5.ORDER_TYPE_BUY, symbol, lot, price, deviation, sl_points, tp_points)
            log_message(f"Resultado de la orden de COMPRA: {result}")
            if result.retcode == mt5.TRADE_RETCODE_DONE:
                log_transaction(mt5.ORDER_TYPE_BUY, result)
        elif last_row['positions'] == -1.0:
            price = mt5.symbol_info_tick(symbol).bid
            log_message(f"Enviando orden de VENTA. Precio: {price}")
            result = send_order_with_risk_management(mt5.ORDER_TYPE_SELL, symbol, lot, price, deviation, sl_points, tp_points)
            log_message(f"Resultado de la orden de VENTA: {result}")
            if result.retcode == mt5.TRADE_RETCODE_DONE:
                log_transaction(mt5.ORDER_TYPE_SELL, result)

        time.sleep(300)  # Espera 5 minutos antes de la siguiente iteración

def start_bot():
    global bot_thread, stop_event
    stop_event.clear()
    bot_thread = threading.Thread(target=main)
    bot_thread.start()
    log_message("Bot iniciado.")

def stop_bot():
    global stop_event
    stop_event.set()
    log_message("Bot detenido.")

if __name__ == "__main__":
    sg.theme('dark grey 9')

    layout = [
        [sg.Text("Trading Bot Logs", size=(40, 1), justification='center', font=("Helvetica", 14))],
        [sg.Text(" ▄▄▄▄▄▄▄▄▄▄▄  ▄         ▄  ▄▄▄▄▄▄▄▄▄▄▄  ▄▄▄▄▄▄▄▄▄▄   ▄▄▄▄▄▄▄▄▄▄▄  ▄▄▄▄▄▄▄▄▄▄▄  ▄▄▄▄▄▄▄▄▄▄▄  ▄    ▄           ▄▄▄▄▄▄▄▄▄▄   ▄▄▄▄▄▄▄▄▄▄▄  ▄▄▄▄▄▄▄▄▄▄▄ ", font=("Courier", 6), text_color=('yellow'))],
        [sg.Text("▐░░░░░░░░░░░▌▐░▌       ▐░▌▐░░░░░░░░░░░▌▐░░░░░░░░░░▌ ▐░░░░░░░░░░░▌▐░░░░░░░░░░░▌▐░░░░░░░░░░░▌▐░▌  ▐░▌         ▐░░░░░░░░░░▌ ▐░░░░░░░░░░░▌▐░░░░░░░░░░░▌", font=("Courier", 6), text_color=('yellow'))],
        [sg.Text("▐░█▀▀▀▀▀▀▀█░▌▐░▌       ▐░▌ ▀▀▀▀█░█▀▀▀▀ ▐░█▀▀▀▀▀▀▀█░▌▐░█▀▀▀▀▀▀▀█░▌▐░█▀▀▀▀▀▀▀▀▀ ▐░█▀▀▀▀▀▀▀█░▌▐░▌ ▐░▌          ▐░█▀▀▀▀▀▀▀█░▌▐░█▀▀▀▀▀▀▀█░▌ ▀▀▀▀█░█▀▀▀▀ ", font=("Courier", 6), text_color=('yellow'))],
        [sg.Text("▐░▌       ▐░▌▐░▌       ▐░▌     ▐░▌     ▐░▌       ▐░▌▐░▌       ▐░▌▐░▌          ▐░▌       ▐░▌▐░▌▐░▌           ▐░▌       ▐░▌▐░▌       ▐░▌     ▐░▌     ", font=("Courier", 6), text_color=('yellow'))],
        [sg.Text("▐░▌       ▐░▌▐░▌       ▐░▌     ▐░▌     ▐░█▄▄▄▄▄▄▄█░▌▐░█▄▄▄▄▄▄▄█░▌▐░█▄▄▄▄▄▄▄▄▄ ▐░█▄▄▄▄▄▄▄█░▌▐░▌░▌            ▐░█▄▄▄▄▄▄▄█░▌▐░▌       ▐░▌     ▐░▌     ", font=("Courier", 6), text_color=('yellow'))],
        [sg.Text("▐░▌       ▐░▌▐░▌       ▐░▌     ▐░▌     ▐░░░░░░░░░░▌ ▐░░░░░░░░░░░▌▐░░░░░░░░░░░▌▐░░░░░░░░░░░▌▐░░▌             ▐░░░░░░░░░░▌ ▐░▌       ▐░▌     ▐░▌     ", font=("Courier", 6), text_color=('yellow'))],
        [sg.Text("▐░▌       ▐░▌▐░▌       ▐░▌     ▐░▌     ▐░█▀▀▀▀▀▀▀█░▌▐░█▀▀▀▀█░█▀▀ ▐░█▀▀▀▀▀▀▀▀▀ ▐░█▀▀▀▀▀▀▀█░▌▐░▌░▌            ▐░█▀▀▀▀▀▀▀█░▌▐░▌       ▐░▌     ▐░▌     ", font=("Courier", 6), text_color=('yellow'))],
        [sg.Text("▐░▌       ▐░▌▐░▌       ▐░▌     ▐░▌     ▐░▌       ▐░▌▐░▌     ▐░▌  ▐░▌          ▐░▌       ▐░▌▐░▌▐░▌           ▐░▌       ▐░▌▐░▌       ▐░▌     ▐░▌     ", font=("Courier", 6), text_color=('yellow'))],
        [sg.Text("▐░█▄▄▄▄▄▄▄█░▌▐░█▄▄▄▄▄▄▄█░▌     ▐░▌     ▐░█▄▄▄▄▄▄▄█░▌▐░▌      ▐░▌ ▐░█▄▄▄▄▄▄▄▄▄ ▐░▌       ▐░▌▐░▌ ▐░▌          ▐░█▄▄▄▄▄▄▄█░▌▐░█▄▄▄▄▄▄▄█░▌     ▐░▌     ", font=("Courier", 6), text_color=('yellow'))],
        [sg.Text("▐░░░░░░░░░░░▌▐░░░░░░░░░░░▌     ▐░▌     ▐░░░░░░░░░░▌ ▐░▌       ▐░▌▐░░░░░░░░░░░▌▐░▌       ▐░▌▐░▌  ▐░▌         ▐░░░░░░░░░░▌ ▐░░░░░░░░░░░▌     ▐░▌     ", font=("Courier", 6), text_color=('yellow'))],
        [sg.Text(" ▀▀▀▀▀▀▀▀▀▀▀  ▀▀▀▀▀▀▀▀▀▀▀       ▀       ▀▀▀▀▀▀▀▀▀▀   ▀         ▀  ▀▀▀▀▀▀▀▀▀▀▀  ▀         ▀  ▀    ▀           ▀▀▀▀▀▀▀▀▀▀   ▀▀▀▀▀▀▀▀▀▀▀       ▀      ", font=("Courier", 6), text_color=('yellow'))],
        [
            sg.Multiline(size=(85, 20), key='LOG', autoscroll=True, disabled=True),
            sg.Frame(layout=[
                [sg.Text(f"Símbolo: {config.SYMBOL}", key='SYMBOL', size=(20, 1), font=("Helvetica", 12))],
                [sg.Text(f"Precio Actual: {0.00000:.5f}", key='PRICE', size=(20, 1), font=("Helvetica", 12))],
                [sg.Text(f"{0:,.2f}", size=(15, 1), key='PROFIT', text_color='green')],
                [sg.Text(f"{0:,.2f}", size=(15, 1), key='LOSS', text_color='red')],
                [sg.Text(f"{0:,.2f}", size=(15, 1), key='BALANCE', font=("Helvetica", 14), text_color='blue')]
            ], title='Resumen', relief=sg.RELIEF_SUNKEN)
        ],
        [
            sg.Button("Iniciar Bot", size=(20, 2), key='START'),
            sg.Button("Detener Bot", size=(20, 2), key='STOP')
        ]
    ]

    window = sg.Window("Trading Bot", layout, finalize=True)

    # Mensaje de bienvenida
    welcome_message = (
        "¡Bienvenido al Trading Bot!\n\n"
        "Este bot está diseñado para ejecutar estrategias de trading automático "
        "utilizando la plataforma MetaTrader 5.\n\n"
        "Instrucciones:\n"
        "1. Verifique que las credenciales de MetaTrader 5 estén correctamente configuradas "
        "en el archivo de configuración.\n"
        "2. Haga clic en 'Iniciar Bot' para comenzar a ejecutar el bot.\n"
        "3. Haga clic en 'Detener Bot' para detener la ejecución del bot.\n\n"
        "Los logs de ejecución aparecerán en esta ventana."
    )
    log_message(welcome_message)

    while True:
        event, values = window.read(timeout=1000)  # Añadir un timeout para la interfaz
        if event == sg.WINDOW_CLOSED:
            break
        elif event == 'START':
            start_bot()
        elif event == 'STOP':
            stop_bot()

        # Actualizar el precio cada segundo
        if not stop_event.is_set():
            update_price()

    window.close()