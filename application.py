import os

from flask import Flask, session, render_template, request, url_for, redirect
from flask_session import Session
from sqlalchemy import create_engine
from sqlalchemy.sql import text
from sqlalchemy.orm import scoped_session, sessionmaker
import requests
from json import load, dumps

print('hi')
app = Flask(__name__)
# Check for environment variable
if not os.getenv("DATABASE_URL"):
    raise RuntimeError("DATABASE_URL is not set")

# Configure session to use filesystem
app.config["SESSION_PERMANENT"] = False
app.config["SESSION_TYPE"] = "filesystem"
Session(app)

# Set up database
engine = create_engine(os.getenv("DATABASE_URL"))
db = scoped_session(sessionmaker(bind=engine))

@app.route("/")
def index():
    return render_template("welcome.html")

@app.route("/register.html")
def register():
    return render_template("register.html")

@app.route("/validate_user", methods=["POST"])
def val_user():
    username = request.form.get("user")
    password = request.form.get("password")
    if db.execute("SELECT * FROM users WHERE username = :username", {"username":username}).rowcount == 0:
        db.execute("INSERT INTO users (username, password) VALUES (:username, :password)", {"username":username, "password":password})
        db.commit()
        return render_template("welcome.html")
    else:
        return render_template("register.html", error_message="This username has been taken. Please try a different one.")

@app.route("/login.html")
def login():
    return render_template("login.html")

@app.route("/validate_login", methods=["POST"])
def val_login():
    uname = request.form.get("user")
    password = request.form.get("password")
    if db.execute("SELECT * FROM users WHERE username = :username", {"username":uname}).rowcount == 0:
        return render_template("login.html", error_message="This username doesn't exist! Go back to the register page.")
        # check if password for the username exists and matches the input
    pword = ((db.execute("SELECT password FROM users WHERE username = :username", {"username":uname}).fetchall())[0])[0]
    if password == pword:
        session["username"] = uname
        return redirect(url_for("welcome_user", _external=True))
        # return render_template("welcome_user.html")
    return render_template("login.html", error_message="This password is incorrect!")

@app.route("/welcome_user")
def welcome_user():
    return render_template("welcome_user.html")

@app.route("/search.html", methods=["POST"])
def search():
    input_form = request.form.get("input")
    input_form = '%' + input_form + '%'
    # get all isbn, author, title, from db
    s = text("SELECT * FROM books WHERE (isbn LIKE :i OR title LIKE :i OR author LIKE :i)")
    books = db.execute(s, {"i":input_form}).fetchall()
    for tuple_data in books:
        isbn = tuple_data[0]
        title = tuple_data[1]
        author = tuple_data[2]
        year = tuple_data[3]
    if len(books)==0:
        return render_template("search_results.html", error_message="There were no search results that matched")
    return render_template("search_results.html", books=books)

@app.route("/<string:isbn>.html", methods=["POST", "GET"])
def book(isbn):
    arr = db.execute("SELECT * FROM books WHERE isbn = :isbn", {"isbn":isbn}).fetchall()
    isbn_arr = arr[0][0]
    title = arr[0][1]
    author = arr[0][2]
    year = arr[0][3]
    revs = db.execute("SELECT * FROM reviews WHERE isbn = :isbn", {"isbn":isbn}).fetchall()
    res = requests.get("https://www.goodreads.com/book/review_counts.json", params={"key": "vxRChCqRShjvRw4Ngj5uQ", "isbns": isbn})
    goodreads_json = res.json()
    goodreads_dict = goodreads_json['books'][0]
    ratings_count = goodreads_dict['work_ratings_count']
    avg_rating = goodreads_dict['average_rating']
    if request.method == 'POST':
        print("THIS POST REQUEST IS RUNNING")
        username = session["username"]
        if db.execute("SELECT * FROM reviews WHERE username = :username AND isbn = :isbn", {"username":username, "isbn":isbn_arr}).rowcount != 0:
            return render_template("book.html", title=title, author=author, year=year, ratings_count=ratings_count, rating=avg_rating, error_message="You cannot submit more than one review per book", isbn=isbn_arr, reviews=revs)
        rating = request.form.get("rating")
        review_text = request.form.get("review_text")
        db.execute("INSERT INTO reviews (isbn, username, rating, review) VALUES (:isbn, :username, :rating, :review)", {"isbn":isbn, "username":username, "rating":rating, "review":review_text})
        db.commit()
    return render_template("book.html", title=title, author=author, year=year, isbn=isbn_arr, ratings_count=ratings_count, rating=avg_rating, reviews=revs)

@app.route("/api/<string:isbn>")
def api_isbn(isbn):
    arr = db.execute("SELECT * FROM books WHERE isbn = :isbn", {"isbn":isbn}).fetchall()
    isbn_arr = arr[0][0]
    title = arr[0][1]
    author = arr[0][2]
    year = arr[0][3]
    res = requests.get("https://www.goodreads.com/book/review_counts.json", params={"key": "vxRChCqRShjvRw4Ngj5uQ", "isbns": isbn})
    goodreads_json = res.json()
    goodreads_dict = goodreads_json['books'][0]
    ratings_count = goodreads_dict['work_ratings_count']
    avg_rating = goodreads_dict['average_rating']
    book = {'title': title, 'author':author, 'year':year, 'isbn':isbn_arr, 'review_count':ratings_count, 'average_score':avg_rating}
    return dumps(book)