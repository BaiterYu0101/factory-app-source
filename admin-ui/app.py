import json
import os
import hashlib
import hmac

import requests
from flask import Flask, jsonify, redirect, render_template_string, request, session, url_for


def create_app():
    app = Flask(__name__)
    app.secret_key = os.getenv("FLASK_SECRET_KEY", "dev-secret-key")
    api_base_url = os.getenv("API_BASE_URL", "http://localhost:8001")

    html_template = """
    <!doctype html>
    <html lang="en">
    <head>
        <meta charset="utf-8">
        <meta name="viewport" content="width=device-width, initial-scale=1">
        <title>Data Admin</title>
        <style>
            body { font-family: Arial, sans-serif; margin: 2rem; background: #f6f8fb; color: #1f2937; }
            .card { background: white; padding: 1.2rem; border-radius: 12px; margin-bottom: 1rem; box-shadow: 0 1px 3px rgba(0,0,0,0.08); }
            input, button { padding: 0.6rem; margin: 0.3rem 0; }
            input::placeholder { color: #9ca3af; }
            button { background: #2563eb; color: white; border: none; border-radius: 6px; cursor: pointer; }
            pre { background: #111827; color: #f9fafb; padding: 1rem; border-radius: 8px; overflow: auto; }
            .notice { padding: 0.9rem 1rem; border-radius: 10px; background: #eef2ff; color: #1e3a8a; border: 1px solid #c7d2fe; margin-top: 0.75rem; }
            .top-bar { display: flex; justify-content: space-between; align-items: center; margin-bottom: 1rem; }
            .top-bar span { font-weight: 700; }
            .top-bar a { color: #2563eb; text-decoration: none; }
        </style>
    </head>
    <body>
        <div class="top-bar">
            <div>
                <h1>Market Data Admin</h1>
                <p>Simple Flask UI for the market data API.</p>
            </div>
            <div>
                <span>Signed in as: {{ current_user }}</span>
                &nbsp;|&nbsp;
                <a href="{{ url_for('logout') }}">Logout</a>
            </div>
        </div>

        <div class="card">
            <h2>Stock Lookup</h2>
            <form method="post" action="/stock">
                <input name="symbol" value="{{ stock_symbol | default('') }}" placeholder="AAPL">
                <button type="submit">Lookup</button>
            </form>
            {% if stock_result %}
                <pre>{{ stock_result }}</pre>
            {% endif %}
        </div>

        <div class="card">
            <h2>Watchlist</h2>
            <form method="post" action="/watchlist">
                <input name="symbol" value="{{ watchlist_symbol | default('') }}" placeholder="MSFT">
                <button type="submit">Add</button>
            </form>
            {% if watchlist_result %}
                <div class="notice">{{ watchlist_result }}</div>
            {% endif %}
            <p><a href="{{ url_for('watchlist_page') }}">Go to live watchlist</a></p>
        </div>

        <div class="card">
            <h2>Pattern Alerts</h2>
            <form method="post" action="/alerts">
                <input name="symbol" value="{{ alert_symbol | default('') }}" placeholder="AAPL">
                <input name="pattern" value="{{ alert_pattern | default('') }}" placeholder="bullish-engulfing">
                <input name="threshold" value="{{ alert_threshold | default('') }}" placeholder="150.0">
                <button type="submit">Create Alert</button>
            </form>
            {% if alert_result %}
                <div class="notice">{{ alert_result }}</div>
            {% endif %}
        </div>
    </body>
    </html>
    """

    login_template = """
    <!doctype html>
    <html lang="en">
    <head>
        <meta charset="utf-8">
        <meta name="viewport" content="width=device-width, initial-scale=1">
        <title>Sign In</title>
        <style>
            body { font-family: Arial, sans-serif; margin: 2rem; background: #f6f8fb; color: #1f2937; }
            .card { background: white; padding: 1.6rem; border-radius: 14px; max-width: 420px; margin: auto; box-shadow: 0 12px 30px rgba(15, 23, 42, 0.06); }
            input, button { width: 100%; padding: 0.9rem; margin: 0.75rem 0; border-radius: 10px; border: 1px solid #d1d5db; }
            input::placeholder { color: #9ca3af; }
            button { background: #2563eb; color: white; border: none; cursor: pointer; }
            .error { color: #991b1b; background: #fee2e2; padding: 0.9rem 1rem; border-radius: 10px; margin-bottom: 1rem; border: 1px solid #fecaca; }
            .secondary { color: #2563eb; text-decoration: none; font-weight: 700; }
            h1 { margin-bottom: 0.25rem; }
        </style>
    </head>
    <body>
        <div class="card">
            <h1>Sign in</h1>
            <p>Enter your user ID and password to access your watchlist and alerts.</p>
            {% if login_error %}
                <div class="error">{{ login_error }}</div>
            {% endif %}
            <form method="post" action="/login">
                <input name="user_id" value="{{ user_id }}" placeholder="user-123" autofocus>
                <input type="password" name="password" placeholder="Password">
                <button type="submit">Sign in</button>
            </form>
            <p>Don't have an account? <a class="secondary" href="{{ url_for('signup_page') }}">Create one</a></p>
        </div>
    </body>
    </html>
    """

    signup_template = """
    <!doctype html>
    <html lang="en">
    <head>
        <meta charset="utf-8">
        <meta name="viewport" content="width=device-width, initial-scale=1">
        <title>Sign Up</title>
        <style>
            body { font-family: Arial, sans-serif; margin: 2rem; background: #f6f8fb; color: #1f2937; }
            .card { background: white; padding: 1.6rem; border-radius: 14px; max-width: 420px; margin: auto; box-shadow: 0 12px 30px rgba(15, 23, 42, 0.06); }
            input, button { width: 100%; padding: 0.9rem; margin: 0.75rem 0; border-radius: 10px; border: 1px solid #d1d5db; }
            input::placeholder { color: #9ca3af; }
            button { background: #2563eb; color: white; border: none; cursor: pointer; }
            .error { color: #991b1b; background: #fee2e2; padding: 0.9rem 1rem; border-radius: 10px; margin-bottom: 1rem; border: 1px solid #fecaca; }
            .secondary { color: #2563eb; text-decoration: none; font-weight: 700; }
            h1 { margin-bottom: 0.25rem; }
        </style>
    </head>
    <body>
        <div class="card">
            <h1>Create account</h1>
            <p>Choose a unique user ID and password.</p>
            {% if signup_error %}
                <div class="error">{{ signup_error }}</div>
            {% endif %}
            <form method="post" action="/signup">
                <input name="user_id" value="{{ user_id }}" placeholder="user-123" autofocus>
                <input type="password" name="password" placeholder="Password">
                <button type="submit">Sign up</button>
            </form>
            <p>Already have an account? <a class="secondary" href="{{ url_for('login_page') }}">Sign in</a></p>
        </div>
    </body>
    </html>
    """

    watchlist_template = """
    <!doctype html>
    <html lang="en">
    <head>
        <meta charset="utf-8">
        <meta name="viewport" content="width=device-width, initial-scale=1">
        <title>Live Watchlist</title>
        <style>
            body { font-family: Arial, sans-serif; margin: 2rem; background: #f4f7fb; color: #111827; }
            .page { max-width: 980px; margin: auto; }
            .card { background: white; border-radius: 16px; padding: 1.3rem; margin-bottom: 1.2rem; box-shadow: 0 12px 30px rgba(15, 23, 42, 0.06); }
            .section-title { font-size: 1.25rem; margin-bottom: 0.75rem; }
            table { width: 100%; border-collapse: collapse; margin-top: 1rem; }
            th, td { text-align: left; padding: 0.85rem; border-bottom: 1px solid #e5e7eb; }
            th { color: #374151; }
            .badge { display: inline-flex; align-items: center; gap: 0.35rem; padding: 0.45rem 0.75rem; border-radius: 999px; font-size: 0.95rem; }
            .good { background: #d1fae5; color: #065f46; }
            .danger { background: #fee2e2; color: #991b1b; }
            .notification { margin-top: 1rem; padding: 1rem; border-radius: 12px; }
            .notification.good { background: #ecfdf5; color: #134e4a; }
            .notification.alert { background: #fef2f2; color: #7f1d1d; }
            .top-links { display: flex; justify-content: space-between; align-items: center; flex-wrap: wrap; gap: 1rem; }
            .top-links a { color: #2563eb; font-weight: 700; text-decoration: none; }
            button { background: #2563eb; color: white; border: none; border-radius: 10px; padding: 0.6rem 0.9rem; cursor: pointer; }
        </style>
    </head>
    <body>
        <div class="page">
            <div class="top-links">
                <h1>Live Watchlist</h1>
                <a href="{{ url_for('index') }}">← Back to dashboard</a>
            </div>

            <div class="card">
                <div class="section-title">Watchlist for {{ user_id }}</div>
                <div id="statusBanner" class="notification good">Loading live watchlist...</div>
                <table>
                    <thead>
                        <tr>
                            <th>Symbol</th>
                            <th>Price</th>
                            <th>Previous Close</th>
                            <th>Latency</th>
                            <th>Alert</th>
                            <th>Action</th>
                        </tr>
                    </thead>
                    <tbody id="watchlistRows"></tbody>
                </table>
                <p style="margin-top: 0.75rem; color: #4b5563;">Data refreshes every 6 seconds.</p>
            </div>

            <div class="card">
                <div class="section-title">Pattern Alerts</div>
                <form id="alertForm">
                    <div style="display:grid; gap:0.75rem;">
                        <input name="symbol" placeholder="AAPL">
                        <input name="pattern" placeholder="bullish-engulfing">
                        <input name="threshold" placeholder="150.0">
                        <button type="submit">Create Alert</button>
                    </div>
                </form>
                <div id="alertMessage" class="notification" style="display:none;"></div>
                <table style="margin-top: 1rem;">
                    <thead>
                        <tr>
                            <th>Symbol</th>
                            <th>Pattern</th>
                            <th>Threshold</th>
                            <th>Status</th>
                            <th>Remove</th>
                        </tr>
                    </thead>
                    <tbody id="alertRows"></tbody>
                </table>
            </div>
        </div>

        <script>
            const watchlistRows = document.getElementById('watchlistRows');
            const alertRows = document.getElementById('alertRows');
            const statusBanner = document.getElementById('statusBanner');
            const alertMessage = document.getElementById('alertMessage');

            async function fetchWatchlistData() {
                try {
                    const response = await fetch('/watchlist_data');
                    if (!response.ok) throw new Error(await response.text());
                    return await response.json();
                } catch (error) {
                    statusBanner.textContent = `Unable to load watchlist: ${error.message}`;
                    statusBanner.className = 'notification alert';
                    return null;
                }
            }

            function renderWatchlist(items) {
                if (!items.length) {
                    watchlistRows.innerHTML = '<tr><td colspan="6">Watchlist is empty.</td></tr>';
                    return;
                }
                watchlistRows.innerHTML = items.map(item => {
                    const badgeClass = item.triggered ? 'danger' : 'good';
                    const badgeText = item.triggered ? 'Triggered' : 'OK';
                    return `
                        <tr>
                            <td>${item.symbol}</td>
                            <td>${item.last_price?.toFixed(2) ?? '—'} ${item.currency ?? ''}</td>
                            <td>${item.previous_close?.toFixed(2) ?? '—'}</td>
                            <td>${item.pipeline_latency_ms ?? '—'}</td>
                            <td><span class="badge ${badgeClass}">${badgeText}</span></td>
                            <td><button onclick="removeSymbol('${item.symbol}')">Remove</button></td>
                        </tr>
                    `;
                }).join('');
            }

            function renderAlerts(alerts) {
                if (!alerts.length) {
                    alertRows.innerHTML = '<tr><td colspan="5">No alerts created yet.</td></tr>';
                    return;
                }
                alertRows.innerHTML = alerts.map(alert => {
                    const statusClass = alert.triggered ? 'danger' : 'good';
                    const statusText = alert.triggered ? 'Triggered' : 'Inactive';
                    return `
                        <tr>
                            <td>${alert.symbol}</td>
                            <td>${alert.pattern}</td>
                            <td>${alert.threshold ?? '—'}</td>
                            <td><span class="badge ${statusClass}">${statusText}</span></td>
                            <td><button onclick="deleteAlert('${alert.alert_id}')">Remove</button></td>
                        </tr>
                    `;
                }).join('');
            }

            async function refreshAll() {
                const data = await fetchWatchlistData();
                if (!data) return;
                renderWatchlist(data.watchlist || []);
                renderAlerts(data.alerts || []);
                statusBanner.textContent = `Updated ${new Date().toLocaleTimeString()}. ${data.watchlist.length} symbols.`;
                statusBanner.className = 'notification good';
                const activeAlerts = data.alerts.filter(alert => alert.triggered);
                if (activeAlerts.length > 0) {
                    alertMessage.style.display = 'block';
                    alertMessage.textContent = `${activeAlerts.length} alert(s) triggered.`;
                    alertMessage.className = 'notification alert';
                } else {
                    alertMessage.style.display = 'none';
                }
            }

            async function removeSymbol(symbol) {
                await fetch('/remove_watchlist', {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({ symbol }),
                });
                refreshAll();
            }

            async function deleteAlert(alertId) {
                await fetch('/remove_alert', {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({ alert_id: alertId }),
                });
                refreshAll();
            }

            document.getElementById('alertForm').addEventListener('submit', async event => {
                event.preventDefault();
                const formData = new FormData(event.target);
                const payload = {
                    symbol: formData.get('symbol'),
                    pattern: formData.get('pattern'),
                    threshold: parseFloat(formData.get('threshold')),
                };
                const response = await fetch('/create_alert', {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify(payload),
                });
                const result = await response.json();
                alertMessage.style.display = 'block';
                alertMessage.textContent = result.message || JSON.stringify(result);
                alertMessage.className = response.ok ? 'notification good' : 'notification alert';
                refreshAll();
            });

            refreshAll();
            setInterval(refreshAll, 6000);
        </script>
    </body>
    </html>
    """

    def users_file_path():
        return os.path.join(app.root_path, 'users.json')

    def load_users():
        path = users_file_path()
        if not os.path.exists(path):
            return {}
        with open(path, 'r', encoding='utf-8') as handle:
            return json.load(handle)

    def save_users(users):
        path = users_file_path()
        with open(path, 'w', encoding='utf-8') as handle:
            json.dump(users, handle, indent=2)

    def hash_password(password):
        return hashlib.sha256(password.encode('utf-8')).hexdigest()

    def verify_password(password, password_hash):
        return hmac.compare_digest(hash_password(password), password_hash)

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
        return render_template_string(
            html_template,
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
        return render_template_string(
            signup_template,
            signup_error=None,
            user_id='',
        )

    @app.post('/signup')
    def signup_submit():
        user_id = request.form.get('user_id', '').strip()
        password = request.form.get('password', '')
        if not user_id or not password:
            return render_template_string(
                signup_template,
                signup_error='Both user ID and password are required.',
                user_id=user_id,
            )
        users = load_users()
        if user_id in users:
            return render_template_string(
                signup_template,
                signup_error='That user ID is already registered. Please choose another.',
                user_id=user_id,
            )
        users[user_id] = hash_password(password)
        save_users(users)
        session['user_id'] = user_id
        return redirect(url_for('index'))

    @app.get('/login')
    def login_page():
        if 'user_id' in session:
            return redirect(url_for('index'))
        return render_template_string(
            login_template,
            login_error=None,
            user_id='',
        )

    @app.post('/login')
    def login_submit():
        user_id = request.form.get('user_id', '').strip()
        password = request.form.get('password', '')
        if not user_id or not password:
            return render_template_string(
                login_template,
                login_error='User ID and password are required.',
                user_id=user_id,
            )
        users = load_users()
        password_hash = users.get(user_id)
        if not password_hash or not verify_password(password, password_hash):
            return render_template_string(
                login_template,
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
        symbol = request.form.get('symbol', 'AAPL')
        try:
            response = requests.get(f"{api_base_url}/api/v1/stock/{symbol}", timeout=10)
            response.raise_for_status()
            result = json.dumps(response.json(), indent=2)
        except Exception as exc:
            result = f'Error: {exc}'
        return render_template_string(
            html_template,
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
            'symbol': request.form.get('symbol', 'MSFT'),
        }
        data, error = fetch_api('/api/v1/watchlist', 'POST', payload)
        if error:
            return render_template_string(
                html_template,
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
            'symbol': request.form.get('symbol', 'AAPL'),
            'pattern': request.form.get('pattern', 'bullish-engulfing'),
            'threshold': float(request.form.get('threshold', '150.0')),
        }
        data, error = fetch_api('/api/v1/pattern-alerts', 'POST', payload)
        if error:
            result = f'Error creating alert: {error}'
        else:
            result = f'Alert created for {payload["symbol"].upper()}.'
        return render_template_string(
            html_template,
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
        return render_template_string(watchlist_template, user_id=session['user_id'])

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
            watched = stock['market_data']
            watched['symbol'] = symbol
            watched['triggered'] = False
            watchlist_data.append(watched)

        alerts_data = []
        for alert in alerts.get('alerts', []):
            symbol_data = next((item for item in watchlist_data if item['symbol'] == alert['symbol']), None)
            triggered = False
            if symbol_data and alert.get('threshold') is not None:
                triggered = symbol_data['last_price'] <= alert['threshold']
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
