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

# -------- SIMULATION LANDING PAGE --------
@app.route("/simulation")
def simulation_home():
    if "user" not in session:
        return redirect("/")
    return render_template("simulation_home.html", user=session["user"])

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
@app.route("/short-summary")
def short_summary():
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
        "short_summary.html",
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

#Reports
@app.route("/report")
def report():
    if "user" not in session:
        return redirect("/")
    return render_template("report.html", user=session["user"])

#Report ans api
@app.route("/api/insight/<qid>")
def insight(qid):
    data = list(all_sim_col.find({}, {"_id": 0}))

    # ---------------- 1️⃣ BEST BRAND ----------------
    if qid == "best_brand":
        revenue = {}
        for d in data:
            brand = d["Company"]
            revenue[brand] = revenue.get(brand, 0) + float(d["Final Revenue (USD)"])
        best = max(revenue, key=revenue.get)
        return {"type": "text", "value": f"{best} - ${round(revenue[best],2)}"}

    # ---------------- 2️⃣ TOP TWO BRANDS (PIE) ----------------
    if qid == "top_two":
        revenue = {}
        for d in data:
            brand = d["Company"]
            revenue[brand] = revenue.get(brand, 0) + float(d["Final Revenue (USD)"])
        top = sorted(revenue.items(), key=lambda x: x[1], reverse=True)[:2]
        return {"type": "pie",
                "labels": [i[0] for i in top],
                "values": [i[1] for i in top]}

    # ---------------- 3️⃣ MONTH REVENUE (BAR) ----------------
    if qid == "month_revenue":
        month_map = {}
        for d in data:
            m = d["Month"]
            month_map[m] = month_map.get(m, 0) + float(d["Final Revenue (USD)"])
        return {"type": "bar",
                "labels": list(month_map.keys()),
                "values": list(month_map.values())}

    # ---------------- 4️⃣ BRAND RANKING (PIE) ----------------
    if qid == "brand_ranking":
        revenue = {}
        for d in data:
            brand = d["Company"]
            revenue[brand] = revenue.get(brand, 0) + float(d["Final Revenue (USD)"])
        return {"type": "pie",
                "labels": list(revenue.keys()),
                "values": list(revenue.values())}

    # ---------------- 5️⃣ WORST BRAND ----------------
    if qid == "worst_brand":
        revenue = {}
        for d in data:
            brand = d["Company"]
            revenue[brand] = revenue.get(brand, 0) + float(d["Final Revenue (USD)"])
        worst = min(revenue, key=revenue.get)
        return {"type": "text", "value": f"{worst} - ${round(revenue[worst],2)}"}

    # ---------------- 6️⃣ BEST & WORST SHOES ----------------
    # NEW ✅ PIE
    if qid == "best_worst_shoes":
        revenue = {}
        for d in data:
            brand = d["Company"]
            revenue[brand] = revenue.get(brand, 0) + float(d["Final Revenue (USD)"])

        best = max(revenue, key=revenue.get)
        worst = min(revenue, key=revenue.get)

        return {
            "type": "pie",
            "labels": ["Best: " + best, "Worst: " + worst],
            "values": [revenue[best], revenue[worst]]
        }

    # ---------------- 7️⃣ TOTAL MARGIN BAR ----------------
    if qid == "total_margin_bar":
        margin = {}

        for d in data:
            brand = d.get("Company", "UNKNOWN")

            raw = str(d.get("Profit Margin (%)", "")).replace("%", "").strip()

            try:
                val = float(raw)
            except:
                val = 0   # fallback if bad data

            margin[brand] = margin.get(brand, 0) + val

        return {
            "type": "bar",
            "labels": list(margin.keys()),
            "values": list(margin.values())
        }

    # ---------------- 8️⃣ TOTAL PROFIT BAR ----------------
    if qid == "total_profit_bar":
        profit = {}
        for d in data:
            brand = d["Company"]
            val = float(d.get("Profit (USD)", 0))
            profit[brand] = profit.get(brand, 0) + val

        return {"type": "bar", "labels": list(profit.keys()), "values": list(profit.values())}

    # ---------------- 9️⃣ JANUARY BEST BRAND ----------------
    if qid == "jan_best":
        revenue = {}
        for d in data:
            if d["Month"] == "January":
                brand = d["Company"]
                revenue[brand] = revenue.get(brand, 0) + float(d["Final Revenue (USD)"])
        best = max(revenue, key=revenue.get)
        return {"type": "text", "value": best}

    # ---------------- 🔟 TOP PRODUCT YEAR ----------------
    if qid == "top_product_year":
        sales = {}
        for d in data:
            pid = d["Product ID"]
            sales[pid] = sales.get(pid, 0) + float(d["Final Revenue (USD)"])

        best = max(sales, key=sales.get)

        return {
            "type": "card",
            "title": "Top Selling Product",
            "value": best
        }

    # ---------------- 1️⃣1️⃣ CAMPUS DAILY PROFIT (PIE) ----------------
    if qid == "campus_profit_day":
        day_profit = {}

        for d in data:
            if str(d.get("Company")).upper() == "CAMPUS":
                day = str(d.get("Date", "Unknown")).split(" ")[0]
                try:
                    val = float(d.get("Profit (USD)", 0))
                except:
                    val = 0

                day_profit[day] = day_profit.get(day, 0) + val

        # fallback if no nike data
        if not day_profit:
            return {"type": "text", "value": "No Nike data available"}

        # limit to 7 days for readable pie
        labels = list(day_profit.keys())[:7]
        values = list(day_profit.values())[:7]

        return {"type": "pie", "labels": labels, "values": values}
    
    # ---------------- 1️⃣2️⃣ MAX PROFIT BRAND (BAR) ----------------
    if qid == "max_profit_brand":
        profit = {}

        for d in data:
            brand = d.get("Company", "UNKNOWN")
            try:
                val = float(d.get("Profit (USD)", 0))
            except:
                val = 0

            profit[brand] = profit.get(brand, 0) + val

        return {
            "type": "bar",
            "labels": list(profit.keys()),
            "values": list(profit.values())
        }

    # ---------------- 1️⃣3️⃣ REEBOK TREND (PIE) ----------------
    if qid == "reebok_trend":
        months = []

        for d in data:
            if str(d.get("Company")).upper() == "REEBOK":
                try:
                    months.append(float(d.get("Final Revenue (USD)", 0)))
                except:
                    months.append(0)

        if len(months) < 2:
            return {"type": "text", "value": "Not enough Reebok data"}

        start = months[0]
        end = months[-1]

        return {
            "type": "pie",
            "labels": ["Start Revenue", "End Revenue"],
            "values": [start, end]
        }

    # ---------------- 1️⃣4️⃣ LEAST PRODUCT (CARD) ----------------
    if qid == "least_product_year":
        sales = {}

        for d in data:
            pid = str(d.get("Product ID", "Unknown"))
            try:
                val = float(d.get("Final Revenue (USD)", 0))
            except:
                val = 0

            sales[pid] = sales.get(pid, 0) + val

        worst = min(sales, key=sales.get)

        return {
            "type": "card",
            "title": "Least Selling Product",
            "value": worst
        }

    # ---------------- 1️⃣5️⃣ TOP PRODUCT BAR ----------------
    if qid == "top_product_bar":
        sales = {}
        for d in data:
            pid = d["Product ID"]
            sales[pid] = sales.get(pid, 0) + float(d["Final Revenue (USD)"])
        return {"type": "bar", "labels": list(sales.keys())[:10], "values": list(sales.values())[:10]}

    # ---------------- 1️⃣6️⃣ REDTAPE BEST MONTH (BAR) ----------------
    if qid == "redtape_month":
        month_map = {}

        for d in data:
            if str(d.get("Company")).upper() == "REDTAPE":
                m = d.get("Month", "Unknown")
                try:
                    val = float(d.get("Final Revenue (USD)", 0))
                except:
                    val = 0

                month_map[m] = month_map.get(m, 0) + val

        if not month_map:
            return {"type": "text", "value": "No Redtape data found"}

        return {
            "type": "bar",
            "labels": list(month_map.keys()),
            "values": list(month_map.values())
        }

    # ---------------- 1️⃣7️⃣ FALLING BRAND (BAR) ----------------
    if qid == "fall_brand":
        brand_trend = {}

        for d in data:
            brand = str(d.get("Company")).upper()
            month = d.get("Month")
            revenue = float(d.get("Final Revenue (USD)", 0))

            brand_trend.setdefault(brand, {})
            brand_trend[brand][month] = brand_trend[brand].get(month, 0) + revenue

        falling = {}

        for brand, months in brand_trend.items():
            if len(months) < 2:
                continue
            vals = list(months.values())
            falling[brand] = vals[0] - vals[-1]  # drop

        return {
            "type": "bar",
            "labels": list(falling.keys()),
            "values": list(falling.values())
        }

    # ---------------- 1️⃣8️⃣ AVG PROFIT PER DAY ----------------
    if qid == "avg_profit_day":
        total = 0
        valid_days = set()

        for d in data:
            profit = d.get("Profit (USD)")
            date = str(d.get("Date")).split(" ")[0]

            try:
                profit = float(profit)
            except:
                continue

            total += profit
            valid_days.add(date)

        if not valid_days:
            return {"type": "text", "value": "Profit data missing"}

        avg = total / len(valid_days)
        return {"type": "text", "value": f"${round(avg,2)} per day"}

    # ---------------- 1️⃣9️⃣ STABLE PROFIT (PIE) ----------------
    if qid == "stable_profit":
        month_profit = {}

        for d in data:
            m = d.get("Month")
            try:
                val = float(d.get("Profit (USD)", 0))
            except:
                val = 0

            month_profit[m] = month_profit.get(m, 0) + val

        if not month_profit:
            return {"type": "text", "value": "No profit data"}

        return {
            "type": "pie",
            "labels": list(month_profit.keys()),
            "values": list(month_profit.values())
        }

    # ---------------- 2️⃣0️⃣ REAL DEMAND (BAR) ----------------
    if qid == "demand_bar":
        demand = {}

        for d in data:
            brand = str(d.get("Company")).upper()
            try:
                val = float(d.get("Final Revenue (USD)", 0))
            except:
                val = 0

            demand[brand] = demand.get(brand, 0) + val

        return {
            "type": "bar",
            "labels": list(demand.keys()),
            "values": list(demand.values())
        }

# ---------- LOGOUT ----------
@app.route("/logout")
def logout():
    session.clear()
    return redirect("/")

if __name__ == "__main__":
    app.run(debug=True)
