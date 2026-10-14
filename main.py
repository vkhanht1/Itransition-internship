import math
from flask import Flask, request

app = Flask(__name__)

def is_non_negative_int(val):
    try:
        n = int(val)
        return n >= 0 and str(n) == val.strip()
    except (ValueError, TypeError):
        return False

@app.route('/tvkhanh1692_gmail_com', methods=['GET'])
def calculate_lcm():
    x_str = request.args.get('x')
    y_str = request.args.get('y')

    if not x_str or not y_str or not is_non_negative_int(x_str) or not is_non_negative_int(y_str):
        return "NaN", 200, {'Content-Type': 'text/plain'}

    x = int(x_str)
    y = int(y_str)

    if x == 0 or y == 0:
        lcm_val = 0
    else:
        lcm_val = abs(x * y) // math.gcd(x, y)

    return str(lcm_val), 200, {'Content-Type': 'text/plain'}

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=8080)