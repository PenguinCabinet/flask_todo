from flask import Flask, request, redirect, url_for, jsonify, render_template
from flask_login import (
    LoginManager,
    UserMixin,
    login_user,
    logout_user,
    login_required,
    current_user,
)
from flask_sqlalchemy import SQLAlchemy
from sqlalchemy.orm import DeclarativeBase
from sqlalchemy import Integer, String
from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy.exc import IntegrityError
from sqlalchemy_utils import UUIDType
import uuid
import bcrypt
import base64


class Base(DeclarativeBase):
    pass


db = SQLAlchemy(model_class=Base)

app = Flask(__name__)
app.config["SQLALCHEMY_DATABASE_URI"] = "sqlite:///database.db"

# Change it in production. START
app.config["SECRET_KEY"] = b"SECRET"
# END

salt = bcrypt.gensalt()
print("bcrypt salt", salt)

app.config["JSON_AS_ASCII"] = False

login_manager = LoginManager()
login_manager.init_app(app)


def password_hash(v):
    return base64.b64encode(bcrypt.hashpw(v.encode(encoding="utf-8"), salt)).decode(
        "ascii"
    )


def check_password(input_password: str, password_hash: str):
    return bcrypt.checkpw(
        input_password.encode("utf-8"), base64.b64decode(password_hash)
    )


class User(UserMixin, db.Model):

    id = mapped_column(UUIDType(binary=False), primary_key=True, default=uuid.uuid4)
    username: Mapped[str]
    email: Mapped[str] = mapped_column(unique=True)
    password: Mapped[str]

    def __init__(self, email, username, password):
        self.email = email
        self.username = username
        self.password = password
        super(User, self).__init__()

    def get_id(self):
        return self.id


class TODO(db.Model):
    id: Mapped[UUIDType] = mapped_column(
        UUIDType(binary=False), primary_key=True, default=uuid.uuid4
    )
    created_user_id: Mapped[str]
    name: Mapped[str]

    def __init__(self, created_user_id, name):
        self.created_user_id = created_user_id
        self.name = name
        super(TODO, self).__init__()


db.init_app(app)
with app.app_context():
    db.create_all()


@login_manager.user_loader
def load_user(user_id):
    print("load_user,user_id", user_id)
    print("load_user,User.query.get(user_id)", User.query.get(user_id))
    return User.query.get(user_id)


@app.route("/")
def index():

    return render_template("index.html")


@app.route("/api/register", methods=["POST"])
def register_api():
    if request.method == "POST":
        if (
            request.form["username"]
            and request.form["email"]
            and request.form["password"]
        ):
            try:
                user = User(
                    username=request.form["username"],
                    email=request.form["email"],
                    password=password_hash(request.form["password"]),
                )
                print("register_api,before commit,UUID", user.id)

                db.session.add(user)
                db.session.commit()
                print("register_api,after commit,UUID", user.id)
            except IntegrityError:
                db.session.rollback()
                return redirect(url_for("register"))

            login_user(user)
            return redirect(url_for("home"))

    return redirect(url_for("register"))


@app.route("/register", methods=["GET"])
def register():
    return render_template("register.html")


@app.route("/api/login", methods=["POST"])
def login_api():
    if request.method == "POST":
        if request.form["email"] and request.form["password"]:
            user = User.query.filter(User.email == request.form["email"])
            print(request.form, user.count())
            if user.count() > 0:
                if check_password(request.form["password"], user[0].password):
                    login_user(user[0])
                    return redirect(url_for("home"))
    return redirect(url_for("login"))


@app.route("/login", methods=["GET"])
def login():
    return render_template("login.html")


@app.route("/api/logout", methods=["POST"])
@login_required
def logout_api():
    if request.method == "POST":
        logout_user()
        return redirect(url_for("index"))


@app.route("/home", methods=["GET"])
@login_required
def home():
    return render_template("home.html")


@app.route("/api/todo", methods=["GET", "POST"])
@login_required
def todo():
    if request.method == "GET":
        todo = TODO.query.filter(TODO.created_user_id == str(current_user.id))
        return jsonify([{"id": e.id, "name": e.name} for e in todo])
    if request.method == "POST":
        print(request.form)
        if request.form["name"]:
            todo = TODO(
                created_user_id=str(current_user.id),
                name=request.form["name"],
            )
            print(todo)

            db.session.add(todo)
            db.session.commit()
            return jsonify({})


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000, debug=True)
