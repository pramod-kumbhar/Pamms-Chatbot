# Pamms AI Chatbot Deployment

## Local Run

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
python -m streamlit run main.py --server.port 8502
```

Open:

```text
http://127.0.0.1:8502
```

## SMTP Email Verification

Create a `.env` file in this folder:

```text
C:\Users\pramod\OneDrive\Desktop\codex texting\Langchain Project\Ollama Chatbot\.env
```

Add:

```env
SMTP_HOST=smtp.gmail.com
SMTP_PORT=587
SMTP_USER=your_email@gmail.com
SMTP_PASSWORD=your_gmail_app_password
SMTP_FROM_EMAIL=your_email@gmail.com
```

For Gmail, use a Google App Password:

1. Enable 2-Step Verification on the Google account.
2. Open Google Account > Security > App passwords.
3. Create an app password for Mail.
4. Put that generated password in `SMTP_PASSWORD`.

## Deploy With Ollama

This app depends on local Ollama models, so deploy it on a machine or VM where Ollama can run.

On the server:

```bash
curl -fsSL https://ollama.com/install.sh | sh
ollama pull llama3
ollama pull mistral
ollama pull gemma:2b
ollama serve
```

Then run Streamlit:

```bash
pip install -r requirements.txt
streamlit run main.py --server.address 0.0.0.0 --server.port 8502
```

## Deploy Behind Nginx

Example Nginx reverse proxy:

```nginx
server {
    server_name your-domain.com;

    location / {
        proxy_pass http://127.0.0.1:8502;
        proxy_http_version 1.1;
        proxy_set_header Upgrade $http_upgrade;
        proxy_set_header Connection "upgrade";
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
    }
}
```

Use Certbot for HTTPS.

## Important Production Notes

- The current app stores users and chat history in local JSON files under `data/`.
- For real production, move users and chat history to PostgreSQL.
- Put SMTP credentials in environment variables, never directly in code.
- Keep Ollama behind the server firewall.
