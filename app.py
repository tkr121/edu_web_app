from flask import Flask, render_template, g, session,redirect,url_for,request
from flask_login import LoginManager

import os
from config import *
from exts import db
from flask_migrate import Migrate

from dotenv import load_dotenv

load_dotenv()  # 加载 .env 文件中的环境变量

# 蓝图导入
from blueprints.auth import bp as auth_bp
from blueprints.student import bp as student_bp
from blueprints.teacher import bp as teacher_bp

# 模型导入
from models import Student, Teacher

# 初始化 Flask 应用
app = Flask(__name__)
app.config.from_object('config')  # 使用 Config 类加载配置

# 数据库配置
DB_USER = os.environ.get('DB_USER', 'root')
DB_PASSWORD = os.environ.get('DB_PASSWORD', '123456')
DB_HOST = os.environ.get('DB_HOST', '127.0.0.1')
DB_PORT = os.environ.get('DB_PORT', '3306')
DB_NAME = os.environ.get('DB_NAME', 'flaskdb')
app.config['SQLALCHEMY_DATABASE_URI'] = f"mysql+pymysql://{DB_USER}:{DB_PASSWORD}@{DB_HOST}:{DB_PORT}/{DB_NAME}?charset=utf8mb4"
# 初始化数据库和迁移工具
db.init_app(app)
migrate = Migrate(app, db)


login_manager = LoginManager()
login_manager.init_app(app)
login_manager.login_view = 'auth.login'  # 设置未登录时跳转的视图


# 注册蓝图
app.register_blueprint(auth_bp)
app.register_blueprint(student_bp)

app.register_blueprint(teacher_bp)

# 确保上传目录存在
os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)
@login_manager.user_loader
def load_user(user_id):
    # 从 session 获取 user_type 来决定加载哪个模型
    user_type = session.get('user_type')

    if user_type == 'teacher':
        return Teacher.query.get(int(user_id))
    elif user_type == 'student':
        return Student.query.get(int(user_id))
    else:
        # 如果没有 user_type，默认尝试加载教师或学生（可选）
        teacher = Teacher.query.get(int(user_id))
        if teacher:
            return teacher
        return Student.query.get(int(user_id))


# 请求前钩子：用户身份绑定到 g 对象
@app.before_request
def my_before_request():
    user_id = session.get("user_id")
    user_type = session.get("user_type")  # 'teacher' or 'student'

    if user_id and user_type:
        if user_type == 'teacher':
            user = Teacher.query.get(user_id)
        elif user_type == 'student':
            user = Student.query.get(user_id)
        else:
            user = None
    else:
        user = None

    g.user = user

@app.route('/')
def root():
    return redirect(url_for('auth.index'))

# 上下文处理器：将用户传递给模板
@app.context_processor
def my_context_processor():
    return {"user": g.user}


'''# 错误处理页面
@app.errorhandler(404)
def page_not_found(e):
    return render_template('404.html'), 404


@app.errorhandler(500)
def internal_server_error(e):
    return render_template('500.html'), 500
'''

if __name__ == '__main__':
    app.run()
