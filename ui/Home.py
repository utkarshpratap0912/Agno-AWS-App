import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


import asyncio
import uuid
import psycopg2
import nest_asyncio
import streamlit as st
from agno.tools.streamlit.components import check_password
from ui.css import CUSTOM_CSS
from ui.utils import about_agno, footer

nest_asyncio.apply()

# ----------------------------------
# 🔐 Optional Inline Authentication
# ----------------------------------

ENABLE_AUTH = True  # Toggle to False to bypass auth

DB_URL = "postgresql://postgres:123456@localhost:5433/mydb"
USERS_TABLE = "users"

def get_connection():
    return psycopg2.connect(DB_URL)

def ensure_users_table():
    conn = get_connection()
    cur = conn.cursor()
    cur.execute(f"""
        CREATE TABLE IF NOT EXISTS {USERS_TABLE} (
            user_name TEXT PRIMARY KEY,
            tenant_id UUID NOT NULL
        );
    """)
    conn.commit()
    conn.close()

def get_user(username):
    conn = get_connection()
    cur = conn.cursor()
    cur.execute(f"SELECT tenant_id FROM {USERS_TABLE} WHERE user_name = %s", (username,))
    row = cur.fetchone()
    conn.close()
    return row[0] if row else None

def create_user(username):
    tenant_id = str(uuid.uuid4())
    conn = get_connection()
    cur = conn.cursor()
    cur.execute(f"INSERT INTO {USERS_TABLE} (user_name, tenant_id) VALUES (%s, %s)", (username, tenant_id))
    conn.commit()
    conn.close()
    return tenant_id

# Run auth logic if enabled
if ENABLE_AUTH:
    ensure_users_table()

    if "phantom_token" not in st.session_state:
        st.title("🔐 Login or Register")

        auth_mode = st.radio("Choose an option", ["New User", "Existing User"])
        username = st.text_input("Enter your username")

        if auth_mode == "Existing User":
            if st.button("Login"):
                tenant_id = get_user(username)
                if tenant_id:
                    st.session_state["phantom_token"] = f"{tenant_id}:{username}"
                    st.session_state["user_name"] = username
                    st.success("✅ Logged in successfully!")
                    st.rerun()

                else:
                    st.error("❌ No such user found.")

        elif auth_mode == "New User":
            if st.button("Start"):
                if get_user(username):
                    st.warning("User already exists. Try logging in instead.")
                else:
                    tenant_id = create_user(username)
                    st.session_state["phantom_token"] = f"{tenant_id}:{username}"
                    st.session_state["user_name"] = username
                    st.success("✅ User created and logged in!")
                    st.rerun()

        st.stop()  # Stop rendering until user logs in

# ----------------------------------
# ✅ Main App Starts Here
# ----------------------------------

st.set_page_config(
    page_title="Agno Agents",
    page_icon=":orange_heart:",
    layout="wide",
)
st.markdown(CUSTOM_CSS, unsafe_allow_html=True)

# Display user info in sidebar (if authenticated)
if "phantom_token" in st.session_state:
    tenant_id, user_id = st.session_state["phantom_token"].split(":")
    st.sidebar.write(f"👤 User: {user_id}")
    st.sidebar.write(f"🏢 Tenant: {tenant_id}")

async def header():
    st.markdown("<h1 class='heading'>Agno Agents</h1>", unsafe_allow_html=True)
    st.markdown(
        "<p class='subheading'>Welcome to the Agno Agents platform! We've provided some sample agents to get you started.</p>",
        unsafe_allow_html=True,
    )

async def body():
    st.markdown("### Available Agents")

    col1, col2 = st.columns(2)
    with col1:
        st.markdown(
            """
            <div style="padding: 20px; border-radius: 10px; border: 1px solid #ddd; margin-bottom: 20px;">
                <h3>Sage</h3>
                <p>A knowledge agent that uses Agentic RAG to deliver context-rich answers from a knowledge base.</p>
                <p>Perfect for exploring your own knowledge base.</p>
            </div>
            """,
            unsafe_allow_html=True,
        )
        if st.button("Launch Sage", key="sage_button"):
            st.switch_page("pages/1_Sage.py")

    with col2:
        st.markdown(
            """
            <div style="padding: 20px; border-radius: 10px; border: 1px solid #ddd; margin-bottom: 20px;">
                <h3>Scholar</h3>
                <p>A research agent that uses DuckDuckGo (and optionally Exa) to deliver in-depth answers about any topic.</p>
                <p>Perfect for exploring general knowledge from the web.</p>
            </div>
            """,
            unsafe_allow_html=True,
        )
        if st.button("Launch Scholar", key="scholar_button"):
            st.switch_page("pages/2_Scholar.py")

async def main():
    await header()
    await body()
    await footer()
    await about_agno()

if __name__ == "__main__":
    if check_password():
        asyncio.run(main())
