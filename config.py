# config.py

import os

basedir = os.path.abspath(os.path.dirname(__file__))


# 安全密钥（用于 CSRF、Session 等）
SECRET_KEY = os.environ.get('SECRET_KEY', 'fallback-secret-key-for-dev')

# 上传设置
UPLOAD_FOLDER = os.path.join(basedir, 'uploads')
MAX_CONTENT_LENGTH = 16 * 1024 * 1024  # 最大上传大小：16MB

# 数据库配置
DB_USER = os.environ.get('DB_USER', 'root')
DB_PASSWORD = os.environ.get('DB_PASSWORD', '123456')
DB_HOST = os.environ.get('DB_HOST', '127.0.0.1')
DB_PORT = os.environ.get('DB_PORT', '3306')
DB_NAME = os.environ.get('DB_NAME', 'flaskdb')
SQLALCHEMY_DATABASE_URI = f"mysql+pymysql://{DB_USER}:{DB_PASSWORD}@{DB_HOST}:{DB_PORT}/{DB_NAME}?charset=utf8mb4"
SQLALCHEMY_TRACK_MODIFICATIONS = False
# 登录配置
LOGIN_VIEW = 'auth.login'
LOGIN_MESSAGE = '请先登录以访问该页面。'
LOGIN_MESSAGE_CATEGORY = 'info'

# 表单安全
WTF_CSRF_ENABLED = True

# 日志配置
LOG_TO_STDOUT = os.environ.get('LOG_TO_STDOUT', False)
# AI 模型路径
CHATGLM_MODEL_PATH = os.path.join(basedir, 'models', 'chatglm_6b')

# 知识库路径
KNOWLEDGE_BASE_PATH = os.path.join(basedir, 'knowledge_base')

SPARKAI_URL = 'wss://spark-api.xf-yun.com/v3.5/chat'

# 替换为你自己的 AppID、API Key、Secret
SPARKAI_APP_ID = '1bb6ca2f'
SPARKAI_API_KEY = '139d218f9285c5093675b478966a3b54'
SPARKAI_API_SECRET = 'ZWM5OWY1NWJmOGM3MGZjZTRkYjE0ZWJj'

# domain值
SPARKAI_DOMAIN = 'generalv3.5'

response_format={ "type": "json_object" }