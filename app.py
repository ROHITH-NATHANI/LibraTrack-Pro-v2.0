from flask import Flask, render_template, request, redirect, url_for, flash, jsonify, session
import sqlite3, os, hashlib, re
from datetime import datetime, date, timedelta

app = Flask(__name__)
app.secret_key = 'libra_v2_ultra_secret_2024'
DB = os.path.join(os.path.dirname(__file__), 'library.db')

# ── DB helpers ────────────────────────────────────────────────────────────────
def db():
    c = sqlite3.connect(DB)
    c.row_factory = sqlite3.Row
    return c

def init_db():
    with db() as c:
        c.executescript('''
            CREATE TABLE IF NOT EXISTS books (
                id            INTEGER PRIMARY KEY AUTOINCREMENT,
                title         TEXT    NOT NULL,
                author        TEXT    NOT NULL,
                genre         TEXT    NOT NULL,
                isbn          TEXT,
                publisher     TEXT,
                year          INTEGER,
                total_copies  INTEGER NOT NULL DEFAULT 1,
                available     INTEGER NOT NULL DEFAULT 1,
                cover_color   TEXT    DEFAULT '#c8dfc8',
                description   TEXT,
                rating        REAL    DEFAULT 0,
                rating_count  INTEGER DEFAULT 0,
                added_on      TEXT    NOT NULL
            );
            CREATE TABLE IF NOT EXISTS borrowers (
                id          INTEGER PRIMARY KEY AUTOINCREMENT,
                book_id     INTEGER NOT NULL,
                member_id   INTEGER,
                name        TEXT    NOT NULL,
                email       TEXT    NOT NULL,
                phone       TEXT,
                borrow_date TEXT    NOT NULL,
                due_date    TEXT    NOT NULL,
                returned    INTEGER NOT NULL DEFAULT 0,
                return_date TEXT,
                fine        REAL    DEFAULT 0,
                FOREIGN KEY(book_id) REFERENCES books(id)
            );
            CREATE TABLE IF NOT EXISTS members (
                id         INTEGER PRIMARY KEY AUTOINCREMENT,
                name       TEXT NOT NULL,
                email      TEXT NOT NULL UNIQUE,
                phone      TEXT,
                password   TEXT NOT NULL,
                joined     TEXT NOT NULL,
                active     INTEGER DEFAULT 1
            );
            CREATE TABLE IF NOT EXISTS activity_log (
                id        INTEGER PRIMARY KEY AUTOINCREMENT,
                action    TEXT NOT NULL,
                detail    TEXT,
                timestamp TEXT NOT NULL
            );
        ''')
        # Seed books
        if c.execute("SELECT COUNT(*) FROM books").fetchone()[0] == 0:
            colors = ['#e8d5b7','#c8dfc8','#d0d8f0','#f0d8d0','#ddd0f0','#f0eac8','#d0eef0','#f0dde8']
            seeds = [
                ('The Pragmatic Programmer','Andrew Hunt','Technology','978-0135957059','Addison-Wesley',2019,3,'Two experienced software engineers share their knowledge to help other programmers.',4.5,128),
                ('To Kill a Mockingbird','Harper Lee','Fiction','978-0061935466','Harper Perennial',1960,2,'A gripping, heart-wrenching, and wholly remarkable tale of coming-of-age.',4.8,340),
                ('Sapiens','Yuval Noah Harari','History','978-0062316097','Harper',2011,4,'A brief history of humankind from the Stone Age to the present.',4.7,512),
                ('Clean Code','Robert C. Martin','Technology','978-0132350884','Prentice Hall',2008,2,'A handbook of agile software craftsmanship.',4.4,96),
                ('The Alchemist','Paulo Coelho','Fiction','978-0062315007','HarperOne',1988,3,'A story about following your dreams and listening to your heart.',4.6,220),
                ('Atomic Habits','James Clear','Self-Help','978-0735211292','Avery',2018,3,'An easy and proven way to build good habits and break bad ones.',4.7,410),
                ('1984','George Orwell','Fiction','978-0451524935','Signet Classic',1949,2,'A dystopian masterpiece about totalitarianism and surveillance.',4.9,180),
                ('Deep Work','Cal Newport','Self-Help','978-1455586691','Grand Central',2016,2,'Rules for focused success in a distracted world.',4.3,95),
            ]
            for i, s in enumerate(seeds):
                c.execute(
                    "INSERT INTO books (title,author,genre,isbn,publisher,year,total_copies,available,description,rating,rating_count,cover_color,added_on) VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?)",
                    (*s[:7], s[6], s[7], s[8], s[9], colors[i % len(colors)], date.today().isoformat())
                )
        c.commit()

def log_action(action, detail=''):
    with db() as c:
        c.execute("INSERT INTO activity_log (action,detail,timestamp) VALUES (?,?,?)",
                  (action, detail, datetime.now().strftime('%Y-%m-%d %H:%M:%S')))
        c.commit()

def calc_fine(due_date_str, returned=False):
    due = date.fromisoformat(due_date_str)
    today = date.today()
    if today > due and not returned:
        return (today - due).days * 5  # ₹5/day
    return 0

# ── Routes ─────────────────────────────────────────────────────────────────────

@app.route('/')
def home():
    with db() as c:
        stats = {
            'total':      c.execute("SELECT COUNT(*) FROM books").fetchone()[0],
            'borrowed':   c.execute("SELECT COUNT(*) FROM borrowers WHERE returned=0").fetchone()[0],
            'members':    c.execute("SELECT COUNT(*) FROM members WHERE active=1").fetchone()[0],
        }
    return render_template('home.html', stats=stats)


@app.route('/dashboard')
def index():
    search = request.args.get('q', '').strip()
    genre  = request.args.get('genre', '')
    sort   = request.args.get('sort', 'newest')
    with db() as c:
        q = "SELECT * FROM books WHERE 1=1"
        p = []
        if search:
            q += " AND (title LIKE ? OR author LIKE ? OR isbn LIKE ?)"; p += [f'%{search}%']*3
        if genre:
            q += " AND genre=?"; p.append(genre)
        order = {'newest':'added_on DESC','oldest':'added_on ASC','title':'title ASC','rating':'rating DESC','available':'available DESC'}.get(sort,'added_on DESC')
        q += f" ORDER BY {order}"
        books   = c.execute(q, p).fetchall()
        genres  = c.execute("SELECT DISTINCT genre FROM books ORDER BY genre").fetchall()
        stats   = {
            'total':      c.execute("SELECT COUNT(*) FROM books").fetchone()[0],
            'borrowed':   c.execute("SELECT COUNT(*) FROM borrowers WHERE returned=0").fetchone()[0],
            'overdue':    c.execute("SELECT COUNT(*) FROM borrowers WHERE returned=0 AND due_date<?", (date.today().isoformat(),)).fetchone()[0],
            'members':    c.execute("SELECT COUNT(*) FROM members WHERE active=1").fetchone()[0],
            'returned_today': c.execute("SELECT COUNT(*) FROM borrowers WHERE return_date=?", (date.today().isoformat(),)).fetchone()[0],
        }
        recent_activity = c.execute("SELECT * FROM activity_log ORDER BY timestamp DESC LIMIT 6").fetchall()
    return render_template('index.html', books=books, genres=genres, stats=stats,
                           search=search, sel_genre=genre, sort=sort,
                           recent_activity=recent_activity)


@app.route('/add_book', methods=['GET','POST'])
def add_book():
    if request.method == 'POST':
        f = request.form
        title = f.get('title','').strip(); author = f.get('author','').strip()
        genre = f.get('genre','').strip(); isbn = f.get('isbn','').strip()
        publisher = f.get('publisher','').strip(); year = f.get('year','').strip()
        copies = f.get('copies','1').strip(); desc = f.get('description','').strip()
        cover_color = f.get('cover_color','#c8dfc8')

        errors = []
        if not title: errors.append('Book title is required.')
        if not author: errors.append('Author name is required.')
        if not genre: errors.append('Genre is required.')
        try: copies = int(copies); assert copies >= 1
        except: errors.append('Copies must be a positive number.')
        if year:
            try: year = int(year); assert 1000 <= year <= date.today().year
            except: errors.append(f'Year must be between 1000 and {date.today().year}.')
        else: year = None

        if errors:
            for e in errors: flash(e, 'error')
            return render_template('add_book.html', form_data=f)

        with db() as c:
            c.execute("INSERT INTO books (title,author,genre,isbn,publisher,year,total_copies,available,description,cover_color,added_on) VALUES (?,?,?,?,?,?,?,?,?,?,?)",
                      (title,author,genre,isbn,publisher,year,copies,copies,desc,cover_color,date.today().isoformat()))
            c.commit()
        log_action('Book Added', f'"{title}" by {author}')
        flash(f'"{title}" added to the library! 📚', 'success')
        return redirect(url_for('index'))
    return render_template('add_book.html', form_data={})


@app.route('/book/<int:bid>')
def book_detail(bid):
    with db() as c:
        book = c.execute("SELECT * FROM books WHERE id=?", (bid,)).fetchone()
        if not book: flash('Book not found.','error'); return redirect(url_for('index'))
        history = c.execute("SELECT * FROM borrowers WHERE book_id=? ORDER BY borrow_date DESC LIMIT 10", (bid,)).fetchall()
        today = date.today().isoformat()
    return render_template('book_detail.html', book=book, history=history, today=today)


@app.route('/edit_book/<int:bid>', methods=['GET','POST'])
def edit_book(bid):
    with db() as c:
        book = c.execute("SELECT * FROM books WHERE id=?", (bid,)).fetchone()
    if not book: flash('Not found','error'); return redirect(url_for('index'))

    if request.method == 'POST':
        f = request.form
        title=f.get('title','').strip(); author=f.get('author','').strip()
        genre=f.get('genre','').strip(); isbn=f.get('isbn','').strip()
        publisher=f.get('publisher','').strip(); year=f.get('year','') or None
        desc=f.get('description','').strip(); cover_color=f.get('cover_color','#c8dfc8')
        copies=int(f.get('copies',1))
        diff = copies - book['total_copies']
        if not title or not author or not genre:
            flash('Title, Author, Genre are required.','error')
            return render_template('edit_book.html', book=book)
        with db() as c:
            c.execute("UPDATE books SET title=?,author=?,genre=?,isbn=?,publisher=?,year=?,total_copies=?,available=MAX(0,available+?),description=?,cover_color=? WHERE id=?",
                      (title,author,genre,isbn,publisher,year,copies,diff,desc,cover_color,bid))
            c.commit()
        log_action('Book Edited', f'"{title}"')
        flash('Book updated! ✅','success')
        return redirect(url_for('book_detail', bid=bid))
    return render_template('edit_book.html', book=book)


@app.route('/borrow/<int:bid>', methods=['GET','POST'])
def borrow(bid):
    with db() as c:
        book = c.execute("SELECT * FROM books WHERE id=?", (bid,)).fetchone()
        members = c.execute("SELECT * FROM members WHERE active=1 ORDER BY name").fetchall()
    if not book: flash('Book not found.','error'); return redirect(url_for('index'))

    if request.method == 'POST':
        f = request.form
        name=f.get('name','').strip(); email=f.get('email','').strip()
        phone=f.get('phone','').strip(); due=f.get('due_date','')
        member_id=f.get('member_id') or None

        errors = []
        if not name: errors.append('Name is required.')
        if not email or '@' not in email: errors.append('Valid email is required.')
        if not due: errors.append('Due date is required.')
        elif due <= date.today().isoformat(): errors.append('Due date must be in the future.')
        if book['available'] < 1: errors.append('No copies available.')

        if errors:
            for e in errors: flash(e,'error')
            return render_template('borrow.html', book=book, members=members, form_data=f)

        with db() as c:
            c.execute("INSERT INTO borrowers (book_id,member_id,name,email,phone,borrow_date,due_date) VALUES (?,?,?,?,?,?,?)",
                      (bid,member_id,name,email,phone,date.today().isoformat(),due))
            c.execute("UPDATE books SET available=available-1 WHERE id=?", (bid,))
            c.commit()
        log_action('Book Issued', f'"{book["title"]}" → {name}')
        flash(f'Book issued to {name}! 🎉','success')
        return redirect(url_for('success', name=name, title=book['title'], due=due))
    return render_template('borrow.html', book=book, members=members, form_data={})


@app.route('/return/<int:rid>')
def return_book(rid):
    with db() as c:
        r = c.execute("SELECT br.*,b.title FROM borrowers br JOIN books b ON br.book_id=b.id WHERE br.id=?", (rid,)).fetchone()
        if r and not r['returned']:
            fine = calc_fine(r['due_date'])
            c.execute("UPDATE borrowers SET returned=1,return_date=?,fine=? WHERE id=?",
                      (date.today().isoformat(), fine, rid))
            c.execute("UPDATE books SET available=available+1 WHERE id=?", (r['book_id'],))
            c.commit()
            log_action('Book Returned', f'"{r["title"]}" by {r["name"]}')
            msg = f'Book returned! ✅'
            if fine > 0: msg += f' Late fine: ₹{fine}'
            flash(msg, 'success' if fine == 0 else 'warning')
        else:
            flash('Already returned or not found.','error')
    return redirect(url_for('borrowers'))


@app.route('/borrowers')
def borrowers():
    status = request.args.get('status','active')
    today  = date.today().isoformat()
    with db() as c:
        base = "SELECT br.*,b.title,b.author,b.genre FROM borrowers br JOIN books b ON br.book_id=b.id"
        if status=='overdue':
            rows = c.execute(base+" WHERE br.returned=0 AND br.due_date<? ORDER BY br.due_date ASC", (today,)).fetchall()
        elif status=='returned':
            rows = c.execute(base+" WHERE br.returned=1 ORDER BY br.return_date DESC").fetchall()
        else:
            rows = c.execute(base+" WHERE br.returned=0 ORDER BY br.due_date ASC").fetchall()
        counts = {
            'active':   c.execute("SELECT COUNT(*) FROM borrowers WHERE returned=0").fetchone()[0],
            'overdue':  c.execute("SELECT COUNT(*) FROM borrowers WHERE returned=0 AND due_date<?", (today,)).fetchone()[0],
            'returned': c.execute("SELECT COUNT(*) FROM borrowers WHERE returned=1").fetchone()[0],
        }
    return render_template('borrowers.html', rows=rows, status=status, counts=counts, today=today, calc_fine=calc_fine)


@app.route('/members', methods=['GET','POST'])
def members():
    if request.method == 'POST':
        f = request.form
        name=f.get('name','').strip(); email=f.get('email','').strip()
        phone=f.get('phone','').strip(); pwd=f.get('password','')

        errors = []
        if not name: errors.append('Name required.')
        if not email or '@' not in email: errors.append('Valid email required.')
        if len(pwd) < 6: errors.append('Password must be 6+ characters.')

        if errors:
            for e in errors: flash(e,'error')
        else:
            hashed = hashlib.sha256(pwd.encode()).hexdigest()
            try:
                with db() as c:
                    c.execute("INSERT INTO members (name,email,phone,password,joined) VALUES (?,?,?,?,?)",
                              (name,email,phone,hashed,date.today().isoformat()))
                    c.commit()
                log_action('Member Registered', name)
                flash(f'Member "{name}" registered! 👤','success')
            except sqlite3.IntegrityError:
                flash('Email already registered.','error')

    with db() as c:
        all_members = c.execute("SELECT m.*, (SELECT COUNT(*) FROM borrowers WHERE email=m.email AND returned=0) as active_loans FROM members m ORDER BY joined DESC").fetchall()
    return render_template('members.html', members=all_members)


@app.route('/members/delete/<int:mid>')
def delete_member(mid):
    with db() as c:
        loans = c.execute("SELECT COUNT(*) FROM borrowers WHERE member_id=? AND returned=0", (mid,)).fetchone()[0]
        if loans:
            flash('Cannot delete — member has active loans.','error')
        else:
            c.execute("UPDATE members SET active=0 WHERE id=?", (mid,))
            c.commit()
            flash('Member deactivated.','info')
    return redirect(url_for('members'))


@app.route('/reports')
def reports():
    with db() as c:
        today = date.today().isoformat()
        # Genre distribution
        by_genre = c.execute("SELECT genre, COUNT(*) as cnt FROM books GROUP BY genre ORDER BY cnt DESC").fetchall()
        # Top borrowed
        top_books = c.execute("""
            SELECT b.title, b.author, COUNT(br.id) as borrow_count
            FROM books b LEFT JOIN borrowers br ON b.id=br.book_id
            GROUP BY b.id ORDER BY borrow_count DESC LIMIT 5
        """).fetchall()
        # Monthly issues (last 6 months)
        monthly = c.execute("""
            SELECT strftime('%Y-%m', borrow_date) as month, COUNT(*) as cnt
            FROM borrowers WHERE borrow_date >= date('now','-6 months')
            GROUP BY month ORDER BY month
        """).fetchall()
        # Fines summary
        total_fines = c.execute("SELECT COALESCE(SUM(fine),0) FROM borrowers WHERE returned=1").fetchone()[0]
        pending_fines = c.execute("SELECT COUNT(*) FROM borrowers WHERE returned=0 AND due_date<?", (today,)).fetchone()[0]
        # Activity log
        activity = c.execute("SELECT * FROM activity_log ORDER BY timestamp DESC LIMIT 15").fetchall()
        stats = {
            'total_books':    c.execute("SELECT COUNT(*) FROM books").fetchone()[0],
            'total_issues':   c.execute("SELECT COUNT(*) FROM borrowers").fetchone()[0],
            'active_members': c.execute("SELECT COUNT(*) FROM members WHERE active=1").fetchone()[0],
            'total_fines':    total_fines,
            'pending_fines':  pending_fines,
        }
    return render_template('reports.html', by_genre=by_genre, top_books=top_books,
                           monthly=monthly, stats=stats, activity=activity)


@app.route('/delete_book/<int:bid>')
def delete_book(bid):
    with db() as c:
        active = c.execute("SELECT COUNT(*) FROM borrowers WHERE book_id=? AND returned=0", (bid,)).fetchone()[0]
        if active:
            flash('Cannot delete — book has active loans.','error')
        else:
            title = c.execute("SELECT title FROM books WHERE id=?", (bid,)).fetchone()['title']
            c.execute("DELETE FROM books WHERE id=?", (bid,))
            c.execute("DELETE FROM borrowers WHERE book_id=?", (bid,))
            c.commit()
            log_action('Book Deleted', f'"{title}"')
            flash('Book removed from library.','info')
    return redirect(url_for('index'))


@app.route('/api/search')
def api_search():
    q = request.args.get('q','').strip()
    if len(q) < 2: return jsonify([])
    with db() as c:
        rows = c.execute("SELECT id,title,author,genre,available FROM books WHERE title LIKE ? OR author LIKE ? LIMIT 8",
                         (f'%{q}%',f'%{q}%')).fetchall()
    return jsonify([dict(r) for r in rows])


@app.route('/success')
def success():
    return render_template('success.html',
                           name=request.args.get('name','Borrower'),
                           title=request.args.get('title','the book'),
                           due=request.args.get('due',''))

# ── Boot ──────────────────────────────────────────────────────────────────────
if __name__ == '__main__':
    init_db()
    app.run(debug=True)
