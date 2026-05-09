from flask import Blueprint, render_template


web_bp = Blueprint('web', __name__)


@web_bp.route('/')
def home():
    return render_template('home.html')


@web_bp.route('/login')
def login_page():
    return render_template('login.html')


@web_bp.route('/register')
def register_page():
    return render_template('register.html')