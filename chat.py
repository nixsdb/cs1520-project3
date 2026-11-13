import os
from datetime import date

from flask import Flask, request, session, redirect, url_for, render_template, flash, abort
from flask_sqlalchemy import SQLAlchemy
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship
from sqlalchemy import String, Date, ForeignKey, UniqueConstraint, Text


class Base(DeclarativeBase):
    pass

app = Flask(__name__)
app.secret_key = "4" #still here
app.config["SQLALCHEMY_DATABASE_URI"] = "sqlite:///" + os.path.join(app.root_path, "chat.db")

db = SQLAlchemy(model_class=Base)
db.init_app(app)

class User(db.Model):
    id: Mapped[int] = mapped_column(primary_key=True)
    username: Mapped[str] = mapped_column(String(80), unique=True)
    password: Mapped[str] = mapped_column(String(255))
    chatroom_id: Mapped[int | None] = mapped_column(ForeignKey("chatroom.id"), nullable=True)

    def __init__(self, username, password):
        self.username = username
        self.password = password

class Chatroom(db.Model):
    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(String(80), unique=True)
    creator_id: Mapped[int] = mapped_column(ForeignKey("user.id"), nullable=True)

    creator: Mapped[User] = relationship(foreign_keys=[creator_id]) #foreign_keys not foreign_key!!!
    messages: Mapped[list["Message"]] = relationship(back_populates="chatroom", cascade="all, delete-orphan")

    def __init__(self, name, creator_id):
        self.name = name
        self.creator_id = creator_id

class Message(db.Model):
    id: Mapped[int] = mapped_column(primary_key=True)
    text: Mapped[str] = mapped_column(Text)
    chatroom_id: Mapped[int] = mapped_column(ForeignKey("chatroom.id"), nullable=True)
    author_id: Mapped[int] = mapped_column(ForeignKey("user.id"), nullable=True)
    chatroom: Mapped["Chatroom"] = relationship(back_populates="messages")
    author: Mapped["User"] = relationship()

    def __init__(self, text, chatroom_id, author_id):
        self.text = text
        self.chatroom_id = chatroom_id
        self.author_id = author_id

@app.cli.command("initdb")
def initdb_command():
    db.create_all()
    print("Initialized db")

@app.route("/")
def index():
    if "username" in session:
        return redirect(url_for("chatrooms"))
    return redirect(url_for("login_controller"))

@app.route("/login/", methods=["GET", "POST"])
def login_controller():
    if "username" in session:
        user = User.query.filter_by(username=session["username"]).first()
        if user is not None:
            return redirect(url_for("chatrooms"))
        session.clear()

    if request.method == "POST":
        username = request.form.get("username", "").strip()
        password = request.form.get("password", "")

        user = User.query.filter_by(username=username).first()
        if user is not None and user.password == password:
            session["username"] = user.username
            return redirect(url_for("chatrooms"))

        flash("Incorrect username or password!")

    return render_template("login.html")

@app.route("/logout/")
def logout():
    user = User.query.filter_by(username=session.get("username")).first()
    if user:
        user.chatroom_id = None
        db.session.commit()
    session.clear()
    return redirect(url_for("login_controller"))

@app.route("/register/", methods=["GET", "POST"])
def register():
    if "username" in session:
        return redirect(url_for("chatrooms"))

    if request.method == "POST":
        username = request.form.get("username", "").strip()
        password = request.form.get("password", "")

        if not username or not password:
            flash("Please enter a username and password!")
        elif User.query.filter_by(username=username).first():
            flash("That username is already taken!")
        else:
            user = User(username, password)
            db.session.add(user)
            db.session.commit()
            flash("Account created, please log in!")
            return redirect(url_for("login_controller"))

    return render_template("register.html")

@app.route("/chatrooms/")
def chatrooms():
    user = User.query.filter_by(username=session.get("username")).first()
    if user is None:
        return redirect(url_for("login_controller"))
    if user.chatroom_id:
        return redirect(url_for("chatroom", chatroom_id=user.chatroom_id))

    if request.args.get("deleted") == "1":
        flash("That chatroom is deleted!")

    return render_template("chatrooms.html", chatrooms=Chatroom.query.order_by(Chatroom.id).all(), user=user)

@app.route("/chatroom/create", methods=["POST"])
def create_chatroom():
    user = User.query.filter_by(username=session.get("username")).first()
    if user is None:
        return redirect(url_for("login_controller"))
    if user.chatroom_id:
        flash("You are already in a chatroom!")
        return redirect(url_for("chatrooms"))

    name = request.form.get("name", "").strip()
    if not name:
        flash("Please enter a name!")
    else:
        chatroom = Chatroom(name, user.id)
        db.session.add(chatroom)
        db.session.commit()
        flash("Chatroom created!")

    return redirect(url_for("chatrooms"))

@app.route("/chatroom/<int:chatroom_id>")
def chatroom(chatroom_id):
    user = User.query.filter_by(username=session.get("username")).first()
    if user is None:
        return redirect(url_for("login_controller"))

    room = db.session.get(Chatroom, chatroom_id)
    if room is None:
        flash("That chatroom doesn't exist!")
        return redirect(url_for("chatrooms"))

    if user.chatroom_id != chatroom_id:
        flash("You must join this chatroom first!")
        return redirect(url_for("chatrooms"))

    return render_template("chatroom.html", chatroom=room)

@app.route("/chatroom/<int:chatroom_id>/join", methods=["POST"])
def join_chatroom(chatroom_id):
    user = User.query.filter_by(username=session.get("username")).first()
    if user is None:
        return redirect(url_for("login_controller"))

    if db.session.get(Chatroom, chatroom_id) is None:
        flash("That chatroom doesn't exist!")
        return redirect(url_for("chatrooms"))
    if user.chatroom_id is not None and user.chatroom_id != chatroom_id:
        flash("You must leave your current chatroom first!")
        return redirect(url_for("chatrooms"))

    user.chatroom_id = chatroom_id
    db.session.commit()
    return redirect(url_for("chatroom", chatroom_id=chatroom_id))

@app.route("/chatrooms/<int:chatroom_id>/leave/", methods=["POST"])
def leave_chatroom(chatroom_id):
    user = User.query.filter_by(username=session.get("username")).first()
    if user is None:
        return redirect(url_for("login_controller"))

    if user.chatroom_id == chatroom_id:
        user.chatroom_id = None
        db.session.commit()

    return redirect(url_for("chatrooms"))

@app.route("/chatrooms/<int:chatroom_id>/delete/", methods=["POST"])
def delete_chatroom(chatroom_id):
    user = User.query.filter_by(username=session.get("username")).first()
    if user is None:
        return redirect(url_for("login_controller"))

    chatroom = db.session.get(Chatroom, chatroom_id)
    if chatroom is None:
        flash("That chatroom doesn't exist!")
    elif chatroom.creator_id != user.id:
        flash("You can only delete chatrooms you created!")
    else:
        for member in User.query.filter_by(chatroom_id=chatroom_id).all():
            member.chatroom_id = None
        db.session.delete(chatroom)
        db.session.commit()
        flash("Chatroom deleted!")

    return redirect(url_for("chatrooms"))

"""
http 201 created
http 401 unauthorized
http 403 forbidden
http 404 not found
"""
@app.route("/api/chatrooms/<int:chatroom_id>/messages", methods=["GET", "POST"])
def chatroom_messages(chatroom_id):
    user = User.query.filter_by(username=session.get("username")).first()
    if user is None:
        return {"error": "Please log in first!"}, 401

    chatroom = db.session.get(Chatroom, chatroom_id)
    if chatroom is None:
        return {"deleted": True}, 404
    if user.chatroom_id != chatroom_id:
        return {"error": "You are no longer in this chatroom!"}, 403

    if request.method == "GET": #fix for chatroom.html
        after = request.args.get("after", 0, type=int)
        messages = Message.query.filter(Message.chatroom_id == chatroom_id, Message.id > after).order_by(Message.id).all()
        result = []
        for message in messages:
            result.append({"id": message.id, "username": message.author.username, "text": message.text})
        return {"messages": result}

    req_data = request.get_json()
    if not isinstance(req_data, dict) or not isinstance(req_data.get("text"), str):
        abort(400)

    text = req_data["text"].strip()
    if not text or len(text) > 2000:
        abort(400)

    message = Message(text, chatroom_id, user.id)
    db.session.add(message)
    db.session.commit()

    return {"id": message.id}, 201
