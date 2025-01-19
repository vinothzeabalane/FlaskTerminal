from flask import Flask, render_template, request, jsonify
from flask_socketio import SocketIO
import paramiko
import time

app = Flask(__name__)
app.config['SECRET_KEY'] = 'your_secret_key'
socketio = SocketIO(app)

ssh_sessions = {}

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/connect', methods=['POST'])
def connect():
    data = request.json
    hostname = data['hostname']
    username = data['username']
    password = data['password']
    
    try:
        ssh_client = paramiko.SSHClient()
        ssh_client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
        ssh_client.connect(hostname, username=username, password=password)
        ssh_sessions[request.remote_addr] = ssh_client
        return jsonify({"status": "success", "message": f"Connected to {hostname}, press enter to continue"})
    except Exception as e:
        return jsonify({"status": "error", "message": str(e)})

@app.route('/disconnect', methods=['POST'])
def disconnect():
    ip_address = request.remote_addr
    if ip_address in ssh_sessions:
        ssh_sessions[ip_address].close()
        del ssh_sessions[ip_address]
        return jsonify({"status": "success", "message": "Disconnected from the host."})
    else:
        return jsonify({"status": "error", "message": "No active session to disconnect."})

@socketio.on('command')
def handle_command(data):
    ip_address = request.remote_addr
    command = data['command']
    
    if ip_address in ssh_sessions:
        ssh_client = ssh_sessions[ip_address]
        try:
            channel = ssh_client.invoke_shell()
            channel.send(command + '\n')
            time.sleep(0.5)  # Allow time for command execution
            output = ''
            while channel.recv_ready():
                output += channel.recv(1024).decode('utf-8')
            socketio.emit('output', {'output': output})
        except Exception as e:
            socketio.emit('output', {'output': f"Error: {str(e)}"})
    else:
        socketio.emit('output', {'output': "No active session. Please connect first."})

if __name__ == '__main__':
    socketio.run(app, host='0.0.0.0', port=5000)
