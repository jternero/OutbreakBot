import PySimpleGUI as sg

#config.py
MT5_LOGIN = "YOUR_LOGIN"
MT5_PASSWORD = "YOUR_PASSWORD"
MT5_SERVER = "SERVER"
SYMBOL = "EURUSD"
LOT = 0.1
DEVIATION = 20
SL_POINTS = 100
TP_POINTS = 200
START_DATE = "2022-01-01"
TIMEFRAME = "M5"
ICON = "Outbreak\icon.ico"
BEEP = r"C:\Users\jotag\OneDrive\Documentos\Cyber\OutbreakBot\OutbreakBot\beep.mp3"

# GUI Layout
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
            [sg.Text(f"Símbolo: {SYMBOL}", key='SYMBOL', size=(20, 1), font=("Helvetica", 12))],
            [sg.Text(f"Precio alza: {0.00000:.5f}", key='PRICE_HIGH', size=(20, 1), font=("Helvetica", 12))],
            [sg.Text(f"Precio baja: {0.00000:.5f}", key='PRICE_DOWN', size=(20, 1), font=("Helvetica", 12))],
            [sg.Text(f"{0:,.2f}", size=(15, 1), key='PROFIT', text_color='green')],
            [sg.Text(f"{0:,.2f}", size=(15, 1), key='LOSS', text_color='red')],
            [sg.Text(f"{0:,.2f}", size=(15, 1), key='BALANCE', font=("Helvetica", 14), text_color='blue')],
        ], title='Resumen', relief=sg.RELIEF_SUNKEN)
    ],
    [
        sg.Frame(layout=[
            [sg.Text(f"Total en cuenta: {0:,.2f}", size=(35, 1), key='TOTAL', font=("Helvetica", 12))],
        ], title='Cuentas', relief=sg.RELIEF_SUNKEN)
    ],
    [
        sg.Button("Iniciar Bot", size=(20, 2), key='START'),
        sg.Button("Trade Bot", size=(20, 2), key='START_TRADE'),
        sg.Button("Detener Bot", size=(20, 2), key='STOP'),
    ]
]