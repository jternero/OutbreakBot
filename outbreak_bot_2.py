import MetaTrader5 as mt5
import pandas as pd
import numpy as np
import config
import threading
import queue
import PySimpleGUI as sg
from datetime import datetime, timedelta

stop_event = threading.Event()
profit_total = 0
loss_total = 0
balance_total = 0
last_price_check = None  # To avoid constant failed price checks

# Function to initialize MetaTrader 5 connection
def initialize_mt5():
	if not mt5.initialize():
		log_message("Error al inicializar MT5")
		return False
	if not mt5.login(config.MT5_LOGIN, password=config.MT5_PASSWORD, server=config.MT5_SERVER):
		log_message("Error al iniciar sesión en la cuenta de MT5")
		mt5.shutdown()
		return False
	return True

# Function to check connection and symbol availability
def check_connection_and_symbol():
	if not mt5.initialize():
		log_message("Error al inicializar MT5")
		return False
	if not mt5.login(config.MT5_LOGIN, password=config.MT5_PASSWORD, server=config.MT5_SERVER):
		log_message("Error al iniciar sesión en la cuenta de MT5")
		mt5.shutdown()
		return False

	symbol_info = mt5.symbol_info(config.SYMBOL)
	if symbol_info is None:
		log_message(f"El símbolo {config.SYMBOL} no existe.")
		mt5.shutdown()
		return False
	else:
		
		log_message(f"Símbolo {config.SYMBOL} disponible.")

	mt5.shutdown()
	return True

# Function to retrieve market data
def get_market_data(symbol, timeframe, start, end):
	for attempt in range(5):  # Retry several times
		rates = mt5.copy_rates_range(symbol, timeframe, start, end)
		ownbalance = mt5.account_info()
		if rates is not None and len(rates) > 0:
			data = pd.DataFrame(rates)
			data['time'] = pd.to_datetime(data['time'], unit='s')
			data.set_index('time', inplace=True)

			# Obtener los datos más recientes para actualizar en la interfaz
			last_row = data.iloc[-1]
			open_price = last_row['open']
			high_price = last_row['high']
			low_price = last_row['low']
			close_price = last_row['close']
			tick_volume = last_row['tick_volume']
			spread = last_row['spread']
			real_volume = last_row['real_volume']
			profit_total = ownbalance[10] - ownbalance[11]
			Total = ownbalance[10]

			
			# Retornar los datos relevantes para su uso en main
			return data
		else:
			log_message(f"No se obtuvieron datos de mercado, intento")

	log_message(f"No se obtuvieron datos de mercado para {symbol} desde {start} hasta {end}.")
	return pd.DataFrame(), None, None, None, None, None, None, None, None, None, None, None  # Devolver un DataFrame vacío y variables nulas


#Function to apply trading strategy
def apply_strategy(data):
	# Calcula la media móvil simple de 50 períodos
	sma50 = data['close'].rolling(50).mean()
	sma200 = data['close'].rolling(200).mean()
	
	data['sma50'] = sma50
	data['sma200'] = sma200
	
	# Calcula la media móvil simple de 200 períodos
	data['sma200'] = data['close'].rolling(200).mean()
	
	# Genera señales de trading basadas en las medias móviles
	data['positions'] = np.where(data['sma50'] > data['sma200'], 1.0, 0.0)  # Si sma50 > sma200, posición larga (1.0)
	data['positions'] = np.where(data['sma50'] < data['sma200'], -1.0, data['positions'])  # Si sma50 < sma200, posición corta (-1.0)
	
	# Determina la señal de trading actual
	signal = data['positions'].iloc[-1]  # Último valor de la columna 'positions' como señal
	
	# Muestra mensajes de registro para depuración
	log_message("Estrategia aplicada:")
	log_message(f"Señal de trading: {signal}")  # Muestra la señal actual de trading
	
	return data  # Devuelve el DataFrame actualizado con las nuevas columnas 'sma50', 'sma200' y 'positions'


# Function to send trading order with risk management
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
	if result.comment == "Market closed":
		log_message("El mercado está cerrado.")
		log_message("Se detiene el bot.")
		stop_event.set()
		return None
	else:
		log_message(f"Order Send Result={result._asdict()}")
		return result

# Function to log transaction details
def log_transaction(action, result):
	global profit_total, loss_total, balance_total

	profit = result.profit
	if profit >= 0:
		profit_total += profit
	else:
		loss_total += abs(profit)
	
	balance_total = profit_total - loss_total + mt5.account_info().balance

	# Update values in the interface
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



# Function to log messages in the GUI window
def log_message(message):
	window['LOG'].print(message)
 
# Funcion para verificar si el mercado esta abierto
 
stop_event = threading.Event()
signal_queue = queue.Queue()

def update_and_analyze_data(symbol, start, end, timeframe):
    while not stop_event.is_set():
        market_data = get_market_data(symbol, timeframe, start, end)
        market_data = apply_strategy(market_data)
        
        last_row = market_data.iloc[-1]
        
        # Colocar la señal en la cola para que el hilo de ejecución de trades la procese
        signal_queue.put(last_row['positions'])
        
        # Actualizar la interfaz gráfica con los valores más recientes
        close_price_high = mt5.symbol_info_tick(symbol).ask
        close_price_low = mt5.symbol_info_tick(symbol).bid
        Total = mt5.account_info().balance
        
        window['SYMBOL'].update(f"Símbolo: {symbol}")
        window['PRICE_HIGH'].update(f"Precio Actual (ask): {close_price_low:.5f}")
        window['PRICE_DOWN'].update(f"Precio Actual (bid): {close_price_high:.5f}")
        window['TOTAL'].update(f"Total en cuenta: {Total:,.2f}")
        window['BALANCE'].update(f"{Total:,.2f}")

def execute_trades(symbol, lot, deviation, sl_points, tp_points):
    while not stop_event.is_set():
        try:
            signal = signal_queue.get(timeout=1)  # Esperar por una señal nueva
        except queue.Empty:
            continue
        
        if signal == 1.0:  # Señal de compra
            price = mt5.symbol_info_tick(symbol).ask
            log_message(f"Enviando orden de COMPRA. Precio: {price}")
            result = send_order_with_risk_management(mt5.ORDER_TYPE_BUY, symbol, lot, price, deviation, sl_points, tp_points)
            if result is not None:
                log_transaction(mt5.ORDER_TYPE_BUY, result)
            else:
                return
        elif signal == -1.0:  # Señal de venta
            price = mt5.symbol_info_tick(symbol).bid
            log_message(f"Enviando orden de VENTA. Precio: {price}")
            result = send_order_with_risk_management(mt5.ORDER_TYPE_SELL, symbol, lot, price, deviation, sl_points, tp_points)
            log_transaction(mt5.ORDER_TYPE_SELL, result)

def start_trade_thread():
    global trade_thread
    if not stop_event.is_set() and not trade_thread.is_alive():
        trade_thread = threading.Thread(target=execute_trades, args=(symbol, lot, deviation, sl_points, tp_points))
        trade_thread.start()

def main():
    # Verificar la conexión y la disponibilidad del símbolo
    if not check_connection_and_symbol():
        return
    
    # Inicializar MetaTrader 5
    if not initialize_mt5():
        return
    
    # Configuración de las variables de trading
    symbol = config.SYMBOL
    lot = config.LOT
    deviation = config.DEVIATION
    sl_points = config.SL_POINTS
    tp_points = config.TP_POINTS

    # Configuración de las fechas de inicio y fin para obtener los datos del mercado
    end = datetime.now()
    start = end - timedelta(days=30)  # Cambiar según sea necesario
    timeframe = eval(f"mt5.TIMEFRAME_{config.TIMEFRAME}")
    
    # Crear el hilo para la actualización de datos y análisis
    update_thread = threading.Thread(target=update_and_analyze_data, args=(symbol, start, end, timeframe))
    update_thread.start()

    # Esperar hasta que se cierre la ventana
    window.read(close=True)

    # Detener los hilos al cerrar la ventana
    stop_event.set()
    update_thread.join()
    if trade_thread.is_alive():
        trade_thread.join()

    mt5.shutdown()

layout = config.layout
window = sg.Window('Outbreak Bot', layout, finalize=True)

# Bucle de eventos de la ventana
while True:
    event, values = window.read()
    
    if event == sg.WIN_CLOSED:
        stop_event.set()
        break
    elif event == 'START':
        threading.Thread(target=main).start()
    elif event == 'STOP':
        stop_event.set()
    elif event == 'START_TRADES':  # Este evento es para iniciar el hilo de trades
        start_trade_thread()

window.close()