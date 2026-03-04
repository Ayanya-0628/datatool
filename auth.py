# 可选认证模块：用户注册/登录，仅当 ENABLE_AUTH=1 时启用
# 适用于方式三云端部署时「注册后使用」
import os
import sqlite3
from functools import wraps
from flask import Blueprint, request, redirect, url_for, render_template, jsonify, flash
from flask_login import LoginManager, login_user, logout_user, login_required, current_user
from werkzeug.security import generate_password_hash, check_password_hash

# 仅环境变量开启时生效
ENABLE_AUTH = os.environ.get("ENABLE_AUTH", "").lower() in ("1", "true", "yes")

# 供 app 使用的“需要登录”装饰器（未开启认证时为 no-op）
def _noop_decorator(f):
    return f


def init_auth(app, data_dir):
    """初始化认证：SQLite 用户表、Flask-Login、登录/注册/登出路由。返回装饰器 require_auth。"""
    if not ENABLE_AUTH:
        return _noop_decorator

    db_path = os.path.join(data_dir, "users.db")
    app.config["AUTH_DB_PATH"] = db_path

    login_manager = LoginManager(app)
    login_manager.login_view = "auth.login"
    login_manager.login_message = "请先登录"
    login_manager.session_protection = "strong"

    def get_db():
        conn = sqlite3.connect(app.config["AUTH_DB_PATH"])
        conn.row_factory = sqlite3.Row
        return conn

    def init_db():
        with get_db() as c:
            c.execute(
                """
                CREATE TABLE IF NOT EXISTS users (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    username TEXT UNIQUE NOT NULL,
                    password_hash TEXT NOT NULL,
                    created_at TEXT NOT NULL
                )
            """
            )

    init_db()

    class User:
        def __init__(self, uid, username, password_hash_str):
            self.id = uid
            self.username = username
            self.password_hash = password_hash_str

        @property
        def is_authenticated(self):
            return True

        @property
        def is_active(self):
            return True

        @property
        def is_anonymous(self):
            return False

        def get_id(self):
            return str(self.id)

    @login_manager.user_loader
    def load_user(uid):
        try:
            with get_db() as c:
                row = c.execute("SELECT id, username, password_hash FROM users WHERE id = ?", (int(uid),)).fetchone()
            if row:
                return User(row["id"], row["username"], row["password_hash"])
        except Exception:
            pass
        return None

    bp = Blueprint("auth", __name__, url_prefix="", template_folder="templates")

    @bp.route("/login", methods=["GET", "POST"])
    def login():
        if request.method == "GET":
            return render_template("login.html")
        username = (request.form.get("username") or "").strip()
        password = request.form.get("password") or ""
        if not username or not password:
            flash("请输入用户名和密码", "error")
            return render_template("login.html")
        with get_db() as c:
            row = c.execute(
                "SELECT id, username, password_hash FROM users WHERE username = ?",
                (username,),
            ).fetchone()
        if not row or not check_password_hash(row["password_hash"], password):
            flash("用户名或密码错误", "error")
            return render_template("login.html")
        user = User(row["id"], row["username"], row["password_hash"])
        login_user(user, remember=True)
        next_url = request.args.get("next") or url_for("index")
        return redirect(next_url)

    @bp.route("/register", methods=["GET", "POST"])
    def register():
        if request.method == "GET":
            return render_template("register.html")
        username = (request.form.get("username") or "").strip()
        password = request.form.get("password") or ""
        password2 = request.form.get("password2") or ""
        if not username or not password:
            flash("请填写用户名和密码", "error")
            return render_template("register.html")
        if len(username) < 2:
            flash("用户名至少 2 个字符", "error")
            return render_template("register.html")
        if password != password2:
            flash("两次输入的密码不一致", "error")
            return render_template("register.html")
        if len(password) < 6:
            flash("密码至少 6 个字符", "error")
            return render_template("register.html")
        pw_hash = generate_password_hash(password, method="scrypt")
        try:
            with get_db() as c:
                c.execute(
                    "INSERT INTO users (username, password_hash, created_at) VALUES (?, ?, datetime('now'))",
                    (username, pw_hash),
                )
        except sqlite3.IntegrityError:
            flash("该用户名已被注册", "error")
            return render_template("register.html")
        flash("注册成功，请登录", "success")
        return redirect(url_for("auth.login"))

    @bp.route("/logout", methods=["GET", "POST"])
    def logout():
        logout_user()
        return redirect(url_for("auth.login"))

    app.register_blueprint(bp)

    @app.before_request
    def auth_before_request():
        if request.endpoint in ("static", "auth.login", "auth.register", "auth.logout"):
            return
        if current_user.is_authenticated:
            return
        if request.path.startswith("/api/"):
            return jsonify({"error": "请先登录", "require_login": True}), 401
        return redirect(url_for("auth.login", next=request.url))

