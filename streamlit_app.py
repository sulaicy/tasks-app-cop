# streamlit_app.py
import streamlit as st
import os
from dotenv import load_dotenv
from models import get_engine, get_session, User, Group, Task, TaskInstance
from werkzeug.security import generate_password_hash, check_password_hash
from datetime import date, datetime
import pandas as pd
import plotly.express as px

load_dotenv()
DB_URL = os.getenv('DATABASE_URL', 'sqlite:///task_tracker.db')
engine = get_engine(DB_URL)
session = get_session(engine)

st.set_page_config(page_title="Task Tracker", layout="wide")

# --- Helpers ---
def get_user_by_email(email):
    return session.query(User).filter_by(email=email).first()

def create_admin_if_none():
    admin = session.query(User).filter_by(role='admin').first()
    if not admin:
        # إنشاء آدمن افتراضي للمبتدئين
        if not get_user_by_email('admin@example.com'):
            u = User(name='Admin', email='admin@example.com',
                     password_hash=generate_password_hash('admin123'), role='admin')
            session.add(u); session.commit()
            st.info("Admin created: admin@example.com / admin123")

def login(email, password):
    u = get_user_by_email(email)
    if not u: return None
    if check_password_hash(u.password_hash, password):
        return u
    return None

def require_login():
    if 'user_id' not in st.session_state:
        st.session_state['page'] = 'login'

def compute_points(completed_value, points_per_unit):
    return completed_value * (points_per_unit or 1.0)

# --- Init ---
create_admin_if_none()
if 'page' not in st.session_state:
    st.session_state['page'] = 'login'

# --- Navigation ---
if st.session_state['page'] == 'login':
    st.title("تسجيل الدخول")
    with st.form("login_form"):
        email = st.text_input("البريد الإلكتروني")
        password = st.text_input("كلمة المرور", type="password")
        submitted = st.form_submit_button("دخول")
    if submitted:
        user = login(email.strip(), password)
        if user:
            st.session_state['user_id'] = user.id
            st.session_state['user_name'] = user.name
            st.session_state['user_role'] = user.role
            st.session_state['page'] = 'dashboard'
            st.experimental_rerun()
        else:
            st.error("بيانات غير صحيحة")

# --- Authenticated pages ---
if 'user_id' in st.session_state and st.session_state.get('page') != 'login':
    user = session.query(User).get(st.session_state['user_id'])
    st.sidebar.write(f"**{user.name}** ({user.role})")
    if st.sidebar.button("تسجيل خروج"):
        for k in list(st.session_state.keys()):
            del st.session_state[k]
        st.session_state['page'] = 'login'
        st.experimental_rerun()

    menu = st.sidebar.radio("القائمة", ["Dashboard", "مهام اليوم", "المهام", "المستخدمون" if user.role=='admin' else None])
    if menu == "Dashboard":
        st.header("لوحة التقدم")
        # جمع بيانات نقاط لكل مستخدم لليوم
        today = date.today()
        q = session.query(TaskInstance).filter_by(date=today).all()
        rows = []
        for i in q:
            u = session.query(User).get(i.completed_by) if i.completed_by else None
            task = session.query(Task).get(i.task_id)
            rows.append({
                "user": u.name if u else "غير مكتمل",
                "task": task.title if task else f"#{i.task_id}",
                "points": i.points_awarded or 0
            })
        df = pd.DataFrame(rows)
        if df.empty:
            st.info("لا توجد بيانات لليوم")
        else:
            agg = df.groupby('user', as_index=False).sum()
            fig = px.bar(agg, x='user', y='points', title='نقاط كل مستخدم اليوم')
            st.plotly_chart(fig, use_container_width=True)

    elif menu == "مهام اليوم":
        st.header("مهام اليوم")
        today = date.today()
        # عرض كل TaskInstance لليوم؛ إن لم توجد يمكن إنشاءها من المهام
        instances = session.query(TaskInstance).filter_by(date=today).all()
        if not instances:
            st.info("لا توجد TaskInstance لليوم. يمكنك إنشاءها من المهام.")
        for inst in instances:
            task = session.query(Task).get(inst.task_id)
            st.subheader(task.title if task else f"مهمة #{inst.task_id}")
            st.write(task.description if task and task.description else "")
            col1, col2 = st.columns([2,1])
            with col1:
                st.write(f"الهدف: {inst.target_value} {task.unit_name if task else ''}")
                val = st.number_input("قيمة الإنجاز", value=float(inst.completed_value or 0.0), key=f"val_{inst.id}")
            with col2:
                if st.button("تسجيل إنجاز", key=f"btn_{inst.id}"):
                    points = compute_points(val, task.points_per_unit if task else 1.0)
                    inst.completed_value = val
                    inst.completed_by = user.id
                    inst.status = 'done'
                    inst.points_awarded = points
                    session.commit()
                    st.success(f"تم تسجيل {points} نقطة")
                    st.experimental_rerun()

    elif menu == "المهام":
        st.header("إدارة المهام")
        st.subheader("إنشاء مهمة جديدة")
        with st.form("create_task"):
            title = st.text_input("عنوان المهمة")
            desc = st.text_area("وصف")
            is_global = st.checkbox("مهمة للجميع")
            groups = session.query(Group).all()
            users = session.query(User).all()
            assigned_to = st.selectbox("تعيين لمستخدم (اختياري)", options=[None]+[u.id for u in users], format_func=lambda x: "—" if x is None else session.query(User).get(x).name)
            assigned_group = st.selectbox("تعيين لمجموعة (اختياري)", options=[None]+[g.id for g in groups], format_func=lambda x: "—" if x is None else session.query(Group).get(x).name)
            points_per_unit = st.number_input("نقاط لكل وحدة (مثلاً لكل صفحة)", value=1.0)
            unit_name = st.text_input("اسم الوحدة (مثلاً: صفحة)")
            submitted = st.form_submit_button("إنشاء")
        if submitted:
            t = Task(title=title, description=desc, is_global=is_global,
                     assigned_to=assigned_to, assigned_group_id=assigned_group,
                     points_per_unit=points_per_unit, unit_name=unit_name, created_by=user.id)
            session.add(t); session.commit()
            st.success("تم إنشاء المهمة")
        st.subheader("قائمة المهام")
        tasks = session.query(Task).all()
        for t in tasks:
            st.write(f"- **{t.title}** — {t.unit_name or ''} — نقاط/وحدة: {t.points_per_unit}")

        st.subheader("إنشاء TaskInstance لليوم من مهمة")
        task_options = session.query(Task).all()
        sel = st.selectbox("اختر مهمة", options=[None]+[t.id for t in task_options], format_func=lambda x: "—" if x is None else session.query(Task).get(x).title)
        if sel:
            if st.button("إنشاء مثيل لليوم"):
                today = date.today()
                exists = session.query(TaskInstance).filter_by(task_id=sel, date=today).first()
                if exists:
                    st.warning("موجود بالفعل لليوم")
                else:
                    ti = TaskInstance(task_id=sel, date=today, target_value=0.0)
                    session.add(ti); session.commit()
                    st.success("تم الإنشاء")
                    st.experimental_rerun()

    elif menu == "المستخدمون" and user.role == 'admin':
        st.header("إدارة المستخدمين والمجموعات")
        st.subheader("إنشاء مجموعة")
        with st.form("create_group"):
            gname = st.text_input("اسم المجموعة")
            if st.form_submit_button("إنشاء مجموعة"):
                grp = Group(name=gname)
                session.add(grp); session.commit()
                st.success("تم إنشاء المجموعة")
        st.subheader("إنشاء مستخدم")
        with st.form("create_user"):
            uname = st.text_input("الاسم")
            uemail = st.text_input("البريد")
            upass = st.text_input("كلمة المرور", type="password")
            groups = session.query(Group).all()
            gid = st.selectbox("اختر مجموعة (اختياري)", options=[None]+[g.id for g in groups], format_func=lambda x: "—" if x is None else session.query(Group).get(x).name)
            if st.form_submit_button("إنشاء مستخدم"):
                if get_user_by_email(uemail):
                    st.error("البريد موجود")
                else:
                    u = User(name=uname, email=uemail, password_hash=generate_password_hash(upass), role='user', group_id=gid)
                    session.add(u); session.commit()
                    st.success("تم إنشاء المستخدم")
        st.subheader("قائمة المستخدمين")
        users = session.query(User).all()
        for u in users:
            st.write(f"- {u.name} ({u.email}) — {u.role} — مجموعة: {u.group.name if u.group else '-'}")