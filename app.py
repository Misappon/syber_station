from datetime import datetime

from flask import Flask, render_template, request, redirect, session
import sqlite3
from functools import wraps
from flask_wtf import FlaskForm
from wtforms import StringField, SubmitField
from wtforms.validators import DataRequired


app = Flask(__name__)
app.secret_key = 'your_secret_key'  # 设置会话密钥，用于安全目的

# 配置数据库连接
db = sqlite3.connect('page_visit.db', check_same_thread=False)
cursor = db.cursor()

# 创建表格
cursor.execute('''
    CREATE TABLE IF NOT EXISTS page_visit (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        url TEXT NOT NULL,
        ip TEXT NOT NULL
    )
''')
def create_table():
    conn = get_db_connection()
    conn.execute('CREATE TABLE IF NOT EXISTS messages (content TEXT, sender_ip TEXT, timestamp TEXT)')
    conn.commit()
    conn.close()

class MessageForm(FlaskForm):
    content = StringField('Message', validators=[DataRequired()])
    submit = SubmitField('Send')


db.commit()


# 数据库连接和表格创建
def get_db_connection():
    conn = sqlite3.connect('msg.db')
    conn.row_factory = sqlite3.Row
    return conn

def get_admin_db_connection():
    conn = sqlite3.connect('msg_admin.db')
    conn.row_factory = sqlite3.Row
    return conn

def create_tables():
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute('CREATE TABLE IF NOT EXISTS messages (content TEXT, sender_ip TEXT, timestamp TEXT)')
    conn.commit()
    conn.close()

    admin_conn = get_admin_db_connection()
    admin_cursor = admin_conn.cursor()
    admin_cursor.execute('CREATE TABLE IF NOT EXISTS messages (content TEXT, sender_ip TEXT, timestamp TEXT)')
    admin_conn.commit()
    admin_conn.close()

# 登录状态检查装饰器
def login_required(view_func):
    @wraps(view_func)
    def wrapper(*args, **kwargs):
        if 'logged_in' in session:
            return view_func(*args, **kwargs)
        else:
            return redirect('/login')
    return wrapper

# 登录前检查注册装饰器
def registration_required(view_func):
    @wraps(view_func)
    def wrapper(*args, **kwargs):
        if 'registered' in session:
            return view_func(*args, **kwargs)
        else:
            return redirect('/register')
    return wrapper

# 主页路由
@app.route('/')
def index():
    return render_template('index.html')

# 登录页面
@app.route('/login', methods=['GET', 'POST'])
@registration_required
def login():
    if request.method == 'POST':
        username = request.form.get('username')
        password = request.form.get('password')
        # 在这里进行登录验证逻辑

        # 假设判断用户是否为管理员的逻辑为 is_admin() 函数
        admin = is_admin(username)

        # 如果验证通过，将登录状态和管理员权限保存到会话中
        session['logged_in'] = True
        session['admin'] = admin
        return redirect('/panel')
    return render_template('login.html')

# 注册页面
@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        username = request.form.get('username')
        password = request.form.get('password')
        # 在这里进行注册逻辑

        # 如果注册成功，将注册状态保存到会话中
        session['registered'] = True
        return redirect('/login')
    return render_template('register.html')

# 面板页面
@app.route('/panel', methods=['GET', 'POST'])
@app.route('/panel/msg_delete/<int:message_id>', methods=['GET', 'POST'])
@login_required
def panel(message_id=None):
    if request.method == 'POST':
        if request.form.get('action') == 'clear':
            # 清除访问记录
            cursor.execute('DELETE FROM page_visit')
            db.commit()
            return redirect('/panel')

        if request.form.get('action') == 'clear_msg_admin':
            # 清除消息记录
            conn_admin = get_admin_db_connection()
            cursor_admin = conn_admin.cursor()
            cursor_admin.execute('DELETE FROM messages')
            conn_admin.commit()
            conn_admin.close()
            return redirect('/panel')

    if request.method == 'GET':
        if message_id is not None:
            conn_admin = get_admin_db_connection()
            cursor_admin = conn_admin.cursor()
            cursor_admin.execute('DELETE FROM messages WHERE rowid = ?', (message_id,))
            conn_admin.commit()
            conn_admin.close()
            return redirect('/panel')

    if request.path.startswith('/panel/msg_delete/') and request.method == 'POST':
        # 处理删除消息的逻辑
        message_id = int(request.path.split('/panel/msg_delete/')[1])

        conn_admin = get_admin_db_connection()
        cursor_admin = conn_admin.cursor()
        cursor_admin.execute('DELETE FROM messages WHERE rowid = ?', (message_id,))
        conn_admin.commit()
        conn_admin.close()

        return redirect('/panel')

    # 读取数据库中的访问记录
    conn_admin = get_admin_db_connection()
    cursor_admin = conn_admin.cursor()
    cursor_admin.execute('SELECT * FROM messages')
    admin_messages = cursor_admin.fetchall()
    cursor.execute('SELECT url, ip FROM page_visit')
    visit_records = cursor.fetchall()
    return render_template('panel.html', visit_records=visit_records, admin=session.get('admin'), admin_messages=admin_messages)




    # 读取数据库中的访问记录
    conn_admin = get_admin_db_connection()
    cursor_admin = conn_admin.cursor()
    cursor_admin.execute('SELECT * FROM messages')
    admin_messages = cursor_admin.fetchall()
    cursor.execute('SELECT url, ip FROM page_visit')
    visit_records = cursor.fetchall()
    return render_template('panel.html', visit_records=visit_records, admin=session.get('admin'), admin_messages=admin_messages)


# 页面访问记录
@app.before_request
def log_page_visit():
    url = request.path
    ip = request.remote_addr
    # 将访问记录插入数据库
    cursor.execute('INSERT INTO page_visit (url, ip) VALUES (?, ?)', (url, ip))
    db.commit()

# 部署至/skips/skip1并自动跳转
@app.route('/skips/skip1')
def skip1():
    return redirect('https://y.music.163.com/m/playlist?id=6965428938&userid=1333458949&creatorId=1333458949')

# 注销登录
@app.route('/logout')
@login_required
def logout():
    session.clear()
    return redirect('/login')


# 留言板路由
@app.route('/msgb', methods=['GET', 'POST'])
@app.route('/msgb/create', methods=['POST'])
@app.route('/msgb/delete/<int:message_id>', methods=['POST'])
def message_board(message_id=None):
    create_table()

    if request.method == 'POST':
        if request.path == '/msgb/create':
            # 处理发送消息的逻辑
            content = request.form['content']
            sender_ip = request.remote_addr
            timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

            # 保存消息到数据库
            conn = get_db_connection()
            cursor = conn.cursor()
            cursor.execute('INSERT INTO messages (content, sender_ip, timestamp) VALUES (?, ?, ?)',
                           (content, sender_ip, timestamp))
            conn.commit()
            conn.close()

            # 保存消息到管理员数据库
            admin_conn = get_admin_db_connection()
            admin_cursor = admin_conn.cursor()
            admin_cursor.execute('INSERT INTO messages (content, sender_ip, timestamp) VALUES (?, ?, ?)',
                                 (content, sender_ip, timestamp))
            admin_conn.commit()
            admin_conn.close()

            return redirect('/msgb')

        elif request.path.startswith('/msgb/delete/'):
            # 处理删除消息的逻辑
            message_id = int(request.path.split('/msgb/delete/')[1])

            conn = get_db_connection()
            cursor = conn.cursor()
            cursor.execute('DELETE FROM messages WHERE rowid = ?', (message_id,))
            conn.commit()
            conn.close()

            return redirect('/msgb')

    # 获取留言列表
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute('SELECT rowid, * FROM messages')
    messages = cursor.fetchall()
    conn.close()

    return render_template('msgb.html', messages=messages)






def is_admin(username):
    # 判断用户是否为管理员的逻辑
    # 返回 True 或 False
    return False

if __name__ == '__main__':
    create_tables()
    app.run(host='0.0.0.0')
