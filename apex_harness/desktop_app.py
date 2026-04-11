import threading
import time
import webview
from .web import start_server

def start_flask():
    start_server(port=5005)

def run_app():
    # Start the Flask web server in a daemon thread
    t = threading.Thread(target=start_flask, daemon=True)
    t.start()
    
    # Wait a moment for Flask to initialize
    time.sleep(1)
    
    # Create the native desktop window pointing to the local server
    webview.create_window(
        title="APEX-HARNESS Security Toolkit",
        url="http://localhost:5005",
        width=1200,
        height=800,
        min_size=(800, 600)
    )
    
    # Start the application loop
    webview.start(debug=False)

if __name__ == '__main__':
    run_app()
