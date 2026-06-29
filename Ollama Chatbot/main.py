import json
import os
import secrets
import smtplib
import uuid
from datetime import datetime
from email.message import EmailMessage
from hashlib import pbkdf2_hmac
from pathlib import Path

import streamlit as st
from dotenv import load_dotenv
from langchain_core.output_parsers import StrOutputParser
from langchain_core.prompts import ChatPromptTemplate
from langchain_groq import ChatGroq



BASE_DIR = Path(__file__).resolve().parent
DATA_DIR = BASE_DIR / "data"
USERS_FILE = DATA_DIR / "users.json"
MODEL_OPTIONS = {
    "Llama 3.1 8B Instant": "llama-3.1-8b-instant",
    "Llama 3.3 70B Versatile": "llama-3.3-70b-versatile",
    "Gemma 2 9B": "gemma2-9b-it",
}
FREE_CHAT_LIMIT = 10
SUBSCRIPTION_PLANS = {
    "Plus - Rs 199/month": {
        "plan": "Plus",
        "chat_limit": 200,
        "description": "200 chats per month",
    },
    "Pro - Rs 499/month": {
        "plan": "Pro",
        "chat_limit": 1000,
        "description": "1,000 chats per month",
    },
    "Business - Rs 999/month": {
        "plan": "Business",
        "chat_limit": None,
        "description": "Unlimited chats",
    },
}

load_dotenv()
DATA_DIR.mkdir(exist_ok=True)
APP_ENV = os.getenv("APP_ENV", "development").lower()
IS_DEVELOPMENT = APP_ENV != "production"

if os.getenv("LANGCHAIN_API_KEY"):
    os.environ["LANGCHAIN_API_KEY"] = os.getenv("LANGCHAIN_API_KEY", "")
    os.environ["LANGCHAIN_TRACING_V2"] = "true"
    os.environ["LANGCHAIN_PROJECT"] = "Pamms AI Chatbot with Groq"


prompt = ChatPromptTemplate.from_messages(
    [
        (
            "system",
            (
                "You are a helpful, direct AI assistant. Answer the user's request clearly. "
                "Use uploaded file or photo names as context when provided. If the user asks "
                "for code, provide complete usable code instead of only explaining steps."
            ),
        ),
        (
            "user",
            (
                "Conversation context:\n{history}\n\n"
                "Additional context:\n{attachments}\n\n"
                "Question:\n{question}"
            ),
        ),
    ]
)


def normalize_email(email: str) -> str:
    return email.strip().lower()


def safe_user_key(email: str) -> str:
    return normalize_email(email).replace("@", "_at_").replace(".", "_")


def user_history_file(email: str) -> Path:
    return DATA_DIR / f"chat_history_{safe_user_key(email)}.json"


def load_json(path: Path, default):
    if not path.exists():
        return default
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError):
        return default


def save_json(path: Path, data) -> None:
    path.write_text(json.dumps(data, indent=2), encoding="utf-8")


def load_users() -> dict:
    return load_json(USERS_FILE, {})


def save_users(users: dict) -> None:
    save_json(USERS_FILE, users)


def hash_password(password: str, salt: str | None = None) -> tuple[str, str]:
    salt = salt or secrets.token_hex(16)
    digest = pbkdf2_hmac("sha256", password.encode("utf-8"), salt.encode("utf-8"), 260000)
    return salt, digest.hex()


def verify_password(password: str, salt: str, expected_hash: str) -> bool:
    _, actual_hash = hash_password(password, salt)
    return secrets.compare_digest(actual_hash, expected_hash)


def send_email(to_email: str, subject: str, body: str) -> tuple[bool, str]:
    smtp_host = os.getenv("SMTP_HOST", "")
    smtp_port = int(os.getenv("SMTP_PORT", "587"))
    smtp_user = os.getenv("SMTP_USER", "")
    smtp_password = os.getenv("SMTP_PASSWORD", "")
    from_email = os.getenv("SMTP_FROM_EMAIL", smtp_user)

    if not all([smtp_host, smtp_user, smtp_password, from_email]):
        return False, "SMTP is not configured. Add SMTP_HOST, SMTP_USER, SMTP_PASSWORD, and SMTP_FROM_EMAIL."

    message = EmailMessage()
    message["From"] = from_email
    message["To"] = to_email
    message["Subject"] = subject
    message.set_content(body)

    with smtplib.SMTP(smtp_host, smtp_port, timeout=20) as server:
        server.starttls()
        server.login(smtp_user, smtp_password)
        server.send_message(message)

    return True, "Email sent."


def send_verification_email(email: str, name: str, code: str) -> tuple[bool, str]:
    return send_email(
        email,
        "Verify your Pamms AI Chatbot account",
        (
            f"Hello {name},\n\n"
            "Welcome to Pamms AI Chatbot.\n\n"
            f"Your verification code is: {code}\n\n"
            "Enter this code in the app to activate your account."
        ),
    )


def send_signin_email(email: str, name: str) -> tuple[bool, str]:
    return send_email(
        email,
        "Successfully signed in to Pamms AI Chatbot",
        (
            f"Hello {name},\n\n"
            "You have successfully signed in to Pamms AI Chatbot.\n\n"
            "If this was not you, please change your password immediately."
        ),
    )


def send_password_reset_email(email: str, name: str, code: str) -> tuple[bool, str]:
    return send_email(
        email,
        "Reset your Pamms AI Chatbot password",
        (
            f"Hello {name},\n\n"
            "Use this password reset code for Pamms AI Chatbot:\n\n"
            f"{code}\n\n"
            "If you did not request this, you can ignore this email."
        ),
    )


def get_current_user(users: dict | None = None) -> dict:
    users = users or load_users()
    email = st.session_state.get("user_email", "")
    return users.get(email, {})


def update_current_user(updates: dict) -> None:
    email = st.session_state.get("user_email", "")
    if not email:
        return
    users = load_users()
    user = users.get(email, {})
    user.update(updates)
    users[email] = user
    save_users(users)


def get_chat_limit(user: dict) -> int | None:
    plan = user.get("plan", "Free")
    if plan == "Free":
        return FREE_CHAT_LIMIT
    for package in SUBSCRIPTION_PLANS.values():
        if package["plan"] == plan:
            return package["chat_limit"]
    return FREE_CHAT_LIMIT


def get_message_usage(user: dict) -> int:
    return int(user.get("messages_used", 0))


def get_remaining_chats(user: dict) -> int | None:
    chat_limit = get_chat_limit(user)
    if chat_limit is None:
        return None
    return max(chat_limit - get_message_usage(user), 0)


def can_send_message(user: dict) -> bool:
    remaining = get_remaining_chats(user)
    return remaining is None or remaining > 0


def increment_message_usage() -> None:
    user = get_current_user()
    update_current_user({"messages_used": get_message_usage(user) + 1})


def load_history() -> dict:
    email = st.session_state.get("user_email", "")
    if not email:
        return {}
    history_file = user_history_file(email)
    if not history_file.exists():
        return {}
    return load_json(history_file, {})


def save_history(conversations: dict) -> None:
    email = st.session_state.get("user_email", "")
    if email:
        save_json(user_history_file(email), conversations)


def new_conversation() -> str:
    conversation_id = str(uuid.uuid4())
    st.session_state.conversations[conversation_id] = {
        "title": "New chat",
        "created_at": datetime.now().isoformat(timespec="seconds"),
        "messages": [],
    }
    st.session_state.active_conversation_id = conversation_id
    save_history(st.session_state.conversations)
    return conversation_id


def clear_active_conversation() -> None:
    conversation = get_active_conversation()
    conversation["title"] = "New chat"
    conversation["messages"] = []
    conversation["cleared_at"] = datetime.now().isoformat(timespec="seconds")
    save_history(st.session_state.conversations)


def get_active_conversation() -> dict:
    if "conversations" not in st.session_state:
        st.session_state.conversations = load_history()
    if not st.session_state.conversations:
        new_conversation()
    if "active_conversation_id" not in st.session_state:
        st.session_state.active_conversation_id = next(iter(st.session_state.conversations))
    return st.session_state.conversations[st.session_state.active_conversation_id]


def summarize_history(messages: list[dict], limit: int = 8) -> str:
    recent_messages = messages[-limit:]
    if not recent_messages:
        return "No previous messages."
    return "\n".join(
        f"{message['role'].title()}: {message['content']}" for message in recent_messages
    )


def build_attachment_context(uploaded_files: list) -> str:
    if not uploaded_files:
        return "No files or photos uploaded."
    lines = []
    for uploaded_file in uploaded_files:
        size_kb = round(uploaded_file.size / 1024, 1)
        lines.append(f"- {uploaded_file.name} ({uploaded_file.type}, {size_kb} KB)")
    return "\n".join(lines)


def export_conversation_markdown(conversation: dict) -> str:
    title = conversation.get("title", "Pamms AI Chat")
    created_at = conversation.get("created_at", "")
    lines = [f"# {title}", ""]
    if created_at:
        lines.extend([f"Created: {created_at}", ""])

    for message in conversation.get("messages", []):
        role = "User" if message["role"] == "user" else "Pamms AI"
        lines.extend([f"## {role}", message["content"], ""])
        attachments = message.get("attachments") or []
        if attachments:
            lines.extend(["Attachments:", *[f"- {name}" for name in attachments], ""])

    return "\n".join(lines).strip() + "\n"


def generate_response(
    question: str,
    model_name: str,
    temperature: float,
    max_tokens: int,
    history: str,
    attachments: str,
) -> str:
    if not os.getenv("GROQ_API_KEY"):
        raise RuntimeError(
            "GROQ_API_KEY is missing. Add your Groq API key in the .env file."
        )

    llm = ChatGroq(
        model=model_name,
        temperature=temperature,
        max_tokens=max_tokens,
    )
    chain = prompt | llm | StrOutputParser()
    return chain.invoke(
        {
            "question": question,
            "history": history,
            "attachments": attachments,
        }
    )


def apply_styles() -> None:
    st.markdown(
        """
        <style>
        :root {
            --bg: #101010;
            --panel: #181818;
            --panel-soft: #242424;
            --text: #f3f3f3;
            --muted: #a7a7a7;
            --border: #363636;
            --accent: #ffffff;
        }

        .stApp {
            background: var(--bg);
            color: var(--text);
        }

        [data-testid="stSidebar"] {
            background: #151515;
            border-right: 1px solid var(--border);
            min-width: 18rem;
            overflow: visible;
        }

        [data-testid="stSidebar"] * {
            color: var(--text);
        }

        [data-testid="stSidebarContent"] {
            overflow-y: auto;
            padding-bottom: 0;
        }

        [data-testid="stSidebarContent"] > div {
            min-height: auto;
            overflow: visible;
        }

        section.main > div {
            padding-top: 0;
        }

        .main-title {
            backdrop-filter: blur(14px);
            background: rgba(16, 16, 16, 0.92);
            border-bottom: 1px solid var(--border);
            font-size: 1.5rem;
            font-weight: 700;
            left: 0;
            margin: 0 0 0.25rem;
            padding: 1rem 0 0.4rem;
            position: sticky;
            top: 0;
            z-index: 20;
        }

        .auth-shell {
            margin: 2.5rem auto 0;
            max-width: 460px;
        }

        .auth-title {
            font-size: 1.8rem;
            font-weight: 800;
            margin-bottom: 0.35rem;
            text-align: center;
        }

        .auth-subtitle {
            color: var(--muted);
            font-size: 0.94rem;
            margin-bottom: 1.25rem;
            text-align: center;
        }

        .subtle {
            color: var(--muted);
            font-size: 0.95rem;
            margin-bottom: 1.5rem;
        }

        [data-testid="stChatMessage"] {
            background: transparent;
        }

        [data-testid="stChatMessageContent"] {
            border-radius: 18px;
            line-height: 1.55;
            padding: 0.25rem 0;
        }

        [data-testid="stChatInput"] {
            background: #27272f;
            border: 1px solid #4a4a55;
            border-radius: 28px;
            box-shadow: 0 16px 40px rgba(0, 0, 0, 0.28);
            min-height: 74px;
            padding: 0.45rem 0.75rem;
            position: relative;
        }

        [data-testid="stChatInput"]:focus-within {
            border-color: #6b6b78;
            box-shadow: 0 16px 40px rgba(0, 0, 0, 0.28);
        }

        [data-testid="stChatInput"] textarea {
            caret-color: #d7d8e2;
            color: #d7d8e2 !important;
            font-size: 1.05rem;
            font-weight: 400;
            line-height: 1.45 !important;
            min-height: 58px;
            opacity: 1 !important;
            overflow-y: auto !important;
            padding-bottom: 0.75rem !important;
            padding-top: 1.05rem !important;
            -webkit-text-fill-color: #d7d8e2 !important;
        }

        [data-testid="stChatInput"] textarea *,
        [data-testid="stChatInput"] [contenteditable="true"],
        [data-testid="stChatInput"] [role="textbox"] {
            color: #d7d8e2 !important;
            line-height: 1.45 !important;
            opacity: 1 !important;
            padding-top: 0.15rem !important;
            -webkit-text-fill-color: #d7d8e2 !important;
        }

        [data-testid="stChatInput"] textarea::placeholder,
        [data-testid="stChatInput"] [contenteditable="true"]:empty::before,
        [data-testid="stChatInput"] [role="textbox"]:empty::before,
        input::placeholder,
        textarea::placeholder {
            color: #b9bbc8 !important;
            opacity: 1 !important;
        }

        [data-testid="stChatInput"] button {
            border-radius: 50%;
        }

        div[data-testid="stSelectbox"] label,
        div[data-testid="stSlider"] label {
            color: var(--muted);
        }

        .history-caption {
            color: var(--muted);
            font-size: 0.82rem;
            margin: 0.5rem 0;
        }

        .recents-title {
            color: var(--text);
            font-size: 1.12rem;
            font-weight: 800;
            margin: 0.85rem 0 0.45rem;
        }

        .sidebar-profile {
            align-items: center;
            background: #151515;
            border-top: 1px solid var(--border);
            display: flex;
            gap: 0.75rem;
            margin-top: 0.35rem;
            padding: 0.7rem 0 0.35rem;
            z-index: 10;
        }

        .avatar {
            align-items: center;
            background: #344050;
            border-radius: 50%;
            color: var(--text);
            display: inline-flex;
            font-size: 0.82rem;
            height: 34px;
            justify-content: center;
            width: 34px;
        }

        .profile-name {
            font-weight: 700;
            line-height: 1.1;
        }

        .profile-plan {
            color: var(--muted);
            font-size: 0.82rem;
        }

        .control-strip {
            align-items: center;
            color: var(--muted);
            display: flex;
            flex-wrap: wrap;
            gap: 0.75rem;
            margin: 1rem 0 0.4rem;
        }

        @media (max-width: 720px) {
            .main-title {
                font-size: 1.25rem;
            }
        }
        </style>
        """,
        unsafe_allow_html=True,
    )


def render_auth_screen() -> bool:
    users = load_users()
    if st.session_state.get("authenticated"):
        return True

    left, center, right = st.columns([1, 1.05, 1])
    with center:
        st.markdown(
            """
            <div class="auth-shell">
                <div class="auth-title">Pamms AI Chatbot</div>
                <div class="auth-subtitle">Login or create an account to continue with private chat history.</div>
            </div>
            """,
            unsafe_allow_html=True,
        )

        tab_login, tab_signup, tab_verify, tab_forgot = st.tabs(
            ["Login", "Sign up", "Verify", "Forgot password"]
        )

        with tab_login:
            with st.form("login-form"):
                email = normalize_email(st.text_input("Email", key="login-email"))
                password = st.text_input("Password", type="password", key="login-password")
                submitted = st.form_submit_button("Login", use_container_width=True)

            if submitted:
                user = users.get(email)
                if not user or not verify_password(password, user["salt"], user["password_hash"]):
                    st.error("Invalid email or password.")
                elif not user.get("is_verified"):
                    st.warning("Please verify your email before logging in.")
                    st.session_state.pending_email = email
                else:
                    st.session_state.authenticated = True
                    st.session_state.user_email = email
                    st.session_state.user_name = user["name"]
                    st.session_state.conversations = load_history()
                    send_signin_email(email, user["name"])
                    st.success("Signed in successfully.")
                    st.rerun()

        with tab_signup:
            with st.form("signup-form"):
                name = st.text_input("Full name", key="signup-name")
                email = normalize_email(st.text_input("Email", key="signup-email"))
                password = st.text_input("Password", type="password", key="signup-password")
                confirm_password = st.text_input("Confirm password", type="password", key="signup-confirm")
                submitted = st.form_submit_button("Create account", use_container_width=True)

            if submitted:
                if not name.strip() or not email or not password:
                    st.error("Name, email, and password are required.")
                elif len(password) < 8:
                    st.error("Password must be at least 8 characters.")
                elif password != confirm_password:
                    st.error("Passwords do not match.")
                elif email in users:
                    st.error("An account already exists for this email.")
                else:
                    code = f"{secrets.randbelow(900000) + 100000}"
                    salt, password_hash = hash_password(password)
                    users[email] = {
                        "name": name.strip(),
                        "email": email,
                        "salt": salt,
                        "password_hash": password_hash,
                        "is_verified": False,
                        "verification_code": code,
                        "plan": "Free",
                        "messages_used": 0,
                        "created_at": datetime.now().isoformat(timespec="seconds"),
                    }
                    save_users(users)
                    sent, detail = send_verification_email(email, name.strip(), code)
                    st.session_state.pending_email = email
                    if sent:
                        st.success("Account created. Check your email for the verification code.")
                    else:
                        st.warning(f"Account created, but email was not sent: {detail}")
                        if IS_DEVELOPMENT:
                            st.info(f"Development verification code: {code}")
                        else:
                            st.error("Email delivery is not configured. Contact support.")

        with tab_verify:
            pending_email = st.session_state.get("pending_email", "")
            with st.form("verify-form"):
                email = normalize_email(st.text_input("Email", value=pending_email, key="verify-email"))
                code = st.text_input("Verification code", key="verify-code")
                submitted = st.form_submit_button("Verify email", use_container_width=True)

            if submitted:
                user = users.get(email)
                if not user:
                    st.error("No account found for this email.")
                elif user.get("is_verified"):
                    st.success("This email is already verified. You can login now.")
                elif code.strip() != user.get("verification_code"):
                    st.error("Invalid verification code.")
                else:
                    user["is_verified"] = True
                    user["verification_code"] = ""
                    user.setdefault("plan", "Free")
                    user.setdefault("messages_used", 0)
                    users[email] = user
                    save_users(users)
                    st.success("Email verified successfully. You can login now.")

        with tab_forgot:
            st.caption("Send a reset code to your email, then set a new password.")
            with st.form("forgot-code-form"):
                reset_email = normalize_email(
                    st.text_input("Account email", key="forgot-email")
                )
                send_reset = st.form_submit_button(
                    "Send reset code", use_container_width=True
                )

            if send_reset:
                user = users.get(reset_email)
                if not user:
                    st.error("No account found for this email.")
                else:
                    code = f"{secrets.randbelow(900000) + 100000}"
                    user["password_reset_code"] = code
                    user["password_reset_requested_at"] = datetime.now().isoformat(
                        timespec="seconds"
                    )
                    users[reset_email] = user
                    save_users(users)
                    sent, detail = send_password_reset_email(
                        reset_email, user.get("name", "User"), code
                    )
                    st.session_state.reset_email = reset_email
                    if sent:
                        st.success("Reset code sent. Check your email inbox.")
                    else:
                        st.warning(f"Reset code created, but email was not sent: {detail}")
                        if IS_DEVELOPMENT:
                            st.info(f"Development reset code: {code}")
                        else:
                            st.error("Email delivery is not configured. Contact support.")

            with st.form("reset-password-form"):
                reset_email = normalize_email(
                    st.text_input(
                        "Email",
                        value=st.session_state.get("reset_email", ""),
                        key="reset-email",
                    )
                )
                reset_code = st.text_input("Reset code", key="reset-code")
                new_password = st.text_input(
                    "New password", type="password", key="reset-new-password"
                )
                confirm_password = st.text_input(
                    "Confirm new password",
                    type="password",
                    key="reset-confirm-password",
                )
                reset_submitted = st.form_submit_button(
                    "Update password", use_container_width=True
                )

            if reset_submitted:
                user = users.get(reset_email)
                if not user:
                    st.error("No account found for this email.")
                elif reset_code.strip() != user.get("password_reset_code"):
                    st.error("Invalid reset code.")
                elif len(new_password) < 8:
                    st.error("Password must be at least 8 characters.")
                elif new_password != confirm_password:
                    st.error("Passwords do not match.")
                else:
                    salt, password_hash = hash_password(new_password)
                    user["salt"] = salt
                    user["password_hash"] = password_hash
                    user["password_reset_code"] = ""
                    user["password_reset_requested_at"] = ""
                    users[reset_email] = user
                    save_users(users)
                    st.success("Password updated successfully. You can login now.")

    return False


def render_sidebar() -> tuple[str, float, int]:
    with st.sidebar:
        st.title("Pamms AI")
        if st.button("+ New chat", use_container_width=True):
            new_conversation()
            st.rerun()

        st.divider()
        with st.expander("Settings", expanded=True):
            selected_label = st.selectbox("Model", list(MODEL_OPTIONS.keys()), index=0)
            temperature = st.slider(
                "Temperature", min_value=0.0, max_value=1.0, value=0.7
            )
            max_tokens = st.slider("Max tokens", min_value=50, max_value=1200, value=300)

            users = load_users()
            current_user = get_current_user(users)
            messages_used = get_message_usage(current_user)
            chat_limit = get_chat_limit(current_user)
            remaining_chats = get_remaining_chats(current_user)
            if chat_limit is None:
                st.metric("Chat usage", f"{messages_used:,} / Unlimited")
            else:
                st.metric("Free/plan chats left", f"{remaining_chats:,}")
                st.caption(f"Used {messages_used:,} of {chat_limit:,} chats.")

            selected_package = st.selectbox("Subscription plan", list(SUBSCRIPTION_PLANS.keys()))
            selected_plan = SUBSCRIPTION_PLANS[selected_package]
            st.caption(selected_plan["description"])
            if st.button("Subscribe / Upgrade", use_container_width=True):
                update_current_user(
                    {
                        "plan": selected_plan["plan"],
                        "subscribed_at": datetime.now().isoformat(timespec="seconds"),
                    }
                )
                st.success(f"{selected_plan['plan']} plan activated.")
                st.rerun()

        st.divider()
        active_conversation = get_active_conversation()
        st.download_button(
            "Download current chat",
            data=export_conversation_markdown(active_conversation),
            file_name=f"{active_conversation.get('title', 'pamms-ai-chat')[:40]}.md",
            mime="text/markdown",
            use_container_width=True,
        )
        if st.button("Clear current chat", use_container_width=True):
            clear_active_conversation()
            st.rerun()

        st.divider()
        st.markdown('<div class="recents-title">Recents</div>', unsafe_allow_html=True)
        history_search = st.text_input("Search chats", placeholder="Search history")

        conversations = sorted(
            st.session_state.conversations.items(),
            key=lambda item: item[1].get("created_at", ""),
            reverse=True,
        )
        if history_search.strip():
            query = history_search.strip().lower()
            conversations = [
                (conversation_id, conversation)
                for conversation_id, conversation in conversations
                if query in (conversation.get("title") or "New chat").lower()
            ]

        history_height = min(max(len(conversations), 1) * 46 + 18, 230)
        with st.container(height=history_height, border=False):
            if not conversations:
                st.caption("No chats found.")
            for conversation_id, conversation in conversations:
                title = conversation.get("title") or "New chat"
                if st.button(title[:42], key=f"history-{conversation_id}", use_container_width=True):
                    st.session_state.active_conversation_id = conversation_id
                    st.rerun()

        user_name = st.session_state.get("user_name", "User")
        current_user = get_current_user()
        user_plan = current_user.get("plan", "Free")
        chat_limit = get_chat_limit(current_user)
        messages_used = get_message_usage(current_user)
        usage_label = (
            f"{messages_used:,} / Unlimited chats"
            if chat_limit is None
            else f"{messages_used:,} / {chat_limit:,} chats"
        )
        initials = "".join(part[0] for part in user_name.split()[:2]).upper() or "U"
        st.markdown(
            f"""
            <div class="sidebar-profile">
                <div class="avatar">{initials}</div>
                <div>
                    <div class="profile-name">{user_name}</div>
                    <div class="profile-plan">{user_plan} - {usage_label}</div>
                </div>
            </div>
            """,
            unsafe_allow_html=True,
        )
        if st.button("Logout", use_container_width=True):
            for key in [
                "authenticated",
                "user_email",
                "user_name",
                "conversations",
                "active_conversation_id",
            ]:
                st.session_state.pop(key, None)
            st.rerun()

    return MODEL_OPTIONS[selected_label], temperature, max_tokens


def render_messages(conversation: dict) -> None:
    for message in conversation["messages"]:
        with st.chat_message(message["role"]):
            st.markdown(message["content"])
            if message.get("attachments"):
                st.caption("Attached: " + ", ".join(message["attachments"]))


def append_message(role: str, content: str, attachments: list[str] | None = None) -> None:
    conversation = get_active_conversation()
    conversation["messages"].append(
        {
            "role": role,
            "content": content,
            "attachments": attachments or [],
            "created_at": datetime.now().isoformat(timespec="seconds"),
        }
    )
    if conversation["title"] == "New chat" and role == "user":
        conversation["title"] = content[:48] or "New chat"
    save_history(st.session_state.conversations)


def main() -> None:
    st.set_page_config(
        page_title="Pamms AI Chatbot",
        page_icon="AI",
        layout="wide",
        initial_sidebar_state="expanded",
    )
    apply_styles()

    if not render_auth_screen():
        return

    if "conversations" not in st.session_state:
        st.session_state.conversations = load_history()
    get_active_conversation()

    model_name, temperature, max_tokens = render_sidebar()
    conversation = get_active_conversation()

    st.markdown('<div class="main-title">Pamms AI Chatbot</div>', unsafe_allow_html=True)
    st.markdown(
        '<div class="subtle">Ask naturally. Choose a model, attach files or photos, and continue from chat history.</div>',
        unsafe_allow_html=True,
    )

    render_messages(conversation)

    st.markdown(
        f'<div class="control-strip">Groq model: {model_name}</div>',
        unsafe_allow_html=True,
    )

    user_input = st.chat_input(
        "Ask for follow-up changes",
        accept_file="multiple",
        file_type=["txt", "md", "py", "csv", "json", "pdf", "png", "jpg", "jpeg"],
    )

    if user_input:
        if isinstance(user_input, str):
            question = user_input
            uploaded_files = []
        else:
            question = user_input.text
            uploaded_files = user_input.files or []

        if not question.strip() and not uploaded_files:
            st.warning("Please enter a message or attach a file.")
            return

        current_user = get_current_user()
        if not can_send_message(current_user):
            st.error(
                "Your 10 free chats are finished. Open Settings in the sidebar and "
                "choose a subscription plan to continue."
            )
            return

        attachment_names = [uploaded_file.name for uploaded_file in uploaded_files]
        question = question.strip() or "Please review the uploaded file or photo."
        append_message("user", question, attachment_names)

        with st.chat_message("user"):
            st.markdown(question)
            if attachment_names:
                st.caption("Attached: " + ", ".join(attachment_names))

        with st.chat_message("assistant"):
            with st.spinner(f"Thinking with {model_name}..."):
                try:
                    answer = generate_response(
                        question=question,
                        model_name=model_name,
                        temperature=temperature,
                        max_tokens=max_tokens,
                        history=summarize_history(conversation["messages"]),
                        attachments=build_attachment_context(uploaded_files),
                    )
                except Exception as exc:
                    answer = (
                        f"I could not get a response from `{model_name}`.\n\n"
                        f"Error: {exc}\n\n"
                        "Check that `GROQ_API_KEY` is set correctly and the selected Groq model is available."
                    )
                st.markdown(answer)

        append_message("assistant", answer)
        increment_message_usage()
        st.rerun()


if __name__ == "__main__":
    main()
