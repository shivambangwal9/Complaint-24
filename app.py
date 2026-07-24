import os
import sqlite3
import random
from datetime import datetime, timedelta
# pyrefly: ignore [missing-import]
from flask import Flask, jsonify, request, send_from_directory
from flask_cors import CORS
import jwt
from functools import wraps
import uuid
from werkzeug.security import generate_password_hash, check_password_hash

try:
    # pyrefly: ignore [missing-import]
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    pass

app = Flask(__name__, static_folder='.')
app.config['SECRET_KEY'] = os.environ.get('JWT_SECRET', 'fallback_super_secret_key_change_me')
app.config['UPLOAD_FOLDER'] = os.environ.get('UPLOAD_FOLDER', 'uploads')
os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)

# Allow all origins in development; lock down in production via CORS_ORIGINS env var
_cors_origins = os.environ.get('CORS_ORIGINS', '*')
CORS(app, origins=_cors_origins)

DB_PATH = os.environ.get("DB_PATH", "complain24.db")

def dict_factory(cursor, row):
    d = {}
    for idx, col in enumerate(cursor.description):
        d[col[0]] = row[idx]
    return d


def token_required(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        token = None
        if 'Authorization' in request.headers:
            auth_header = request.headers['Authorization']
            if auth_header.startswith('Bearer '):
                token = auth_header.split(' ')[1]
        
        if not token:
            return jsonify({'error': 'Token is missing!'}), 401
            
        try:
            data = jwt.decode(token, app.config['SECRET_KEY'], algorithms=['HS256'])
            current_user_id = data['user_id']
        except Exception as e:
            return jsonify({'error': 'Token is invalid!', 'details': str(e)}), 401
            
        return f(current_user_id, *args, **kwargs)
    return decorated

def get_db_connection():
    conn = sqlite3.connect(DB_PATH, check_same_thread=False)
    conn.row_factory = dict_factory
    return conn

def init_db():
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        # Users
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS users (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name VARCHAR(255),
                email VARCHAR(255) UNIQUE,
                password_hash VARCHAR(255),
                role VARCHAR(50),
                phone VARCHAR(50),
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        ''')
        # Departments
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS departments (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name VARCHAR(255),
                head_officer_id INT,
                contact_email VARCHAR(255),
                contact_phone VARCHAR(50)
            )
        ''')
        # Complaints (Legacy IDs were strings like CMP-1234, so id is VARCHAR)
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS complaints (
                id VARCHAR(50) PRIMARY KEY,
                user_id INT,
                title VARCHAR(255),
                description TEXT,
                category VARCHAR(100),
                priority VARCHAR(50),
                status VARCHAR(50),
                department VARCHAR(100),
                department_id INT,
                lat VARCHAR(50),
                lng VARCHAR(50),
                date VARCHAR(100),
                resolvedDate VARCHAR(100),
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        ''')
        # History
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS history (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                complaint_id VARCHAR(50),
                status_changed_to VARCHAR(50),
                remarks TEXT,
                changed_by_user_id INT,
                timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        ''')
        # Notices
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS notices (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                title VARCHAR(255),
                content TEXT,
                author_id INT,
                posted_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                is_active BOOLEAN DEFAULT TRUE
            )
        ''')
        # Contacts
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS contacts (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                department_id INT,
                contact_type VARCHAR(50),
                phone_number VARCHAR(50)
            )
        ''')
        # Payments
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS payments (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                complaint_id VARCHAR(50),
                user_id INT,
                amount DECIMAL(10,2),
                status VARCHAR(50),
                transaction_id VARCHAR(255),
                timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        ''')
        # Feedback
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS feedback (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                complaint_id VARCHAR(50),
                user_id INT,
                rating INT,
                comments TEXT,
                submitted_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        ''')
        # OTPs
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS otps (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                contact_info VARCHAR(255),
                otp_code VARCHAR(10),
                expires_at DATETIME,
                verified BOOLEAN DEFAULT FALSE,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        ''')
        # Seed default admin user using INSERT OR IGNORE to prevent duplicate entry errors
        password_hash = generate_password_hash("admin123")
        cursor.execute('''
            INSERT OR IGNORE INTO users (name, email, password_hash, role, phone)
            VALUES (?, ?, ?, ?, ?)
        ''', ("Super Admin", "admin@complain24.com", password_hash, "admin", "9999999999"))
        
        conn.commit()
        cursor.close()
        conn.close()
        
        # Migrate: Add karma_points to users if not present
        conn2 = get_db_connection()
        cur2 = conn2.cursor()
        try:
            cur2.execute("ALTER TABLE users ADD COLUMN karma_points INTEGER DEFAULT 0")
            conn2.commit()
            print("Migration: Added karma_points column to users.")
        except Exception:
            pass  # Column already exists
        # Migrate: Add photo_url to complaints if not present
        try:
            cur2.execute("ALTER TABLE complaints ADD COLUMN photo_url TEXT")
            conn2.commit()
        except Exception:
            pass
        cur2.close()
        conn2.close()
        print("Database schema successfully verified/created in SQLite.")
    except Exception as e:
        print(f"Failed to initialize database: {e}")

init_db()


@app.route('/')
def index():
    return send_from_directory('.', 'index.html')

@app.route('/<path:path>')
def serve_static(path):
    return send_from_directory('.', path)

@app.route('/api/complaints', methods=['GET'])
def get_complaints():
    user_id = request.args.get('user_id')
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        if user_id:
            cursor.execute("SELECT * FROM complaints WHERE user_id = ? ORDER BY date DESC", (user_id,))
        else:
            cursor.execute("SELECT * FROM complaints ORDER BY date DESC")
        complaints = cursor.fetchall()
        cursor.close()
        conn.close()
        return jsonify(complaints)
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route('/api/complaints', methods=['POST'])
def submit_complaint():
    data = request.json
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute('''
            INSERT INTO complaints (id, user_id, title, description, category, priority, status, department, date, resolvedDate, lat, lng, photo_url)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        ''', (
            data.get('id'),
            data.get('user_id'),
            data.get('title'),
            data.get('description'),
            data.get('category'),
            data.get('priority'),
            data.get('status', 'Pending'),
            data.get('department'),
            data.get('date'),
            data.get('resolvedDate', None),
            data.get('lat'),
            data.get('lng'),
            data.get('photo_url')
        ))
        conn.commit()
        cursor.close()
        conn.close()
        return jsonify({"success": True, "id": data.get('id')})
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route('/api/complaints/<id>', methods=['PUT'])
@token_required
def update_complaint(current_user_id, id):
    data = request.json
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute('''
            UPDATE complaints 
            SET status = ?, resolvedDate = ?
            WHERE id = ?
        ''', (
            data.get('status'),
            data.get('resolvedDate', None),
            id
        ))
        # Also insert history log
        cursor.execute('''
            INSERT INTO history (complaint_id, status_changed_to, remarks)
            VALUES (?, ?, ?)
        ''', (id, data.get('status'), data.get('remarks', '')))
        
        # Send Notification
        cursor.execute("SELECT u.email, u.phone, u.name, u.id FROM users u JOIN complaints c ON u.id = c.user_id WHERE c.id = ?", (id,))
        user = cursor.fetchone()
        if user and data.get('status') in ['In Progress', 'Resolved']:
            msg = f"Hello {user['name']}, your complaint ({id}) status has been updated to: {data.get('status')}."
            contact = user['phone'] or user['email']
            if contact:
                if '@' in contact:
                    print(f"\n{'='*40}\n[MOCK NOTIFICATION EMAIL]\nTo: {contact}\n{msg}\n{'='*40}\n")
                else:
                    print(f"\n{'='*40}\n[MOCK NOTIFICATION SMS]\nTo: {contact}\n{msg}\n{'='*40}\n")
        
        # Award Karma Points on Resolution
        if data.get('status') == 'Resolved' and user:
            cursor.execute("UPDATE users SET karma_points = COALESCE(karma_points, 0) + 10 WHERE id = ?", (user['id'],))
            print(f"[KARMA] Awarded +10 karma points to user {user['name']} (ID: {user['id']})")
                    
        conn.commit()
        cursor.close()
        conn.close()
        return jsonify({"success": True})
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@app.route('/uploads/<filename>')
def serve_uploads(filename):
    return send_from_directory(app.config['UPLOAD_FOLDER'], filename)

@app.route('/api/upload', methods=['POST'])
@token_required
def upload_file(current_user_id):
    if 'photo' not in request.files:
        return jsonify({'error': 'No photo part'}), 400
    file = request.files['photo']
    if file.filename == '':
        return jsonify({'error': 'No selected file'}), 400
    if file:
        ext = file.filename.rsplit('.', 1)[1].lower() if '.' in file.filename else 'jpg'
        filename = f"{uuid.uuid4().hex}.{ext}"
        filepath = os.path.join(app.config['UPLOAD_FOLDER'], filename)
        file.save(filepath)
        return jsonify({'success': True, 'photo_url': f'/uploads/{filename}'})
    return jsonify({'error': 'Upload failed'}), 500

@app.route('/api/feedback', methods=['POST'])
def submit_feedback():
    data = request.json
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute('''
            INSERT INTO feedback (complaint_id, user_id, rating, comments)
            VALUES (?, ?, ?, ?)
        ''', (
            data.get('complaint_id'),
            data.get('user_id'),
            data.get('rating'),
            data.get('comments')
        ))
        conn.commit()
        cursor.close()
        conn.close()
        return jsonify({"success": True})
    except Exception as e:
        return jsonify({"error": str(e)}), 500

def send_sms(to_number, otp_code):
    # Try GetOTP if API key is provided
    GETOTP_KEY = os.environ.get("GETOTP_API_KEY")
    GETOTP_TEMPLATE = os.environ.get("GETOTP_TEMPLATE_ID", "087dd7e2-43d0-448d-afef-3adee7f35ee2")
    GETOTP_SENDER = os.environ.get("GETOTP_SENDER", "OTP Dev")
    
    if GETOTP_KEY:
        try:
            import requests
            clean_number = ''.join(c for c in to_number if c.isdigit())
            if len(clean_number) == 10:
                clean_number = "91" + clean_number
            url = "https://api.otp.dev/v1/verifications"
            headers = {
                "X-OTP-Key": GETOTP_KEY,
                "Content-Type": "application/json",
                "Accept": "application/json"
            }
            payload = {
                "data": {
                    "channel": "sms",
                    "phone": clean_number,
                    "sender": GETOTP_SENDER,
                    "template": GETOTP_TEMPLATE,
                    "code": otp_code
                }
            }
            res = requests.post(url, json=payload, headers=headers)
            if res.status_code in [200, 201]:
                print(f"SMS successfully sent via GetOTP to {clean_number}")
                return True
            else:
                print(f"GetOTP API returned error ({res.status_code}): {res.text}")
        except Exception as e:
            print(f"Failed to send SMS via GetOTP: {e}")
    # Mock fallback if no API credentials
    print(f"\n{'='*40}\n[MOCK SMS] (NO API CREDENTIALS FOUND)\nTo: {to_number}\nYour Complain 24 OTP is: {otp_code}\n{'='*40}\n")
    return False

def send_email(to_email, otp_code):
    SMTP_SERVER = os.environ.get("SMTP_SERVER", "smtp.gmail.com")
    SMTP_PORT = int(os.environ.get("SMTP_PORT", "587"))
    SMTP_USER = os.environ.get("SMTP_USER")
    SMTP_PASS = os.environ.get("SMTP_PASS")
    
    if SMTP_USER and SMTP_PASS:
        try:
            import smtplib
            from email.mime.text import MIMEText
            from email.mime.multipart import MIMEMultipart
            
            msg = MIMEMultipart()
            msg['From'] = SMTP_USER
            msg['To'] = to_email
            msg['Subject'] = "Your Complain 24 OTP Verification Code"
            
            body = f"Your Complain 24 One-Time Password (OTP) is: {otp_code}.\n\nThis code is valid for 5 minutes."
            msg.attach(MIMEText(body, 'plain'))
            
            server = smtplib.SMTP(SMTP_SERVER, SMTP_PORT)
            server.starttls()
            server.login(SMTP_USER, SMTP_PASS)
            server.sendmail(SMTP_USER, to_email, msg.as_string())
            server.quit()
            print(f"Email successfully sent via SMTP to {to_email}")
            return True
        except Exception as e:
            print(f"Failed to send email via SMTP: {e}")
            
    print(f"\n{'='*40}\n[MOCK EMAIL] (NO SMTP CREDENTIALS FOUND)\nTo: {to_email}\nYour Complain 24 OTP is: {otp_code}\n{'='*40}\n")
    return False

@app.route('/api/user/<int:user_id>', methods=['GET'])
def get_user_profile(user_id):
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT id, name, email, role, karma_points FROM users WHERE id = ?", (user_id,))
        user = cursor.fetchone()
        cursor.close()
        conn.close()
        if not user:
            return jsonify({"error": "User not found"}), 404
        return jsonify(user)
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route('/api/auth/request-otp', methods=['POST'])
def request_otp():
    data = request.json
    contact_info = data.get('contact_info')
    if not contact_info:
        return jsonify({"error": "Phone number or email is required"}), 400
        
    otp_code = str(random.randint(100000, 999999))
    expires_at = datetime.now() + timedelta(minutes=5)
    
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        # Check if user already exists
        cursor.execute("SELECT id FROM users WHERE phone = ? OR email = ?", (contact_info, contact_info))
        if cursor.fetchone():
            cursor.close()
            conn.close()
            return jsonify({"error": "Account already exists with this phone or email. Please log in."}), 400

        # Delete any previous unverified OTPs for this contact
        cursor.execute("DELETE FROM otps WHERE contact_info = ?", (contact_info,))
        cursor.execute('''
            INSERT INTO otps (contact_info, otp_code, expires_at)
            VALUES (?, ?, ?)
        ''', (contact_info, otp_code, expires_at))
        conn.commit()
        cursor.close()
        conn.close()
        
        # Route dispatching based on contact type
        if '@' in contact_info:
            send_email(contact_info, otp_code)
        else:
            send_sms(contact_info, otp_code)
        
        return jsonify({"success": True, "message": "OTP sent successfully"})
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route('/api/auth/verify-otp', methods=['POST'])
def verify_otp():
    data = request.json
    contact_info = data.get('contact_info')
    otp_code = data.get('otp_code')
    
    if not contact_info or not otp_code:
        return jsonify({"error": "Contact info and OTP are required"}), 400
        
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        # Verify OTP
        cursor.execute('''
            SELECT * FROM otps 
            WHERE contact_info = ? AND otp_code = ? AND verified = 0
        ''', (contact_info, otp_code))
        otp_record = cursor.fetchone()
        
        if not otp_record:
            cursor.close()
            conn.close()
            return jsonify({"error": "Invalid or expired OTP"}), 400
            
        expires_at_val = otp_record['expires_at']
        if isinstance(expires_at_val, str):
            try:
                expires_at_dt = datetime.strptime(expires_at_val.split('.')[0], "%Y-%m-%d %H:%M:%S")
            except Exception:
                expires_at_dt = datetime.fromisoformat(expires_at_val)
        else:
            expires_at_dt = expires_at_val

        if expires_at_dt < datetime.now():
            cursor.close()
            conn.close()
            return jsonify({"error": "OTP has expired"}), 400
            
        # Mark verified
        cursor.execute("UPDATE otps SET verified = 1 WHERE id = ?", (otp_record['id'],))
        
        # Check if user exists, if not, create user
        cursor.execute("SELECT * FROM users WHERE phone = ? OR email = ?", (contact_info, contact_info))
        user = cursor.fetchone()
        
        if not user:
            name = data.get('name', 'Citizen')
            password = data.get('password')
            role = data.get('role', 'citizen')
            if role not in ['citizen', 'admin']:
                role = 'citizen'
            if not password:
                cursor.close()
                conn.close()
                return jsonify({"error": "Password is required for registration"}), 400
            password_hash = generate_password_hash(password)
            
            email_val = contact_info if '@' in contact_info else None
            phone_val = contact_info if '@' not in contact_info else None
            
            # Register new user with password and dynamic role
            cursor.execute('''
                INSERT INTO users (name, email, password_hash, role, phone) 
                VALUES (?, ?, ?, ?, ?)
            ''', (name, email_val, password_hash, role, phone_val))
            user_id = cursor.lastrowid
            cursor.execute("SELECT * FROM users WHERE id = ?", (user_id,))
            user = cursor.fetchone()
            
        conn.commit()
        cursor.close()
        conn.close()
        
        if user and 'password_hash' in user:
            del user['password_hash']
            
        import datetime
        token = jwt.encode({
            'user_id': user['id'],
            'role': user['role'],
            'exp': datetime.datetime.utcnow() + datetime.timedelta(days=7)
        }, app.config['SECRET_KEY'], algorithm='HS256')
            
        return jsonify({"success": True, "user": user, "token": token})
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route('/api/auth/login', methods=['POST'])
def login():
    data = request.json
    contact_info = data.get('contact_info')
    password = data.get('password')
    
    if not contact_info or not password:
        return jsonify({"error": "Email/Phone and password are required"}), 400
        
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM users WHERE email = ? OR phone = ?", (contact_info, contact_info))
        user = cursor.fetchone()
        cursor.close()
        conn.close()
        
        if not user:
            return jsonify({"error": "Invalid email/phone or password"}), 401
            
        # Verify password
        if not user['password_hash'] or not check_password_hash(user['password_hash'], password):
            return jsonify({"error": "Invalid email/phone or password"}), 401
            
        if 'password_hash' in user:
            del user['password_hash']
            
        import datetime
        token = jwt.encode({
            'user_id': user['id'],
            'role': user['role'],
            'exp': datetime.datetime.utcnow() + datetime.timedelta(days=7)
        }, app.config['SECRET_KEY'], algorithm='HS256')
            
        return jsonify({"success": True, "user": user, "token": token})
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route('/api/auth/admin-register', methods=['POST'])
def admin_register():
    data = request.json
    name = data.get('name')
    email = data.get('email')
    phone = data.get('phone')
    password = data.get('password')
    
    if not name or not email or not phone or not password:
        return jsonify({"error": "Name, email, phone, and password are required"}), 400
        
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        # Check duplicate email
        cursor.execute("SELECT id FROM users WHERE email = ?", (email,))
        if cursor.fetchone():
            cursor.close()
            conn.close()
            return jsonify({"error": "A user with this email already exists"}), 400
            
        # Check duplicate phone
        cursor.execute("SELECT id FROM users WHERE phone = ?", (phone,))
        if cursor.fetchone():
            cursor.close()
            conn.close()
            return jsonify({"error": "A user with this phone number already exists"}), 400
            
        # Create hashed password and insert
        password_hash = generate_password_hash(password)
        cursor.execute('''
            INSERT INTO users (name, email, password_hash, role, phone)
            VALUES (?, ?, ?, ?, ?)
        ''', (name, email, password_hash, 'admin', phone))
        user_id = cursor.lastrowid
        
        cursor.execute("SELECT * FROM users WHERE id = ?", (user_id,))
        user = cursor.fetchone()
        
        conn.commit()
        cursor.close()
        conn.close()
        
        if user and 'password_hash' in user:
            del user['password_hash']
            
        import datetime
        token = jwt.encode({
            'user_id': user['id'],
            'role': user['role'],
            'exp': datetime.datetime.utcnow() + datetime.timedelta(days=7)
        }, app.config['SECRET_KEY'], algorithm='HS256')
            
        return jsonify({"success": True, "user": user, "token": token})
    except Exception as e:
        return jsonify({"error": str(e)}), 500

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5000))
    debug = os.environ.get('FLASK_DEBUG', 'false').lower() == 'true'
    app.run(host='0.0.0.0', port=port, debug=debug)
