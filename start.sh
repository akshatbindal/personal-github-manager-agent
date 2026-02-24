#!/bin/bash
# Enable unbuffered output for Python
export PYTHONUNBUFFERED=1

echo "Starting Personal GitHub Manager Agent..."

# Start the polling service in the background
python -u -m src.polling &
# Start a dummy web server to satisfy Cloud Run's health check
python -u -c "from http.server import HTTPServer, BaseHTTPRequestHandler; import os; port = int(os.environ.get('PORT', 8080)); HTTPServer(('', port), type('H', (BaseHTTPRequestHandler,), {'do_GET': lambda s: (s.send_response(200), s.end_headers(), s.wfile.write(b'OK'))})).serve_forever()" &
# Start the bot (this is our main process)
python -u -m src.bot
