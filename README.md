# 🤖 Pamms AI Chatbot

Pamms AI Chatbot is an AI-powered conversational assistant built with **Python**, **Streamlit**, **LangChain**, and **Groq LLMs**. It provides secure user authentication, persistent chat history, multiple AI model support, file uploads, subscription plans, and a modern responsive interface.

---

## ✨ Features

### 🔐 User Authentication
- User Registration
- Login & Logout
- Email Verification
- Forgot Password
- Password Reset
- Secure Password Hashing (PBKDF2)

---

### 🤖 AI Chat

- Powered by Groq LLM
- Supports multiple AI models:
  - Llama 3.1 8B Instant
  - Llama 3.3 70B Versatile
  - Gemma 2 9B
  - Whisper Large V3 Turbo
- Conversation memory
- Multi-turn chat
- Adjustable temperature
- Adjustable maximum tokens

---

### 📂 File Upload

Users can upload:

- PDF
- Python files
- JSON
- CSV
- Markdown
- TXT
- PNG
- JPG
- JPEG

The chatbot uses uploaded file names as conversation context.

---

### 💬 Chat History

- Multiple conversations
- Create new chats
- Search previous chats
- Download chats as Markdown
- Clear current conversation

---

### 👤 User Profiles

Each user has:

- Private chat history
- Subscription plan
- Message usage tracking
- Secure account information

---

### 💳 Subscription Plans

| Plan | Monthly Price | Chat Limit |
|-------|--------------|------------|
| Free | ₹0 | 10 Chats |
| Plus | ₹199 | 200 Chats |
| Pro | ₹499 | 1000 Chats |
| Business | ₹999 | Unlimited |

---

### 📧 Email Features

SMTP support for:

- Account Verification
- Login Notifications
- Password Reset

---

### 🎨 Modern UI

- Dark theme
- Responsive layout
- Sidebar navigation
- Chat interface
- Mobile-friendly design
- Download chat history

---

## 🛠️ Technologies Used

- Python
- Streamlit
- LangChain
- Groq API
- dotenv
- JSON Database
- SMTP Email
- HTML/CSS
- PBKDF2 Password Hashing

---

## 📁 Project Structure

```
Pamms-AI-Chatbot/
│
├── data/
│   ├── users.json
│   └── chat_history_*.json
│
├── .env
├── requirements.txt
├── main.py
└── README.md
```

---

## ⚙️ Installation

### Clone Repository

```bash
git clone https://github.com/yourusername/pamms-ai-chatbot.git

cd pamms-ai-chatbot
```

### Create Virtual Environment

Windows

```bash
python -m venv venv

venv\Scripts\activate
```

Linux/Mac

```bash
python3 -m venv venv

source venv/bin/activate
```

---

### Install Dependencies

```bash
pip install -r requirements.txt
```

---

## 🔑 Environment Variables

Create a `.env` file.

```env
# Groq
GROQ_API_KEY=your_groq_api_key

# Optional
LANGCHAIN_API_KEY=your_langchain_api_key

APP_ENV=development

# SMTP
SMTP_HOST=smtp.gmail.com
SMTP_PORT=587
SMTP_USER=your_email@gmail.com
SMTP_PASSWORD=your_password
SMTP_FROM_EMAIL=your_email@gmail.com
```

---

## ▶️ Run the Project

```bash
streamlit run main.py
```

Open your browser:

```
http://localhost:8501
```

---

## 📱 Supported AI Models

- Llama 3.1 8B Instant
- Llama 3.3 70B Versatile
- Gemma 2 9B
- Whisper Large V3 Turbo

---

## 🔒 Security

- Passwords hashed using PBKDF2
- Email verification
- Password reset via email
- Session-based authentication
- Separate chat history for every user

---

## 📥 Export Chat

Users can download the current conversation as a Markdown (`.md`) file.

---

## 🚀 Future Improvements

- Voice Chat
- Image Understanding
- PDF Content Analysis
- Database Integration (MySQL/MongoDB)
- Admin Dashboard
- Razorpay/Stripe Payment Gateway
- Google OAuth Login
- User Profile Pictures
- Chat Search by Message
- AI Image Generation

---

## 📸 Screenshots

Add screenshots here.

Example:

```
screenshots/
    login.png
    signup.png
    chatbot.png
    sidebar.png
```

---

## 🤝 Contributing

Contributions are welcome!

1. Fork the repository.
2. Create your feature branch.

```bash
git checkout -b feature-name
```

3. Commit your changes.

```bash
git commit -m "Added new feature"
```

4. Push to GitHub.

```bash
git push origin feature-name
```

5. Open a Pull Request.

---

## 📄 License

This project is licensed under the MIT License.

---

## 👨‍💻 Developer

**Pramod Kumbhar**


LinkedIn: https://linkedin.com/in/pramod-kumbhar-658410256

Email: kumbharpramod834@gmail.com

---

⭐ If you like this project, don't forget to give it a Star on GitHub!
