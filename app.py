from flask import Flask, jsonify, request, send_from_directory
import sqlite3
import json
import os
from datetime import datetime, timedelta
import secrets
import hashlib
from functools import wraps

app = Flask(__name__, static_folder='static')
app.secret_key = os.environ.get('SECRET_KEY', secrets.token_hex(32))

# ─── CORS ────────────────────────────────────────────────────────────────────
@app.after_request
def after_request(response):
    origin = request.headers.get('Origin', '*')
    response.headers['Access-Control-Allow-Origin'] = origin
    response.headers['Access-Control-Allow-Headers'] = 'Content-Type,Authorization'
    response.headers['Access-Control-Allow-Methods'] = 'GET,POST,PUT,DELETE,OPTIONS'
    response.headers['Access-Control-Allow-Credentials'] = 'true'
    if request.method == 'OPTIONS':
        response.status_code = 200
    return response

# ─── HELPERS ─────────────────────────────────────────────────────────────────
def hash_password(password):
    return hashlib.sha256(password.encode()).hexdigest()

def get_db():
    db_path = os.environ.get('DB_PATH', 'quiz_elite.db')
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row          # access columns by name
    conn.execute("PRAGMA foreign_keys = ON")
    return conn

# ─── DB INIT ─────────────────────────────────────────────────────────────────
def init_db():
    conn = get_db()
    c = conn.cursor()

    c.executescript('''
        CREATE TABLE IF NOT EXISTS users (
            id           INTEGER PRIMARY KEY AUTOINCREMENT,
            username     TEXT UNIQUE NOT NULL,
            password     TEXT NOT NULL,
            email        TEXT,
            full_name    TEXT,
            role         TEXT DEFAULT 'student',
            school       TEXT,
            student_level TEXT,
            created_by   INTEGER,
            is_active    BOOLEAN DEFAULT 1,
            created_at   TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        );

        CREATE TABLE IF NOT EXISTS competitions (
            id               INTEGER PRIMARY KEY AUTOINCREMENT,
            title            TEXT NOT NULL,
            description      TEXT,
            subject          TEXT,
            difficulty       TEXT,
            student_level    TEXT,
            question_count   INTEGER,
            competition_type TEXT DEFAULT 'practice',
            start_time       TIMESTAMP,
            end_time         TIMESTAMP,
            duration_minutes INTEGER,
            rules            TEXT,
            status           TEXT DEFAULT 'upcoming',
            created_by       INTEGER,
            created_at       TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        );

        CREATE TABLE IF NOT EXISTS questions (
            id              INTEGER PRIMARY KEY AUTOINCREMENT,
            question_number INTEGER,
            question_text   TEXT NOT NULL,
            option_a        TEXT,
            option_b        TEXT,
            option_c        TEXT,
            option_d        TEXT,
            correct_answer  TEXT,
            subject         TEXT,
            difficulty      TEXT,
            student_level   TEXT,
            points          INTEGER DEFAULT 10,
            created_by      INTEGER,
            created_at      TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        );

        CREATE TABLE IF NOT EXISTS competition_participants (
            id             INTEGER PRIMARY KEY AUTOINCREMENT,
            competition_id INTEGER,
            user_id        INTEGER,
            assigned_by    INTEGER,
            assigned_at    TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            UNIQUE(competition_id, user_id),
            FOREIGN KEY (competition_id) REFERENCES competitions(id),
            FOREIGN KEY (user_id)        REFERENCES users(id)
        );

        CREATE TABLE IF NOT EXISTS competition_questions (
            id             INTEGER PRIMARY KEY AUTOINCREMENT,
            competition_id INTEGER,
            question_id    INTEGER,
            question_order INTEGER,
            FOREIGN KEY (competition_id) REFERENCES competitions(id),
            FOREIGN KEY (question_id)   REFERENCES questions(id)
        );

        CREATE TABLE IF NOT EXISTS answer_submissions (
            id             INTEGER PRIMARY KEY AUTOINCREMENT,
            competition_id INTEGER,
            question_id    INTEGER,
            user_id        INTEGER,
            answer         TEXT,
            is_correct     BOOLEAN,
            is_bonus       BOOLEAN DEFAULT 0,
            points_awarded INTEGER,
            answered_at    TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (competition_id) REFERENCES competitions(id),
            FOREIGN KEY (question_id)   REFERENCES questions(id),
            FOREIGN KEY (user_id)       REFERENCES users(id)
        );

        CREATE TABLE IF NOT EXISTS scoreboard (
            id             INTEGER PRIMARY KEY AUTOINCREMENT,
            competition_id INTEGER,
            user_id        INTEGER,
            total_points   INTEGER DEFAULT 0,
            correct_answers INTEGER DEFAULT 0,
            bonus_points   INTEGER DEFAULT 0,
            updated_at     TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            UNIQUE(competition_id, user_id),
            FOREIGN KEY (competition_id) REFERENCES competitions(id),
            FOREIGN KEY (user_id)       REFERENCES users(id)
        );
    ''')

    # Seed data only if no admin exists
    c.execute("SELECT COUNT(*) FROM users WHERE role = 'admin'")
    if c.fetchone()[0] == 0:
        admin_pass = hash_password('admin123')
        c.execute("""INSERT INTO users (username, password, email, full_name, role)
                     VALUES (?, ?, ?, ?, ?)""",
                  ('admin', admin_pass, 'admin@quizmaster.com', 'System Administrator', 'admin'))

        student_pass = hash_password('student123')
        students = [
            ('student1', student_pass, 'student1@school.com', 'Amina Yusuf',      'student', 'Government Secondary School Dutse',   'Secondary School'),
            ('student2', student_pass, 'student2@school.com', 'Ibrahim Hassan',   'student', 'Federal Government College Kazaure',   'Secondary School'),
            ('student3', student_pass, 'student3@school.com', 'Fatima Abubakar', 'student', 'Unity Secondary School Hadejia',       'Secondary School'),
            ('student4', student_pass, 'student4@school.com', 'Musa Sani',        'student', 'Government Secondary School Dutse',   'Secondary School'),
            ('student5', student_pass, 'student5@school.com', 'Hauwa Mohammed',   'student', 'Federal Government College Kazaure',   'Primary School'),
            ('student6', student_pass, 'student6@school.com', 'Aliyu Bello',      'student', 'Unity Secondary School Hadejia',       'Primary School'),
        ]
        c.executemany("""INSERT INTO users (username, password, email, full_name, role, school, student_level)
                         VALUES (?, ?, ?, ?, ?, ?, ?)""", students)

        questions = [
            (1,  'What is the powerhouse of the cell?',                    'Nucleus','Mitochondria','Ribosome','Chloroplast',    'B','Biology',     'Easy',  'Secondary School', 10),
            (2,  'Which blood type is the universal donor?',               'A','B','AB','O',                                    'D','Biology',     'Medium','Secondary School', 15),
            (3,  'By which process do plants make their food?',            'Respiration','Photosynthesis','Digestion','Absorption','B','Biology',   'Easy',  'Secondary School', 10),
            (4,  'How many chambers does the human heart have?',           '2','3','4','5',                                     'C','Biology',     'Easy',  'Primary School',   10),
            (5,  'What is the largest organ in the human body?',           'Liver','Brain','Skin','Heart',                      'C','Biology',     'Medium','Secondary School', 15),
            (6,  'What is the square root of 144?',                        '10','11','12','13',                                 'C','Mathematics', 'Easy',  'Secondary School', 10),
            (7,  'What is 15% of 200?',                                    '20','25','30','35',                                 'C','Mathematics', 'Medium','Secondary School', 15),
            (8,  'What is the value of π (pi) to 2 decimal places?',      '3.12','3.14','3.16','3.18',                         'B','Mathematics', 'Easy',  'Secondary School', 10),
            (9,  'If x + 5 = 12, what is x?',                             '5','6','7','8',                                    'C','Mathematics', 'Easy',  'Primary School',   10),
            (10, 'What is 7 × 8?',                                         '54','56','58','60',                                'B','Mathematics', 'Easy',  'Primary School',   10),
            (11, 'What is the speed of light in vacuum?',                  '3×10⁸ m/s','2×10⁸ m/s','4×10⁸ m/s','5×10⁸ m/s', 'A','Physics',     'Medium','Secondary School', 15),
            (12, 'What is the SI unit of force?',                          'Joule','Newton','Watt','Pascal',                    'B','Physics',     'Easy',  'Secondary School', 10),
            (13, 'What force keeps planets in orbit around the sun?',      'Magnetic','Gravitational','Electric','Nuclear',     'B','Physics',     'Easy',  'Secondary School', 10),
            (14, 'What is the chemical symbol for Gold?',                  'Go','Gd','Au','Ag',                                'C','Chemistry',   'Easy',  'Secondary School', 10),
            (15, 'What is the atomic number of Carbon?',                   '4','6','8','12',                                   'B','Chemistry',   'Easy',  'Secondary School', 10),
            (16, 'What is H₂O commonly known as?',                        'Hydrogen Peroxide','Water','Hydrochloric Acid','Hydroxide','B','Chemistry','Easy','Primary School',  10),
            (17, 'What is the plural of "child"?',                         'Childs','Childes','Children','Childrens',           'C','English',     'Easy',  'Primary School',   10),
            (18, 'Which of these is a verb?',                              'Beautiful','Run','Happiness','Blue',                'B','English',     'Easy',  'Secondary School', 10),
            (19, 'What is a noun?',                                        'An action word','A naming word','A describing word','A connecting word','B','English','Easy','Primary School',10),
            (20, 'What punctuation mark ends a question?',                 'Period','Comma','Question mark','Exclamation mark', 'C','English',     'Easy',  'Primary School',   10),
            (21, 'What is the capital of Nigeria?',                        'Lagos','Abuja','Kano','Port Harcourt',              'B','Geography',   'Easy',  'Secondary School', 10),
            (22, 'Which is the largest ocean on Earth?',                   'Atlantic','Indian','Arctic','Pacific',              'D','Geography',   'Easy',  'Secondary School', 10),
            (23, 'How many continents are there?',                         '5','6','7','8',                                    'C','Geography',   'Easy',  'Primary School',   10),
            (24, 'What is the longest river in the world?',                'Amazon','Nile','Mississippi','Yangtze',             'B','Geography',   'Medium','Secondary School', 15),
        ]
        c.executemany("""INSERT INTO questions
                         (question_number, question_text, option_a, option_b, option_c, option_d,
                          correct_answer, subject, difficulty, student_level, points, created_by)
                         VALUES (?,?,?,?,?,?,?,?,?,?,?,1)""", questions)

        # Sample competition
        c.execute("""INSERT INTO competitions
                     (title, description, subject, difficulty, student_level, question_count,
                      competition_type, start_time, duration_minutes, status, created_by)
                     VALUES (?,?,?,?,?,?,?,?,?,?,?)""",
                  ('Inter-School Mathematics Quiz', 'Annual mathematics competition',
                   'Mathematics', 'Easy', 'Secondary School', 3, 'official',
                   (datetime.now() + timedelta(hours=2)).isoformat(), 30, 'upcoming', 1))
        comp_id = c.lastrowid

        c.execute("""SELECT id FROM questions
                     WHERE subject='Mathematics' AND difficulty='Easy'
                     AND student_level='Secondary School' LIMIT 3""")
        for idx, row in enumerate(c.fetchall()):
            c.execute("INSERT INTO competition_questions (competition_id, question_id, question_order) VALUES (?,?,?)",
                      (comp_id, row[0], idx + 1))

        c.execute("SELECT id FROM users WHERE role='student' AND student_level='Secondary School' LIMIT 3")
        for row in c.fetchall():
            c.execute("INSERT OR IGNORE INTO competition_participants (competition_id, user_id, assigned_by) VALUES (?,?,1)",
                      (comp_id, row[0]))

    conn.commit()
    conn.close()

# ─── STATIC / INDEX ──────────────────────────────────────────────────────────
@app.route('/')
def index():
    return send_from_directory('.', 'index.html')

@app.route('/static/<path:filename>')
def static_files(filename):
    return send_from_directory('static', filename)

# ─── AUTH ────────────────────────────────────────────────────────────────────
@app.route('/api/auth/login', methods=['POST', 'OPTIONS'])
def login():
    if request.method == 'OPTIONS':
        return jsonify({}), 200
    data = request.json or {}
    username = data.get('username', '').strip()
    password = data.get('password', '')

    conn = get_db()
    c = conn.cursor()
    c.execute('SELECT * FROM users WHERE username=? AND password=? AND is_active=1',
              (username, hash_password(password)))
    user = c.fetchone()
    conn.close()

    if user:
        return jsonify({
            'success': True,
            'user': {
                'id':            user['id'],
                'username':      user['username'],
                'email':         user['email'],
                'full_name':     user['full_name'],
                'role':          user['role'],
                'school':        user['school'],
                'student_level': user['student_level']
            },
            'token': secrets.token_hex(32)
        })
    return jsonify({'success': False, 'error': 'Invalid credentials'}), 401

# ─── ADMIN – USERS ───────────────────────────────────────────────────────────
@app.route('/api/admin/users', methods=['GET', 'POST', 'OPTIONS'])
def manage_users():
    if request.method == 'OPTIONS':
        return jsonify({}), 200

    conn = get_db()
    c = conn.cursor()

    if request.method == 'GET':
        c.execute('SELECT * FROM users ORDER BY created_at DESC')
        users = [dict(row) for row in c.fetchall()]
        # remove password from response
        for u in users:
            u.pop('password', None)
        conn.close()
        return jsonify(users)

    # POST – create user
    data = request.json or {}
    password = secrets.token_urlsafe(8)
    try:
        c.execute("""INSERT INTO users
                     (username, password, email, full_name, role, school, student_level, created_by)
                     VALUES (?,?,?,?,?,?,?,1)""",
                  (data['username'], hash_password(password),
                   data.get('email', ''), data.get('full_name', ''),
                   data.get('role', 'student'), data.get('school', ''),
                   data.get('student_level', '')))
        conn.commit()
        user_id = c.lastrowid
        conn.close()
        return jsonify({'success': True, 'user_id': user_id,
                        'username': data['username'], 'password': password})
    except Exception as e:
        conn.close()
        return jsonify({'success': False, 'error': str(e)}), 400

@app.route('/api/admin/users/<int:user_id>', methods=['PUT', 'DELETE', 'OPTIONS'])
def manage_user(user_id):
    if request.method == 'OPTIONS':
        return jsonify({}), 200

    conn = get_db()
    c = conn.cursor()

    if request.method == 'DELETE':
        c.execute('UPDATE users SET is_active=0 WHERE id=?', (user_id,))
        conn.commit()
        conn.close()
        return jsonify({'success': True})

    if request.method == 'PUT':
        data = request.json or {}
        fields = []
        values = []
        for key in ('email', 'full_name', 'school', 'student_level', 'is_active'):
            if key in data:
                fields.append(f'{key}=?')
                values.append(data[key])
        if fields:
            values.append(user_id)
            c.execute(f"UPDATE users SET {', '.join(fields)} WHERE id=?", values)
            conn.commit()
        conn.close()
        return jsonify({'success': True})

# ─── ADMIN – QUESTIONS ───────────────────────────────────────────────────────
@app.route('/api/admin/questions', methods=['GET', 'POST', 'OPTIONS'])
def manage_questions():
    if request.method == 'OPTIONS':
        return jsonify({}), 200

    conn = get_db()
    c = conn.cursor()

    if request.method == 'GET':
        subject       = request.args.get('subject')
        difficulty    = request.args.get('difficulty')
        student_level = request.args.get('student_level')

        query  = 'SELECT * FROM questions WHERE 1=1'
        params = []
        if subject:       query += ' AND subject=?';       params.append(subject)
        if difficulty:    query += ' AND difficulty=?';    params.append(difficulty)
        if student_level: query += ' AND student_level=?'; params.append(student_level)
        query += ' ORDER BY question_number'

        c.execute(query, params)
        questions = [dict(row) for row in c.fetchall()]
        conn.close()
        return jsonify(questions)

    # POST
    data = request.json or {}
    try:
        c.execute("""INSERT INTO questions
                     (question_number, question_text, option_a, option_b, option_c, option_d,
                      correct_answer, subject, difficulty, student_level, points, created_by)
                     VALUES (?,?,?,?,?,?,?,?,?,?,?,1)""",
                  (data.get('question_number', 0), data['question_text'],
                   data['option_a'], data['option_b'], data['option_c'], data['option_d'],
                   data['correct_answer'], data['subject'], data['difficulty'],
                   data['student_level'], data.get('points', 10)))
        conn.commit()
        q_id = c.lastrowid
        conn.close()
        return jsonify({'success': True, 'question_id': q_id})
    except Exception as e:
        conn.close()
        return jsonify({'success': False, 'error': str(e)}), 400

@app.route('/api/admin/questions/<int:question_id>', methods=['DELETE', 'OPTIONS'])
def delete_question(question_id):
    if request.method == 'OPTIONS':
        return jsonify({}), 200
    conn = get_db()
    conn.execute('DELETE FROM questions WHERE id=?', (question_id,))
    conn.commit()
    conn.close()
    return jsonify({'success': True})

# ─── ADMIN – COMPETITIONS ────────────────────────────────────────────────────
@app.route('/api/admin/competitions', methods=['GET', 'POST', 'OPTIONS'])
def manage_competitions():
    if request.method == 'OPTIONS':
        return jsonify({}), 200

    conn = get_db()
    c = conn.cursor()

    if request.method == 'GET':
        c.execute('''SELECT c.*,
                     COUNT(DISTINCT cp.user_id)   AS participant_count,
                     COUNT(DISTINCT cq.question_id) AS assigned_question_count
                     FROM competitions c
                     LEFT JOIN competition_participants cp ON c.id = cp.competition_id
                     LEFT JOIN competition_questions   cq ON c.id = cq.competition_id
                     GROUP BY c.id
                     ORDER BY c.created_at DESC''')
        competitions = [dict(row) for row in c.fetchall()]
        conn.close()
        return jsonify(competitions)

    # POST – create competition
    data = request.json or {}
    try:
        c.execute("""INSERT INTO competitions
                     (title, description, subject, difficulty, student_level, question_count,
                      competition_type, start_time, duration_minutes, rules, status, created_by)
                     VALUES (?,?,?,?,?,?,?,?,?,?,?,1)""",
                  (data['title'], data.get('description', ''), data['subject'],
                   data['difficulty'], data['student_level'], data['question_count'],
                   data.get('competition_type', 'official'), data.get('start_time'),
                   data['duration_minutes'], json.dumps(data.get('rules', {})), 'upcoming'))
        comp_id = c.lastrowid

        c.execute("""SELECT id FROM questions
                     WHERE subject=? AND difficulty=? AND student_level=?
                     ORDER BY RANDOM() LIMIT ?""",
                  (data['subject'], data['difficulty'], data['student_level'], data['question_count']))
        qs = c.fetchall()
        for idx, q in enumerate(qs):
            c.execute("INSERT INTO competition_questions (competition_id, question_id, question_order) VALUES (?,?,?)",
                      (comp_id, q['id'], idx + 1))

        conn.commit()
        conn.close()
        return jsonify({'success': True, 'competition_id': comp_id, 'questions_assigned': len(qs)})
    except Exception as e:
        conn.close()
        return jsonify({'success': False, 'error': str(e)}), 400

@app.route('/api/admin/competitions/<int:comp_id>/assign-participants', methods=['POST', 'OPTIONS'])
def assign_participants(comp_id):
    if request.method == 'OPTIONS':
        return jsonify({}), 200
    data     = request.json or {}
    user_ids = data.get('user_ids', [])

    conn = get_db()
    c    = conn.cursor()
    try:
        for uid in user_ids:
            c.execute("""INSERT OR IGNORE INTO competition_participants
                         (competition_id, user_id, assigned_by) VALUES (?,?,1)""",
                      (comp_id, uid))
        conn.commit()
        conn.close()
        return jsonify({'success': True, 'assigned_count': len(user_ids)})
    except Exception as e:
        conn.close()
        return jsonify({'success': False, 'error': str(e)}), 400

@app.route('/api/admin/competitions/<int:comp_id>/participants', methods=['GET', 'OPTIONS'])
def get_competition_participants(comp_id):
    if request.method == 'OPTIONS':
        return jsonify({}), 200
    conn = get_db()
    c    = conn.cursor()
    c.execute('''SELECT u.id, u.username, u.full_name, u.school, u.student_level
                 FROM users u
                 JOIN competition_participants cp ON u.id = cp.user_id
                 WHERE cp.competition_id=?''', (comp_id,))
    participants = [dict(row) for row in c.fetchall()]
    conn.close()
    return jsonify(participants)

@app.route('/api/admin/students', methods=['GET', 'OPTIONS'])
def get_students():
    if request.method == 'OPTIONS':
        return jsonify({}), 200
    conn = get_db()
    c    = conn.cursor()
    c.execute("SELECT id, username, full_name, school, student_level FROM users WHERE role='student' AND is_active=1")
    students = [dict(row) for row in c.fetchall()]
    conn.close()
    return jsonify(students)

@app.route('/api/admin/competitions/<int:comp_id>/start', methods=['POST', 'OPTIONS'])
def start_competition(comp_id):
    if request.method == 'OPTIONS':
        return jsonify({}), 200
    conn = get_db()
    c    = conn.cursor()
    c.execute("UPDATE competitions SET status='live', start_time=? WHERE id=?",
              (datetime.now().isoformat(), comp_id))
    # initialise scoreboard rows for every participant
    c.execute("SELECT user_id FROM competition_participants WHERE competition_id=?", (comp_id,))
    for row in c.fetchall():
        c.execute("INSERT OR IGNORE INTO scoreboard (competition_id, user_id, total_points, correct_answers) VALUES (?,?,0,0)",
                  (comp_id, row['user_id']))
    conn.commit()
    conn.close()
    return jsonify({'success': True})

@app.route('/api/admin/competitions/<int:comp_id>/end', methods=['POST', 'OPTIONS'])
def end_competition(comp_id):
    if request.method == 'OPTIONS':
        return jsonify({}), 200
    conn = get_db()
    conn.execute("UPDATE competitions SET status='completed', end_time=? WHERE id=?",
                 (datetime.now().isoformat(), comp_id))
    conn.commit()
    conn.close()
    return jsonify({'success': True})

# ─── STUDENT ROUTES ──────────────────────────────────────────────────────────
@app.route('/api/student/competitions', methods=['GET', 'OPTIONS'])
def get_student_competitions():
    """Return all competitions the student is enrolled in."""
    if request.method == 'OPTIONS':
        return jsonify({}), 200

    user_id = request.args.get('user_id')
    if not user_id:
        return jsonify({'error': 'user_id required'}), 400

    conn = get_db()
    c    = conn.cursor()
    c.execute('''SELECT c.id, c.title, c.description, c.subject, c.difficulty,
                 c.student_level, c.duration_minutes, c.status, c.start_time,
                 c.competition_type,
                 COUNT(DISTINCT cq.question_id) AS question_count,
                 COALESCE(s.total_points, 0)     AS my_score,
                 COALESCE(s.correct_answers, 0)  AS my_correct
                 FROM competitions c
                 JOIN competition_participants cp ON c.id = cp.competition_id
                 LEFT JOIN competition_questions cq ON c.id = cq.competition_id
                 LEFT JOIN scoreboard s ON c.id = s.competition_id AND s.user_id = ?
                 WHERE cp.user_id = ?
                 GROUP BY c.id
                 ORDER BY c.start_time DESC''', (user_id, user_id))
    competitions = [dict(row) for row in c.fetchall()]
    conn.close()
    return jsonify(competitions)

@app.route('/api/competition/<int:comp_id>/questions', methods=['GET', 'OPTIONS'])
def get_competition_questions(comp_id):
    """Return questions for a competition (answers hidden for students)."""
    if request.method == 'OPTIONS':
        return jsonify({}), 200

    # BUG FIX: original code exposed correct_answer – now hidden for student-facing calls
    conn = get_db()
    c    = conn.cursor()

    # Verify competition is live or allow admin preview
    c.execute("SELECT status FROM competitions WHERE id=?", (comp_id,))
    comp = c.fetchone()
    if not comp:
        conn.close()
        return jsonify({'error': 'Competition not found'}), 404

    c.execute('''SELECT q.id, q.question_number, q.question_text,
                 q.option_a, q.option_b, q.option_c, q.option_d, q.points, q.subject
                 FROM questions q
                 JOIN competition_questions cq ON q.id = cq.question_id
                 WHERE cq.competition_id = ?
                 ORDER BY cq.question_order''', (comp_id,))

    questions = []
    for row in c.fetchall():
        questions.append({
            'id':              row['id'],
            'question_number': row['question_number'],
            'question_text':   row['question_text'],
            'options': {
                'A': row['option_a'],
                'B': row['option_b'],
                'C': row['option_c'],
                'D': row['option_d'],
            },
            'points':  row['points'],
            'subject': row['subject'],
        })
    conn.close()
    return jsonify({'questions': questions, 'status': comp['status']})

@app.route('/api/competition/<int:comp_id>/submit', methods=['POST', 'OPTIONS'])
def submit_competition(comp_id):
    if request.method == 'OPTIONS':
        return jsonify({}), 200

    data    = request.json or {}
    user_id = data.get('user_id')
    answers = data.get('answers', {})   # {question_id: selected_option}

    if not user_id:
        return jsonify({'error': 'user_id required'}), 400

    conn = get_db()
    c    = conn.cursor()

    # Verify participant
    c.execute("SELECT id FROM competition_participants WHERE competition_id=? AND user_id=?",
              (comp_id, user_id))
    if not c.fetchone():
        conn.close()
        return jsonify({'error': 'Not enrolled in this competition'}), 403

    score         = 0
    correct_count = 0

    for q_id, answer in answers.items():
        c.execute('SELECT correct_answer, points FROM questions WHERE id=?', (q_id,))
        row = c.fetchone()
        if not row:
            continue
        is_correct = (answer == row['correct_answer'])
        pts        = row['points'] if is_correct else 0
        if is_correct:
            score         += pts
            correct_count += 1

        # Upsert answer
        c.execute("""INSERT OR REPLACE INTO answer_submissions
                     (competition_id, question_id, user_id, answer, is_correct, points_awarded)
                     VALUES (?,?,?,?,?,?)""",
                  (comp_id, q_id, user_id, answer, is_correct, pts))

    # Upsert scoreboard
    c.execute("""INSERT OR REPLACE INTO scoreboard
                 (competition_id, user_id, total_points, correct_answers, updated_at)
                 VALUES (?,?,?,?,?)""",
              (comp_id, user_id, score, correct_count, datetime.now().isoformat()))

    conn.commit()
    conn.close()
    return jsonify({'success': True, 'score': score, 'correct_count': correct_count})

@app.route('/api/competition/<int:comp_id>/scoreboard', methods=['GET', 'OPTIONS'])
def get_scoreboard(comp_id):
    if request.method == 'OPTIONS':
        return jsonify({}), 200
    conn = get_db()
    c    = conn.cursor()
    c.execute('''SELECT s.user_id, u.full_name, u.school,
                 s.total_points, s.correct_answers
                 FROM scoreboard s
                 JOIN users u ON s.user_id = u.id
                 WHERE s.competition_id=?
                 ORDER BY s.total_points DESC''', (comp_id,))
    scoreboard = [dict(row) for row in c.fetchall()]
    conn.close()
    return jsonify(scoreboard)

@app.route('/api/student/results', methods=['GET', 'OPTIONS'])
def get_student_results():
    """Return a student's full result history across all competitions."""
    if request.method == 'OPTIONS':
        return jsonify({}), 200

    user_id = request.args.get('user_id')
    if not user_id:
        return jsonify({'error': 'user_id required'}), 400

    conn = get_db()
    c    = conn.cursor()
    c.execute('''SELECT s.competition_id, c.title, c.subject, c.difficulty,
                 s.total_points, s.correct_answers, s.updated_at,
                 COUNT(cq.question_id) AS total_questions
                 FROM scoreboard s
                 JOIN competitions c ON s.competition_id = c.id
                 LEFT JOIN competition_questions cq ON c.id = cq.competition_id
                 WHERE s.user_id = ?
                 GROUP BY s.competition_id
                 ORDER BY s.updated_at DESC''', (user_id,))
    results = [dict(row) for row in c.fetchall()]
    conn.close()
    return jsonify(results)

# ─── PRACTICE QUIZ ───────────────────────────────────────────────────────────
@app.route('/api/practice/questions', methods=['GET', 'OPTIONS'])
def get_practice_questions():
    if request.method == 'OPTIONS':
        return jsonify({}), 200

    limit         = request.args.get('limit', 10, type=int)
    subject       = request.args.get('subject')
    student_level = request.args.get('student_level')

    conn   = get_db()
    c      = conn.cursor()
    query  = 'SELECT * FROM questions WHERE 1=1'
    params = []
    if subject:       query += ' AND subject=?';       params.append(subject)
    if student_level: query += ' AND student_level=?'; params.append(student_level)
    query += ' ORDER BY RANDOM() LIMIT ?'
    params.append(limit)

    c.execute(query, params)
    questions = []
    for row in c.fetchall():
        questions.append({
            'id':            row['id'],
            'question_text': row['question_text'],
            'options': {
                'A': row['option_a'],
                'B': row['option_b'],
                'C': row['option_c'],
                'D': row['option_d'],
            },
            'subject': row['subject'],
            'points':  row['points'],
        })
    conn.close()
    return jsonify(questions)

@app.route('/api/practice/submit', methods=['POST', 'OPTIONS'])
def submit_practice():
    if request.method == 'OPTIONS':
        return jsonify({}), 200

    data    = request.json or {}
    answers = data.get('answers', {})

    conn  = get_db()
    c     = conn.cursor()
    score = total = 0
    details = []

    for q_id, answer in answers.items():
        c.execute('SELECT question_text, correct_answer, points FROM questions WHERE id=?', (q_id,))
        row = c.fetchone()
        if row:
            is_correct = answer == row['correct_answer']
            total      += row['points']
            if is_correct:
                score += row['points']
            details.append({
                'question_id':     int(q_id),
                'question_text':   row['question_text'],
                'your_answer':     answer,
                'correct_answer':  row['correct_answer'],
                'is_correct':      is_correct,
                'points':          row['points'],
            })

    conn.close()
    return jsonify({
        'score':      score,
        'total':      total,
        'percentage': round((score / total * 100) if total > 0 else 0, 1),
        'details':    details,
    })

# ─── ANALYTICS ───────────────────────────────────────────────────────────────
@app.route('/api/analytics/dashboard', methods=['GET', 'OPTIONS'])
def get_analytics():
    if request.method == 'OPTIONS':
        return jsonify({}), 200

    conn = get_db()
    c    = conn.cursor()

    c.execute("SELECT COUNT(*) AS n FROM users WHERE role='student' AND is_active=1")
    total_students = c.fetchone()['n']

    c.execute("SELECT COUNT(*) AS n FROM competitions")
    total_competitions = c.fetchone()['n']

    c.execute("SELECT COUNT(*) AS n FROM questions")
    total_questions = c.fetchone()['n']

    c.execute("SELECT COUNT(*) AS n FROM competitions WHERE status='live'")
    active_competitions = c.fetchone()['n']

    c.execute("SELECT subject, COUNT(*) AS count FROM questions GROUP BY subject")
    subjects = [{'name': r['subject'], 'count': r['count']} for r in c.fetchall()]

    c.execute('''SELECT u.full_name AS student, c.title AS competition,
                 a.is_correct, a.points_awarded AS points, a.answered_at AS time
                 FROM answer_submissions a
                 JOIN users        u ON a.user_id        = u.id
                 JOIN competitions c ON a.competition_id = c.id
                 ORDER BY a.answered_at DESC LIMIT 10''')
    recent_activity = [dict(r) for r in c.fetchall()]

    c.execute('''SELECT u.full_name AS name, u.school,
                 SUM(s.total_points) AS total_points, COUNT(s.id) AS attempts
                 FROM scoreboard s
                 JOIN users u ON s.user_id = u.id
                 GROUP BY u.id
                 ORDER BY total_points DESC LIMIT 5''')
    top_performers = [dict(r) for r in c.fetchall()]

    c.execute('''SELECT q.subject,
                 COUNT(CASE WHEN a.is_correct=1 THEN 1 END) AS correct,
                 COUNT(*) AS total
                 FROM answer_submissions a
                 JOIN questions q ON a.question_id = q.id
                 GROUP BY q.subject''')
    subject_performance = []
    for r in c.fetchall():
        subject_performance.append({
            'subject':    r['subject'],
            'correct':    r['correct'],
            'total':      r['total'],
            'percentage': round((r['correct'] / r['total'] * 100) if r['total'] > 0 else 0, 1),
        })

    c.execute('''SELECT c.title, c.status,
                 COUNT(DISTINCT cp.user_id) AS participants,
                 COALESCE(AVG(s.total_points), 0) AS avg_score
                 FROM competitions c
                 LEFT JOIN competition_participants cp ON c.id = cp.competition_id
                 LEFT JOIN scoreboard               s  ON c.id = s.competition_id
                 GROUP BY c.id
                 ORDER BY c.created_at DESC LIMIT 5''')
    competition_stats = []
    for r in c.fetchall():
        competition_stats.append({
            'title':        r['title'],
            'status':       r['status'],
            'participants': r['participants'],
            'avg_score':    round(r['avg_score'], 1),
        })

    conn.close()
    return jsonify({
        'total_students':      total_students,
        'total_competitions':  total_competitions,
        'total_questions':     total_questions,
        'active_competitions': active_competitions,
        'subjects':            subjects,
        'recent_activity':     recent_activity,
        'top_performers':      top_performers,
        'subject_performance': subject_performance,
        'competition_stats':   competition_stats,
    })

# ─── ENTRY POINT ─────────────────────────────────────────────────────────────
if __name__ == '__main__':
    init_db()
    port  = int(os.environ.get('PORT', 5000))
    debug = os.environ.get('FLASK_DEBUG', 'true').lower() == 'true'
    app.run(host='0.0.0.0', port=port, debug=debug, threaded=True)
