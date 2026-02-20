from flask import Flask, render_template, request, redirect, session
from pymongo import MongoClient
import config
# from datetime import datetime

app = Flask(__name__)
app.secret_key = "mall_secret_key"

# ---------- MONGODB ----------
client = MongoClient(config.MONGO_URI)
db = client[config.DB_NAME]
users_col = db["users"]
inventory_col = db["inventory"]
sales_col = db["sales"]
simulation_col=db["simulation"]
brand_reports_col = db["brand_reports"]
all_sim_col = db["all_simulations"]

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

#-----------Simulation----------
@app.route("/simulation")
def simulation():
    if "user" not in session:
        return redirect("/")

    brand = request.args.get("brand")
    pid_search = request.args.get("pid")  # 🔥 NEW SEARCH FIELD

    brand_prefix = {
        "NIKE": "NK",
        "PUMA": "PU",
        "ADIDAS": "AD",
        "REEBOK": "RB",
        "LOTTO": "LTO",
        "NIVIA": "NV",
        "CAMPUS": "CMP",
        "REDTAPE": "RDT",
        "LIFELONG": "LC",
        "JASPO": "JAS"
    }

    query_list = []

    # Brand filter
    if brand and brand in brand_prefix:
        prefix = brand_prefix[brand]
        query_list.append({
            "$or": [
                {"Product ID": {"$regex": prefix, "$options": "i"}},
                {"Product_ID": {"$regex": prefix, "$options": "i"}},
                {"ID": {"$regex": prefix, "$options": "i"}}
            ]
        })

    # PRODUCT ID SEARCH
    if pid_search:
        query_list.append({
            "$or": [
                {"Product ID": {"$regex": pid_search, "$options": "i"}},
                {"Product_ID": {"$regex": pid_search, "$options": "i"}},
                {"ID": {"$regex": pid_search, "$options": "i"}}
            ]
        })

    query = {"$and": query_list} if query_list else {}

    raw_items = list(simulation_col.find(query, {"_id": 0}))

    items = []
    for r in raw_items:
        pid = r.get("Product ID") or r.get("Product_ID") or r.get("ID")

        item = {
            "Date": str(r.get("Date", "-")).split(" ")[0],
            "Product ID": pid,
            "Month": r.get("Month", "-"),
            "Base Revenue": r.get("Base Revenue (USD)", "-"),
            "Seasonal Factor": r.get("Seasonal Factor", "-"),
            "Final Revenue": r.get("Final Revenue (USD)", "-"),
            "Profit Margin": r.get("Profit Margin (%)", "-"),
            "Profit": r.get("Profit (USD)", "-")
        }
        items.append(item)

    return render_template(
        "simulation.html",
        user=session["user"],
        items=items,
        selected_brand=brand,
        pid_search=pid_search
    )

#-----------Brand simulation ------------
@app.route("/brand-simulation")
def brand_simulation():
    if "user" not in session:
        return redirect("/")
    return render_template("brand_simulation.html", user=session["user"])

#------Brand simulation view----------------
@app.route("/brand/<brand>")
def brand_view(brand):
    if "user" not in session:
        return redirect("/")

    brand = brand.upper()

    brand_prefix = {
        "NIKE": "NK",
        "PUMA": "PU",
        "ADIDAS": "AD",
        "REEBOK": "RB",
        "LOTTO": "LO",
        "NIVIA": "NV",
        "CAMPUS": "CP",
        "REDTAPE": "RT",
        "LIFELONG": "LL",
        "JASPO": "JS"
    }

    prefix = brand_prefix.get(brand)

    # UNIVERSAL QUERY (ID + Product ID support)
    query = {
        "$or": [
            {"ID": {"$regex": prefix, "$options": "i"}},
            {"Product ID": {"$regex": prefix, "$options": "i"}}
        ]
    }

    raw_items = list(brand_reports_col.find(query, {"_id": 0}))

    # NORMALIZER (ID fix)
    items = []
    for r in raw_items:
        pid = r.get("Product ID") or r.get("ID")

        items.append({
            "ID": pid,
            "Product Name": r.get("Product Name", "-"),
            "Month": r.get("Month", "-"),
            "Selling Price": r.get("Selling Price", "-"),
            "Margin (%)": r.get("Margin (%)", "-"),
            "Quantity Sold": r.get("Quantity Sold", "-"),
            "Revenue": r.get("Revenue", "-"),
            "Monthly Profit": r.get("Monthly Profit", "-")
        })

    return render_template(
        "brand_view.html",
        brand=brand,
        items=items,
        user=session["user"]
    )

# -------- ALL COMPANY SIMULATION --------
@app.route("/all-simulation")
def all_simulation():
    if "user" not in session:
        return redirect("/")

    raw = list(all_sim_col.find({}, {"_id": 0}))

    items = []
    for r in raw:
        items.append({
            "Company": r.get("Company", "-").upper(),
            "Date": str(r.get("Date", "-")).split(" ")[0],
            "Month": r.get("Month", "-"),
            "Product ID": r.get("Product ID", "-"),
            "Base Revenue": r.get("Base Revenue (USD)", "-"),
            "Seasonal Factor": r.get("Seasonal Factor", "-"),
            "Final Revenue": r.get("Final Revenue (USD)", "-"),
            "Margin": r.get("Profit Margin (%)", "-"),
            "Profit": r.get("Profit (USD)", "-")
        })

    return render_template(
        "all_simulation.html",
        items=items,
        user=session["user"]
    )

# ---------- LOGOUT ----------
@app.route("/logout")
def logout():
    session.clear()
    return redirect("/")

if __name__ == "__main__":
    app.run(debug=True)
