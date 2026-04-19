import os
import json
import uuid # นำเข้าไลบรารีสำหรับสร้าง ID ให้ข้อความ
from flask import Flask, render_template, request, send_from_directory, session, redirect, url_for, jsonify
from flask_socketio import SocketIO, emit
from datetime import timedelta
from werkzeug.utils import secure_filename

app = Flask(__name__)
app.config['SECRET_KEY'] = 'chat-project-super-secret'
app.config['HISTORY_FILE'] = 'chat_history.json' # ไฟล์ที่ใช้เก็บข้อมูล
app.config['UPLOAD_FOLDER'] = 'uploads'
app.config['MAX_CONTENT_LENGTH'] = 16 * 1024 * 1024
app.config['PERMANENT_SESSION_LIFETIME'] = timedelta(days=7)

MAX_HISTORY = 1000000  # ย้ายมากำหนดค่าคงที่ไว้ด้านบน

# ตรวจสอบและสร้างโฟลเดอร์ uploads อัตโนมัติ (ป้องกัน Error ตอนส่งไฟล์)
os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)

# ฟังก์ชันโหลดข้อมูลจากไฟล์
def load_data():
    if os.path.exists(app.config['HISTORY_FILE']):
        with open(app.config['HISTORY_FILE'], 'r', encoding='utf-8') as f:
            return json.load(f)
    return []

# ฟังก์ชันบันทึกข้อมูลลงไฟล์
def save_data(data):
    with open(app.config['HISTORY_FILE'], 'w', encoding='utf-8') as f:
        json.dump(data, f, ensure_ascii=False, indent=4)

# โหลดประวัติเก่า และตั้งค่า SocketIO แค่ครั้งเดียว
chat_history = load_data() 
socketio = SocketIO(app, cors_allowed_origins="*")

@socketio.on('send_message')
def handle_message(data):
    data['id'] = str(uuid.uuid4())
    
    global chat_history
    chat_history.append(data)
    if len(chat_history) > MAX_HISTORY: 
        chat_history.pop(0)
        
    save_data(chat_history) 
    emit('receive_message', data, broadcast=True)
    
    # ส่วนของ Chatbot
    bot_reply = chatbot_response(data['message'])
    if bot_reply:
        bot_data = {
            'id': str(uuid.uuid4()), 
            'username': 'Chatbot 🤖', 
            'message': bot_reply, 
            'type': 'text'
        }
        chat_history.append(bot_data)
        save_data(chat_history) # บันทึกบอทลงไฟล์
        emit('receive_message', bot_data, broadcast=True)


@socketio.on('user_joined')
def handle_user_joined(da):
    username = da['username']
    welcome_text = f"ยินดีต้อนรับคุณ {username} ครับ! 🎉 คุณสามารถพิมพ์คำสั่งต่างๆ เช่น 'สวัสดี', 'เวลา', หรือ 'ทำอะไรได้บ้าง' เพื่อดูว่าผมช่วยอะไรได้บ้างนะครับ!"
    
    bot_msg = {
        'id': str(uuid.uuid4()),      
        'username': 'Chatbot 🤖',     
        'message': welcome_text,      
        'type': 'text'
    }
    
    global chat_history
    chat_history.append(bot_msg)
    if len(chat_history) > MAX_HISTORY: 
        chat_history.pop(0)
        
    save_data(chat_history) # เพิ่มการบันทึกข้อมูล
    emit('receive_message', bot_msg, broadcast=True)

def chatbot_response(msg):
    msg = msg.lower()
    if 'สวัสดี' in msg or 'hello' in msg:
        return "สวัสดีครับ! ยินดีต้อนรับสู่ห้องแชท มีอะไรให้ช่วยไหมครับ?"
    elif 'ทำอะไรได้บ้าง' in msg:
        return "ผมช่วยบันทึกประวัติแชท ตอบคำถามพื้นฐาน และแสดงไฟล์ที่ส่งได้ครับ!"
    elif 'เวลา' in msg or 'time' in msg:
        import datetime
        return f"ขณะนี้เวลา {datetime.datetime.now().strftime('%H:%M:%S')} ครับ"
    elif 'ช่วยด้วย' in msg or 'help' in msg:
        return "ขอโทษครับ ฉันพยายามช่วยคุณอย่างเต็มที่แล้ว แต่บางครั้งก็อาจมีข้อผิดพลาดเกิดขึ้น ลองสอบถามอีกครั้งได้นะครับ!"
    elif 'ลบข้อความ' in msg or 'ลบ' in msg:
        return "คุณสามารถลบข้อความได้โดยคลิกที่ปุ่ม 'ลบ' ที่อยู่ถัดจากข้อความนั้นครับ!"
    elif 'ขอบคุณ' in msg or 'thanks' in msg:
        return "ยินดีครับ! ถ้ามีคำถามเพิ่มเติมก็ถามได้เลยนะครับ!"
    return None
    
@app.route('/')
def index():
    if 'username' not in session:
        return redirect(url_for('login'))
    return render_template('index.html', username=session['username'])

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        session.permanent = True
        session['username'] = request.form['username']
        return redirect(url_for('index'))
    return render_template('login.html')

@app.route('/logout')
def logout():
    session.pop('username', None)
    return redirect(url_for('login'))

@app.route('/upload', methods=['POST'])
def upload_file():
    if 'file' not in request.files:
        return jsonify({'error': 'No file part'}), 400
    
    file = request.files['file']
    if file.filename == '':
        return jsonify({'error': 'No selected file'}), 400
        
    if file:
        filename = secure_filename(file.filename)
        file.save(os.path.join(app.config['UPLOAD_FOLDER'], filename))
        return jsonify({
            'filename': filename, 
            'file_url': f"/download/{filename}"
        })

@app.route('/download/<filename>')
def download_file(filename):
    return send_from_directory(app.config['UPLOAD_FOLDER'], filename)

@socketio.on('connect')
def handle_connect():
    emit('load_history', chat_history)

@socketio.on('send_file')
def handle_file(data):
    data['id'] = str(uuid.uuid4())
    global chat_history
    chat_history.append(data)
    save_data(chat_history) # เพิ่มการบันทึกข้อมูล
    emit('receive_message', data, broadcast=True)

@socketio.on('delete_message')
def handle_delete(data):
    msg_id = data.get('id')
    global chat_history
    
    # อัปเดตตัวแปรและเซฟลงไฟล์ เพื่อไม่ให้ข้อความที่ถูกลบโผล่มาอีกตอนรีสตาร์ทเซิร์ฟเวอร์
    chat_history = [msg for msg in chat_history if msg.get('id') != msg_id]
    save_data(chat_history) 
    
    emit('message_deleted', {'id': msg_id}, broadcast=True)

if __name__ == '__main__':
    socketio.run(app, debug=True, host='0.0.0.0', port=5000)
