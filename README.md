# 📚 LibraTrack Pro v2.1 — Library Management System

A professional, full-featured Flask library management system with a premium sidebar UI, analytics, member management, smart book issuing workflow, and newly added interactive features like Reviews, Fines, and Dark Mode.

---

## ✨ System Features (v2.1 Updates)

| Feature | Description |
|---------|-------------|
| 🗂️ Sidebar Layout | Fixed sidebar with section-based navigation |
| 🌙 **Dark Mode Theme** | **[NEW]** Instantly toggle between light and eye-friendly dark layouts, saved via localStorage. |
| 👤 Member System & Auth | **[NEW]** Self-serve user registration and login/logout gateway. |
| ❤️ **Wishlist** | **[NEW]** Members can browse the catalogue and save books they want to read later into their personal Wishlist. |
| 💬 **Written Reviews** | **[NEW]** Members can submit text comments alongside 1-5 star ratings. Reviews are publicly visible on the book's detail page! |
| 💰 **Simulated Fine Payments** | **[NEW]** Auto ₹5/day fine for overdue returns. Members get a "My Loans & Fines" dashboard where they can simulate paying their overdue balances via an interactive modal. |
| 🔍 Live Search | Global instant search with dropdown suggestions (via API) |
| 📊 Reports & Analytics | Genre charts, top books, monthly issues bar chart |
| 📖 Book Detail Page | Full book info, borrow history, reader reviews |
| ✏️ Edit Books | Update any book field including cover color visually |
| 📋 Activity Log | Timestamped log of all library actions |

---

## 🛠️ Technologies

| Layer | Technology |
|-------|-----------|
| Backend | Python 3, Flask 3.0 |
| Database | SQLite (via `sqlite3` module) |
| Frontend | HTML5, Vanilla JS, Bootstrap 5, Bootstrap Icons |
| JS | jQuery 3.7 |
| Fonts | Cormorant Garamond + Plus Jakarta Sans |
| Templating | Jinja2 |

---

## 📁 Project Structure

```
libra_v2/
├── app.py                    ← Flask app + all backend routes + DB schemas
├── requirements.txt
├── README.md                 ← Project documentation
├── static/
│   ├── css/style.css         ← Global stylesheets including [data-theme="dark"]
│   └── js/app.js             ← Interactions & live search JSON parsing
└── templates/
    ├── base.html             ← Persistent UI, Sidebar, Dark Mode Toggle
    ├── index.html            ← Dashboard & Catalogue
    ├── register.html         ← Public member signup
    ├── wishlist.html         ← Member's saved books grid
    ├── my_loans.html         ← Active loans + Fines payment gateway
    ├── book_detail.html      ← Book stats + Reader Reviews
    ├── ... (other admin templates)
```

---

## 🚀 Setup & Run

```bash
# 1. Enter folder
cd libra_v2

# 2. (Optional) Virtual environment
python -m venv venv
venv\Scripts\activate     # Windows
source venv/bin/activate  # Mac/Linux

# 3. Install dependencies
pip install -r requirements.txt

# 4. Run Server
python app.py

# 5. Open browser
# http://127.0.0.1:5000
```

> SQLite database (`library.db`) and 8 beautifully colored sample books are auto-created on the first run.

---

## 🔗 Main Routes

| Route | Privileges | Description |
|-------|--------|-------------|
| `/` | Public | Home Dashboard & Book catalogue |
| `/register` | Public | Create new member account |
| `/login` / `/logout`| Mixed | Session authentication |
| `/book/<id>` | Public | View book details & community reviews |
| `/wishlist` | Member | View personal saved books |
| `/my_loans` | Member | View active loans and pay fines |
| `/rate_book/<id>`| Member | Submit star rating + text review |
| `/add_book` | Admin | Insert new catalogue entry |
| `/borrow/<id>` | Admin | Issue a book to a user |

---

## 🔧 Git Setup & Contribution

```bash
git add app.py static/ templates/ requirements.txt README.md
git commit -m "feat: complete v2.1 overhaul with Wishlist, Reviews, Fines, and Dark Mode"
git push -u origin main
```
