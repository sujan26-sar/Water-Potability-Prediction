from flask import Flask, render_template, request, redirect, session, url_for
import numpy as np
import joblib
import matplotlib.pyplot as plt
import os
from flask_sqlalchemy import SQLAlchemy
from werkzeug.security import generate_password_hash, check_password_hash


app = Flask(__name__)
app.secret_key = os.environ.get("SECRET_KEY")
app.config["SQLALCHEMY_DATABASE_URI"] = "sqlite:///users.db"
app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False

db = SQLAlchemy(app)

class User(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(100), unique=True, nullable=False)
    password = db.Column(db.String(200), nullable=False)


model = joblib.load("model.pkl")   # or "best_model.pkl"

@app.route("/login", methods=["GET", "POST"])
def login():

    if request.method == "POST":
        username = request.form["username"]
        password = request.form["password"]

        # 👇 DEFINE USER FIRST
        user = User.query.filter_by(username=username).first()

        if user and check_password_hash(user.password, password):
            session["user"] = username
            return redirect(url_for("home"))
        else:
            return render_template("login.html", error="Invalid Credentials")

    return render_template("login.html")
@app.route("/logout")
def logout():
    session.pop("user", None)
    return redirect(url_for("login"))

@app.route("/register", methods=["GET", "POST"])
def register():

    if request.method == "POST":
        username = request.form["username"]
        password = request.form["password"]

        hashed_password = generate_password_hash(password)

        new_user = User(username=username, password=hashed_password)

        try:
            db.session.add(new_user)
            db.session.commit()
            return redirect(url_for("login"))
        except:
            return render_template("register.html", error="User already exists")

    return render_template("register.html")

@app.route("/")
def home():
    if "user" not in session:
        return redirect(url_for("login"))
    return render_template("index.html")

@app.route("/predict", methods=["POST"])


def predict():
    if "user" not in session:
        return redirect(url_for("login"))
    try:
        # Get form values
        ph = float(request.form["ph"])
        hardness = float(request.form["Hardness"])
        solids = float(request.form["Solids"])
        chloramines = float(request.form["Chloramines"])
        sulfate = float(request.form["Sulfate"])
        conductivity = float(request.form["Conductivity"])
        organic_carbon = float(request.form["Organic_carbon"])
        trihalomethanes = float(request.form["Trihalomethanes"])
        turbidity = float(request.form["Turbidity"])

        # Create feature array
        features = np.array([[ph, hardness, solids, chloramines,
                              sulfate, conductivity, organic_carbon,
                              trihalomethanes, turbidity]])

        # Prediction
        prediction = model.predict(features)[0]

        # Confidence (if model supports probability)
        if hasattr(model, "predict_proba"):
            probability = model.predict_proba(features)[0][1]
            confidence = round(probability * 100, 2)
        else:
            confidence = 85.0  # default fallback

        # Result interpretation
        if prediction == 1:
            prediction_text = "⚠️ Water is NOT Safe for Drinking"
            alert_color = "danger"
            risk = "High"
        else:
            prediction_text = "✅ Water is Safe for Drinking"
            alert_color = "success"
            risk = "Low"
        
        # Feature Importance Graph (only if Decision Tree)
        if hasattr(model, "feature_importances_"):

            feature_names = [
                "pH", "Hardness", "Solids", "Chloramines",
                "Sulfate", "Conductivity", "Organic Carbon",
                "Trihalomethanes", "Turbidity"
            ]

            importances = model.feature_importances_

            plt.figure(figsize=(8,5))
            sorted_idx = importances.argsort() 
            plt.barh(np.array(feature_names)[sorted_idx], importances[sorted_idx])
            plt.xlabel("Importance Score")
            plt.title("Feature Importance (Decision Tree)")
            plt.tight_layout()

            # Save image inside static folder
            if not os.path.exists("static"):
                os.makedirs("static")
            plt.savefig("static/feature_importance.png")
            plt.close()

        return render_template(
            "index.html",
            prediction_text=prediction_text,
            alert_color=alert_color,
            risk=risk,
            confidence=confidence,
            accuracy=92  # change this to your real model accuracy
        )

    except Exception as e:
        return render_template("index.html", error="Please fill all fields correctly.")

if __name__ == "__main__":
    with app.app_context():
        db.create_all()
    app.run(debug=True)