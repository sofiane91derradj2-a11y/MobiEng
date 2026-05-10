# MobiEng Web App 🌐
### Version 8.0.1 — Web Edition

A fully self-contained web application. Run it locally or deploy it to the
internet on any platform — free hosting options included.

---

## 📂 Project Structure

```
MobiEng-WebApp/
├── app.py              ← Flask server (the brain)
├── requirements.txt    ← Python dependencies
├── Procfile            ← For Heroku / Railway / Render
├── render.yaml         ← One-click Render.com config
├── railway.json        ← Railway.app config
├── Dockerfile          ← For VPS / Docker / AWS
├── .gitignore          ← Keeps data/ out of git
├── app/
│   └── index.html      ← The full MobiEng app
└── data/               ← All user progress saved here (auto-created)
```

---

## 🖥️ Run Locally (on your computer)

```bash
# 1. Install dependencies
pip install -r requirements.txt

# 2. Run
python app.py

# 3. Open browser
# Go to: http://localhost:5000
```

---

## 🌍 Deploy to the Internet — Free Options

### Option A — Render.com (Recommended, free tier)

1. Create a free account at **render.com**
2. Click **New → Web Service**
3. Connect your GitHub repo (upload this folder first)
4. Render auto-detects `render.yaml` — click **Deploy**
5. Your app is live at `https://mobieng-web.onrender.com`

> ✅ The `render.yaml` file already configures a 1 GB persistent disk
> so all user data survives server restarts.

---

### Option B — Railway.app (Easiest, free tier)

1. Create a free account at **railway.app**
2. Click **New Project → Deploy from GitHub**
3. Select this repo — Railway reads `railway.json` automatically
4. Click **Deploy** — done in ~2 minutes
5. Go to **Settings → Domains** to get your public URL

> ⚠️ Railway's free tier doesn't include persistent disk.
> Add a Volume in Settings → Volumes → mount at `/app/data`

---

### Option C — Heroku

```bash
# Install Heroku CLI, then:
heroku create mobieng-web
git push heroku main
heroku open
```

> ⚠️ Heroku's filesystem resets on restart. Add a Heroku Postgres or
> Cloudcube add-on for persistence, or use the backup/restore feature.

---

### Option D — VPS / Ubuntu Server (full control)

```bash
# On your server:
git clone <your-repo> /srv/mobieng
cd /srv/mobieng
pip install -r requirements.txt

# Run with gunicorn
gunicorn app:app --workers 2 --bind 0.0.0.0:5000 --daemon

# Or use the Dockerfile:
docker build -t mobieng .
docker run -d -p 5000:5000 -v /srv/mobieng/data:/app/data mobieng
```

Then set up **Nginx** as a reverse proxy:

```nginx
server {
    listen 80;
    server_name yourdomain.com;

    location / {
        proxy_pass http://127.0.0.1:5000;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
    }
}
```

Get a free SSL certificate: `sudo certbot --nginx -d yourdomain.com`

---

## 💾 How Data is Saved

Each user gets a unique anonymous session ID stored in their browser cookie.
Their progress is saved in `data/<user-id>/` as individual JSON files.

- No login required
- Data persists as long as the user keeps their browser cookies
- Users can download a full backup from inside the app

---

## 🔒 Environment Variables

| Variable | Default | Description |
|---|---|---|
| `SECRET_KEY` | random | Flask session secret — set a fixed value in production |
| `PORT` | `5000` | Port to listen on |
| `HOST` | `0.0.0.0` | Host to bind to |
| `DEBUG` | `false` | Enable debug mode (never in production) |

Set `SECRET_KEY` to a long random string in production so user sessions
survive server restarts:

```bash
export SECRET_KEY="your-long-random-secret-key-here"
```

---

## 🛟 API Endpoints

| Endpoint | Method | Description |
|---|---|---|
| `/` | GET | Serves the app |
| `/storage/keys` | GET | List all keys for current user |
| `/storage/get/<key>` | GET | Get a value |
| `/storage/set` | POST | Set a key/value |
| `/storage/remove` | POST | Delete a key |
| `/storage/clear` | POST | Clear all data for user |
| `/api/backup` | GET | Download full JSON backup |
| `/api/restore` | POST | Restore from JSON backup |
| `/api/storage/info` | GET | Storage usage stats |
| `/health` | GET | Health check |

---

*MobiEng Web — Mobilis English Training Platform*
