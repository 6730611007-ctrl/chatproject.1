import os
import uuid # นำเข้าไลบรารีสำหรับสร้าง ID ให้ข้อความ
from flask import Flask, render_template, request, send_from_directory, session, redirect, url_for, jsonify
from flask_socketio import SocketIO, emit
from datetime import timedelta
from werkzeug.utils import secure_filename

app = Flask(__name__)
app.config['SECRET_KEY'] = 'chat-project-super-secret'
app.config['UPLOAD_FOLDER'] = 'uploads'
app.config['MAX_CONTENT_LENGTH'] = 16 * 1024 * 1024
app.config['PERMANENT_SESSION_LIFETIME'] = timedelta(days=7)

if not os.path.exists(app.config['UPLOAD_FOLDER']):
    os.makedirs(app.config['UPLOAD_FOLDER'])

socketio = SocketIO(app, cors_allowed_origins="*")

chat_history = []
MAX_HISTORY = 1000000  # กำหนดจำนวนข้อความสูงสุดในประวัติแชท (ปรับได้ตามต้องการ)

# --- ส่วนที่เพิ่ม: ฟังก์ชันต้อนรับเมื่อมีคนเข้ามาใหม่ ---
@socketio.on('user_joined')
def handle_user_joined(da):
    username = da['username']
    
    welcome_text = f"ยินดีต้อนรับคุณ {username} ครับ! 🎉 คุณสามารถพิมพ์คำสั่งต่างๆ เช่น 'สวัสดี', 'เวลา', หรือ 'ทำอะไรได้บ้าง' เพื่อดูว่าผมช่วยอะไรได้บ้างนะครับ!"
    
    # จัดรูปแบบให้เป็นข้อความจากบอท
    bot_msg = {
        'id': str(uuid.uuid4()),      # ใส่รหัสข้อความ (ให้ลบได้)
        'username': 'Chatbot 🤖',     # ชื่อผู้ส่งคือบอท
        'message': welcome_text,      # ข้อความต้อนรับของคุณ
        'type': 'text'
    }
    
    # บันทึกลงประวัติแชท และกระจายข้อความให้ทุกคนในห้องเห็น
    global chat_history
    chat_history.append(bot_msg)
    if len(chat_history) > MAX_HISTORY: 
        chat_history.pop(0)
        
    emit('receive_message', bot_msg, broadcast=True)

def chatbot_response(msg):
    msg = msg.lower()
    if 'สวัสดี' in msg or 'hello' in msg:
        return "สวัสดีครับ! ยินดีต้อนรับสู่ห้องแชท มีอะไรให้ช่วยไหมครับ?"
    
    # เอา "ทำอะไรได้บ้าง" มาไว้ก่อน เพราะคำนี้มีคำว่า "เวลา" ปนอยู่ (ทำอะไ"รได้"บ้าง)
    elif 'ทำอะไรได้บ้าง' in msg:
        return "ผมช่วยบันทึกประวัติแชท ตอบคำถามพื้นฐาน และแสดงไฟล์ที่ส่งได้ครับ!"
    
    elif 'เวลา' in msg:
        import datetime
        return f"ขณะนี้เวลา {datetime.datetime.now().strftime('%H:%M:%S')} ครับ"
        
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

@socketio.on('send_message')
def handle_message(data):
    # สร้าง ID ให้ข้อความทุกครั้งที่มีคนพิมพ์
    data['id'] = str(uuid.uuid4())
    
    chat_history.append(data)
    if len(chat_history) > MAX_HISTORY: chat_history.pop(0)
    emit('receive_message', data, broadcast=True)
    
    bot_reply = chatbot_response(data['message'])
    if bot_reply:
        bot_data = {'id': str(uuid.uuid4()), 'username': 'Chatbot 🤖', 'message': bot_reply, 'type': 'text'}
        chat_history.append(bot_data)
        emit('receive_message', bot_data, broadcast=True)

@socketio.on('send_file')
def handle_file(data):
    # สร้าง ID ให้การส่งไฟล์ด้วย
    data['id'] = str(uuid.uuid4())
    chat_history.append(data)
    emit('receive_message', data, broadcast=True)

# --- ส่วนที่เพิ่ม: API สำหรับรับคำสั่งยกเลิกข้อความ ---
@socketio.on('delete_message')
def handle_delete(data):
    msg_id = data.get('id')
    global chat_history
    # อัปเดตประวัติแชท โดยลบข้อความที่มี id ตรงกันออก
    chat_history = [msg for msg in chat_history if msg.get('id') != msg_id]
    
    # ส่งสัญญาณไปบอกให้ทุกเครื่องลบข้อความนี้ออกจากหน้าจอ
    emit('message_deleted', {'id': msg_id}, broadcast=True)

if __name__ == '__main__':
    socketio.run(app, debug=True, host='0.0.0.0', port=5000)