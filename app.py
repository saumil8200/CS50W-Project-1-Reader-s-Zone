from flask import *
import os, requests
from flask_session import Session
from flask import render_template, request, redirect, url_for
from sqlalchemy import create_engine
from sqlalchemy.orm import scoped_session, sessionmaker

app = Flask(__name__)

# Check for environment variable
if not os.getenv("DATABASE_URL"):
    raise RuntimeError("DATABASE_URL is not set")

# Configure session to use filesystem
app.config["SQLALCHEMY_DATABASE_URI"] = os.getenv("DATABASE_URL")
app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False
app.config["SECRET_KEY"]=os.urandom(24)
app.config["SESSION_PERMANENT"] = False
app.config["SESSION_TYPE"] = "filesystem"
Session(app)

# Set up database
engine = create_engine(os.getenv("DATABASE_URL"))
db = scoped_session(sessionmaker(bind=engine))

@app.route("/")
def welcome():
    return render_template("welcome.html")

@app.route("/index")
def index():
    if 'user_id' in session:
        username = session["user_id"].capitalize()
        return render_template("index.html", username = username)
    return render_template("index.html")

@app.route('/signup', methods=['GET','POST'])
def signup():
    if request.method == 'GET':
        return render_template('signup.html')
    else:
        username = request.form['username']
        email = request.form['email']
        password = request.form['password']
        db.execute("INSERT INTO users (username, email, password) VALUES  (:username, :email, :password)",
        {"username": username, "email": email, "password": password})
        db.commit()
        flash('New entry was successfully posted')
        get_flashed_messages
        return redirect(url_for('login'))
    return redirect(url_for('index'))

@app.route("/login", methods=['GET', 'POST'])
def login():
    if request.method == 'GET':
        return render_template('login.html')
    else:
        #session['user'] = False
        username = request.form['username']
        password = request.form['password']
        
        data = db.execute("SELECT * FROM users WHERE username=:username and password=:password",
        {"username":username, "password":password}).fetchone()
        if data is not None:
            session["user_id"] = username
            session["user"] = True
            return redirect(url_for('index'))
        return render_template("error.html", error = "Username or Password not matched!")
    return render_template("signup.html")

@app.route("/logout")
def logout():
    session.pop("user_id", None)  
    session["user"] = False
    return redirect(url_for('welcome'))

