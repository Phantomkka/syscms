"""SysCMS v2 — компании, ПК, сисадмины, инвентарные карточки."""
import os, sqlite3, urllib.parse
from hashlib import sha256
from flask import (Flask, render_template, request, redirect, url_for,
                   session, flash, g, abort)

app = Flask(__name__)
app.secret_key = os.environ.get("SECRET_KEY", "syscms-dev-key")
DB = os.path.join(os.path.dirname(__file__), "syscms.db")

def get_db():
    if "db" not in g:
        g.db = sqlite3.connect(DB)
        g.db.row_factory = sqlite3.Row
    return g.db

@app.teardown_appcontext
def close_db(exc):
    db = g.pop("db", None)
    if db: db.close()

def init_db():
    db = sqlite3.connect(DB)
    db.executescript("""
        CREATE TABLE IF NOT EXISTS admins (id INTEGER PRIMARY KEY, username TEXT UNIQUE NOT NULL, password TEXT NOT NULL);
        CREATE TABLE IF NOT EXISTS companies (id INTEGER PRIMARY KEY, name TEXT NOT NULL, inn TEXT, kpp TEXT, phone TEXT, email TEXT, address TEXT, created_at TEXT DEFAULT (datetime('now')));
        CREATE TABLE IF NOT EXISTS pcs (id INTEGER PRIMARY KEY, company_id INTEGER REFERENCES companies(id), hostname TEXT NOT NULL, cpu TEXT, ram TEXT, hdd TEXT, os TEXT, ip TEXT, mac TEXT, inventory_no TEXT, responsible_id INTEGER REFERENCES sysadmins(id), created_at TEXT DEFAULT (datetime('now')));
        CREATE TABLE IF NOT EXISTS sysadmins (id INTEGER PRIMARY KEY, username TEXT UNIQUE NOT NULL, password TEXT NOT NULL, full_name TEXT, telegram TEXT, phone TEXT, photo_url TEXT, notes TEXT, created_at TEXT DEFAULT (datetime('now')));
        CREATE TABLE IF NOT EXISTS sysadmin_companies (sysadmin_id INTEGER REFERENCES sysadmins(id), company_id INTEGER REFERENCES companies(id), PRIMARY KEY (sysadmin_id, company_id));
    """)
    if not db.execute("SELECT id FROM admins WHERE username=?", ("root",)).fetchone():
        db.execute("INSERT INTO admins (username,password) VALUES (?,?)", ("root", sha256("admin".encode()).hexdigest()))
    db.commit()
    db.close()

def login_required(fn):
    from functools import wraps
    @wraps(fn)
    def w(*a, **kw):
        if "user" not in session: return redirect(url_for("login"))
        return fn(*a, **kw)
    return w

def hash_pass(p): return sha256(p.encode()).hexdigest()

# ── index ────────────────────────────────────────────────────────────
@app.route("/")
@login_required
def index():
    db = get_db()
    c = db.execute("SELECT count(*) FROM companies").fetchone()[0]
    p = db.execute("SELECT count(*) FROM pcs").fetchone()[0]
    s = db.execute("SELECT count(*) FROM sysadmins").fetchone()[0]
    return render_template("index.html", companies=c, pcs=p, sysadmins=s)

@app.route("/login", methods=["GET","POST"])
def login():
    if request.method == "POST":
        u, p = request.form["username"], hash_pass(request.form["password"])
        row = get_db().execute("SELECT id FROM admins WHERE username=? AND password=?", (u,p)).fetchone()
        if row:
            session["user"] = u
            return redirect(url_for("index"))
        flash("Неверный логин или пароль", "danger")
    return render_template("login.html")

@app.route("/logout")
def logout():
    session.clear()
    return redirect(url_for("login"))

# ── companies ────────────────────────────────────────────────────────
@app.route("/companies")
@login_required
def companies():
    return render_template("companies.html",
                           companies=get_db().execute(
                               "SELECT c.*, (SELECT count(*) FROM pcs WHERE company_id=c.id) as pc_count FROM companies c ORDER BY c.created_at DESC").fetchall())

@app.route("/companies/add", methods=["POST"])
@login_required
def company_add():
    f = request.form
    get_db().execute("INSERT INTO companies (name,inn,kpp,phone,email,address) VALUES (?,?,?,?,?,?)",
                     (f["name"], f.get("inn",""), f.get("kpp",""), f.get("phone",""), f.get("email",""), f.get("address","")))
    get_db().commit()
    flash("Компания добавлена", "success")
    return redirect(url_for("companies"))

@app.route("/companies/<int:cid>/edit", methods=["POST"])
@login_required
def company_edit(cid):
    f = request.form
    get_db().execute("UPDATE companies SET name=?,inn=?,kpp=?,phone=?,email=?,address=? WHERE id=?",
                     (f["name"], f.get("inn",""), f.get("kpp",""), f.get("phone",""), f.get("email",""), f.get("address",""), cid))
    get_db().commit()
    flash("Обновлено", "success")
    return redirect(url_for("companies"))

@app.route("/companies/<int:cid>/delete", methods=["POST"])
@login_required
def company_delete(cid):
    get_db().execute("DELETE FROM companies WHERE id=?", (cid,))
    get_db().commit()
    flash("Удалено", "warning")
    return redirect(url_for("companies"))

# ── pcs ──────────────────────────────────────────────────────────────
@app.route("/pcs")
@login_required
def pcs():
    return render_template("pcs.html",
                           pcs=get_db().execute(
                               "SELECT pcs.*, companies.name as company_name FROM pcs LEFT JOIN companies ON pcs.company_id=companies.id ORDER BY pcs.created_at DESC").fetchall(),
                           companies=get_db().execute("SELECT id,name FROM companies ORDER BY name").fetchall())

@app.route("/pcs/add", methods=["POST"])
@login_required
def pc_add():
    f = request.form
    get_db().execute(
        "INSERT INTO pcs (company_id,hostname,cpu,ram,hdd,os,ip,mac,inventory_no,responsible_id) VALUES (?,?,?,?,?,?,?,?,?,?)",
        (int(f.get("company_id",0)) or None, f["hostname"], f.get("cpu",""), f.get("ram",""),
         f.get("hdd",""), f.get("os",""), f.get("ip",""), f.get("mac",""),
         f.get("inventory_no",""), int(f.get("responsible_id",0)) or None))
    get_db().commit()
    flash("ПК добавлен", "success")
    return redirect(url_for("pcs"))

@app.route("/pcs/<int:pid>/edit", methods=["POST"])
@login_required
def pc_edit(pid):
    f = request.form
    get_db().execute(
        "UPDATE pcs SET company_id=?,hostname=?,cpu=?,ram=?,hdd=?,os=?,ip=?,mac=?,inventory_no=?,responsible_id=? WHERE id=?",
        (int(f.get("company_id",0)) or None, f["hostname"], f.get("cpu",""), f.get("ram",""),
         f.get("hdd",""), f.get("os",""), f.get("ip",""), f.get("mac",""),
         f.get("inventory_no",""), int(f.get("responsible_id",0)) or None, pid))
    get_db().commit()
    flash("Обновлено", "success")
    return redirect(url_for("pcs"))

@app.route("/pcs/<int:pid>/delete", methods=["POST"])
@login_required
def pc_delete(pid):
    get_db().execute("DELETE FROM pcs WHERE id=?", (pid,))
    get_db().commit()
    flash("Удалено", "warning")
    return redirect(url_for("pcs"))

# ── company pcs list ─────────────────────────────────────────────────
@app.route("/companies/<int:cid>/pcs")
@login_required
def company_pcs(cid):
    company = get_db().execute("SELECT * FROM companies WHERE id=?", (cid,)).fetchone()
    if not company:
        flash("Не найдена", "danger")
        return redirect(url_for("companies"))
    pcs = get_db().execute(
        "SELECT pcs.*, sysadmins.full_name as sa_name FROM pcs LEFT JOIN sysadmins ON pcs.responsible_id=sysadmins.id WHERE company_id=? ORDER BY pcs.created_at DESC", (cid,)).fetchall()
    comps = get_db().execute("SELECT id,name FROM companies ORDER BY name").fetchall()
    sas = get_db().execute(
        "SELECT s.*, GROUP_CONCAT(c.name) as companies FROM sysadmins s LEFT JOIN sysadmin_companies sc ON s.id=sc.sysadmin_id LEFT JOIN companies c ON sc.company_id=c.id GROUP BY s.id ORDER BY s.full_name").fetchall()
    return render_template("company_pcs.html", pcs=pcs, companies=comps, company=company, sysadmins=sas)

# ── pc detail card ───────────────────────────────────────────────────
@app.route("/pcs/<int:pid>/detail")
@login_required
def pc_detail(pid):
    pc = get_db().execute("SELECT * FROM pcs WHERE id=?", (pid,)).fetchone()
    if not pc:
        flash("Не найден", "danger")
        return redirect(url_for("pcs"))
    company = get_db().execute("SELECT * FROM companies WHERE id=?", (pc["company_id"],)).fetchone() if pc["company_id"] else None
    sa = None
    if pc["responsible_id"]:
        sa = get_db().execute(
            "SELECT s.*, GROUP_CONCAT(c.name) as companies FROM sysadmins s LEFT JOIN sysadmin_companies sc ON s.id=sc.sysadmin_id LEFT JOIN companies c ON sc.company_id=c.id WHERE s.id=? GROUP BY s.id", (pc["responsible_id"],)).fetchone()
    comps = get_db().execute("SELECT id,name FROM companies ORDER BY name").fetchall()
    sas = get_db().execute(
        "SELECT s.*, GROUP_CONCAT(c.name) as companies FROM sysadmins s LEFT JOIN sysadmin_companies sc ON s.id=sc.sysadmin_id LEFT JOIN companies c ON sc.company_id=c.id GROUP BY s.id ORDER BY s.full_name").fetchall()
    return render_template("pc_detail.html", pc=pc, company=company, sa=sa, companies=comps, sysadmins=sas)

# ── public pc card (no auth) ─────────────────────────────────────────
@app.route("/pc-card/<int:pid>")
def pc_card(pid):
    pc = get_db().execute("SELECT * FROM pcs WHERE id=?", (pid,)).fetchone()
    if not pc: abort(404)
    company = get_db().execute("SELECT * FROM companies WHERE id=?", (pc["company_id"],)).fetchone() if pc["company_id"] else None
    sa = None
    if pc["responsible_id"]:
        sa = get_db().execute(
            "SELECT s.*, GROUP_CONCAT(c.name) as companies FROM sysadmins s LEFT JOIN sysadmin_companies sc ON s.id=sc.sysadmin_id LEFT JOIN companies c ON sc.company_id=c.id WHERE s.id=? GROUP BY s.id", (pc["responsible_id"],)).fetchone()
    return render_template("pc_card.html", pc=pc, company=company, sa=sa)

# ── sysadmins ────────────────────────────────────────────────────────
@app.route("/sysadmins")
@login_required
def sysadmins_list():
    return render_template("sysadmins.html", sysadmins=get_db().execute(
        "SELECT s.*, GROUP_CONCAT(c.name) as companies FROM sysadmins s LEFT JOIN sysadmin_companies sc ON s.id=sc.sysadmin_id LEFT JOIN companies c ON sc.company_id=c.id GROUP BY s.id ORDER BY s.full_name").fetchall())

@app.route("/sysadmins/add", methods=["POST"])
@login_required
def sysadmin_add():
    f = request.form
    pw = f.get("password", "")
    if not pw:
        flash("Укажите пароль", "danger")
        return redirect(url_for("sysadmins_list"))
    cur = get_db().execute(
        "INSERT INTO sysadmins (username,password,full_name,telegram,phone,photo_url,notes) VALUES (?,?,?,?,?,?,?)",
        (f["username"], hash_pass(pw), f.get("full_name",""), f.get("telegram",""), f.get("phone",""), f.get("photo_url",""), f.get("notes","")))
    sa_id = cur.lastrowid
    for cid in f.getlist("company_ids"):
        try: get_db().execute("INSERT INTO sysadmin_companies (sysadmin_id,company_id) VALUES (?,?)", (sa_id, int(cid)))
        except: pass
    get_db().commit()
    flash("Сисадмин добавлен", "success")
    return redirect(url_for("sysadmins_list"))

@app.route("/sysadmins/<int:sid>/edit", methods=["POST"])
@login_required
def sysadmin_edit(sid):
    f = request.form
    pw = f.get("password", "")
    if pw:
        get_db().execute("UPDATE sysadmins SET username=?,password=?,full_name=?,telegram=?,phone=?,photo_url=?,notes=? WHERE id=?",
                         (f["username"], hash_pass(pw), f.get("full_name",""), f.get("telegram",""), f.get("phone",""), f.get("photo_url",""), f.get("notes",""), sid))
    else:
        get_db().execute("UPDATE sysadmins SET username=?,full_name=?,telegram=?,phone=?,photo_url=?,notes=? WHERE id=?",
                         (f["username"], f.get("full_name",""), f.get("telegram",""), f.get("phone",""), f.get("photo_url",""), f.get("notes",""), sid))
    get_db().execute("DELETE FROM sysadmin_companies WHERE sysadmin_id=?", (sid,))
    for cid in f.getlist("company_ids"):
        try: get_db().execute("INSERT INTO sysadmin_companies (sysadmin_id,company_id) VALUES (?,?)", (sid, int(cid)))
        except: pass
    get_db().commit()
    flash("Обновлено", "success")
    return redirect(url_for("sysadmins_list"))

@app.route("/sysadmins/<int:sid>/delete", methods=["POST"])
@login_required
def sysadmin_delete(sid):
    get_db().execute("DELETE FROM sysadmins WHERE id=?", (sid,))
    get_db().execute("DELETE FROM sysadmin_companies WHERE sysadmin_id=?", (sid,))
    get_db().commit()
    flash("Удалено", "warning")
    return redirect(url_for("sysadmins_list"))

# ── sysadmin card ────────────────────────────────────────────────────
@app.route("/sysadmins/<int:sid>/card")
@login_required
def sysadmin_card(sid):
    sa = get_db().execute(
        "SELECT s.*, GROUP_CONCAT(c.name) as companies FROM sysadmins s LEFT JOIN sysadmin_companies sc ON s.id=sc.sysadmin_id LEFT JOIN companies c ON sc.company_id=c.id WHERE s.id=? GROUP BY s.id", (sid,)).fetchone()
    if not sa:
        flash("Не найден", "danger")
        return redirect(url_for("sysadmins_list"))
    companies = get_db().execute(
        "SELECT c.id, c.name, (SELECT count(*) FROM pcs WHERE company_id=c.id) as pc_count FROM companies c JOIN sysadmin_companies sc ON c.id=sc.company_id WHERE sc.sysadmin_id=? ORDER BY c.name", (sid,)).fetchall()
    pcs = get_db().execute(
        "SELECT pcs.*, companies.name as company_name FROM pcs JOIN sysadmin_companies sc ON pcs.company_id=sc.company_id WHERE sc.sysadmin_id=? ORDER BY pcs.hostname", (sid,)).fetchall()
    return render_template("sysadmin_card.html", sa=sa, companies=companies, pcs=pcs)

with app.app_context():
    init_db()

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000, debug=True)
