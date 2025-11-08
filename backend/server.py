from fastapi import FastAPI, APIRouter, HTTPException, Depends, Request, Response, UploadFile, File, Form
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from fastapi.responses import StreamingResponse
from dotenv import load_dotenv
from starlette.middleware.cors import CORSMiddleware
from slowapi import Limiter, _rate_limit_exceeded_handler
from slowapi.util import get_remote_address
from slowapi.errors import RateLimitExceeded
from motor.motor_asyncio import AsyncIOMotorClient
import os
import logging
from pathlib import Path
from pydantic import BaseModel, Field, EmailStr, validator
from typing import List, Optional, Dict, Any
import uuid
from datetime import datetime, timezone, timedelta
import jwt
import bcrypt
import google.generativeai as genai
import json
import base64
import io
import re
import subprocess

# Import our utility modules
from rag_utils import get_rag_pipeline
from document_utils import extract_text_from_file, validate_file_type
from export_utils import (
    export_chat_to_pdf, export_chat_to_docx, export_chat_to_txt,
    export_analysis_to_pdf, export_analysis_to_docx, export_analysis_to_txt
)

ROOT_DIR = Path(__file__).parent
load_dotenv(ROOT_DIR / '.env')

# MongoDB connection
mongo_url = os.environ['MONGO_URL']
client = AsyncIOMotorClient(mongo_url)
db = client[os.environ['DB_NAME']]

# Initialize Gemini API
genai.configure(api_key=os.environ['GEMINI_API_KEY'])

# JWT configuration
JWT_SECRET = os.environ['JWT_SECRET']
JWT_ALGORITHM = "HS256"
JWT_EXPIRATION = timedelta(days=7)

# Create the main app
app = FastAPI(title="Pleader AI", version="1.0.0")

# Rate limiting
limiter = Limiter(key_func=get_remote_address)
app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)

# Create a router with the /api prefix
api_router = APIRouter(prefix="/api")

# Security
security = HTTPBearer(auto_error=False)

# ==================== INPUT SANITIZATION ====================

def sanitize_string(text: str, max_length: int = 10000) -> str:
    """Sanitize user input to prevent injection attacks"""
    if not text:
        return ""
    # Remove null bytes
    text = text.replace('\x00', '')
    # Limit length
    text = text[:max_length]
    # Remove potentially dangerous patterns
    text = re.sub(r'[<>]', '', text)
    return text.strip()

def validate_email(email: str) -> bool:
    """Validate email format"""
    pattern = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
    return re.match(pattern, email) is not None

# ==================== MODELS ====================

class UserCreate(BaseModel):
    name: str
    email: EmailStr
    password: str
    
    @validator('name')
    def validate_name(cls, v):
        v = sanitize_string(v, 100)
        if len(v) < 2:
            raise ValueError('Name must be at least 2 characters')
        return v
    
    @validator('password')
    def validate_password(cls, v):
        if len(v) < 8:
            raise ValueError('Password must be at least 8 characters')
        return v

class UserLogin(BaseModel):
    email: EmailStr
    password: str

class User(BaseModel):
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    name: str
    email: EmailStr
    avatar_url: Optional[str] = None
    auth_provider: str = "email"  # email, google
    preferences: Dict[str, Any] = Field(default_factory=lambda: {
        "theme": "light",
        "language": "en",
        "notifications": True
    })
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    last_active: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))

class SessionData(BaseModel):
    session_token: str
    user_id: str
    expires_at: datetime

class Message(BaseModel):
    sender: str  # "user" or "ai"
    content: str
    timestamp: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    attachments: List[str] = Field(default_factory=list)

class Chat(BaseModel):
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    user_id: str
    title: str = "New Chat"
    messages: List[Message] = Field(default_factory=list)
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    updated_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))

class SendMessageRequest(BaseModel):
    chat_id: Optional[str] = None
    message: str
    mode: Optional[str] = "detailed"  # "concise" or "detailed"
    
    @validator('message')
    def validate_message(cls, v):
        v = sanitize_string(v, 5000)
        if len(v) < 1:
            raise ValueError('Message cannot be empty')
        return v

class DocumentAnalyzeRequest(BaseModel):
    document_type: str = "legal_document"

class RAGQueryRequest(BaseModel):
    query: str
    top_k: int = Field(default=5, ge=1, le=20)
    use_rerank: bool = True
    
    @validator('query')
    def validate_query(cls, v):
        v = sanitize_string(v, 2000)
        if len(v) < 1:
            raise ValueError('Query cannot be empty')
        return v

# ==================== HELPER FUNCTIONS ====================

def get_git_version():
    """Get Git commit hash for version tracking"""
    try:
        result = subprocess.run(
            ['git', 'rev-parse', '--short', 'HEAD'],
            capture_output=True,
            text=True,
            cwd=ROOT_DIR
        )
        return result.stdout.strip() if result.returncode == 0 else "unknown"
    except:
        return "unknown"

async def get_current_user(credentials: HTTPAuthorizationCredentials = Depends(security)):
    if not credentials:
        raise HTTPException(status_code=401, detail="Not authenticated")
    
    try:
        token = credentials.credentials
        payload = jwt.decode(token, JWT_SECRET, algorithms=[JWT_ALGORITHM])
        user_id = payload.get("user_id")
        
        if not user_id:
            raise HTTPException(status_code=401, detail="Invalid token")
        
        user = await db.users.find_one({"id": user_id}, {"_id": 0})
        if not user:
            raise HTTPException(status_code=401, detail="User not found")
        
        return User(**user)
    except jwt.ExpiredSignatureError:
        raise HTTPException(status_code=401, detail="Token expired")
    except jwt.InvalidTokenError:
        raise HTTPException(status_code=401, detail="Invalid token")

# ==================== ENDPOINTS ====================

@app.get("/health")
@limiter.limit("60/minute")
async def health_check(request: Request):
    """Health check endpoint with version information"""
    return {
        "status": "healthy",
        "version": "1.0.0",
        "git_commit": get_git_version(),
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "services": {
            "database": "connected",
            "gemini_api": "configured",
            "rag_pipeline": "ready"
        }
    }

@api_router.post("/auth/signup")
@limiter.limit("5/minute")
async def signup(request: Request, user_data: UserCreate):
    # Check if user exists
    existing_user = await db.users.find_one({"email": user_data.email})
    if existing_user:
        raise HTTPException(status_code=400, detail="Email already registered")
    
    # Hash password
    password_bytes = user_data.password.encode('utf-8')
    salt = bcrypt.gensalt()
    hashed_password = bcrypt.hashpw(password_bytes, salt)
    
    # Create user
    user = User(
        name=user_data.name,
        email=user_data.email,
        auth_provider="email"
    )
    
    user_dict = user.model_dump()
    user_dict['password_hash'] = hashed_password.decode('utf-8')
    
    await db.users.insert_one(user_dict)
    
    # Generate JWT token
    token_payload = {
        "user_id": user.id,
        "exp": datetime.now(timezone.utc) + JWT_EXPIRATION
    }
    token = jwt.encode(token_payload, JWT_SECRET, algorithm=JWT_ALGORITHM)
    
    return {
        "message": "User created successfully",
        "token": token,
        "user": {
            "id": user.id,
            "name": user.name,
            "email": user.email,
            "avatar_url": user.avatar_url
        }
    }

@api_router.post("/auth/login")
@limiter.limit("10/minute")
async def login(request: Request, login_data: UserLogin):
    # Find user
    user = await db.users.find_one({"email": login_data.email}, {"_id": 0})
    if not user:
        raise HTTPException(status_code=401, detail="Invalid email or password")
    
    # Verify password using bcrypt.checkpw
    password_bytes = login_data.password.encode('utf-8')
    stored_hash = user['password_hash'].encode('utf-8')
    
    if not bcrypt.checkpw(password_bytes, stored_hash):
        raise HTTPException(status_code=401, detail="Invalid email or password")
    
    # Generate JWT token
    token_payload = {
        "user_id": user['id'],
        "exp": datetime.now(timezone.utc) + JWT_EXPIRATION
    }
    token = jwt.encode(token_payload, JWT_SECRET, algorithm=JWT_ALGORITHM)
    
    return {
        "message": "Login successful",
        "token": token,
        "user": {
            "id": user['id'],
            "name": user['name'],
            "email": user['email'],
            "avatar_url": user.get('avatar_url')
        }
    }

@api_router.post("/auth/session")
@limiter.limit("10/minute")
async def create_session(request: Request, user_data: dict):
    """Handle OAuth login (Google, etc.)"""
    email = user_data.get("email")
    name = user_data.get("name")
    avatar_url = user_data.get("avatar_url")
    provider = user_data.get("provider", "google")
    
    if not email or not validate_email(email):
        raise HTTPException(status_code=400, detail="Invalid email")
    
    # Check if user exists
    user = await db.users.find_one({"email": email}, {"_id": 0})
    
    if not user:
        # Create new user
        new_user = User(
            name=sanitize_string(name or email.split('@')[0], 100),
            email=email,
            avatar_url=avatar_url,
            auth_provider=provider
        )
        user_dict = new_user.model_dump()
        await db.users.insert_one(user_dict)
        user = user_dict
    
    # Generate JWT token
    token_payload = {
        "user_id": user['id'],
        "exp": datetime.now(timezone.utc) + JWT_EXPIRATION
    }
    token = jwt.encode(token_payload, JWT_SECRET, algorithm=JWT_ALGORITHM)
    
    return {
        "message": "Session created",
        "token": token,
        "user": {
            "id": user['id'],
            "name": user['name'],
            "email": user['email'],
            "avatar_url": user.get('avatar_url')
        }
    }

@api_router.post("/auth/logout")
async def logout(current_user: User = Depends(get_current_user)):
    return {"message": "Logged out successfully"}

@api_router.get("/auth/me")
async def get_me(current_user: User = Depends(get_current_user)):
    return {
        "id": current_user.id,
        "name": current_user.name,
        "email": current_user.email,
        "avatar_url": current_user.avatar_url,
        "preferences": current_user.preferences
    }

@api_router.post("/chat/send")
@limiter.limit("30/minute")
async def send_message(
    request: Request,
    message_request: SendMessageRequest,
    current_user: User = Depends(get_current_user)
):
    chat_id = message_request.chat_id
    user_message = message_request.message
    mode = message_request.mode or "detailed"
    
    # Create or get chat
    if not chat_id:
        chat = Chat(
            user_id=current_user.id,
            title=user_message[:50] + ("..." if len(user_message) > 50 else "")
        )
        chat_id = chat.id
        await db.chats.insert_one(chat.model_dump())
    else:
        chat_data = await db.chats.find_one({"id": chat_id, "user_id": current_user.id}, {"_id": 0})
        if not chat_data:
            raise HTTPException(status_code=404, detail="Chat not found")
        chat = Chat(**chat_data)
    
    # Add user message
    user_msg = Message(sender="user", content=user_message)
    chat.messages.append(user_msg)
    
    # Generate AI response with mode-specific prompt
    try:
        model = genai.GenerativeModel('gemini-2.0-flash-exp')
        
        # Build conversation history
        conversation_history = "\n".join([
            f"{msg.sender.upper()}: {msg.content}"
            for msg in chat.messages[-5:]  # Last 5 messages for context
        ])
        
        mode_instruction = ""
        if mode == "concise":
            mode_instruction = "Provide a CONCISE response (2-3 sentences maximum). Be brief and to the point."
        else:
            mode_instruction = "Provide a DETAILED, comprehensive response with explanations and examples."
        
        prompt = f"""You are Pleader AI, an expert Indian legal assistant. {mode_instruction}

Your role:
- Answer EXCLUSIVELY based on Indian legal framework (Constitution, IPC, CPC, CrPC, etc.)
- Cite specific sections, articles, and Acts
- Reference Supreme Court and High Court judgments when relevant
- Provide practical legal guidance for Indian jurisdiction only

IMPORTANT GUIDELINES:
- Always cite Indian laws: IPC sections, Constitutional articles, Act names
- Reference landmark Indian Supreme Court cases when applicable
- If a question is outside Indian law, politely state that you focus on Indian legal matters
- Structure your response clearly with headings and bullet points

Conversation history:
{conversation_history}

Provide your response now:"""
        
        response = model.generate_content(prompt)
        ai_message_text = response.text
        
        # Add AI response
        ai_msg = Message(sender="ai", content=ai_message_text)
        chat.messages.append(ai_msg)
        
        # Update chat
        chat.updated_at = datetime.now(timezone.utc)
        await db.chats.update_one(
            {"id": chat_id},
            {"$set": {
                "messages": [msg.model_dump() for msg in chat.messages],
                "updated_at": chat.updated_at,
                "title": chat.title
            }}
        )
        
        return {
            "chat_id": chat_id,
            "message": ai_msg.model_dump()
        }
        
    except Exception as e:
        logging.error(f"Error generating AI response: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Failed to generate response: {str(e)}")

@api_router.get("/chat/history")
async def get_chat_history(current_user: User = Depends(get_current_user)):
    chats = await db.chats.find({"user_id": current_user.id}, {"_id": 0}).sort("updated_at", -1).to_list(100)
    return {"chats": chats}

@api_router.get("/chat/{chat_id}")
async def get_chat(chat_id: str, current_user: User = Depends(get_current_user)):
    chat = await db.chats.find_one({"id": chat_id, "user_id": current_user.id}, {"_id": 0})
    if not chat:
        raise HTTPException(status_code=404, detail="Chat not found")
    return chat

@api_router.delete("/chat/{chat_id}")
async def delete_chat(chat_id: str, current_user: User = Depends(get_current_user)):
    result = await db.chats.delete_one({"id": chat_id, "user_id": current_user.id})
    if result.deleted_count == 0:
        raise HTTPException(status_code=404, detail="Chat not found")
    return {"message": "Chat deleted successfully"}

@api_router.post("/documents/analyze")
@limiter.limit("20/minute")
async def analyze_document(
    request: Request,
    file: UploadFile = File(...),
    document_type: str = Form("legal_document"),
    current_user: User = Depends(get_current_user)
):
    # Validate file type and size
    if not validate_file_type(file.filename):
        raise HTTPException(status_code=400, detail="Unsupported file type. Supported: PDF, DOCX, TXT, JPG, PNG")
    
    # Check file size (max 10MB)
    contents = await file.read()
    if len(contents) > 10 * 1024 * 1024:
        raise HTTPException(status_code=400, detail="File too large. Maximum size: 10MB")
    
    await file.seek(0)
    
    try:
        # Extract text from document
        extracted_text = await extract_text_from_file(file, file.filename)
        
        if not extracted_text or len(extracted_text.strip()) < 10:
            raise HTTPException(status_code=400, detail="Could not extract sufficient text from document")
        
        # Generate analysis using Gemini
        model = genai.GenerativeModel('gemini-2.0-flash-exp')
        
        analysis_prompt = f"""You are Pleader AI, an expert Indian legal document analyst.

Analyze the following {document_type} and provide:

1. **Document Summary**: Brief overview of the document's purpose and key parties
2. **Legal Framework**: Identify applicable Indian laws, Acts, and sections
3. **Key Provisions**: List main clauses, terms, and conditions
4. **Rights & Obligations**: Outline rights and obligations of all parties
5. **Risk Analysis**: Identify potential legal risks under Indian law
6. **Compliance Check**: Verify compliance with relevant Indian Acts (Indian Contract Act, Consumer Protection Act, etc.)
7. **Recommendations**: Suggest improvements or missing clauses per Indian legal standards

Document text:
{extracted_text[:5000]}

Provide a comprehensive analysis:"""
        
        response = model.generate_content(analysis_prompt)
        analysis_text = response.text
        
        # Store document in database
        document_id = str(uuid.uuid4())
        document = {
            "id": document_id,
            "user_id": current_user.id,
            "filename": file.filename,
            "document_type": document_type,
            "extracted_text": extracted_text[:10000],  # Store first 10k chars
            "analysis": analysis_text,
            "created_at": datetime.now(timezone.utc)
        }
        
        await db.documents.insert_one(document)
        
        # Index document in RAG pipeline
        try:
            rag_pipeline = get_rag_pipeline()
            rag_pipeline.add_documents([extracted_text], [document_id])
            logging.info(f"Document {document_id} indexed in RAG pipeline")
        except Exception as e:
            logging.error(f"Failed to index document in RAG: {str(e)}")
        
        return {
            "document_id": document_id,
            "filename": file.filename,
            "analysis": analysis_text,
            "extracted_text_length": len(extracted_text)
        }
        
    except Exception as e:
        logging.error(f"Error analyzing document: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Failed to analyze document: {str(e)}")

@api_router.get("/documents")
async def get_documents(current_user: User = Depends(get_current_user)):
    documents = await db.documents.find(
        {"user_id": current_user.id},
        {"_id": 0, "extracted_text": 0}  # Exclude large text field
    ).sort("created_at", -1).to_list(100)
    return {"documents": documents}

@api_router.delete("/documents/{document_id}")
async def delete_document(document_id: str, current_user: User = Depends(get_current_user)):
    result = await db.documents.delete_one({"id": document_id, "user_id": current_user.id})
    if result.deleted_count == 0:
        raise HTTPException(status_code=404, detail="Document not found")
    return {"message": "Document deleted successfully"}

@api_router.post("/rag/query")
@limiter.limit("30/minute")
async def rag_query(
    request: Request,
    query_request: RAGQueryRequest,
    current_user: User = Depends(get_current_user)
):
    try:
        rag_pipeline = get_rag_pipeline()
        
        # Query the RAG pipeline
        results = rag_pipeline.query(
            query=query_request.query,
            top_k=query_request.top_k,
            use_rerank=query_request.use_rerank
        )
        
        return {
            "query": query_request.query,
            "results": results
        }
        
    except Exception as e:
        logging.error(f"Error in RAG query: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Failed to process query: {str(e)}")

@api_router.get("/rag/stats")
async def get_rag_stats(current_user: User = Depends(get_current_user)):
    try:
        rag_pipeline = get_rag_pipeline()
        stats = rag_pipeline.get_stats()
        return stats
    except Exception as e:
        logging.error(f"Error getting RAG stats: {str(e)}")
        return {"total_documents": 0, "total_chunks": 0}

@api_router.get("/chat/{chat_id}/export/{format}")
async def export_chat(
    chat_id: str,
    format: str,
    current_user: User = Depends(get_current_user)
):
    if format not in ["pdf", "docx", "txt"]:
        raise HTTPException(status_code=400, detail="Invalid format. Use: pdf, docx, or txt")
    
    # Get chat
    chat_data = await db.chats.find_one({"id": chat_id, "user_id": current_user.id}, {"_id": 0})
    if not chat_data:
        raise HTTPException(status_code=404, detail="Chat not found")
    
    try:
        # Generate export
        if format == "pdf":
            file_bytes = export_chat_to_pdf(chat_data)
            media_type = "application/pdf"
        elif format == "docx":
            file_bytes = export_chat_to_docx(chat_data)
            media_type = "application/vnd.openxmlformats-officedocument.wordprocessingml.document"
        else:  # txt
            file_bytes = export_chat_to_txt(chat_data)
            media_type = "text/plain"
        
        filename = f"chat_{chat_id[:8]}.{format}"
        
        return StreamingResponse(
            io.BytesIO(file_bytes),
            media_type=media_type,
            headers={"Content-Disposition": f"attachment; filename={filename}"}
        )
        
    except Exception as e:
        logging.error(f"Error exporting chat: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Failed to export chat: {str(e)}")

@api_router.get("/documents/{document_id}/export/{format}")
async def export_document_analysis(
    document_id: str,
    format: str,
    current_user: User = Depends(get_current_user)
):
    if format not in ["pdf", "docx", "txt"]:
        raise HTTPException(status_code=400, detail="Invalid format. Use: pdf, docx, or txt")
    
    # Get document
    document = await db.documents.find_one(
        {"id": document_id, "user_id": current_user.id},
        {"_id": 0}
    )
    if not document:
        raise HTTPException(status_code=404, detail="Document not found")
    
    try:
        # Generate export
        if format == "pdf":
            file_bytes = export_analysis_to_pdf(document)
            media_type = "application/pdf"
        elif format == "docx":
            file_bytes = export_analysis_to_docx(document)
            media_type = "application/vnd.openxmlformats-officedocument.wordprocessingml.document"
        else:  # txt
            file_bytes = export_analysis_to_txt(document)
            media_type = "text/plain"
        
        filename = f"analysis_{document_id[:8]}.{format}"
        
        return StreamingResponse(
            io.BytesIO(file_bytes),
            media_type=media_type,
            headers={"Content-Disposition": f"attachment; filename={filename}"}
        )
        
    except Exception as e:
        logging.error(f"Error exporting document: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Failed to export document: {str(e)}")

@api_router.put("/user/preferences")
async def update_preferences(
    preferences: Dict[str, Any],
    current_user: User = Depends(get_current_user)
):
    # Update user preferences
    await db.users.update_one(
        {"id": current_user.id},
        {"$set": {"preferences": preferences}}
    )
    return {"message": "Preferences updated successfully"}

# Include the router in the main app
app.include_router(api_router)

app.add_middleware(
    CORSMiddleware,
    allow_credentials=True,
    allow_origins=os.environ.get('CORS_ORIGINS', '*').split(','),
    allow_methods=["*"],
    allow_headers=["*"],
)

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

@app.on_event("shutdown")
async def shutdown_db_client():
    client.close()
