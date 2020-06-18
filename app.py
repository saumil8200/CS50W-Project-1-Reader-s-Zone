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

# Set Api Key
key = os.getenv("API_KEY")
if not key:
    raise RuntimeError("API_KEY is not set")

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

#GoodRead API
def gdApi(isbn):
    data = requests.get("https://www.goodreads.com/book/review_counts.json", params={ "key": key, "isbns": isbn})
    data = data.json()
    return data

#Welcome page
@app.route("/")
def welcome():
    return render_template("welcome.html")

#Index
@app.route("/index")
def index():
    if 'user_id' in session:
        username = session["user_id"].capitalize()
        return render_template("index.html", username = username)
    return render_template("index.html")

#Sign Up
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

#Login
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

#Log Out
@app.route("/logout")
def logout():
    session.pop("user_id", None)  
    session["user"] = False
    return redirect(url_for('welcome'))

#Search Books
@app.route("/search", methods=['GET', 'POST'])
def search():
    if request.method == 'GET':
        abort(403)
    if request.method == 'POST':
        search = request.form.get('getinput')
        data = db.execute("SELECT * FROM books WHERE (isbn LIKE '%' || :isbn || '%') OR (title LIKE '%' || :title || '%') OR (author LIKE '%' || :author || '%') ORDER BY year DESC", 
        {"isbn": search, "title": search, "author": search}).fetchall()
        
        # If Book Does Not Exist In DB
        if data is None:
            abort(404)
        # Creating Session For List Items of Books
        session["val"] = True
        session["book"] = False
        return render_template("books.html", data = data) 
    return "HELLO"

# Book Data => Reviews Rating etc
@app.route("/book/<id>", methods=["GET", "POST"])
def book(id):
    comments= []
    user = session["user_id"]

    # If User Submit The Review And Rating Then This Section Will Response
    if request.method == 'POST':
        isbn = request.form["post_id"]
        review = request.form["review"] 
        rating = int(request.form["rating"])
        book = db.execute("SELECT * FROM reviews WHERE username= :username AND book_id= :book_id",
        {"username": user, "book_id": isbn}).first()
        if book == None:
            db.execute("INSERT INTO reviews (username, rating, review, book_id) VALUES (:username, :rating, :review, :book_id)",
            {"username": user, "rating": rating, "review": review, "book_id": isbn})
            db.commit()
        return redirect(url_for('book', id = isbn))
    # ===== END ======

    if request.method == "GET":
        if 'user' not in session:
            return redirect(url_for('login'))

        # Creating Session For Books
        session["val"] = False
        session["book"] = True
        book = db.execute("SELECT * FROM books WHERE isbn= :id",
        {"id": id}).first()   

        # Search The Reviews And Rating Of The Book in DB
        data = db.execute("SELECT * FROM reviews WHERE username= :username AND book_id= :id",
        {"username": user,"id": id}).first()
        if data is None:
            session["review"] = False
        else:
            session["review"] = True
            comments = data

    # GoodRead Api Data
        api = gdApi(id)

    return render_template("books.html", book = book, api = api, comments = comments)


    

# API => Get JSON Data 
@app.route("/api/<int:isbn>", methods=['GET', 'POST'])
def api(isbn):
    if request.method == 'GET':
        dbapi = db.execute("SELECT * FROM books WHERE isbn= :isbn",
        {"isbn": isbn}).first()
        if dbapi is None:
            return jsonify({
                'error': 'No Books Found'
            })

        # GoodRead Api Data
        api = gdApi(isbn)

        # Return JSON Data
        return jsonify({ 
            "books": {
                "reviews_count": api["books"][0]["reviews_count"], 
                "title": dbapi.title,
                "author": dbapi.author,
                "year": dbapi.year,
                "isbn": dbapi.isbn, 
                "average_rating": api["books"][0]["average_rating"]
                }
            })

if __name__ == "__main__":     
    app.run()