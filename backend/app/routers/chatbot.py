from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from pydantic import BaseModel
from typing import List, Optional, Dict, Any
from datetime import datetime
from ..database import get_db
from .. import models
import re
import random

router = APIRouter()


# ============================================================================
# PLATFORM KNOWLEDGE BASE (Albanian)
# ============================================================================

PLATFORM_KNOWLEDGE = {
    "platform_info": {
        "name": "AlbLingo",
        "description": "Platforma më e avancuar për mësimin e drejtshkrimit të gjuhës shqipe për fëmijë.",
        "target_audience": "Fëmijë nga 5 deri 18 vjeç",
        "features": [
            "Klasa dhe nivele të ndryshme mësimore",
            "Ushtrime interaktive drejtshkrimi",
            "Diktim me audio (zëra neural profesionalë)",
            "OCR për kontroll të diktimeve me imazhe",
            "Gamifikimi (badges, streaks, sfida ditore)",
            "AI Coach personal për drejtshkrim",
            "Spaced Repetition System (SRS) për përsëritje",
            "Leaderboard dhe konkurrencë",
            "Ushtrime të personalizuara me AI"
        ]
    },
    
    "how_to_use": {
        "getting_started": [
            "Regjistrohu me username, email dhe moshën",
            "Identifikohu me kredencialet e tua",
            "Fillo me Klasën 1, Niveli 1",
            "Plotëso ushtrimet për të avancuar",
            "Arri 80%+ saktësi për të hapur klasën tjetër"
        ],
        "exercises": [
            "Lexo pyetjen me kujdes",
            "Shkruaj përgjigjen saktë në shqip",
            "Kliko 'Dërgo Përgjigjen' për të kontrolluar",
            "Merr feedback të menjëhershëm",
            "Vazhdo me ushtrimin tjetër"
        ],
        "gamification": [
            "Mbledh pikë duke plotësuar ushtrime saktë",
            "Vazhdo streak-un tënd duke ushtruar çdo ditë",
            "Fito badges duke arritur objektiva",
            "Plotëso sfidat ditore për bonuse",
            "Shiko pozicionin tënd në leaderboard"
        ]
    },
    
    "faq": {
        "Si hap klasën tjetër?": "Duhet të arrish të paktën 80% saktësi në klasën aktuale. Plotëso të gjitha ushtrimet dhe përpiqu të japësh përgjigje të sakta.",
        
        "Çfarë janë ushtrimet AI?": "Janë ushtrime të personalizuara që gjenerohen automatikisht bazuar në fjalët që gabove më shpesh. Ndihmojnë të përmirësosh pikat e dobëta.",
        
        "Si funksionon streak-u?": "Streak-u është numri i ditëve rresht që ke ushtruar. Nëse ushtroni çdo ditë, streak-u rritet. Nëse humbni një ditë, streak-u fillojë nga zero.",
        
        "Çfarë është AI Coach?": "AI Coach është një asistent personal që analizon gabimet e tua dhe të jep këshilla të personalizuara për të përmirësuar drejtshkrimin shqip.",
        
        "Si funksionon OCR?": "OCR (Optical Character Recognition) të lejon të ngarkosh foto të diktimeve dhe sistemi do të nxjerrë tekstin dhe do të identifikojë gabimet e drejtshkrimit.",
        
        "Çfarë është SRS?": "Spaced Repetition System është një teknikë shkencore që të ndihmon të mësosh fjalë duke i përsëritur në intervale optimale kohore.",
        
        "Si marr më shumë pikë?": "Merr pikë duke plotësuar ushtrime saktë, duke arritur nivele të reja, duke plotësuar sfida ditore dhe duke fituar badges.",
        
        "A mund të ndryshoj zërin e audio?": "Po! Platforma ofron zëra profesionalë shqip: Anila (femër) dhe Ilir (mashkull). Zërat janë të bazuar në Azure Neural TTS.",
        
        "Si shoh progresin tim?": "Shiko sidebar-in në të majtë për të parë klasat e tua, progresin, AI Insights dhe gamifikimin.",
        
        "Çfarë nëse nuk kuptoj një ushtrim?": "Kliko ikonën 'hint' (nëse ka) ose pyet AI Chatbot-in për ndihmë. Gjithashtu mund të përdorësh audio për të dëgjuar fjalën."
    },
    
    "grammar_tips": {
        "ë vs e": "Shkronja 'ë' është shkronjë e veçantë shqipe (shqiptohet si 'schwa'). P.sh.: 'shtëpi' jo 'shtepi', 'përshëndetje' jo 'pershendetje'.",
        "ç vs c": "Shkronja 'ç' është një tingull më i butë (si 'ch' në anglisht). P.sh.: 'çanta' jo 'canta', 'çelësi' jo 'celesi'.",
        "dh": "Shkronja e dyfishtë 'dh' shqiptohet si 'th' në anglisht 'this'. P.sh.: 'dhe', 'dhëmbë'.",
        "th": "Shkronja e dyfishtë 'th' shqiptohet si 'th' në anglisht 'think'. P.sh.: 'thënie', 'thjesht'.",
        "Shkronjat e dyfishta": "Në shqip ka shkronja të dyfishta: ll, rr, nn, tt. P.sh.: 'dallim', 'territor', 'nënë', 'fëmijët'."
    }
}


# ============================================================================
# CHATBOT SCHEMAS
# ============================================================================

class ChatMessage(BaseModel):
    message: str
    user_id: Optional[str] = None
    context: Optional[Dict[str, Any]] = None


class ChatResponse(BaseModel):
    response: str
    suggestions: Optional[List[str]] = None
    related_topics: Optional[List[str]] = None
    timestamp: str


# ============================================================================
# CHATBOT LOGIC
# ============================================================================

def _normalize_query(query: str) -> str:
    """Normalize user query for better matching"""
    query = query.lower().strip()
    # Remove punctuation
    query = re.sub(r'[?!.,;:]', '', query)
    return query


def _match_faq(query: str) -> Optional[Dict[str, Any]]:
    """Match query against FAQ using keywords"""
    query_norm = _normalize_query(query)
    
    # Keyword matching for FAQs
    faq_keywords = {
        "Si hap klasën tjetër?": ["hap", "klase", "tjeter", "niveau", "unlock", "avanco"],
        "Çfarë janë ushtrimet AI?": ["ai", "ushtrime", "personalizuar", "inteligjenc", "gjeneroj"],
        "Si funksionon streak-u?": ["streak", "dit", "rresht", "vazhdo"],
        "Çfarë është AI Coach?": ["coach", "asistent", "mentor", "ndihm", "personalizuar"],
        "Si funksionon OCR?": ["ocr", "foto", "imazh", "diktim", "upload", "ngarko"],
        "Çfarë është SRS?": ["srs", "spaced", "repetition", "perserit", "mem"],
        "Si marr më shumë pikë?": ["pike", "point", "score", "fito", "mbledh"],
        "A mund të ndryshoj zërin e audio?": ["ze", "audio", "voice", "anila", "ilir", "ndryshoj"],
        "Si shoh progresin tim?": ["progres", "status", "shiko", "statistik"],
        "Çfarë nëse nuk kuptoj një ushtrim?": ["kuptoj", "veshtir", "ndihm", "hint"]
    }
    
    best_match = None
    best_score = 0
    
    for question, keywords in faq_keywords.items():
        score = sum(1 for kw in keywords if kw in query_norm)
        if score > best_score:
            best_score = score
            best_match = question
    
    if best_score >= 1:  # At least one keyword match
        return {
            "question": best_match,
            "answer": PLATFORM_KNOWLEDGE["faq"][best_match]
        }
    
    return None


def _get_contextual_response(query: str, user_id: Optional[str], db: Optional[Session]) -> Dict[str, Any]:
    """Generate contextual response based on query and user data"""
    query_norm = _normalize_query(query)
    
    # Category detection
    if any(word in query_norm for word in ["cila", "sa", "platforme", "alblingo", "kush", "pershkrim"]):
        return {
            "response": f"**{PLATFORM_KNOWLEDGE['platform_info']['name']}** është {PLATFORM_KNOWLEDGE['platform_info']['description']}\n\n"
                       f"Platforma ofron:\n" + "\n".join(f"✅ {feat}" for feat in PLATFORM_KNOWLEDGE['platform_info']['features'][:5]),
            "suggestions": ["Si filloj?", "Çfarë janë ushtrimet AI?", "Si marr pikë?"],
            "related_topics": ["Udhëzuesi për fillestartë", "Features", "Gamifikimi"]
        }
    
    if any(word in query_norm for word in ["filloj", "start", "regjistro", "regjistr", "begin"]):
        steps = PLATFORM_KNOWLEDGE['how_to_use']['getting_started']
        return {
            "response": "Si të fillosh:\n\n" + "\n".join(f"{i+1}. {step}" for i, step in enumerate(steps)),
            "suggestions": ["Si plotësoj ushtrime?", "Si hap klasën tjetër?"],
            "related_topics": ["Regjistrim", "Identifikim", "Klasa 1"]
        }
    
    if any(word in query_norm for word in ["ushtrime", "exercise", "detyra", "plotesoj"]):
        steps = PLATFORM_KNOWLEDGE['how_to_use']['exercises']
        return {
            "response": "Si të plotësosh ushtrime:\n\n" + "\n".join(f"{i+1}. {step}" for i, step in enumerate(steps)),
            "suggestions": ["Çfarë nëse gaboj?", "Si përdor audio?"],
            "related_topics": ["Drejtshkrim", "Feedback", "Nivele"]
        }
    
    if any(word in query_norm for word in ["ë", "shkronje", "grammar", "drejtshkrim", "sakte"]):
        tips = list(PLATFORM_KNOWLEDGE['grammar_tips'].items())
        tip = random.choice(tips)
        return {
            "response": f"Këshillë për drejtshkrim:\n\n{tip[0]}: {tip[1]}",
            "suggestions": ["Më trego këshilla të tjera", "Si përmirësoj drejtshkrimin?"],
            "related_topics": ["Gramatikë Shqipe", "AI Coach", "Ushtrime"]
        }
    
    if any(word in query_norm for word in ["gamifikimi", "badge", "streak", "pike", "competition"]):
        steps = PLATFORM_KNOWLEDGE['how_to_use']['gamification']
        return {
            "response": "**Gamifikimi në AlbLingo:**\n\n" + "\n".join(f"🏆 {step}" for step in steps),
            "suggestions": ["Si fitoj badges?", "Çfarë është streak-u?", "Si shoh leaderboard?"],
            "related_topics": ["Achievements", "Streaks", "Leaderboard"]
        }
    
    # Try FAQ matching
    faq_match = _match_faq(query)
    if faq_match:
        return {
            "response": f"**{faq_match['question']}**\n\n{faq_match['answer']}",
            "suggestions": ["Pyetje të tjera", "Si filloj?"],
            "related_topics": ["FAQ", "Udhëzime"]
        }
    
    # User-specific responses if logged in
    if user_id and db:
        try:
            user = db.query(models.User).filter(models.User.id == int(user_id)).first()
            if user:
                progress_count = db.query(models.Progress).filter(models.Progress.user_id == user_id).count()
                
                if "progres" in query_norm or "status" in query_norm:
                    return {
                        "response": f"**Progresi yt, {user.username}:**\n\n"
                                   f"📊 Nivele të plotësuara: {progress_count}\n"
                                   f"🔥 Streak aktual: {user.current_streak or 0} ditë\n"
                                   f"🏆 Arritje të fituara: {user.total_achievements or 0}\n\n"
                                   f"Vazhdo kështu! 💪",
                        "suggestions": ["Si përmirësohem?", "Çfarë është AI Coach?"],
                        "related_topics": ["Progresi", "Statistika", "Leaderboard"]
                    }
        except:
            pass
    
    # Default helpful response
    return {
        "response": "Më fal, nuk e kuptova plotësisht pyetjen. Por jam këtu për të ndihmuar!\n\n"
                   "Mund të më pyesësh për:\n"
                   "• Si të përdor platformën\n"
                   "• Ushtrime dhe nivele\n"
                   "• Gamifikimi (badges, streaks)\n"
                   "• Këshilla drejtshkrimi\n"
                   "• OCR dhe audio\n"
                   "• AI Coach dhe ushtrime të personalizuara",
        "suggestions": ["Si filloj?", "Çfarë ofron platforma?", "Si marr më shumë pikë?"],
        "related_topics": ["FAQ", "Udhëzuesi", "Features"]
    }


# ============================================================================
# CHATBOT ENDPOINT
# ============================================================================

@router.post("/chatbot/ask", response_model=ChatResponse)
async def ask_chatbot(message: ChatMessage, db: Session = Depends(get_db)):
    """
    AI Chatbot endpoint for Albanian language support.
    Provides help about the platform, exercises, gamification, and Albanian grammar.
    """
    if not message.message or len(message.message.strip()) < 2:
        raise HTTPException(status_code=400, detail="Mesazhi është shumë i shkurtër")
    
    # Get contextual response
    result = _get_contextual_response(
        query=message.message,
        user_id=message.user_id,
        db=db
    )
    
    return ChatResponse(
        response=result["response"],
        suggestions=result.get("suggestions"),
        related_topics=result.get("related_topics"),
        timestamp=datetime.utcnow().isoformat() + "Z"
    )


@router.get("/chatbot/suggestions")
async def get_chat_suggestions():
    """Get quick suggestions for common questions"""
    return {
        "suggestions": [
            "Si filloj të përdor platformën?",
            "Çfarë janë ushtrimet AI?",
            "Si hap klasën tjetër?",
            "Si funksionon gamifikimi?",
            "Më jep këshilla për drejtshkrim"
        ]
    }


@router.get("/chatbot/topics")
async def get_chat_topics():
    """Get available topics the chatbot can help with"""
    return {
        "topics": [
            {
                "title": "Për platformën",
                "icon": "🏠",
                "questions": ["Çfarë është AlbLingo?", "Cilat janë features kryesore?"]
            },
            {
                "title": "Si të fillosh",
                "icon": "🚀",
                "questions": ["Si regjistrohem?", "Si filloj me Klasën 1?"]
            },
            {
                "title": "Ushtrime",
                "icon": "📝",
                "questions": ["Si plotësoj ushtrime?", "Çfarë nëse gaboj?"]
            },
            {
                "title": "Gamifikimi",
                "icon": "🏆",
                "questions": ["Si fitoj badges?", "Çfarë është streak-u?"]
            },
            {
                "title": "Drejtshkrim",
                "icon": "✍️",
                "questions": ["Më jep këshilla", "Si përdor AI Coach?"]
            }
        ]
    }
