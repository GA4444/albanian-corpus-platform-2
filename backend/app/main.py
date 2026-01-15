from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from .database import Base, engine
from .routers import exercises, progress, seed, auth, ai, audio, course_progression, database_viewer, leaderboard, admin, ocr, gamification, chatbot, chatbot_advanced


def create_app() -> FastAPI:
	app = FastAPI(title="AlbLingo - Albanian Language Learning Platform", version="1.0.0")

	# CORS configuration
	import os
	allowed_origins = [
		"http://localhost:5173",
		"http://127.0.0.1:5173",
		"http://localhost:5174",
		"http://127.0.0.1:5174",
	]
	
	# Add production frontend URL from environment variable
	frontend_url = os.getenv("FRONTEND_URL")
	if frontend_url:
		allowed_origins.append(frontend_url)
	
	app.add_middleware(
		CORSMiddleware,
		allow_origins=allowed_origins,
		allow_credentials=True,
		allow_methods=["*"],
		allow_headers=["*"],
	)

	# Create tables if not exist
	Base.metadata.create_all(bind=engine)

	# Routers
	app.include_router(exercises.router, prefix="/api", tags=["exercises"])
	app.include_router(progress.router, prefix="/api", tags=["progress"])
	app.include_router(seed.router, prefix="/api", tags=["seed"])
	app.include_router(auth.router, prefix="/api", tags=["auth"])
	app.include_router(ai.router, prefix="/api", tags=["ai"])
	app.include_router(audio.router, prefix="/api", tags=["audio"])
	app.include_router(course_progression.router, prefix="/api", tags=["course-progression"])
	app.include_router(ocr.router, prefix="/api", tags=["ocr"])
	app.include_router(gamification.router, prefix="/api", tags=["gamification"])
	app.include_router(chatbot.router, prefix="/api", tags=["chatbot"])
	app.include_router(chatbot_advanced.router, prefix="/api", tags=["chatbot-advanced"])
	app.include_router(database_viewer.router, tags=["database-viewer"])
	app.include_router(leaderboard.router, prefix="/api", tags=["leaderboard"])
	app.include_router(admin.router, prefix="/api/admin", tags=["admin"])

	return app


app = create_app()

# Root endpoint
@app.get("/")
def read_root():
	return {"message": "Welcome to Shqipto API", "status": "running"}

# Health check endpoint
@app.get("/health")
def health_check():
	return {"status": "healthy", "timestamp": "2024-08-21T15:44:00Z"}


