# Pleader AI - Indian Legal Assistant

<div align="center">
  <h3>🏛️ AI-Powered Legal Assistant for Indian Law</h3>
  <p>Chat, Analyze Documents, and Get Expert Legal Advice Based on Indian Legal Framework</p>
</div>

## ✨ Features

- **🤖 AI Legal Chat** - Interactive conversations about Indian law with Gemini 2.5
- **📄 Document Analysis** - Upload and analyze legal documents (PDF, DOCX, TXT, JPG, PNG)
- **🔍 RAG Pipeline** - Document-grounded Q&A with FAISS vector search
- **💾 Export** - Export chats and analyses to PDF, DOCX, or TXT
- **🎨 Adaptive Themes** - 6 beautiful color themes (Green, Blue, Purple, Orange, Pink, Indigo)
- **🎤 Voice Typing** - Hands-free input using Web Speech API
- **🔐 Secure Auth** - JWT authentication with bcrypt password hashing
- **📱 Responsive** - Works on desktop, tablet, and mobile

## 🏗️ Tech Stack

**Backend:**
- FastAPI (Python)
- MongoDB (Database)
- Google Gemini 2.5 (LLM)
- FAISS (Vector Search)
- JWT + bcrypt (Authentication)

**Frontend:**
- React 19
- Tailwind CSS
- Radix UI Components
- Axios

## 🚀 Quick Start

### Prerequisites

- Python 3.11+
- Node.js 18+
- MongoDB
- Gemini API Key (Get from [Google AI Studio](https://makersuite.google.com/app/apikey))

### 1. Clone the Repository

```bash
git clone https://github.com/ashokkumarboya93/Pleader.ai.git
cd Pleader.ai
```

### 2. Backend Setup

```bash
cd backend

# Create virtual environment
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt

# Create .env file from example
cp .env.example .env

# Edit .env and add your credentials:
# - GEMINI_API_KEY: Your Gemini API key
# - MONGO_URL: Your MongoDB connection string
# - JWT_SECRET: A secure random string

# Run the backend
uvicorn server:app --host 0.0.0.0 --port 8001 --reload
```

Backend will be running at `http://localhost:8001`

### 3. Frontend Setup

```bash
cd frontend

# Install dependencies
yarn install

# Create .env file from example
cp .env.example .env

# Edit .env and set:
# REACT_APP_BACKEND_URL=http://localhost:8001

# Run the frontend
yarn start
```

Frontend will be running at `http://localhost:3000`

## 🧪 Running Tests

### Backend Tests

```bash
cd backend
pytest test_api.py -v
```

## 📦 Deployment

### Backend Deployment (Railway)

1. Create a new project on [Railway](https://railway.app/)
2. Connect your GitHub repository
3. Set the root directory to `/backend`
4. Add environment variables:
   - `GEMINI_API_KEY`
   - `MONGO_URL` (Use MongoDB Atlas for production)
   - `JWT_SECRET`
   - `CORS_ORIGINS` (Your frontend URL)
5. Railway will auto-detect the Dockerfile and deploy

### Frontend Deployment (Vercel)

1. Import project on [Vercel](https://vercel.com/)
2. Set root directory to `/frontend`
3. Add environment variable:
   - `REACT_APP_BACKEND_URL` (Your Railway backend URL)
4. Deploy with default React settings

## 🔧 Configuration

### Backend Environment Variables

| Variable | Description | Example |
|----------|-------------|----------|
| `MONGO_URL` | MongoDB connection string | `mongodb://localhost:27017` |
| `DB_NAME` | Database name | `pleader_ai_db` |
| `GEMINI_API_KEY` | Google Gemini API key | `AIzaSy...` |
| `JWT_SECRET` | Secret key for JWT tokens | `your_secure_secret_123` |
| `CORS_ORIGINS` | Allowed origins (comma-separated) | `http://localhost:3000` |

### Frontend Environment Variables

| Variable | Description | Example |
|----------|-------------|----------|
| `REACT_APP_BACKEND_URL` | Backend API URL | `http://localhost:8001` |
| `WDS_SOCKET_PORT` | WebSocket port (dev) | `443` |

## 📚 API Documentation

Once the backend is running, visit:
- **Swagger UI**: `http://localhost:8001/docs`
- **ReDoc**: `http://localhost:8001/redoc`
- **Health Check**: `http://localhost:8001/health`

### Key Endpoints

#### Authentication
- `POST /api/auth/signup` - Register new user
- `POST /api/auth/login` - Login user
- `GET /api/auth/me` - Get current user
- `POST /api/auth/logout` - Logout

#### Chat
- `POST /api/chat/send` - Send message
- `GET /api/chat/history` - Get chat history
- `GET /api/chat/{chat_id}` - Get specific chat
- `DELETE /api/chat/{chat_id}` - Delete chat
- `GET /api/chat/{chat_id}/export/{format}` - Export chat (pdf/docx/txt)

#### Documents
- `POST /api/documents/analyze` - Analyze document
- `GET /api/documents` - List documents
- `DELETE /api/documents/{id}` - Delete document
- `GET /api/documents/{id}/export/{format}` - Export analysis

#### RAG
- `POST /api/rag/query` - Query uploaded documents
- `GET /api/rag/stats` - Get RAG statistics

## 🎨 Features Guide

### Theme Selector
Click the theme button in the header to choose from 6 beautiful themes. Your preference is saved automatically.

### Voice Typing
Click the microphone icon in the chat input to start voice typing. Works with Indian English accent.

### Document Analysis
1. Go to "Analyze Documents" from sidebar
2. Upload PDF, DOCX, TXT, JPG, or PNG
3. Get comprehensive legal analysis
4. Export results in your preferred format

### RAG Queries
After uploading documents, ask questions about them. The AI will answer based only on your uploaded content.

### Export Options
Export any chat or document analysis as:
- **PDF** - Formatted document
- **DOCX** - Editable Word document
- **TXT** - Plain text

## 🤝 Contributing

Contributions are welcome! Please follow these steps:

1. Fork the repository
2. Create a feature branch: `git checkout -b feature/amazing-feature`
3. Commit changes: `git commit -m 'Add amazing feature'`
4. Push to branch: `git push origin feature/amazing-feature`
5. Open a Pull Request

## 📄 License

This project is licensed under the MIT License.

## 👨‍💻 Developer

**Ashok Kumar Boya**
- GitHub: [@ashokkumarboya93](https://github.com/ashokkumarboya93)

## 🙏 Acknowledgments

- Google Gemini for LLM capabilities
- FastAPI for the excellent Python framework
- React and Tailwind CSS communities
- FAISS for vector search

## 📞 Support

For issues and questions:
- Open an issue on GitHub
- Contact: [Your Email]

---

<div align="center">
  <p>Made with ❤️ for Indian Legal Community</p>
  <p>⚖️ Pleader AI - Your Digital Legal Assistant</p>
</div>
