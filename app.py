"""
LibraTrack Pro v2.1 - Enhanced Library Management System
Improvements:
- Enhanced security (password hashing, input validation)
- Better error handling and logging
- Pagination support
- CSV export functionality
- Input validation and sanitization
- Database optimization with indexes
- Code refactoring and better organization
"""

from flask import Flask, render_template, request, redirect, url_for, flash, jsonify, session, send_file
from werkzeug.security import check_password_hash, generate_password_hash
from werkzeug.utils import secure_filename
import sqlite3, os, re, logging, csv, io, math
from datetime import datetime, date, timedelta
from functools import wraps

# ┌─ Configuration ──────────────────────────────────────────────────────────┐
app = Flask(__name__)
app.config['SECRET_KEY'] = os.environ.get('SECRET_KEY', 'libra-v2-dev-key-2024')
app.config['SESSION_COOKIE_SECURE'] = False  # Set to True in production with HTTPS
app.config['SESSION_COOKIE_HTTPONLY'] = True
app.config['PERMANENT_SESSION_LIFETIME'] = timedelta(hours=24)

DB = os.path.join(os.path.dirname(__file__), 'library.db')
ITEMS_PER_PAGE = 15

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# ┌─ Database Helpers ───────────────────────────────────────────────────────┐
def db():
    """Get database connection with row factory"""
    conn = sqlite3.connect(DB)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    return conn

def init_db():
    """Initialize database schema with proper indexes"""
    try:
        with db() as c:
            c.executescript('''
                -- Books table
                CREATE TABLE IF NOT EXISTS books (
                    id            INTEGER PRIMARY KEY AUTOINCREMENT,
                    title         TEXT    NOT NULL,
                    author        TEXT    NOT NULL,
                    genre         TEXT    NOT NULL,
                    isbn          TEXT    UNIQUE,
                    publisher     TEXT,
                    year          INTEGER,
                    total_copies  INTEGER NOT NULL DEFAULT 1,
                    available     INTEGER NOT NULL DEFAULT 1,
                    cover_color   TEXT    DEFAULT '#c8dfc8',
                    description   TEXT,
                    rating        REAL    DEFAULT 0,
                    rating_count  INTEGER DEFAULT 0,
                    added_on      TEXT    NOT NULL,
                    updated_on    TEXT
                );
                
                -- Books indexes for performance
                CREATE INDEX IF NOT EXISTS idx_books_genre ON books(genre);
                CREATE INDEX IF NOT EXISTS idx_books_title ON books(title);
                CREATE INDEX IF NOT EXISTS idx_books_author ON books(author);
                
                -- Borrowers table
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
                    FOREIGN KEY(book_id) REFERENCES books(id) ON DELETE CASCADE
                );
                
                -- Borrowers indexes
                CREATE INDEX IF NOT EXISTS idx_borrowers_book ON borrowers(book_id);
                CREATE INDEX IF NOT EXISTS idx_borrowers_email ON borrowers(email);
                CREATE INDEX IF NOT EXISTS idx_borrowers_returned ON borrowers(returned);
                CREATE INDEX IF NOT EXISTS idx_borrowers_due_date ON borrowers(due_date);
                
                -- Members table
                CREATE TABLE IF NOT EXISTS members (
                    id         INTEGER PRIMARY KEY AUTOINCREMENT,
                    name       TEXT NOT NULL,
                    email      TEXT NOT NULL UNIQUE,
                    phone      TEXT,
                    password   TEXT NOT NULL,
                    joined     TEXT NOT NULL,
                    active     INTEGER DEFAULT 1
                );
                
                CREATE INDEX IF NOT EXISTS idx_members_active ON members(active);
                CREATE INDEX IF NOT EXISTS idx_members_email ON members(email);
                
                -- Activity log table
                CREATE TABLE IF NOT EXISTS activity_log (
                    id        INTEGER PRIMARY KEY AUTOINCREMENT,
                    action    TEXT NOT NULL,
                    detail    TEXT,
                    user_id   INTEGER,
                    timestamp TEXT NOT NULL
                );
                CREATE INDEX IF NOT EXISTS idx_activity_timestamp ON activity_log(timestamp);
                
                -- Wishlist table
                CREATE TABLE IF NOT EXISTS wishlist (
                    id        INTEGER PRIMARY KEY AUTOINCREMENT,
                    member_id INTEGER NOT NULL,
                    book_id   INTEGER NOT NULL,
                    added_on  TEXT NOT NULL,
                    FOREIGN KEY(member_id) REFERENCES members(id) ON DELETE CASCADE,
                    FOREIGN KEY(book_id) REFERENCES books(id) ON DELETE CASCADE,
                    UNIQUE(member_id, book_id)
                );
                CREATE INDEX IF NOT EXISTS idx_wishlist_member ON wishlist(member_id);
                
                -- Reviews table
                CREATE TABLE IF NOT EXISTS reviews (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    book_id INTEGER NOT NULL,
                    member_id INTEGER NOT NULL,
                    rating INTEGER NOT NULL,
                    comment TEXT,
                    timestamp TEXT NOT NULL,
                    FOREIGN KEY(book_id) REFERENCES books(id) ON DELETE CASCADE,
                    FOREIGN KEY(member_id) REFERENCES members(id) ON DELETE CASCADE
                );
                CREATE INDEX IF NOT EXISTS idx_reviews_book ON reviews(book_id);
            ''')
            
            # Seed initial data if empty
            if c.execute("SELECT COUNT(*) FROM books").fetchone()[0] == 0:
                colors = ['#e8d5b7', '#c8dfc8', '#d0d8f0', '#f0d8d0', '#ddd0f0', '#f0eac8', '#d0eef0', '#f0dde8']
                seeds = [
                    ('The Pragmatic Programmer', 'Andrew Hunt', 'Technology', '978-0135957059', 'Addison-Wesley', 2019, 3, 'A handbook of pragmatic software development.', 4.5, 128),
                    ('To Kill a Mockingbird', 'Harper Lee', 'Fiction', '978-0061935466', 'Harper Perennial', 1960, 2, 'A classic American novel about justice and morality.', 4.8, 340),
                    ('Sapiens', 'Yuval Noah Harari', 'History', '978-0062316097', 'Harper', 2011, 4, 'A brief history of humankind.', 4.7, 512),
                    ('Clean Code', 'Robert C. Martin', 'Technology', '978-0132350884', 'Prentice Hall', 2008, 2, 'A guide to writing beautiful code.', 4.4, 96),
                    ('The Alchemist', 'Paulo Coelho', 'Fiction', '978-0062315007', 'HarperOne', 1988, 3, 'A journey of personal discovery.', 4.6, 220),
                    ('Atomic Habits', 'James Clear', 'Self-Help', '978-0735211292', 'Avery', 2018, 3, 'Build better habits through small changes.', 4.7, 410),
                    ('1984', 'George Orwell', 'Fiction', '978-0451524935', 'Signet Classic', 1949, 2, 'A dystopian novel about totalitarianism.', 4.9, 180),
                    ('Deep Work', 'Cal Newport', 'Self-Help', '978-1455586691', 'Grand Central', 2016, 2, 'Focus on meaningful work.', 4.3, 95),
                ]
                
                for i, seed in enumerate(seeds):
                    c.execute('''
                        INSERT INTO books 
                        (title, author, genre, isbn, publisher, year, total_copies, available, 
                         description, rating, rating_count, cover_color, added_on) 
                        VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?)
                    ''', (*seed[:7], seed[7], seed[8], seed[9], colors[i % len(colors)], date.today().isoformat()))
            
            c.commit()
        logger.info("✓ Database initialized successfully")
    except Exception as e:
        logger.error(f"✗ Database initialization error: {e}")
        raise

def log_action(action, detail='', user_id=None):
    """Log user actions with timestamp"""
    try:
        with db() as c:
            c.execute(
                "INSERT INTO activity_log (action, detail, user_id, timestamp) VALUES (?,?,?,?)",
                (action, detail, user_id, datetime.now().isoformat())
            )
            c.commit()
    except Exception as e:
        logger.warning(f"Failed to log action '{action}': {e}")

# ┌─ Validation Helpers ─────────────────────────────────────────────────────┐
def validate_email(email):
    """Validate email format"""
    pattern = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
    return re.match(pattern, email.strip()) is not None if email else False

def validate_isbn(isbn):
    """Validate ISBN format (10 or 13 digits)"""
    if not isbn:
        return True
    clean = isbn.replace('-', '').replace(' ', '')
    return len(clean) in [10, 13] and clean.isdigit()

def sanitize_string(text, max_length=500):
    """Sanitize and validate string input"""
    if not text:
        return ''
    text = str(text).strip()
    text = re.sub(r'[<>]', '', text)  # Remove basic HTML tags
    return text[:max_length]

def calc_fine(due_date_str, returned=False):
    """Calculate fine for overdue books (₹5/day)"""
    try:
        due = date.fromisoformat(due_date_str)
        today = date.today()
        if today > due and not returned:
            days_late = (today - due).days
            return max(0, days_late * 5)
        return 0
    except (ValueError, TypeError):
        logger.error(f"Invalid date format: {due_date_str}")
        return 0

# ┌─ Decorators ─────────────────────────────────────────────────────────────┐
def require_session(f):
    """Decorator to require active session"""
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'user_id' not in session:
            flash('Please log in to access this page.', 'warning')
            return redirect(url_for('login'))
        return f(*args, **kwargs)
    return decorated_function

# ┌─ Routes - Home & Auth ───────────────────────────────────────────────────┐
@app.route('/')
def home():
    """Home page with library stats"""
    try:
        with db() as c:
            stats = {
                'total_books': c.execute("SELECT COUNT(*) FROM books").fetchone()[0],
                'borrowed': c.execute("SELECT COUNT(*) FROM borrowers WHERE returned=0").fetchone()[0],
                'members': c.execute("SELECT COUNT(*) FROM members WHERE active=1").fetchone()[0],
                'overdue': c.execute("SELECT COUNT(*) FROM borrowers WHERE returned=0 AND due_date<?", (date.today().isoformat(),)).fetchone()[0],
            }
        return render_template('home.html', stats=stats)
    except Exception as e:
        logger.error(f"Error loading home: {e}")
        flash('Error loading dashboard.', 'error')
        stats = {'total_books': 0, 'borrowed': 0, 'members': 0, 'overdue': 0}
        return render_template('home.html', stats=stats)

@app.route('/login', methods=['GET', 'POST'])
def login():
    """Member login"""
    if request.method == 'POST':
        email = sanitize_string(request.form.get('email', ''))
        password = request.form.get('password', '')
        
        if not email or not password:
            flash('Email and password required.', 'error')
            return render_template('login.html')
        
        try:
            with db() as c:
                member = c.execute("SELECT * FROM members WHERE email=? AND active=1", (email,)).fetchone()
                if member and check_password_hash(member['password'], password):
                    session['user_id'] = member['id']
                    session['user_name'] = member['name']
                    session.permanent = True
                    log_action('Member Login', f'Member: {member["name"]}', member['id'])
                    flash(f'Welcome, {member["name"]}! 👋', 'success')
                    return redirect(url_for('index'))
                else:
                    flash('Invalid email or password.', 'error')
        except Exception as e:
            logger.error(f"Login error: {e}")
            flash('Login failed. Please try again.', 'error')
    
    return render_template('login.html')

@app.route('/logout')
def logout():
    """Member logout"""
    if 'user_name' in session:
        log_action('Member Logout', f'Member: {session["user_name"]}', session.get('user_id'))
    session.clear()
    flash('Logged out successfully.', 'info')
    return redirect(url_for('home'))

@app.route('/register', methods=['GET', 'POST'])
def register():
    """Public Member Registration"""
    if request.method == 'POST':
        name = sanitize_string(request.form.get('name', ''), 100)
        email = sanitize_string(request.form.get('email', ''), 100)
        phone = sanitize_string(request.form.get('phone', ''), 20)
        password = request.form.get('password', '')
        
        errors = []
        if not name: errors.append('Name is required.')
        if not email or not validate_email(email): errors.append('Valid email is required.')
        if len(password) < 6: errors.append('Password must be at least 6 characters.')
        
        if errors:
            for error in errors: flash(error, 'error')
        else:
            hashed = generate_password_hash(password, method='pbkdf2:sha256')
            try:
                with db() as c:
                    c.execute('''
                        INSERT INTO members (name, email, phone, password, joined) 
                        VALUES (?,?,?,?,?)
                    ''', (name, email, phone, hashed, date.today().isoformat()))
                    c.commit()
                log_action('Public Registration', name)
                flash(f'✓ Account created for "{name}"! Please log in.', 'success')
                return redirect(url_for('login'))
            except sqlite3.IntegrityError:
                flash('Email already registered.', 'error')
            except Exception as e:
                logger.error(f"Registration error: {e}")
                flash('Registration failed.', 'error')
    return render_template('register.html')

# ┌─ Routes - Dashboard ─────────────────────────────────────────────────────┐
@app.route('/dashboard')
def index():
    """Main dashboard with books and filtering"""
    try:
        search = sanitize_string(request.args.get('q', ''), 100)
        genre = sanitize_string(request.args.get('genre', ''), 50)
        sort = request.args.get('sort', 'newest')
        page = request.args.get('page', 1, type=int)
        
        with db() as c:
            # Build query
            query = "SELECT * FROM books WHERE 1=1"
            params = []
            
            if search:
                query += " AND (title LIKE ? OR author LIKE ? OR isbn LIKE ?)"
                search_param = f'%{search}%'
                params.extend([search_param, search_param, search_param])
            
            if genre:
                query += " AND genre=?"
                params.append(genre)
            
            # Sorting
            sort_map = {
                'newest': 'added_on DESC',
                'oldest': 'added_on ASC',
                'title': 'title ASC',
                'rating': 'rating DESC',
                'available': 'available DESC'
            }
            order_by = sort_map.get(sort, 'added_on DESC')
            query += f" ORDER BY {order_by}"
            
            # Get total count
            count_query = query.split(' ORDER BY')[0].replace('SELECT *', 'SELECT COUNT(*)')
            total_count = c.execute(count_query, params).fetchone()[0]
            
            # Pagination
            offset = (page - 1) * ITEMS_PER_PAGE
            query += f" LIMIT {ITEMS_PER_PAGE} OFFSET {offset}"
            
            books = c.execute(query, params).fetchall()
            genres = c.execute("SELECT DISTINCT genre FROM books WHERE genre IS NOT NULL ORDER BY genre").fetchall()
            
            total_pages = math.ceil(total_count / ITEMS_PER_PAGE) if total_count else 1
            
            stats = {
                'total': c.execute("SELECT COUNT(*) FROM books").fetchone()[0],
                'borrowed': c.execute("SELECT COUNT(*) FROM borrowers WHERE returned=0").fetchone()[0],
                'overdue': c.execute("SELECT COUNT(*) FROM borrowers WHERE returned=0 AND due_date<?", (date.today().isoformat(),)).fetchone()[0],
                'members': c.execute("SELECT COUNT(*) FROM members WHERE active=1").fetchone()[0],
            }
            
            recent_activity = c.execute("SELECT * FROM activity_log ORDER BY timestamp DESC LIMIT 5").fetchall()
        
        return render_template('index.html',
            books=books, genres=genres, stats=stats,
            search=search, sel_genre=genre, sort=sort,
            page=page, total_pages=total_pages,
            recent_activity=recent_activity)
    except Exception as e:
        logger.error(f"Dashboard error: {e}")
        flash('Error loading dashboard.', 'error')
        return render_template('index.html', books=[], genres=[], stats={'total': 0, 'borrowed': 0, 'overdue': 0, 'members': 0}, search='', sel_genre='', sort='newest', page=1, total_pages=1, recent_activity=[])

# ┌─ Routes - Books ─────────────────────────────────────────────────────────┐
@app.route('/add_book', methods=['GET', 'POST'])
def add_book():
    """Add new book to library"""
    if request.method == 'POST':
        try:
            title = sanitize_string(request.form.get('title', ''), 200)
            author = sanitize_string(request.form.get('author', ''), 150)
            genre = sanitize_string(request.form.get('genre', ''), 50)
            isbn = sanitize_string(request.form.get('isbn', ''), 20)
            publisher = sanitize_string(request.form.get('publisher', ''), 150)
            year_str = request.form.get('year', '')
            copies_str = request.form.get('copies', '1')
            description = sanitize_string(request.form.get('description', ''), 1000)
            cover_color = request.form.get('cover_color', '#c8dfc8')
            
            errors = []
            
            # Validation
            if not title:
                errors.append('Book title is required.')
            if not author:
                errors.append('Author name is required.')
            if not genre:
                errors.append('Genre is required.')
            
            try:
                copies = int(copies_str)
                if copies < 1:
                    errors.append('Copies must be at least 1.')
            except ValueError:
                errors.append('Copies must be a positive number.')
            
            if year_str:
                try:
                    year = int(year_str)
                    if year < 1000 or year > date.today().year:
                        errors.append(f'Year must be between 1000 and {date.today().year}.')
                except ValueError:
                    errors.append('Year must be a valid number.')
            else:
                year = None
            
            if isbn and not validate_isbn(isbn):
                errors.append('ISBN must be 10 or 13 digits.')
            
            if not re.match(r'^#[0-9a-fA-F]{6}$', cover_color):
                cover_color = '#c8dfc8'
            
            if errors:
                for error in errors:
                    flash(error, 'error')
                return render_template('add_book.html', form_data=request.form)
            
            # Insert book
            with db() as c:
                c.execute('''
                    INSERT INTO books 
                    (title, author, genre, isbn, publisher, year, total_copies, available, 
                     description, cover_color, added_on) 
                    VALUES (?,?,?,?,?,?,?,?,?,?,?)
                ''', (title, author, genre, isbn or None, publisher, year, copies, copies, 
                      description, cover_color, date.today().isoformat()))
                c.commit()
            
            log_action('Book Added', f'"{title}" by {author}')
            flash(f'✓ "{title}" added to the library!', 'success')
            return redirect(url_for('index'))
        
        except sqlite3.IntegrityError as e:
            if 'isbn' in str(e).lower():
                flash('ISBN already exists in library.', 'error')
            else:
                flash('Error adding book. Please try again.', 'error')
        except Exception as e:
            logger.error(f"Add book error: {e}")
            flash('An error occurred. Please try again.', 'error')
    
    return render_template('add_book.html', form_data={})

@app.route('/book/<int:bid>')
def book_detail(bid):
    """View book details and borrowing history"""
    try:
        with db() as c:
            book = c.execute("SELECT * FROM books WHERE id=?", (bid,)).fetchone()
            if not book:
                flash('Book not found.', 'error')
                return redirect(url_for('index'))
            
            history = c.execute('''
                SELECT * FROM borrowers 
                WHERE book_id=? 
                ORDER BY borrow_date DESC LIMIT 10
            ''', (bid,)).fetchall()
            
            reviews = c.execute('''
                SELECT r.*, m.name as member_name 
                FROM reviews r
                JOIN members m ON r.member_id = m.id
                WHERE r.book_id=?
                ORDER BY r.timestamp DESC
            ''', (bid,)).fetchall()
        
        today = date.today().isoformat()
        return render_template('book_detail.html', book=book, history=history, reviews=reviews, today=today, calc_fine=calc_fine)
    except Exception as e:
        logger.error(f"Book detail error: {e}")
        flash('Error loading book details.', 'error')
        return redirect(url_for('index'))

@app.route('/edit_book/<int:bid>', methods=['GET', 'POST'])
def edit_book(bid):
    """Edit book information"""
    try:
        with db() as c:
            book = c.execute("SELECT * FROM books WHERE id=?", (bid,)).fetchone()
        
        if not book:
            flash('Book not found.', 'error')
            return redirect(url_for('index'))
        
        if request.method == 'POST':
            title = sanitize_string(request.form.get('title', ''), 200)
            author = sanitize_string(request.form.get('author', ''), 150)
            genre = sanitize_string(request.form.get('genre', ''), 50)
            isbn = sanitize_string(request.form.get('isbn', ''), 20)
            publisher = sanitize_string(request.form.get('publisher', ''), 150)
            year_str = request.form.get('year', '')
            description = sanitize_string(request.form.get('description', ''), 1000)
            cover_color = request.form.get('cover_color', '#c8dfc8')
            copies_str = request.form.get('copies', str(book['total_copies']))
            
            errors = []
            if not title:
                errors.append('Title is required.')
            if not author:
                errors.append('Author is required.')
            if not genre:
                errors.append('Genre is required.')
            
            try:
                copies = int(copies_str)
            except ValueError:
                errors.append('Copies must be a number.')
                copies = book['total_copies']
            
            if errors:
                for error in errors:
                    flash(error, 'error')
                return render_template('edit_book.html', book=book)
            
            year = None
            if year_str:
                try:
                    year = int(year_str)
                except ValueError:
                    pass
            
            copies_diff = copies - book['total_copies']
            
            try:
                with db() as c:
                    c.execute('''
                        UPDATE books 
                        SET title=?, author=?, genre=?, isbn=?, publisher=?, year=?, 
                            total_copies=?, available=MAX(0,available+?), description=?, 
                            cover_color=?, updated_on=?
                        WHERE id=?
                    ''', (title, author, genre, isbn or None, publisher, year, copies, 
                          copies_diff, description, cover_color, datetime.now().isoformat(), bid))
                    c.commit()
                
                log_action('Book Edited', f'"{title}"')
                flash('✓ Book updated successfully!', 'success')
                return redirect(url_for('book_detail', bid=bid))
            except Exception as e:
                logger.error(f"Edit book error: {e}")
                flash('Error updating book.', 'error')
        
        return render_template('edit_book.html', book=book)
    except Exception as e:
        logger.error(f"Edit book error: {e}")
        flash('Error loading book.', 'error')
        return redirect(url_for('index'))

@app.route('/rate_book/<int:bid>', methods=['POST'])
@require_session
def rate_book(bid):
    """Rate and review a book (AJAX)"""
    try:
        rating = request.form.get('rating', type=float)
        comment = sanitize_string(request.form.get('comment', ''), 1000)
        
        if not rating or not (1 <= rating <= 5):
            return jsonify({'error': 'Invalid rating (1-5).'}), 400
        
        with db() as c:
            book = c.execute("SELECT rating, rating_count FROM books WHERE id=?", (bid,)).fetchone()
            if not book: return jsonify({'error': 'Book not found.'}), 404
            
            existing = c.execute("SELECT id FROM reviews WHERE book_id=? AND member_id=?", (bid, session['user_id'])).fetchone()
            if existing: return jsonify({'error': 'You have already reviewed this book.'}), 400
            
            new_count = book['rating_count'] + 1
            new_rating = (book['rating'] * book['rating_count'] + rating) / new_count
            
            c.execute("UPDATE books SET rating=?, rating_count=? WHERE id=?", (new_rating, new_count, bid))
            c.execute('''
                INSERT INTO reviews (book_id, member_id, rating, comment, timestamp)
                VALUES (?, ?, ?, ?, ?)
            ''', (bid, session['user_id'], rating, comment, datetime.now().isoformat()))
            c.commit()
            
            member_name = session.get('user_name', 'Member')
        
        log_action('Book Rated', f'Book {bid}: {rating}⭐ by user {session["user_id"]}')
        now_str = datetime.now().strftime('%Y-%m-%d %H:%M')
        
        return jsonify({
            'rating': round(new_rating, 1), 
            'count': new_count,
            'review': {
                'member_name': member_name,
                'rating': rating,
                'comment': comment,
                'timestamp': now_str
            }
        })
    except Exception as e:
        logger.error(f"Rating error: {e}")
        return jsonify({'error': 'Rating failed.'}), 500

@app.route('/delete_book/<int:bid>')
def delete_book(bid):
    """Delete book from library"""
    try:
        with db() as c:
            active_loans = c.execute("SELECT COUNT(*) FROM borrowers WHERE book_id=? AND returned=0", (bid,)).fetchone()[0]
            if active_loans:
                flash('Cannot delete book with active loans.', 'warning')
            else:
                book = c.execute("SELECT title FROM books WHERE id=?", (bid,)).fetchone()
                c.execute("DELETE FROM books WHERE id=?", (bid,))
                c.commit()
                log_action('Book Deleted', f'"{book["title"]}"')
                flash('✓ Book removed from library.', 'success')
    except Exception as e:
        logger.error(f"Delete book error: {e}")
        flash('Error deleting book.', 'error')
    
    return redirect(url_for('index'))

# ┌─ Routes - Borrowing ─────────────────────────────────────────────────────┐
@app.route('/borrow/<int:bid>', methods=['GET', 'POST'])
def borrow(bid):
    """Issue book to borrower"""
    try:
        with db() as c:
            book = c.execute("SELECT * FROM books WHERE id=?", (bid,)).fetchone()
            members = c.execute("SELECT * FROM members WHERE active=1 ORDER BY name").fetchall()
        
        if not book:
            flash('Book not found.', 'error')
            return redirect(url_for('index'))
        
        if request.method == 'POST':
            name = sanitize_string(request.form.get('name', ''), 100)
            email = sanitize_string(request.form.get('email', ''), 100)
            phone = sanitize_string(request.form.get('phone', ''), 20)
            due_date = request.form.get('due_date', '')
            member_id = request.form.get('member_id') or None
            
            errors = []
            
            if not name:
                errors.append('Borrower name is required.')
            if not email or not validate_email(email):
                errors.append('Valid email is required.')
            if not due_date:
                errors.append('Due date is required.')
            elif due_date <= date.today().isoformat():
                errors.append('Due date must be in the future.')
            if book['available'] < 1:
                errors.append('No copies available.')
            
            if errors:
                for error in errors:
                    flash(error, 'error')
                return render_template('borrow.html', book=book, members=members, form_data=request.form)
            
            try:
                with db() as c:
                    c.execute('''
                        INSERT INTO borrowers 
                        (book_id, member_id, name, email, phone, borrow_date, due_date) 
                        VALUES (?,?,?,?,?,?,?)
                    ''', (bid, member_id, name, email, phone, date.today().isoformat(), due_date))
                    c.execute("UPDATE books SET available=available-1 WHERE id=?", (bid,))
                    c.commit()
                
                log_action('Book Issued', f'"{book["title"]}" → {name}')
                flash(f'✓ Book issued to {name}! 🎉', 'success')
                return redirect(url_for('success', name=name, title=book['title'], due=due_date))
            except Exception as e:
                logger.error(f"Borrow error: {e}")
                flash('Error issuing book.', 'error')
        
        return render_template('borrow.html', book=book, members=members, form_data={})
    except Exception as e:
        logger.error(f"Borrow page error: {e}")
        flash('Error accessing borrow page.', 'error')
        return redirect(url_for('index'))

@app.route('/return/<int:rid>')
def return_book(rid):
    """Return book from borrower"""
    try:
        with db() as c:
            borrow_record = c.execute('''
                SELECT br.*, b.title FROM borrowers br 
                JOIN books b ON br.book_id=b.id 
                WHERE br.id=?
            ''', (rid,)).fetchone()
            
            if borrow_record and not borrow_record['returned']:
                fine = calc_fine(borrow_record['due_date'])
                c.execute('''
                    UPDATE borrowers 
                    SET returned=1, return_date=?, fine=? 
                    WHERE id=?
                ''', (date.today().isoformat(), fine, rid))
                c.execute("UPDATE books SET available=available+1 WHERE id=?", (borrow_record['book_id'],))
                c.commit()
                
                log_action('Book Returned', f'"{borrow_record["title"]}" by {borrow_record["name"]}')
                
                msg = '✓ Book returned successfully!'
                if fine > 0:
                    msg += f' Late fine: ₹{fine}'
                flash(msg, 'success' if fine == 0 else 'warning')
            else:
                flash('Book already returned or not found.', 'error')
    except Exception as e:
        logger.error(f"Return book error: {e}")
        flash('Error returning book.', 'error')
    
    return redirect(url_for('borrowers'))

@app.route('/borrowers')
def borrowers():
    """View borrowing records with filters"""
    try:
        status = request.args.get('status', 'active')
        page = request.args.get('page', 1, type=int)
        today = date.today().isoformat()
        
        with db() as c:
            base_query = '''
                SELECT br.*, b.title, b.author, b.genre 
                FROM borrowers br 
                JOIN books b ON br.book_id=b.id
            '''
            
            if status == 'overdue':
                query = base_query + " WHERE br.returned=0 AND br.due_date<? ORDER BY br.due_date ASC"
                params = [today]
            elif status == 'returned':
                query = base_query + " WHERE br.returned=1 ORDER BY br.return_date DESC"
                params = []
            else:
                query = base_query + " WHERE br.returned=0 ORDER BY br.due_date ASC"
                params = []
            
            # Count
            count_query = query.split('ORDER')[0]
            total_count = c.execute(count_query, params).fetchall()
            total_count = len(total_count)
            
            # Pagination
            offset = (page - 1) * ITEMS_PER_PAGE
            query += f" LIMIT {ITEMS_PER_PAGE} OFFSET {offset}"
            rows = c.execute(query, params).fetchall()
            
            counts = {
                'active': c.execute("SELECT COUNT(*) FROM borrowers WHERE returned=0").fetchone()[0],
                'overdue': c.execute("SELECT COUNT(*) FROM borrowers WHERE returned=0 AND due_date<?", (today,)).fetchone()[0],
                'returned': c.execute("SELECT COUNT(*) FROM borrowers WHERE returned=1").fetchone()[0],
            }
            
            total_pages = math.ceil(total_count / ITEMS_PER_PAGE) if total_count else 1
        
        return render_template('borrowers.html',
            rows=rows, status=status, counts=counts, today=today,
            calc_fine=calc_fine, page=page, total_pages=total_pages)
    except Exception as e:
        logger.error(f"Borrowers page error: {e}")
        flash('Error loading borrowers.', 'error')
        return render_template('borrowers.html', rows=[], status='active', counts={}, today='', calc_fine=calc_fine, page=1, total_pages=1)

# ┌─ Routes - Members ───────────────────────────────────────────────────────┐
@app.route('/members', methods=['GET', 'POST'])
def members():
    """Member management"""
    if request.method == 'POST':
        try:
            name = sanitize_string(request.form.get('name', ''), 100)
            email = sanitize_string(request.form.get('email', ''), 100)
            phone = sanitize_string(request.form.get('phone', ''), 20)
            password = request.form.get('password', '')
            
            errors = []
            if not name:
                errors.append('Name is required.')
            if not email or not validate_email(email):
                errors.append('Valid email is required.')
            if len(password) < 6:
                errors.append('Password must be at least 6 characters.')
            
            if errors:
                for error in errors:
                    flash(error, 'error')
            else:
                hashed = generate_password_hash(password, method='pbkdf2:sha256')
                try:
                    with db() as c:
                        c.execute('''
                            INSERT INTO members (name, email, phone, password, joined) 
                            VALUES (?,?,?,?,?)
                        ''', (name, email, phone, hashed, date.today().isoformat()))
                        c.commit()
                    
                    log_action('Member Registered', name)
                    flash(f'✓ Member "{name}" registered!', 'success')
                except sqlite3.IntegrityError:
                    flash('Email already registered.', 'error')
        except Exception as e:
            logger.error(f"Member registration error: {e}")
            flash('Registration failed.', 'error')
    
    try:
        with db() as c:
            members_list = c.execute('''
                SELECT m.*, 
                       (SELECT COUNT(*) FROM borrowers WHERE member_id=m.id AND returned=0) as active_loans 
                FROM members m 
                WHERE active=1
                ORDER BY joined DESC
            ''').fetchall()
        
        return render_template('members.html', members=members_list)
    except Exception as e:
        logger.error(f"Members page error: {e}")
        flash('Error loading members.', 'error')
        return render_template('members.html', members=[])

@app.route('/members/delete/<int:mid>')
def delete_member(mid):
    """Deactivate member"""
    try:
        with db() as c:
            active_loans = c.execute("SELECT COUNT(*) FROM borrowers WHERE member_id=? AND returned=0", (mid,)).fetchone()[0]
            if active_loans:
                flash('Cannot deactivate member with active loans.', 'warning')
            else:
                member = c.execute("SELECT name FROM members WHERE id=?", (mid,)).fetchone()
                c.execute("UPDATE members SET active=0 WHERE id=?", (mid,))
                c.commit()
                log_action('Member Deactivated', member['name'])
                flash('✓ Member deactivated.', 'success')
    except Exception as e:
        logger.error(f"Delete member error: {e}")
        flash('Error deleting member.', 'error')
    
    return redirect(url_for('members'))

# ┌─ Routes - Reports & Export ──────────────────────────────────────────────┐
@app.route('/reports')
def reports():
    """Analytics and reports dashboard"""
    try:
        with db() as c:
            today = date.today().isoformat()
            
            # Genre distribution
            by_genre = c.execute('''
                SELECT genre, COUNT(*) as cnt 
                FROM books 
                WHERE genre IS NOT NULL
                GROUP BY genre 
                ORDER BY cnt DESC
            ''').fetchall()
            
            # Top borrowed books
            top_books = c.execute('''
                SELECT b.id, b.title, b.author, COUNT(br.id) as borrow_count
                FROM books b 
                LEFT JOIN borrowers br ON b.id=br.book_id
                GROUP BY b.id 
                ORDER BY borrow_count DESC 
                LIMIT 5
            ''').fetchall()
            
            # Monthly issues
            monthly = c.execute('''
                SELECT strftime('%Y-%m', borrow_date) as month, COUNT(*) as cnt
                FROM borrowers 
                WHERE borrow_date >= date('now','-6 months')
                GROUP BY month 
                ORDER BY month
            ''').fetchall()
            
            # Fines summary
            total_fines = c.execute("SELECT COALESCE(SUM(fine),0) FROM borrowers WHERE returned=1").fetchone()[0]
            pending_fines = c.execute("SELECT COUNT(*) FROM borrowers WHERE returned=0 AND due_date<?", (today,)).fetchone()[0]
            
            # Recent activity
            activity = c.execute('''
                SELECT * FROM activity_log 
                ORDER BY timestamp DESC 
                LIMIT 15
            ''').fetchall()
            
            stats = {
                'total_books': c.execute("SELECT COUNT(*) FROM books").fetchone()[0],
                'total_issues': c.execute("SELECT COUNT(*) FROM borrowers").fetchone()[0],
                'active_members': c.execute("SELECT COUNT(*) FROM members WHERE active=1").fetchone()[0],
                'total_fines': round(total_fines, 2),
                'pending_fines': pending_fines,
            }
        
        return render_template('reports.html',
            by_genre=by_genre, top_books=top_books, monthly=monthly,
            stats=stats, activity=activity)
    except Exception as e:
        logger.error(f"Reports error: {e}")
        flash('Error loading reports.', 'error')
        return render_template('reports.html', by_genre=[], top_books=[], monthly=[], stats={}, activity=[])

# ┌─ Routes - Wishlist ─────────────────────────────────────────────────────┐
@app.route('/wishlist')
@require_session
def wishlist():
    try:
        with db() as c:
            books = c.execute('''
                SELECT b.*, w.added_on as wishlist_added 
                FROM books b
                JOIN wishlist w ON b.id = w.book_id
                WHERE w.member_id = ?
                ORDER BY w.added_on DESC
            ''', (session['user_id'],)).fetchall()
        return render_template('wishlist.html', books=books)
    except Exception as e:
        logger.error(f"Wishlist error: {e}")
        flash('Error loading wishlist.', 'error')
        return redirect(url_for('index'))

@app.route('/add_wishlist/<int:bid>')
@require_session
def add_wishlist(bid):
    try:
        with db() as c:
            c.execute('''
                INSERT OR IGNORE INTO wishlist (member_id, book_id, added_on)
                VALUES (?, ?, ?)
            ''', (session['user_id'], bid, datetime.now().isoformat()))
            c.commit()
            book = c.execute("SELECT title FROM books WHERE id=?", (bid,)).fetchone()
            name = book['title'] if book else 'Book'
            flash(f'✓ "{name}" added to your wishlist.', 'success')
    except Exception as e:
        logger.error(f"Add wishlist error: {e}")
        flash('Error adding to wishlist.', 'error')
    return redirect(request.referrer or url_for('index'))

@app.route('/remove_wishlist/<int:bid>')
@require_session
def remove_wishlist(bid):
    try:
        with db() as c:
            c.execute('DELETE FROM wishlist WHERE member_id=? AND book_id=?', (session['user_id'], bid))
            c.commit()
            flash('✓ Removed from wishlist.', 'info')
    except Exception as e:
         logger.error(f"Remove wishlist error: {e}")
         flash('Error removing from wishlist.', 'error')
    return redirect(request.referrer or url_for('wishlist'))

# ┌─ Routes - My Loans / Fines ──────────────────────────────────────────────┐
@app.route('/my_loans')
@require_session
def my_loans():
    try:
        with db() as c:
            active_loans = c.execute('''
                SELECT br.*, b.title, b.author, b.cover_color
                FROM borrowers br
                JOIN books b ON br.book_id = b.id
                WHERE br.member_id = ? AND br.returned = 0
                ORDER BY br.due_date ASC
            ''', (session['user_id'],)).fetchall()
            
            past_loans = c.execute('''
                SELECT br.*, b.title, b.author, b.cover_color
                FROM borrowers br
                JOIN books b ON br.book_id = b.id
                WHERE br.member_id = ? AND br.returned = 1
                ORDER BY br.return_date DESC
                LIMIT 30
            ''', (session['user_id'],)).fetchall()
            
        today = date.today().isoformat()
        return render_template('my_loans.html', active_loans=active_loans, past_loans=past_loans, today=today, calc_fine=calc_fine)
    except Exception as e:
        logger.error(f"My Loans error: {e}")
        flash('Error loading your loans.', 'error')
        return redirect(url_for('index'))

@app.route('/pay_fine/<int:rid>', methods=['POST'])
@require_session
def pay_fine(rid):
    try:
        with db() as c:
            record = c.execute('SELECT fine, member_id FROM borrowers WHERE id=?', (rid,)).fetchone()
            if not record or record['member_id'] != session['user_id']:
                return jsonify({'error': 'Record not found.'}), 404
            if record['fine'] <= 0:
                return jsonify({'error': 'No fine to pay.'}), 400
                
            c.execute('UPDATE borrowers SET fine=0 WHERE id=? AND member_id=?', (rid, session['user_id']))
            c.commit()
            
        log_action('Fine Paid', f'Fine cleared for record {rid} by user {session["user_id"]}')
        return jsonify({'success': True, 'message': 'Fine paid successfully!'})
    except Exception as e:
        logger.error(f"Pay fine error: {e}")
        return jsonify({'error': 'Payment failed.'}), 500

@app.route('/export/books')
def export_books_csv():
    """Export books to CSV"""
    try:
        with db() as c:
            books = c.execute('''
                SELECT id, title, author, genre, isbn, publisher, year, 
                       total_copies, available, rating, added_on 
                FROM books 
                ORDER BY added_on DESC
            ''').fetchall()
        
        output = io.StringIO()
        writer = csv.writer(output)
        writer.writerow(['ID', 'Title', 'Author', 'Genre', 'ISBN', 'Publisher', 'Year', 
                        'Total Copies', 'Available', 'Rating', 'Added On'])
        
        for book in books:
            writer.writerow(book)
        
        output.seek(0)
        return send_file(
            io.BytesIO(output.getvalue().encode('utf-8')),
            mimetype='text/csv',
            as_attachment=True,
            download_name=f'books_export_{date.today().isoformat()}.csv'
        )
    except Exception as e:
        logger.error(f"CSV export error: {e}")
        flash('Error exporting books.', 'error')
        return redirect(url_for('reports'))

@app.route('/export/borrowers')
def export_borrowers_csv():
    """Export borrowing records to CSV"""
    try:
        with db() as c:
            borrowers_data = c.execute('''
                SELECT br.id, b.title, br.name, br.email, br.borrow_date, 
                       br.due_date, br.returned, br.return_date, br.fine
                FROM borrowers br
                JOIN books b ON br.book_id=b.id
                ORDER BY br.borrow_date DESC
            ''').fetchall()
        
        output = io.StringIO()
        writer = csv.writer(output)
        writer.writerow(['ID', 'Book Title', 'Borrower Name', 'Email', 'Borrow Date', 
                        'Due Date', 'Returned', 'Return Date', 'Fine (₹)'])
        
        for record in borrowers_data:
            writer.writerow(record)
        
        output.seek(0)
        return send_file(
            io.BytesIO(output.getvalue().encode('utf-8')),
            mimetype='text/csv',
            as_attachment=True,
            download_name=f'borrowers_export_{date.today().isoformat()}.csv'
        )
    except Exception as e:
        logger.error(f"CSV export error: {e}")
        flash('Error exporting borrowers.', 'error')
        return redirect(url_for('reports'))

# ┌─ Routes - Search & Misc ─────────────────────────────────────────────────┐
@app.route('/api/search')
def api_search():
    """Quick search API"""
    try:
        query = sanitize_string(request.args.get('q', ''), 100)
        if len(query) < 2:
            return jsonify([])
        
        with db() as c:
            results = c.execute('''
                SELECT id, title, author, genre, available 
                FROM books 
                WHERE title LIKE ? OR author LIKE ? 
                LIMIT 8
            ''', (f'%{query}%', f'%{query}%')).fetchall()
        
        return jsonify([dict(r) for r in results])
    except Exception as e:
        logger.error(f"Search API error: {e}")
        return jsonify([])

@app.route('/success')
def success():
    """Success page after book issue"""
    return render_template('success.html',
        name=sanitize_string(request.args.get('name', 'Borrower'), 100),
        title=sanitize_string(request.args.get('title', 'the book'), 200),
        due=request.args.get('due', ''))

# ┌─ Error Handlers ─────────────────────────────────────────────────────────┐
@app.errorhandler(404)
def not_found(e):
    """Handle 404 errors"""
    logger.warning(f"404 error: {request.url}")
    return render_template('error.html', error='Page not found'), 404

@app.errorhandler(500)
def server_error(e):
    """Handle 500 errors"""
    logger.error(f"500 error: {e}")
    return render_template('error.html', error='Server error'), 500

# ┌─ Application Initialization ─────────────────────────────────────────────┐
if __name__ == '__main__':
    try:
        init_db()
        print("✓ LibraTrack Pro v2.1 - Starting server...\n")
        app.run(debug=True, host='127.0.0.1', port=5000)
    except Exception as e:
        print(f"✗ Fatal error: {e}")
        logger.error(f"Application startup failed: {e}")
