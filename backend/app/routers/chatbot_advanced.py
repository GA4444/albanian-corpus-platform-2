"""
Advanced AI Chatbot with:
- LLM Integration (OpenAI/Anthropic with local fallback)
- RAG (Retrieval Augmented Generation) from corpus
- Conversation history & session management
- Real-time exercise generation
- Voice input/output support
"""
from fastapi import APIRouter, Depends, HTTPException, UploadFile, File
from fastapi.responses import FileResponse
from sqlalchemy.orm import Session
from pydantic import BaseModel, ConfigDict
from typing import List, Optional, Dict, Any
from datetime import datetime, timedelta
import os
import json
import uuid
import time
from ..database import get_db
from .. import models

router = APIRouter()

# LLM Configuration
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
ANTHROPIC_API_KEY = os.getenv("ANTHROPIC_API_KEY")
USE_LLM = os.getenv("USE_LLM", "false").lower() == "true"

# Try to import LLM libraries
try:
    import openai
    if OPENAI_API_KEY:
        openai.api_key = OPENAI_API_KEY
        OPENAI_AVAILABLE = True
    else:
        OPENAI_AVAILABLE = False
except ImportError:
    OPENAI_AVAILABLE = False

try:
    import anthropic
    if ANTHROPIC_API_KEY:
        ANTHROPIC_CLIENT = anthropic.Anthropic(api_key=ANTHROPIC_API_KEY)
        ANTHROPIC_AVAILABLE = True
    else:
        ANTHROPIC_AVAILABLE = False
except ImportError:
    ANTHROPIC_AVAILABLE = False


# ============================================================================
# SCHEMAS
# ============================================================================

class AdvancedChatRequest(BaseModel):
    message: str
    user_id: Optional[str] = None
    session_token: Optional[str] = None
    use_llm: bool = False
    generate_exercise: bool = False
    voice_input: bool = False


class AdvancedChatResponse(BaseModel):
    model_config = ConfigDict(protected_namespaces=())  # Allow 'model_used' field name
    
    response: str
    session_token: str
    suggestions: Optional[List[str]] = None
    related_topics: Optional[List[str]] = None
    generated_exercise: Optional[Dict[str, Any]] = None
    audio_url: Optional[str] = None
    model_used: str
    timestamp: str


# ============================================================================
# RAG SYSTEM
# ============================================================================

def _search_corpus(query: str, db: Session, limit: int = 5) -> List[Dict[str, Any]]:
    """
    Simple RAG: Search through exercises and return relevant content.
    In production, use vector embeddings (FAISS, Pinecone, etc.)
    """
    query_lower = query.lower()
    keywords = query_lower.split()
    
    # Search in exercises
    relevant_exercises = []
    exercises = db.query(models.Exercise).filter(models.Exercise.enabled == True).limit(1000).all()
    
    for ex in exercises:
        score = 0
        prompt_lower = (ex.prompt or "").lower()
        answer_lower = (ex.answer or "").lower()
        
        for keyword in keywords:
            if keyword in prompt_lower:
                score += 2
            if keyword in answer_lower:
                score += 1
        
        if score > 0:
            relevant_exercises.append({
                "exercise_id": ex.id,
                "prompt": ex.prompt,
                "answer": ex.answer,
                "category": ex.category.value if ex.category else None,
                "score": score
            })
    
    # Sort by relevance
    relevant_exercises.sort(key=lambda x: x["score"], reverse=True)
    
    return relevant_exercises[:limit]


def _build_rag_context(query: str, db: Session) -> str:
    """Build context from corpus for RAG"""
    corpus_results = _search_corpus(query, db, limit=3)
    
    if not corpus_results:
        return ""
    
    context = "Bazuar në korpusin e platformës:\n\n"
    for idx, result in enumerate(corpus_results, 1):
        context += f"{idx}. Ushtrim ({result['category']}): {result['prompt'][:100]}...\n"
    
    return context


# ============================================================================
# LLM INTEGRATION
# ============================================================================

def _call_openai(messages: List[Dict[str, str]], temperature: float = 0.7) -> tuple[str, int]:
    """Call OpenAI API"""
    if not OPENAI_AVAILABLE:
        raise ValueError("OpenAI not available")
    
    response = openai.ChatCompletion.create(
        model="gpt-4-turbo-preview",
        messages=messages,
        temperature=temperature,
        max_tokens=800
    )
    
    content = response.choices[0].message.content
    tokens = response.usage.total_tokens
    
    return content, tokens


def _call_anthropic(messages: List[Dict[str, str]], temperature: float = 0.7) -> tuple[str, int]:
    """Call Anthropic Claude API"""
    if not ANTHROPIC_AVAILABLE:
        raise ValueError("Anthropic not available")
    
    # Convert messages format
    system_msg = next((m["content"] for m in messages if m["role"] == "system"), None)
    user_messages = [m for m in messages if m["role"] != "system"]
    
    response = ANTHROPIC_CLIENT.messages.create(
        model="claude-3-sonnet-20240229",
        max_tokens=800,
        temperature=temperature,
        system=system_msg or "Ti je një asistent mësimor për gjuhën shqipe.",
        messages=user_messages
    )
    
    content = response.content[0].text
    tokens = response.usage.input_tokens + response.usage.output_tokens
    
    return content, tokens


def _generate_llm_response(
    query: str,
    conversation_history: List[Dict[str, str]],
    rag_context: str,
    user_info: Optional[Dict[str, Any]] = None
) -> tuple[str, str, int]:
    """
    Generate response using LLM with RAG context.
    Returns: (response, model_used, tokens_used)
    """
    # Build system prompt
    system_prompt = """Ti je një asistent AI i avancuar për AlbLingo - platformën e mësimit të gjuhës shqipe për fëmijë.

Detyrat e tua:
- Përgjigju pyetjeve në gjuhën shqipe me ton miqësor dhe profesional
- Jep këshilla për drejtshkrim dhe gramatikë shqipe
- Ndihmo përdoruesit të përdorin platformën
- Ofro rekomandime të personalizuara bazuar në progresin e tyre
- Krijo ushtrime të reja kur kërkohet

Rregullat:
- Përdor gjuhë të thjeshtë dhe të kuptueshme për fëmijë
- Jep shembuj konkretë
- Inkurajo dhe motivoje përdoruesin
- Në fund të përgjigjes, sugjeroje pyetje të lidhura"""

    if rag_context:
        system_prompt += f"\n\n{rag_context}"
    
    if user_info:
        system_prompt += f"\n\nInformacion për përdoruesin: {json.dumps(user_info, ensure_ascii=False)}"
    
    # Build messages
    messages = [{"role": "system", "content": system_prompt}]
    messages.extend(conversation_history[-10:])  # Last 10 messages for context
    messages.append({"role": "user", "content": query})
    
    # Try OpenAI first, then Anthropic, then fallback
    try:
        if OPENAI_AVAILABLE:
            content, tokens = _call_openai(messages)
            return content, "gpt-4-turbo", tokens
    except Exception as e:
        print(f"[WARNING] OpenAI failed: {e}")
    
    try:
        if ANTHROPIC_AVAILABLE:
            content, tokens = _call_anthropic(messages)
            return content, "claude-3-sonnet", tokens
    except Exception as e:
        print(f"[WARNING] Anthropic failed: {e}")
    
    # Fallback to local logic
    from .chatbot import _get_contextual_response
    result = _get_contextual_response(query, user_info.get("user_id") if user_info else None, None)
    return result["response"], "local-advanced", 0


# ============================================================================
# EXERCISE GENERATION
# ============================================================================

def _generate_exercise_with_llm(
    topic: str,
    difficulty: str,
    user_mistakes: List[str],
    db: Session
) -> Optional[Dict[str, Any]]:
    """Generate a new exercise using LLM based on conversation context"""
    
    prompt = f"""Gjeneroje një ushtrim të ri për drejtshkrimin shqip:

Tema: {topic}
Vështirësia: {difficulty}
Gabimet e zakonshme të përdoruesit: {', '.join(user_mistakes) if user_mistakes else 'None'}

Formati i ushtrimittë jetë JSON me këto fusha:
{{
    "prompt": "Pyetja/Udhëzimi për ushtrimin",
    "answer": "Përgjigja e saktë",
    "hint": "Një këshillë ndihmëse",
    "category": "spelling"
}}

Sigurohu që ushtrimi të jetë i përshtatshëm për fëmijë dhe të fokusohet në gabimet e përmendura."""

    try:
        if OPENAI_AVAILABLE:
            response = openai.ChatCompletion.create(
                model="gpt-4-turbo-preview",
                messages=[
                    {"role": "system", "content": "Ti je një gjenerues ushtrimesh për mësimin e gjuhës shqipe."},
                    {"role": "user", "content": prompt}
                ],
                temperature=0.8,
                max_tokens=400
            )
            
            content = response.choices[0].message.content
            # Extract JSON
            import re
            json_match = re.search(r'\{.*\}', content, re.DOTALL)
            if json_match:
                exercise_data = json.loads(json_match.group())
                return exercise_data
    except Exception as e:
        print(f"[ERROR] Exercise generation failed: {e}")
    
    return None


# ============================================================================
# SESSION MANAGEMENT
# ============================================================================

def _get_or_create_session(
    user_id: Optional[str],
    session_token: Optional[str],
    db: Session
) -> models.ChatSession:
    """Get existing session or create new one"""
    
    if session_token:
        session = db.query(models.ChatSession).filter(
            models.ChatSession.session_token == session_token,
            models.ChatSession.is_active == True
        ).first()
        
        if session:
            # Update last activity
            session.last_activity = datetime.utcnow()
            db.commit()
            return session
    
    # Create new session
    session = models.ChatSession(
        user_id=user_id,
        session_token=str(uuid.uuid4()),
        started_at=datetime.utcnow(),
        last_activity=datetime.utcnow()
    )
    db.add(session)
    db.commit()
    db.refresh(session)
    
    return session


def _get_conversation_history(session: models.ChatSession, db: Session) -> List[Dict[str, str]]:
    """Get conversation history for context"""
    messages = db.query(models.ChatMessage).filter(
        models.ChatMessage.session_id == session.id
    ).order_by(models.ChatMessage.created_at.asc()).all()
    
    return [
        {"role": msg.role, "content": msg.content}
        for msg in messages
    ]


# ============================================================================
# ADVANCED CHATBOT ENDPOINT
# ============================================================================

@router.post("/chatbot/advanced/ask", response_model=AdvancedChatResponse)
async def advanced_chatbot_ask(request: AdvancedChatRequest, db: Session = Depends(get_db)):
    """
    Advanced AI Chatbot with LLM, RAG, conversation history, and exercise generation.
    
    Features:
    - LLM integration (OpenAI/Anthropic) with local fallback
    - RAG from corpus
    - Persistent conversation history
    - Real-time exercise generation
    - Voice output (TTS)
    """
    start_time = time.time()
    
    if not request.message or len(request.message.strip()) < 2:
        raise HTTPException(status_code=400, detail="Mesazhi është shumë i shkurtër")
    
    # Get or create session
    session = _get_or_create_session(request.user_id, request.session_token, db)
    
    # Get conversation history
    conversation_history = _get_conversation_history(session, db)
    
    # Get user info if logged in
    user_info = None
    if request.user_id:
        user = db.query(models.User).filter(models.User.id == int(request.user_id)).first()
        if user:
            progress_count = db.query(models.Progress).filter(models.Progress.user_id == request.user_id).count()
            user_info = {
                "user_id": request.user_id,
                "username": user.username,
                "progress_count": progress_count,
                "current_streak": user.current_streak,
                "total_achievements": user.total_achievements
            }
    
    # RAG: Search corpus
    rag_context = _build_rag_context(request.message, db) if (request.use_llm or USE_LLM) else ""
    
    # Generate response
    if request.use_llm or USE_LLM:
        response_text, model_used, tokens_used = _generate_llm_response(
            query=request.message,
            conversation_history=conversation_history,
            rag_context=rag_context,
            user_info=user_info
        )
    else:
        # Fallback to basic chatbot
        from .chatbot import _get_contextual_response
        result = _get_contextual_response(request.message, request.user_id, db)
        response_text = result["response"]
        model_used = "local-basic"
        tokens_used = 0
    
    # Save user message
    user_msg = models.ChatMessage(
        session_id=session.id,
        role="user",
        content=request.message,
        created_at=datetime.utcnow()
    )
    db.add(user_msg)
    
    # Generate exercise if requested
    generated_exercise = None
    if request.generate_exercise:
        # Detect topic and user mistakes
        user_mistakes = []  # TODO: Extract from progress
        generated_exercise = _generate_exercise_with_llm(
            topic=request.message,
            difficulty="medium",
            user_mistakes=user_mistakes,
            db=db
        )
    
    # Calculate response time
    response_time_ms = int((time.time() - start_time) * 1000)
    
    # Save assistant message
    assistant_msg = models.ChatMessage(
        session_id=session.id,
        role="assistant",
        content=response_text,
        model_used=model_used,
        tokens_used=tokens_used if tokens_used > 0 else None,
        response_time_ms=response_time_ms,
        created_at=datetime.utcnow()
    )
    db.add(assistant_msg)
    
    # Update session
    session.total_messages += 2
    session.last_activity = datetime.utcnow()
    
    db.commit()
    
    return AdvancedChatResponse(
        response=response_text,
        session_token=session.session_token,
        suggestions=None,  # TODO: Extract from LLM response
        related_topics=None,
        generated_exercise=generated_exercise,
        audio_url=None,  # TODO: Generate TTS
        model_used=model_used,
        timestamp=datetime.utcnow().isoformat() + "Z"
    )


@router.get("/chatbot/advanced/history/{session_token}")
async def get_session_history(session_token: str, db: Session = Depends(get_db)):
    """Get conversation history for a session"""
    session = db.query(models.ChatSession).filter(
        models.ChatSession.session_token == session_token
    ).first()
    
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")
    
    messages = db.query(models.ChatMessage).filter(
        models.ChatMessage.session_id == session.id
    ).order_by(models.ChatMessage.created_at.asc()).all()
    
    return {
        "session_token": session.session_token,
        "started_at": session.started_at.isoformat(),
        "total_messages": session.total_messages,
        "messages": [
            {
                "role": msg.role,
                "content": msg.content,
                "model_used": msg.model_used,
                "created_at": msg.created_at.isoformat()
            }
            for msg in messages
        ]
    }
