import os
import requests

from flask import Flask, render_template, request, session, jsonify
from sqlalchemy.exc import IntegrityError
from flask_session import Session
from sqlalchemy import or_
from models import *

app = Flask(__name__)
app.config["SESSION_PERMANENT"] = False
app.config["SESSION_TYPE"] = "filesystem"
Session(app)
app.config["SQLALCHEMY_DATABASE_URI"] = os.getenv("DATABASE_URL")
app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False
db.init_app(app)

@app.route("/")
def index():
    return render_template("login.html")

@app.route("/login", methods=["POST"])
def login():
    name = request.form.get("uname")
    password = request.form.get("pwd")
    user = User.query.filter_by(uname=name).first()
    if user is None:
        return render_template("login.html", message="Sorry! User doesn't exist")
    elif user.pwd == password:
            session["id"] = user.id
            return render_template("search.html", user_id = session["id"])
    else:
        return render_template("login.html", message="username or password is incorrect")

@app.route("/signup")
def signup():
    return render_template("signup.html")

@app.route("/createuser", methods=["POST"])
def createuser():
    name = request.form.get("uname")
    pwd = request.form.get("pwd")
    user = User(uname=name, pwd=pwd)
    db.session.add(user)
    db.session.commit()
    return render_template("signup.html" , message="Account created successfully")

@app.route("/logout")
def logout():
    session.pop('uname', None)
    session.pop('id', None)
    return render_template("login.html")

@app.route("/search")
def search():
    searchtag = request.args.get("search","")
    searchres = "%{}%".format(searchtag)
    results =Book.query.filter(or_(Book.isbn.like(searchres), Book.title.like(searchres), Book.author.like(searchres) )).all()
    if not results:
        return render_template("search.html", message="Found no results")
    else:
        return render_template("search.html", results=results)

@app.route("/books/<book_isbn>", methods=["POST","GET"])
def book(book_isbn):
    if request.method == "GET":
        book = Book.query.get(book_isbn)
        review = Review.query.filter_by(book_isbn=book_isbn).first()
        res = requests.get("https://www.goodreads.com/book/review_counts.json", params={"key": "wSTncLhjVVyj46Is8Gytdg", "isbns": book_isbn})

        if res.status_code == 404:
            work_ratings_count = "No Ratings Available"
            average_rating = "No Ratings Available"
            return render_template("book.html", book = book, review = review, average_rating = average_rating, work_ratings_count = work_ratings_count, book_isbn=book_isbn)
        else:
            data = res.json()
            for i in data["books"]:
                work_ratings_count = i["work_ratings_count"]
                average_rating = i["average_rating"]
            return render_template("book.html", book = book, review = review, average_rating = average_rating, work_ratings_count = work_ratings_count, book_isbn=book_isbn)

    if request.method == "POST":
        book = Book.query.get(book_isbn)
        rating = request.form.get("rating")
        text = request.form.get("text")
        user_id =session["id"]
        review = Review(rating=rating, text=text, user_id=user_id, book_isbn=book_isbn)
        try:
            db.session.add(review)
            db.session.commit()
            return render_template("book.html", book=book, book_isbn=book_isbn, review=review, message="Thank you for your valuable feedback !!")
        except IntegrityError:
            db.session.rollback()
            return render_template("book.html", book=book, book_isbn=book_isbn, review=review, message="Thank you , Review for this book already submitted !!")

@app.route("/api/<isbn>")
def book_api(isbn):
    book =Book.query.get(isbn)
    if book is None:
        return jsonify({"error": "Invalid Book ISBN"}), 404

    res = requests.get("https://www.goodreads.com/book/review_counts.json",
                       params={"key": "wSTncLhjVVyj46Is8Gytdg", "isbns": isbn})

    if res.status_code == 404:
        work_ratings_count = "No Ratings Available"
        average_rating = "No Ratings Available"
    else:
        data = res.json()
        for i in data["books"]:
            work_ratings_count = i["work_ratings_count"]
            average_rating = i["average_rating"]

    return jsonify({
        "isbn": book.isbn,
        "title": book.title,
        "author": book.author,
        "year": book.year,
        "work_ratings_count": work_ratings_count,
        "average_rating": average_rating
    })




