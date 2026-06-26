from fastapi import FastAPI, Request, Form
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.templating import Jinja2Templates
from fastapi.staticfiles import StaticFiles
import psycopg2
from psycopg2.extras import RealDictCursor
from datetime import datetime, timedelta, timezone
import os
import re

app = FastAPI()
app.mount("/static", StaticFiles(directory="static"), name="static")

templates = Jinja2Templates(directory="templates")

DATABASE_URL = os.getenv("DATABASE_URL")
VN_TZ = timezone(timedelta(hours=7))


def now_vietnam():
    return datetime.now(VN_TZ)


def get_conn():
    return psycopg2.connect(DATABASE_URL)


def init_db():
    conn = get_conn()
    cursor = conn.cursor()

    cursor.execute("""
    CREATE TABLE IF NOT EXISTS survey (
        id SERIAL PRIMARY KEY,
        student_id TEXT UNIQUE NOT NULL,
        full_name TEXT NOT NULL,
        fire_score INTEGER NOT NULL,
        theft_score INTEGER NOT NULL,
        camera_score INTEGER NOT NULL,
        remote_score INTEGER NOT NULL,
        false_alarm_score INTEGER NOT NULL DEFAULT 5,
        created_at TEXT NOT NULL
    )
    """)

    conn.commit()
    cursor.close()
    conn.close()


init_db()


@app.get("/", response_class=HTMLResponse)
def home(request: Request):
    conn = get_conn()
    cursor = conn.cursor()

    today = now_vietnam().strftime("%Y-%m-%d")

    cursor.execute("""
    SELECT COUNT(*)
    FROM survey
    WHERE LEFT(created_at, 10) = %s
    """, (today,))

    total_today = cursor.fetchone()[0]

    cursor.close()
    conn.close()

    return templates.TemplateResponse(
        request=request,
        name="index.html",
        context={"total_today": total_today}
    )


@app.get("/check-student")
def check_student(student_id: str):
    student_id = student_id.strip().upper()

    if not re.fullmatch(r"[A-Z]{2}\d{6}", student_id):
        return {
            "valid": False,
            "exists": False,
            "message": "MSSV phải gồm 2 chữ cái và 6 chữ số. Ví dụ: CE181688"
        }

    conn = get_conn()
    cursor = conn.cursor()

    cursor.execute(
        "SELECT 1 FROM survey WHERE student_id = %s",
        (student_id,)
    )

    exists = cursor.fetchone() is not None

    cursor.close()
    conn.close()

    if exists:
        return {
            "valid": True,
            "exists": True,
            "message": "MSSV này đã tham gia khảo sát"
        }

    return {
        "valid": True,
        "exists": False,
        "message": "MSSV hợp lệ"
    }


@app.post("/submit")
def submit(
    student_id: str = Form(...),
    full_name: str = Form(...),
    fire_score: int = Form(...),
    theft_score: int = Form(...),
    camera_score: int = Form(...),
    remote_score: int = Form(...),
    false_alarm_score: int = Form(...)
):
    student_id = student_id.strip().upper()
    full_name = full_name.strip()

    if not re.fullmatch(r"[A-Z]{2}\d{6}", student_id):
        return RedirectResponse(url="/", status_code=303)

    if len(full_name) < 2:
        return RedirectResponse(url="/", status_code=303)

    conn = get_conn()
    cursor = conn.cursor()

    try:
        cursor.execute("""
        INSERT INTO survey (
            student_id,
            full_name,
            fire_score,
            theft_score,
            camera_score,
            remote_score,
            false_alarm_score,
            created_at
        )
        VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
        """, (
            student_id,
            full_name,
            fire_score,
            theft_score,
            camera_score,
            remote_score,
            false_alarm_score,
            now_vietnam().strftime("%Y-%m-%d %H:%M:%S")
        ))

        conn.commit()

    except psycopg2.errors.UniqueViolation:
        conn.rollback()
        cursor.close()
        conn.close()
        return RedirectResponse(url="/?duplicate=1", status_code=303)

    cursor.close()
    conn.close()

    return RedirectResponse(url="/thanks", status_code=303)


@app.get("/thanks", response_class=HTMLResponse)
def thanks(request: Request):
    return templates.TemplateResponse(
        request=request,
        name="thanks.html"
    )


@app.get("/admin", response_class=HTMLResponse)
def admin(request: Request):
    conn = get_conn()
    cursor = conn.cursor()

    cursor.execute("SELECT COUNT(*) FROM survey")
    total = cursor.fetchone()[0]

    cursor.execute("""
    SELECT
        ROUND(AVG(fire_score), 1),
        ROUND(AVG(theft_score), 1),
        ROUND(AVG(camera_score), 1),
        ROUND(AVG(remote_score), 1),
        ROUND(AVG(false_alarm_score), 1)
    FROM survey
    """)
    avg = cursor.fetchone()

    cursor.execute("""
    SELECT
        student_id,
        full_name,
        fire_score,
        theft_score,
        camera_score,
        remote_score,
        false_alarm_score,
        created_at
    FROM survey
    ORDER BY id DESC
    """)
    students = cursor.fetchall()

    cursor.close()
    conn.close()

    return templates.TemplateResponse(
        request=request,
        name="admin.html",
        context={
            "total": total,
            "avg": avg,
            "students": students
        }
    )