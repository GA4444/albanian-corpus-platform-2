from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from sqlalchemy import text
from sqlalchemy.exc import IntegrityError
from ..database import get_db
from .. import models, schemas
from passlib.context import CryptContext
from datetime import datetime

router = APIRouter()
# Use a modern, battle-tested password hashing scheme that doesn't have
# bcrypt's 72-byte limitation or platform-specific backend issues.
pwd_context = CryptContext(schemes=["pbkdf2_sha256"], deprecated="auto")


@router.post("/register", response_model=schemas.AuthResponse)
def register(user_data: schemas.UserCreate, db: Session = Depends(get_db)):
	# Validate input
	if not user_data.username or not user_data.username.strip():
		raise HTTPException(status_code=400, detail="Username is required")
	if not user_data.email or not user_data.email.strip():
		raise HTTPException(status_code=400, detail="Email is required")
	if not user_data.password or len(user_data.password) < 3:
		raise HTTPException(status_code=400, detail="Password must be at least 3 characters")
	
	# Check if username already exists
	if db.query(models.User).filter(models.User.username == user_data.username.strip()).first():
		raise HTTPException(status_code=400, detail="Username already registered")
	
	# Check if email already exists
	if db.query(models.User).filter(models.User.email == user_data.email.strip()).first():
		raise HTTPException(status_code=400, detail="Email already registered")
	
	# Validate age
	if user_data.age and (user_data.age < 5 or user_data.age > 18):
		raise HTTPException(status_code=400, detail="Age must be between 5 and 18")
	
	# Hash password
	hashed_password = pwd_context.hash(user_data.password)
	
	# Create user with retry logic for sequence issues
	max_retries = 2
	for attempt in range(max_retries):
		try:
			db_user = models.User(
				username=user_data.username.strip(),
				email=user_data.email.strip(),
				age=user_data.age,
				password_hash=hashed_password,
				created_at=datetime.utcnow()
			)
			
			db.add(db_user)
			db.commit()
			db.refresh(db_user)
			
			return schemas.AuthResponse(
				user_id=db_user.id,
				username=db_user.username,
				message="Registration successful! Please log in to continue.",
				is_admin=db_user.is_admin
			)
			
		except IntegrityError as e:
			# Rollback before handling error
			db.rollback()
			
			error_str = str(e.orig) if hasattr(e, 'orig') else str(e)
			
			# Check if it's a username/email unique constraint violation
			if "users_username_key" in error_str or "unique constraint" in error_str.lower() and "username" in error_str.lower():
				raise HTTPException(status_code=400, detail="Username already registered")
			if "users_email_key" in error_str or "unique constraint" in error_str.lower() and "email" in error_str.lower():
				raise HTTPException(status_code=400, detail="Email already registered")
			
			# Check if it's a sequence issue (duplicate key on primary key)
			is_sequence_error = (
				"duplicate key value violates unique constraint" in error_str and 
				"users_pkey" in error_str
			)
			
			if is_sequence_error and attempt < max_retries - 1:
				# Try to fix the sequence and retry
				try:
					result = db.execute(text("SELECT COALESCE(MAX(id), 0) FROM users"))
					max_id = result.scalar()
					db.execute(text(f"SELECT setval('users_id_seq', {max_id + 1}, false)"))
					db.commit()
					print(f"[FIXED] Reset users_id_seq to {max_id + 1}, retrying registration...")
					continue  # Retry the user creation
				except Exception as seq_error:
					print(f"[ERROR] Failed to fix sequence: {seq_error}")
					import traceback
					traceback.print_exc()
					raise HTTPException(status_code=500, detail="Registration failed: Database sequence error. Please contact support.")
			else:
				# Other IntegrityError - log and raise
				print(f"[ERROR] IntegrityError during registration: {error_str}")
				import traceback
				traceback.print_exc()
				raise HTTPException(status_code=400, detail=f"Registration failed: {error_str}")
		except Exception as e:
			# Rollback before handling error
			db.rollback()
			
			error_str = str(e)
			# Check if it's a sequence issue (duplicate key on primary key)
			is_sequence_error = (
				"duplicate key value violates unique constraint" in error_str and 
				"users_pkey" in error_str
			)
			
			if is_sequence_error and attempt < max_retries - 1:
				# Try to fix the sequence and retry
				try:
					result = db.execute(text("SELECT COALESCE(MAX(id), 0) FROM users"))
					max_id = result.scalar()
					db.execute(text(f"SELECT setval('users_id_seq', {max_id + 1}, false)"))
					db.commit()
					print(f"[FIXED] Reset users_id_seq to {max_id + 1}, retrying registration...")
					continue  # Retry the user creation
				except Exception as seq_error:
					print(f"[ERROR] Failed to fix sequence: {seq_error}")
					import traceback
					traceback.print_exc()
					raise HTTPException(status_code=500, detail="Registration failed: Database sequence error. Please contact support.")
			else:
				# Other errors - raise immediately
				print(f"[ERROR] Registration error: {e}")
				import traceback
				traceback.print_exc()
				raise HTTPException(status_code=500, detail=f"Registration failed: {str(e)}")
	
	# Should never reach here, but just in case
	raise HTTPException(status_code=500, detail="Registration failed: Unexpected error")


@router.post("/login", response_model=schemas.AuthResponse)
def login(user_data: schemas.UserLogin, db: Session = Depends(get_db)):
	# Find user by username
	user = db.query(models.User).filter(models.User.username == user_data.username).first()
	
	if not user:
		raise HTTPException(status_code=401, detail="Invalid username or password")
	
	if not user.is_active:
		raise HTTPException(status_code=401, detail="Account is deactivated")
	
	# Verify password
	if not pwd_context.verify(user_data.password, user.password_hash):
		raise HTTPException(status_code=401, detail="Invalid username or password")
	
	# Update last login
	user.last_login = datetime.utcnow()
	db.commit()
	
	return schemas.AuthResponse(
		user_id=user.id,
		username=user.username,
		message="Login successful!",
		is_admin=user.is_admin
	)


@router.get("/user/{user_id}", response_model=schemas.UserOut)
def get_user(user_id: int, db: Session = Depends(get_db)):
	user = db.query(models.User).filter(models.User.id == user_id).first()
	if not user:
		raise HTTPException(status_code=404, detail="User not found")
	return user


@router.put("/user/{user_id}/profile", response_model=schemas.UserOut)
def update_user_profile(
	user_id: int,
	user_update: schemas.UserUpdate,
	db: Session = Depends(get_db)
):
	user = db.query(models.User).filter(models.User.id == user_id).first()
	if not user:
		raise HTTPException(status_code=404, detail="User not found")
	
	# Update email if provided and not already taken
	if user_update.email is not None:
		existing_user = db.query(models.User).filter(
			models.User.email == user_update.email,
			models.User.id != user_id
		).first()
		if existing_user:
			raise HTTPException(status_code=400, detail="Email already registered")
		user.email = user_update.email
	
	# Update other fields
	if user_update.age is not None:
		if user_update.age < 5 or user_update.age > 18:
			raise HTTPException(status_code=400, detail="Age must be between 5 and 18")
		user.age = user_update.age
	
	if user_update.date_of_birth is not None:
		user.date_of_birth = user_update.date_of_birth
	
	if user_update.address is not None:
		user.address = user_update.address
	
	if user_update.phone_number is not None:
		user.phone_number = user_update.phone_number
	
	db.commit()
	db.refresh(user)
	return user


@router.put("/user/{user_id}/preferences")
def update_user_preferences(
	user_id: int, 
	preferences: dict, 
	db: Session = Depends(get_db)
):
	user = db.query(models.User).filter(models.User.id == user_id).first()
	if not user:
		raise HTTPException(status_code=404, detail="User not found")
	
	# Update allowed preferences
	if "learning_style" in preferences:
		valid_styles = ["visual", "auditory", "kinesthetic", "reading", "mixed"]
		if preferences["learning_style"] in valid_styles:
			user.learning_style = preferences["learning_style"]
	
	if "preferred_difficulty" in preferences:
		valid_difficulties = ["easy", "normal", "hard"]
		if preferences["preferred_difficulty"] in valid_difficulties:
			user.preferred_difficulty = preferences["preferred_difficulty"]
	
	db.commit()
	return {"message": "Preferences updated successfully"}


@router.post("/fix-users-sequence")
def fix_users_sequence(db: Session = Depends(get_db)):
	"""Fix PostgreSQL sequence for users table - admin utility"""
	try:
		result = db.execute(text("SELECT COALESCE(MAX(id), 0) FROM users"))
		max_id = result.scalar()
		
		result = db.execute(text("SELECT last_value FROM users_id_seq"))
		current_seq = result.scalar()
		
		if max_id >= current_seq:
			new_seq_value = max_id + 1
			db.execute(text(f"SELECT setval('users_id_seq', {new_seq_value}, false)"))
			db.commit()
			return {
				"message": "Sequence fixed successfully",
				"max_id": max_id,
				"old_sequence": current_seq,
				"new_sequence": new_seq_value
			}
		else:
			return {
				"message": "Sequence is already correct",
				"max_id": max_id,
				"current_sequence": current_seq
			}
	except Exception as e:
		db.rollback()
		raise HTTPException(status_code=500, detail=f"Failed to fix sequence: {str(e)}")


@router.post("/fix-all-sequences")
def fix_all_sequences(db: Session = Depends(get_db)):
	"""Fix PostgreSQL sequences for all tables - admin utility"""
	tables = [
		"users", "courses", "levels", "exercises", 
		"attempts", "progress", "course_progress",
		"achievements", "user_achievements", "daily_challenges",
		"user_daily_progress", "srs_cards", "chat_sessions", "chat_messages"
	]
	
	results = {}
	
	for table_name in tables:
		try:
			# Get max ID
			result = db.execute(text(f"SELECT COALESCE(MAX(id), 0) FROM {table_name}"))
			max_id = result.scalar()
			
			# Get current sequence value
			try:
				result = db.execute(text(f"SELECT last_value FROM {table_name}_id_seq"))
				current_seq = result.scalar()
			except:
				# Sequence might not exist yet
				current_seq = 0
			
			if max_id >= current_seq:
				new_seq_value = max_id + 1
				db.execute(text(f"SELECT setval('{table_name}_id_seq', {new_seq_value}, false)"))
				results[table_name] = {
					"status": "fixed",
					"max_id": max_id,
					"old_sequence": current_seq,
					"new_sequence": new_seq_value
				}
			else:
				results[table_name] = {
					"status": "ok",
					"max_id": max_id,
					"current_sequence": current_seq
				}
		except Exception as e:
			results[table_name] = {
				"status": "error",
				"error": str(e)
			}
	
	db.commit()
	return {
		"message": "Sequence check completed",
		"results": results
	}


