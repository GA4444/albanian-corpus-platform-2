import os
import logging
from dotenv import load_dotenv
from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker, declarative_base
from sqlalchemy.exc import OperationalError, DisconnectionError, IntegrityError
from fastapi import HTTPException

# Import psycopg2 errors for direct handling
try:
	import psycopg2.errors
except ImportError:
	psycopg2 = None

logger = logging.getLogger(__name__)

load_dotenv()
DATABASE_URL = os.getenv("DATABASE_URL", "sqlite:///./dev.db")

# Handle PostgreSQL connection string format from Render
# Render provides DATABASE_URL in format: postgresql://user:pass@host:port/dbname
# SQLAlchemy 2.0+ uses 'postgresql://' but some providers use 'postgres://'
if DATABASE_URL.startswith("postgres://"):
	DATABASE_URL = DATABASE_URL.replace("postgres://", "postgresql://", 1)

# Connection arguments
connect_args = {}
if DATABASE_URL.startswith("sqlite"):
	connect_args = {"check_same_thread": False}

# Engine configuration with connection pool settings for production
engine_kwargs = {
	"echo": False,
	"connect_args": connect_args,
}

# Add connection pool settings for PostgreSQL (production)
if DATABASE_URL.startswith("postgresql"):
	engine_kwargs.update({
		"pool_size": 5,
		"max_overflow": 10,
		"pool_pre_ping": True,  # Verify connections before using
		"pool_recycle": 300,  # Recycle connections after 5 minutes
		"pool_reset_on_return": "commit",  # Reset connections on return
	})

try:
	engine = create_engine(DATABASE_URL, **engine_kwargs)
	
	# Test connection on startup
	with engine.connect() as conn:
		conn.execute(text("SELECT 1"))
	logger.info("Database connection successful")
except Exception as e:
	logger.error(f"Failed to connect to database: {e}")
	logger.error(f"DATABASE_URL format: {DATABASE_URL[:20]}...")  # Log first 20 chars only
	raise

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

Base = declarative_base()

def get_db():
	from sqlalchemy.orm import Session
	
	db: Session = SessionLocal()
	try:
		# Test connection before yielding
		db.execute(text("SELECT 1"))
		yield db
	except (OperationalError, DisconnectionError) as e:
		logger.error(f"Database connection error: {e}")
		db.rollback()
		raise HTTPException(
			status_code=503,
			detail="Database connection error. Please try again in a moment."
		)
	except IntegrityError as e:
		# Let IntegrityError propagate to the endpoint handler
		# The endpoint has retry logic for sequence issues
		logger.warning(f"Database integrity error (will be handled by endpoint): {e}")
		if hasattr(e, 'orig'):
			logger.warning(f"Original error: {e.orig}")
		db.rollback()
		raise  # Re-raise to let endpoint handle it
	except Exception as e:
		# Check if it's a psycopg2 UniqueViolation (which should be IntegrityError)
		error_type = type(e).__name__
		error_str = str(e)
		
		# Check if it's a psycopg2 UniqueViolation error
		is_unique_violation = False
		if psycopg2 and isinstance(e, psycopg2.errors.UniqueViolation):
			is_unique_violation = True
		elif "UniqueViolation" in error_type or ("duplicate key value violates unique constraint" in error_str):
			is_unique_violation = True
		
		if is_unique_violation:
			# Convert to IntegrityError-like behavior - let it propagate
			logger.warning(f"Unique constraint violation (will be handled by endpoint): {e}")
			if hasattr(e, 'orig'):
				logger.warning(f"Original error: {e.orig}")
			db.rollback()
			raise  # Re-raise to let endpoint handle it
		
		logger.error(f"Unexpected database error: {e}")
		logger.error(f"Error type: {error_type}")
		# Log more details
		if hasattr(e, 'orig'):
			logger.error(f"Original error: {e.orig}")
		if hasattr(e, 'params'):
			logger.error(f"Parameters: {e.params}")
		import traceback
		logger.error(f"Traceback: {traceback.format_exc()}")
		db.rollback()
		# Don't raise HTTPException here - let the calling code handle it
		# This allows IntegrityError to propagate to the endpoint handlers
		raise
	finally:
		db.close()


