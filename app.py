from flask import Flask, render_template, request, redirect, session
from pymongo import MongoClient
import config

app = Flask(__name__)
app.secret_key = "mall_secret_key"

# ---------- MONGODB ----------
client = MongoClient(config.MONGO_URI)
db = client[config.DB_NAME]
users_col = db["users"]
inventory_col = db["inventory"]
sales_col = db["sales"]


# ---------- LOGIN ----------
@app.route("/", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        user = users_col.find_one({
            "username": request.form["username"],
            "password": request.form["password"]
        })
        if user:
            session["user"] = user["username"]
            return redirect("/home")
        return render_template("login.html", error="Invalid Credentials")
    return render_template("login.html")

# ---------- HOME ----------
@app.route("/home")
def home():
    if "user" not in session:
        return redirect("/")
    return render_template("home.html", user=session["user"])

# ---------- DASHBOARD ----------
@app.route("/dashboard")
def dashboard():
    if "user" not in session:
        return redirect("/")
    return render_template(
        "dashboard.html",
        user=session["user"],
        selected_brand=session.get("brand")
    )

# ---------- BRAND SELECT (ONLY SELECT) ----------
@app.route("/select-brand/<brand>")
def select_brand(brand):
    session["brand"] = brand
    return redirect("/dashboard")

# ---------- INVENTORY ----------
@app.route("/inventory")
def inventory():
    if "user" not in session:
        return redirect("/dashboard")

    brand = session.get("brand")
    if not brand:
        return redirect("/dashboard")
    
    #brand - ID prefix mapping
    brand_prefix={
        "NIKE": "^NK",
        "PUMA": "^PU",
        "ADIDAS": "^AD",
        "REEBOK": "^RB",
        "LOTTO": "^LO",
        "NIVIA": "^NV",
        "CAMPUS": "^CP",
        "REDTAPE": "^RT",
        "LIFELONG": "^LL",
        "JASPO": "^JS"
    }
    prefix = brand_prefix.get(brand)
    items = []

    if prefix:
        items = list(
            inventory_col.find(
                {"ID": {"$regex": prefix}},
                {"_id": 0}
            )
        )

    return render_template(
        "inventory.html",
        user=session["user"],
        brand=brand,
        items=items
    )

# ---------- SALES ----------
@app.route("/sales")
def sales():
    if "user" not in session:
        return redirect("/")

    brand = request.args.get("brand")

    brand_prefix = {
        "NIKE": "^NK",
        "PUMA": "^PU",
        "ADIDAS": "^AD",
        "REEBOK": "^RB",
        "LOTTO": "^LO",
        "NIVIA": "^NV",
        "CAMPUS": "^CP",
        "REDTAPE": "^RT",
        "LIFELONG": "^LL",
        "JASPO": "^JS"
    }

    query = {}

    if brand and brand in brand_prefix:
        prefix = brand_prefix[brand]

        query = {
            "$or": [
                {"ID": {"$regex": prefix}},
                {"Product ID": {"$regex": prefix}}
            ]
        }

    items = list(sales_col.find(query, {"_id": 0}))

    return render_template(
        "sales.html",
        user=session["user"],
        items=items,
        selected_brand=brand
    )


# ---------- LOGOUT ----------
@app.route("/logout")
def logout():
    session.clear()
    return redirect("/")

if __name__ == "__main__":
    app.run(debug=True)
