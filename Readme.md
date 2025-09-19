# 42 Transcript Generator

An unofficial transcript generator for 42 School students that creates PDF transcripts using data from the official 42 Intranet API.

## 🎯 Features

- **OAuth Authentication**: Secure login using 42's OAuth system
- **PDF Generation**: Creates professional-looking PDF transcripts
- **Real-time Data**: Fetches current student data from 42's API
- **Credit Calculation**: Automatically calculates credits based on project grades
- **Multi-stage Curriculum**: Supports Piscine, Common Core, and Post-Core projects
- **Responsive Design**: Clean, modern web interface
- **Production Ready**: Configured for deployment with Gunicorn

## 📋 Prerequisites

- Python 3.7+
- 42 API Application credentials (UID and SECRET)
- `wkhtmltopdf` installed (for PDF generation)

### Installing wkhtmltopdf

**Ubuntu/Debian:**
```bash
sudo apt-get update
sudo apt-get install wkhtmltopdf
```

**macOS:**
```bash
brew install wkhtmltopdf
```

**CentOS/RHEL:**
```bash
sudo yum install wkhtmltopdf
```

## 🚀 Quick Start

### 1. Clone the repository
```bash
git clone <your-repo-url>
cd 42TranscriptGenerator
```

### 2. Set up environment files

Create your environment files based on the provided templates:

**`.env` (Production):**
```env
TITLE   = 42 Transcript Generator
VERSION = 0.1.0
PORT    = 80
DEBUG   = False

API_URL       = "https://api.intra.42.fr"
API_OAUTH_URL = "https://api.intra.42.fr/oauth/authorize?client_id=$FT_UID&redirect_uri=$REDIRECT_URI&response_type=code"
API_TOKEN_URL = "https://api.intra.42.fr/oauth/token"
REDIRECT_URI  = "$HOST/auth"
```

**`secrets.txt` (Keep this secure!):**
```env
FT_UID     = your_42_app_uid
FT_SECRET  = your_42_app_secret
SECRET_KEY = your_flask_secret_key
```

**`.dev.env` (Development overrides):**
```env
TITLE   = [β] 42TG
VERSION = 0.1.0
PORT    = 5000
DEBUG   = True
```

### 3. Get 42 API Credentials

1. Go to your [42 Intranet Profile](https://profile.intra.42.fr/)
2. Navigate to "API" section
3. Create a new application
4. Set the redirect URI to match your configuration
5. Copy the UID and SECRET to your `secrets.txt` file

### 4. Installation and Setup

```bash
# Install dependencies and set up virtual environment
make init

# For development
make dev

# For production
make all
```

## 🛠️ Development

### Running in Development Mode
```bash
make dev
```

This will:
- Create a virtual environment in `.venv/`
- Install all dependencies from `requirements.txt`
- Start the Flask development server
- Load environment variables from `.env`, `secrets.txt`, and `.dev.env`

### Project Structure
```
.
├── app/
│   ├── main.py               # Flask application entry point
|   ├── wsgi.py               # WSGI entry point for Gunicorn
│   ├── client/               # Static files (CSS, JS, images, HTML)
│   │   ├── css/
│   │   ├── html/
│   │   ├── img/
│   │   └── js/
│   └── server/               # Backend modules
│       ├── data.py           # Configuration constants
│       ├── routes.py         # Flask routes
│       ├── session.py        # 42 API session management
│       ├── transcript.py     # Transcript generation logic
│       ├── utils.py          # Utility functions
│       └── static/
│           └── projects.json # Project definitions and credits
├── .env                      # Production environment variables
├── .dev.env                  # Development environment overrides
├── secrets.txt               # API credentials (keep secure!)
├── requirements.txt          # Python dependencies
└── Makefile                  # Build and deployment commands
```

## 🚀 Production Deployment

### Using the Makefile
```bash
# Deploy to production
make all

# Stop the server
make stop

# Clean up and redeploy
make re
```

### Manual Deployment
```bash
# Set up virtual environment
python3 -m venv .venv
.venv/bin/pip install -r requirements.txt

# Export environment variables
export $(grep -v '^#' .env | xargs)
export $(grep -v '^#' secrets.txt | xargs)

# Run with Gunicorn
.venv/bin/python -m gunicorn \
    --bind 0.0.0.0:80 \
    --workers 4 \
    --pythonpath app \
    wsgi:app
```

### Environment Variables

| Variable | Description | Required |
|----------|-------------|----------|
| `TITLE` | Application title | No |
| `VERSION` | Application version | No |
| `PORT` | Server port | No (default: 5000) |
| `DEBUG` | Enable debug mode | No (default: False) |
| `API_URL` | 42 API base URL | Yes |
| `API_OAUTH_URL` | 42 OAuth authorization URL | Yes |
| `API_TOKEN_URL` | 42 OAuth token endpoint | Yes |
| `REDIRECT_URI` | OAuth redirect URI | Yes |
| `FT_UID` | 42 API application UID | Yes |
| `FT_SECRET` | 42 API application secret | Yes |
| `SECRET_KEY` | Flask session secret key | Yes |

## 📖 Usage

1. **Access the application** at your configured URL
2. **Click "Login with 42"** to authenticate
3. **Generate your transcript** by clicking "Generate Transcript"
4. **Download the PDF** that contains your academic record

## 🔧 Configuration

### Adding New Projects

Edit `app/server/static/projects.json` to add or modify projects:

```json
{
  "commonCore": {
    "newCategory": [
      {
        "id": 1234,
        "name": "Project Name",
        "hasBonus": true,
        "base": 500,
        "cursus": [21]
      }
    ]
  }
}
```

### Customizing Credit Calculation

The credit calculation formula can be modified in `app/server/transcript.py`:

```python
# Current formula: credits = ceil(base^0.25 * 2)
tproject['base'] = ceil(tproject['base'] ** exp * mult)
```

## 📝 API Endpoints

- `GET /` - Main application page
- `GET /auth` - OAuth callback endpoint
- `GET /logout` - User logout
- `GET /transcript` - Generate and download PDF transcript

## 🤝 Contributing

1. Fork the repository
2. Create a feature branch: `git checkout -b feature-name`
3. Make your changes
4. Test thoroughly
5. Commit your changes: `git commit -am 'Add feature'`
6. Push to the branch: `git push origin feature-name`
7. Submit a pull request

## ⚠️ Important Notes

- This is an **unofficial** transcript generator
- 42 School does not issue official transcripts
- This tool is for informational purposes only
- Always verify data accuracy before using for official purposes
- Keep your API credentials secure and never commit them to version control

## 🐛 Troubleshooting

### Common Issues

**PDF generation fails:**
- Ensure `wkhtmltopdf` is installed and in PATH
- Check that the system has sufficient memory

**Authentication errors:**
- Verify your 42 API credentials
- Check that the redirect URI matches your application settings
- Ensure the API application is approved and active

**Missing projects:**
- Check if the project exists in `projects.json`
- Verify the project ID matches the 42 API

## 📄 License

This project is provided as-is for educational and informational purposes. Use responsibly and in accordance with 42's terms of service.
