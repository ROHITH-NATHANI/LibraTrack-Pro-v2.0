# 📚 LibraTrack Pro v2.0 — Library Management System

A professional, full-featured Flask library management system with a premium sidebar UI, analytics, member management, and smart book issuing workflow.

---

## ✨ New Features (v2.0)

| Feature | Description |
|---------|-------------|
| 🗂️ Sidebar Layout | Fixed sidebar with section-based navigation |
| 🔍 Live Search | Global instant search with dropdown suggestions (via API) |
| 👤 Member System | Register, manage & deactivate library members |
| 📊 Reports & Analytics | Genre charts, top books, monthly issues bar chart |
| 📖 Book Detail Page | Full book info, borrow history, edit in-place |
| ✏️ Edit Books | Update any book field including cover color |
| 🎨 Cover Color Picker | Visual color selector for book cards |
| 💰 Fine Calculator | Auto ₹5/day fine for overdue returns |
| 📋 Activity Log | Timestamped log of all library actions |
| ⚡ Quick Duration Buttons | 1 Week / 2 Weeks / 1 Month / 2 Months shortcuts |
| 🔗 Member Auto-fill | Select a registered member to auto-fill borrow form |
| 🔐 Password Strength | Visual strength bar during member registration |
| 📱 Responsive | Mobile-friendly with collapsible sidebar |

---

## 🛠️ Technologies

| Layer | Technology |
|-------|-----------|
| Backend | Python 3, Flask 3.0 |
| Database | SQLite (via `sqlite3` module) |
| Frontend | HTML5, Bootstrap 5, Bootstrap Icons |
| JS | jQuery 3.7 |
| Fonts | Cormorant Garamond + Plus Jakarta Sans |
| Templating | Jinja2 |

---

## 📁 Project Structure

```
libra_v2/
├── app.py                    ← Flask app + all routes + DB
├── requirements.txt
├── README.md
├── static/
│   ├── css/style.css         ← Premium sidebar UI styles
│   └── js/app.js             ← jQuery interactions & validation
└── templates/
    ├── base.html             ← Sidebar layout base
    ├── index.html            ← Dashboard with stats + book grid
    ├── add_book.html         ← Add book with live preview
    ├── edit_book.html        ← Edit book details
    ├── book_detail.html      ← Full book info + history
    ├── borrow.html           ← Issue book form
    ├── borrowers.html        ← Active / Overdue / Returned tabs
    ├── members.html          ← Member registration & listing
    ├── reports.html          ← Analytics & activity log
    └── success.html          ← Confirmation page
```

---

## 🚀 Setup & Run

```bash
# 1. Extract zip and enter folder
cd libra_v2

# 2. (Optional) Virtual environment
python -m venv venv
venv\Scripts\activate     # Windows
source venv/bin/activate  # Mac/Linux

# 3. Install dependencies
pip install -r requirements.txt

# 4. Run
python app.py

# 5. Open browser
# http://127.0.0.1:5000
```

> SQLite database and 8 sample books are auto-created on first run.

---

## 🔗 Routes

| Route | Method | Description |
|-------|--------|-------------|
| `/` | GET | Dashboard & catalogue |
| `/add_book` | GET/POST | Add new book |
| `/book/<id>` | GET | Book detail + history |
| `/edit_book/<id>` | GET/POST | Edit book |
| `/borrow/<id>` | GET/POST | Issue book |
| `/return/<id>` | GET | Return book |
| `/borrowers` | GET | Borrowers (tabs) |
| `/members` | GET/POST | Member list & registration |
| `/reports` | GET | Analytics page |
| `/delete_book/<id>` | GET | Delete book |
| `/api/search` | GET | Live search JSON API |

---

## 🔧 Git Setup

```bash
git init
git add .
git commit -m "feat: LibraTrack Pro v2 - full library management system"
git branch -M main
git remote add origin https://github.com/ROHITH-NATHANI/LibraTrack-Pro-v2.0.git
git push -u origin main
```
