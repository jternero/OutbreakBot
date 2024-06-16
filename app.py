#app.py
from flask import Flask, render_template, jsonify
import pandas as pd

app = Flask(__name__)

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/transactions')
def transactions():
    try:
        transactions_df = pd.read_csv('transaction_log.csv')
        transactions = transactions_df.to_dict(orient='records')
    except Exception as e:
        transactions = []

    return jsonify(transactions)

if __name__ == "__main__":
    app.run(debug=True)
