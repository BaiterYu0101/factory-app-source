import json
import os

import requests
from flask import Flask, jsonify, redirect, render_template, request, session, url_for


def create_app():
    app = Flask(__name__)
    app.secret_key = os.getenv('FLASK_SECRET_KEY', 'dev-secret-key')
    api_base_url = os.getenv('API_BASE_URL', 'http://localhost:8001')

    def fetch_api(path, method='GET', json_body=None):
        url = f"{api_base_url}{path}"
        try:
            if method == 'GET':
                response = requests.get(url, timeout=10)
            elif method == 'POST':
                response = requests.post(url, json=json_body, timeout=10)
            elif method == 'DELETE':
                response = requests.delete(url, timeout=10)
            else:
                raise ValueError('Unsupported method')
            response.raise_for_status()
            return response.json(), None
        except Exception as exc:
            return None, str(exc)

    @app.get('/')
    def index():
        if 'user_id' not in session:
            return redirect(url_for('login_page'))
        return render_template(
            'dashboard.html',
            current_user=session['user_id'],
            stock_result=None,
            watchlist_result=None,
            alert_result=None,
            stock_symbol='',
            watchlist_symbol='',
            alert_symbol='',
            alert_pattern='',
            alert_threshold='',
        )

    @app.get('/signup')
    def signup_page():
        if 'user_id' in session:
            return redirect(url_for('index'))
        return render_template('signup.html', signup_error=None, user_id='')

    @app.post('/signup')
    def signup_submit():
        user_id = request.form.get('user_id', '').strip()
        password = request.form.get('password', '')
        if not user_id or not password:
            return render_template(
                'signup.html',
                signup_error='Both user ID and password are required.',
                user_id=user_id,
            )
        payload = {'user_id': user_id, 'password': password}
        _, error = fetch_api('/api/v1/users/signup', 'POST', payload)
        if error:
            return render_template(
                'signup.html',
                signup_error='Unable to create account. ' + error,
                user_id=user_id,
            )
        session['user_id'] = user_id
        return redirect(url_for('index'))

    @app.get('/login')
    def login_page():
        if 'user_id' in session:
            return redirect(url_for('index'))
        return render_template('login.html', login_error=None, user_id='')

    @app.post('/login')
    def login_submit():
        user_id = request.form.get('user_id', '').strip()
        password = request.form.get('password', '')
        if not user_id or not password:
            return render_template(
                'login.html',
                login_error='User ID and password are required.',
                user_id=user_id,
            )
        payload = {'user_id': user_id, 'password': password}
        _, error = fetch_api('/api/v1/users/login', 'POST', payload)
        if error:
            return render_template(
                'login.html',
                login_error='Invalid user ID or password.',
                user_id=user_id,
            )
        session['user_id'] = user_id
        return redirect(url_for('index'))

    @app.get('/logout')
    def logout():
        session.pop('user_id', None)
        return redirect(url_for('login_page'))

    @app.post('/stock')
    def stock_lookup():
        if 'user_id' not in session:
            return redirect(url_for('login_page'))
        symbol = request.form.get('symbol', 'AAPL').strip()
        try:
            response = requests.get(f"{api_base_url}/api/v1/stock/{symbol}", timeout=10)
            response.raise_for_status()
            result = json.dumps(response.json(), indent=2)
        except Exception as exc:
            result = f'Error: {exc}'
        return render_template(
            'dashboard.html',
            current_user=session['user_id'],
            stock_result=result,
            watchlist_result=None,
            alert_result=None,
            stock_symbol=symbol,
            watchlist_symbol='',
            alert_symbol='',
            alert_pattern='',
            alert_threshold='',
        )

    @app.post('/watchlist')
    def add_watchlist():
        if 'user_id' not in session:
            return redirect(url_for('login_page'))
        payload = {
            'user_id': session['user_id'],
            'symbol': request.form.get('symbol', 'MSFT').strip(),
        }
        data, error = fetch_api('/api/v1/watchlist', 'POST', payload)
        if error:
            return render_template(
                'dashboard.html',
                current_user=session['user_id'],
                stock_result=None,
                watchlist_result=f'Error adding symbol: {error}',
                alert_result=None,
                stock_symbol='',
                watchlist_symbol=payload['symbol'],
                alert_symbol='',
                alert_pattern='',
                alert_threshold='',
            )
        return redirect(url_for('watchlist_page'))

    @app.post('/alerts')
    def create_alert():
        if 'user_id' not in session:
            return redirect(url_for('login_page'))
        payload = {
            'user_id': session['user_id'],
            'symbol': request.form.get('symbol', 'AAPL').strip(),
            'pattern': request.form.get('pattern', 'bullish-engulfing').strip(),
            'threshold': float(request.form.get('threshold', '150.0')),
        }
        data, error = fetch_api('/api/v1/pattern-alerts', 'POST', payload)
        if error:
            result = f'Error creating alert: {error}'
        else:
            result = f'Alert created for {payload["symbol"].upper()}.'
        return render_template(
            'dashboard.html',
            current_user=session['user_id'],
            stock_result=None,
            watchlist_result=None,
            alert_result=result,
            stock_symbol='',
            watchlist_symbol='',
            alert_symbol=payload['symbol'],
            alert_pattern=payload['pattern'],
            alert_threshold=str(payload['threshold']),
        )

    @app.get('/watchlist')
    def watchlist_page():
        if 'user_id' not in session:
            return redirect(url_for('login_page'))
        return render_template('watchlist.html', user_id=session['user_id'])

    @app.get('/watchlist_data')
    def watchlist_data():
        if 'user_id' not in session:
            return jsonify({'error': 'not authenticated'}), 401
        user_id = session['user_id']
        watchlist, watch_err = fetch_api(f'/api/v1/watchlist/{user_id}', 'GET')
        alerts, alert_err = fetch_api(f'/api/v1/pattern-alerts/{user_id}', 'GET')
        if watch_err or alert_err:
            return jsonify({'error': watch_err or alert_err}), 500

        watchlist_data = []
        for symbol in watchlist.get('watchlist', []):
            stock, stock_err = fetch_api(f'/api/v1/stock/{symbol}', 'GET')
            if stock_err:
                continue
            watched = stock.get('market_data', {})
            watched['symbol'] = symbol
            watched['triggered'] = False
            watchlist_data.append(watched)

        alerts_data = []
        for alert in alerts.get('alerts', []):
            symbol_data = next((item for item in watchlist_data if item['symbol'] == alert['symbol']), None)
            triggered = False
            if symbol_data and alert.get('threshold') is not None:
                triggered = symbol_data.get('last_price', 0) <= alert['threshold']
            alerts_data.append({
                'alert_id': alert['alert_id'],
                'symbol': alert['symbol'],
                'pattern': alert['pattern'],
                'threshold': alert['threshold'],
                'triggered': triggered,
            })
        return jsonify({
            'user_id': user_id,
            'watchlist': watchlist_data,
            'alerts': alerts_data,
        })

    @app.post('/remove_watchlist')
    def remove_watchlist():
        if 'user_id' not in session:
            return jsonify({'message': 'not authenticated'}), 401
        data = request.get_json() or {}
        symbol = data.get('symbol')
        if not symbol:
            return jsonify({'message': 'symbol is required'}), 400
        response, error = fetch_api(f'/api/v1/watchlist/{symbol}?user_id={session["user_id"]}', 'DELETE')
        if error:
            return jsonify({'message': error}), 500
        return jsonify(response)

    @app.post('/create_alert')
    def create_alert_json():
        if 'user_id' not in session:
            return jsonify({'message': 'not authenticated'}), 401
        data = request.get_json() or {}
        payload = {
            'user_id': session['user_id'],
            'symbol': data.get('symbol', 'AAPL'),
            'pattern': data.get('pattern', 'bullish-engulfing'),
            'threshold': float(data.get('threshold', 150.0)),
        }
        response, error = fetch_api('/api/v1/pattern-alerts', 'POST', payload)
        if error:
            return jsonify({'message': error}), 500
        return jsonify({'message': f"Alert created for {payload['symbol'].upper()}"})

    @app.post('/remove_alert')
    def remove_alert_json():
        if 'user_id' not in session:
            return jsonify({'message': 'not authenticated'}), 401
        data = request.get_json() or {}
        alert_id = data.get('alert_id')
        if not alert_id:
            return jsonify({'message': 'alert_id is required'}), 400
        response, error = fetch_api(f'/api/v1/pattern-alerts/{alert_id}', 'DELETE')
        if error:
            return jsonify({'message': error}), 500
        return jsonify(response)

    @app.get('/healthz')
    def healthz():
        return 'ok'

    return app


app = create_app()

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=8080, debug=True)
