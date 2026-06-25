# QuizMaster Elite – Jigawa State Edition

A full-stack quiz/competition platform for schools, built with Flask + React (no build step needed).

---

## 🚀 Running in GitHub Codespaces (Recommended)

### Step 1 – Create the Repository

1. Go to [github.com](https://github.com) and click **New repository**
2. Name it `quizmaster-elite`, set it to **Public** (or Private)
3. Click **Create repository**

### Step 2 – Upload the Files

Upload all these files keeping the folder structure:
```
quizmaster-elite/
├── .devcontainer/
│   └── devcontainer.json
├── app.py
├── index.html
├── requirements.txt
└── README.md
```

You can drag-and-drop files in the GitHub web UI, or use:
```bash
git clone https://github.com/YOUR_USERNAME/quizmaster-elite.git
cd quizmaster-elite
# copy your files here
git add .
git commit -m "Initial commit"
git push
```

### Step 3 – Open a Codespace

1. On your repository page click the green **Code** button
2. Select the **Codespaces** tab
3. Click **Create codespace on main**
4. Wait ~60 seconds for the container to build and dependencies to install

### Step 4 – Start the App

In the Codespace terminal, run:
```bash
python app.py
```

You will see:
```
 * Running on all addresses (0.0.0.0)
 * Running on http://127.0.0.1:5000
```

Codespaces will **automatically pop up a browser** pointing at your forwarded port.

> **Important:** The frontend auto-detects Codespaces and rewrites the API URL,
> so no manual configuration is needed.

---

## 💻 Running Locally

```bash
# 1. Clone / download the project
cd quizmaster-elite

# 2. Create a virtual environment (optional but recommended)
python -m venv venv
source venv/bin/activate        # Windows: venv\Scripts\activate

# 3. Install dependencies
pip install -r requirements.txt

# 4. Run
python app.py
```

Open your browser at: **http://localhost:5000**

---

## 🔑 Default Login Credentials

| Role    | Username  | Password    |
|---------|-----------|-------------|
| Admin   | admin     | admin123    |
| Student | student1  | student123  |
| Student | student2  | student123  |
| Student | student3  | student123  |

> Change passwords in production by updating the database directly.

---

## ✅ Features

### Admin
- **Dashboard** – stats overview, top performers, quick actions
- **Student Management** – create/remove students, see generated passwords
- **Question Bank** – add/delete questions with subject, difficulty, level filters
- **Competition Management**
  - Create competitions (questions auto-assigned from bank)
  - Assign students to competitions
  - Start / End competitions
  - View live scoreboard
- **Analytics** – subject performance, competition stats, recent activity feed

### Student
- **Dashboard** – personal stats, live competition alerts
- **My Competitions** – see all enrolled competitions, join live ones
- **Live Quiz** – full timed quiz runner with countdown, question navigator, submit
- **Practice Quiz** – untimed practice with instant correct/wrong feedback
- **My Results** – full history with accuracy bars

---

## 🛠 Project Structure

```
app.py          Flask backend – all API routes
index.html      Single-file React frontend (no build step)
requirements.txt  Python dependencies
.devcontainer/  GitHub Codespaces configuration
quiz_elite.db   SQLite database (auto-created on first run)
```

---

## 🐛 Bug Fixes Applied vs Original Code

| Bug | Fix |
|-----|-----|
| Students couldn't join live quizzes | Added `/api/student/competitions` and `/api/competition/:id/questions` returning correct data; enrollment check on submit |
| Student dashboard showed "Coming Soon" | Fully implemented all 4 student pages |
| No quiz runner for students | Built complete timed QuizRunner component with countdown timer |
| No practice quiz implementation | Built full PracticeQuiz with subject filters and detailed feedback |
| No results page | Built StudentResults page pulling from new `/api/student/results` endpoint |
| API URL hardcoded to localhost | Auto-detects Codespaces and rewrites URL |
| CORS OPTIONS requests failed | Added explicit OPTIONS handler to all routes |
| `row[index]` brittle column access | Switched to `conn.row_factory = sqlite3.Row` (access by name) |
| Correct answers exposed to students | `/competition/:id/questions` now hides `correct_answer` |
| Admin PUT user had no implementation | Added full PUT handler for user updates |
| Scoreboard modal never populated | Fixed data flow; scoreboard now works in admin view |
| Quick action buttons did nothing | Buttons now navigate to correct admin pages |
| `secret_key` regenerated on restart | Now reads from `SECRET_KEY` env var with fallback |

---

## ⚙️ Environment Variables (optional)

| Variable      | Default       | Description |
|---------------|---------------|-------------|
| `PORT`        | `5000`        | Port to listen on |
| `SECRET_KEY`  | random        | Flask secret key (set for stable sessions) |
| `DB_PATH`     | `quiz_elite.db` | Path to SQLite database file |
| `FLASK_DEBUG` | `true`        | Set to `false` in production |
