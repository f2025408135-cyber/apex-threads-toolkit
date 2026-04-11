import os
import sqlite3
import subprocess
import threading
import csv
import io
from flask import Flask, render_template, jsonify, request, Response
from flask_socketio import SocketIO

app = Flask(__name__)
socketio = SocketIO(app, cors_allowed_origins="*")

DB_PATH = "./output/apex_harness.db"
LOG_FILE = "./output/latest_run.log"

def tail_logs():
    if not os.path.exists(LOG_FILE):
        open(LOG_FILE, 'w').close()
    
    with open(LOG_FILE, 'r') as f:
        f.seek(0, 2)
        while True:
            line = f.readline()
            if not line:
                socketio.sleep(0.1)
                continue
            socketio.emit('log_data', {'data': line.strip()})

@socketio.on('connect')
def on_connect():
    socketio.emit('log_data', {'data': '--- Connected to APEX-HARNESS Live Stream ---'})

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/api/stats')
def get_stats():
    if not os.path.exists(DB_PATH):
        return jsonify({
            "total_tests": 0,
            "confirmed_findings": 0,
            "probable_findings": 0,
            "null_signals": 0,
            "ambiguous": 0,
            "errors": 0,
            "findings_list": []
        })
        
    try:
        conn = sqlite3.connect(DB_PATH)
        conn.row_factory = sqlite3.Row
        
        # Get latest run_id
        cur = conn.cursor()
        cur.execute("SELECT run_id FROM run_metadata ORDER BY completed_at DESC LIMIT 1")
        row = cur.fetchone()
        if not row:
            return jsonify({})
            
        run_id = row['run_id']
        
        # Get metrics
        cur.execute("SELECT * FROM run_metadata WHERE run_id = ?", (run_id,))
        metadata = dict(cur.fetchone())
        
        # Get findings
        cur.execute("SELECT * FROM findings WHERE run_id = ?", (run_id,))
        findings = [dict(r) for r in cur.fetchall()]
        
        metadata["findings_list"] = findings
        return jsonify(metadata)
        
    except Exception as e:
        return jsonify({"error": str(e)}), 500
    finally:
        if 'conn' in locals():
            conn.close()

@app.route('/api/start', methods=['POST'])
def start_tests():
    data = request.json
    suite = data.get("suite", "all")
    delay_ms = data.get("delay_ms", 500)
    
    # Clear log
    with open(LOG_FILE, 'w') as f:
        f.write(f"--- Starting new run: {suite} ---\n")
        
    def run_cmd():
        cmd = ["apex-harness"]
        if suite == "all":
            cmd.append("run-all")
        elif suite == "oauth":
            cmd.append("run-oauth")
        elif suite == "race":
            cmd.append("run-race")
        else:
            cmd.extend(["run-suite", f"--suite={suite.upper()}"])
            
        cmd.append(f"--delay-ms={delay_ms}")
        subprocess.Popen(cmd)

    threading.Thread(target=run_cmd).start()
    return jsonify({"status": "started", "suite": suite})

@app.route('/api/export/csv')
def export_csv():
    if not os.path.exists(DB_PATH):
        return "No database found", 404
        
    try:
        conn = sqlite3.connect(DB_PATH)
        conn.row_factory = sqlite3.Row
        cur = conn.cursor()
        
        cur.execute("SELECT run_id FROM run_metadata ORDER BY completed_at DESC LIMIT 1")
        row = cur.fetchone()
        if not row:
            return "No runs available", 404
            
        run_id = row['run_id']
        cur.execute("SELECT * FROM findings WHERE run_id = ?", (run_id,))
        findings = [dict(r) for r in cur.fetchall()]
        
        si = io.StringIO()
        if findings:
            writer = csv.DictWriter(si, fieldnames=findings[0].keys())
            writer.writeheader()
            writer.writerows(findings)
            
        output = si.getvalue()
        
        return Response(
            output,
            mimetype="text/csv",
            headers={"Content-disposition": "attachment; filename=findings_export.csv"}
        )
    except Exception as e:
        return str(e), 500
    finally:
        if 'conn' in locals():
            conn.close()

def start_server(port=5000):
    socketio.start_background_task(tail_logs)
    socketio.run(app, host='0.0.0.0', port=port, allow_unsafe_werkzeug=True)

if __name__ == '__main__':
    start_server()
