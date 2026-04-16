from flask import Flask, render_template
from flask_socketio import SocketIO, emit

app = Flask(__name__)
app.config['SECRET_KEY'] = 'mysecretkey'
# ใช้ SocketIO สำหรับสื่อสารแบบ Real-time สองทาง
socketio = SocketIO(app, cors_allowed_origins="*")

@app.route('/')
def index():
    # ส่งหน้าเว็บ UI ไปให้ผู้ใช้
    return render_template('index.html')

@socketio.on('send_message')
def handle_message(data):
    # รับข้อความจากเครื่องใดๆ แล้วกระจาย (Broadcast) ไปให้ทุกเครื่องที่เชื่อมต่ออยู่
    emit('receive_message', data, broadcast=True)

if __name__ == '__main__':
    # รันเซิร์ฟเวอร์แบบเปิดให้เครื่องอื่นในวง LAN เข้าถึงได้ (host='0.0.0.0')
    socketio.run(app, debug=True, host='0.0.0.0', port=5000)