from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from sqlalchemy import func, and_, distinct
from app.database import get_db
from app.models import Exercise, Progress, User, Course, Level, Attempt, CourseProgress
from app.schemas import SubmitRequest, SubmitResult, ExerciseOut
from typing import List
from datetime import datetime

router = APIRouter()

@router.get("/public-stats")
def get_public_stats(db: Session = Depends(get_db)):
	"""Get public statistics (no auth required)"""
	total_classes = db.query(Course).filter(Course.parent_class_id == None).count()
	total_courses = db.query(Course).filter(Course.parent_class_id != None).count()
	total_levels = db.query(Level).count()
	total_exercises = db.query(Exercise).count()
	# Count distinct categories
	total_categories = db.query(distinct(Exercise.category)).count()
	
	return {
		"total_classes": total_classes,
		"total_courses": total_courses,
		"total_levels": total_levels,
		"total_exercises": total_exercises,
		"total_categories": total_categories
	}

@router.post("/{exercise_id}/submit")
async def submit_answer(exercise_id: int, request: SubmitRequest, db: Session = Depends(get_db)):
    # Get the exercise
    exercise = db.query(Exercise).filter(Exercise.id == exercise_id).first()
    if not exercise:
        raise HTTPException(status_code=404, detail="Exercise not found")
    
    # Get the user
    user = db.query(User).filter(User.id == int(request.user_id)).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    
    # Check if answer is correct
    is_correct = exercise.answer.lower().strip() == request.response.lower().strip()
    
    # Calculate points (use exercise.points directly)
    points_earned = exercise.points if is_correct else 0
    
    # Create attempt record for course progress tracking
    attempt = Attempt(
        exercise_id=exercise_id,
        user_id=request.user_id,
        response=request.response,
        is_correct=is_correct,
        score_delta=points_earned
    )
    db.add(attempt)
    
    # Get or create progress record
    progress = db.query(Progress).filter(
        Progress.user_id == request.user_id,
        Progress.level_id == exercise.level_id
    ).first()
    
    if not progress:
        progress = Progress(
            user_id=request.user_id,
            category=exercise.category,
            level_id=exercise.level_id,
            course_id=exercise.course_id,
            points=0,
            errors=0,
            stars=0,
            completed=False
        )
        db.add(progress)
    
    # Update progress
    if is_correct:
        progress.points += points_earned
        # Calculate stars based on accuracy
        if progress.errors == 0:
            progress.stars = 3
        elif progress.errors < 3:
            progress.stars = 2
        else:
            progress.stars = 1
    else:
        progress.errors += 1
    
    # Check if level is completed (all exercises in level attempted with 80% accuracy)
    level_exercises = db.query(Exercise).filter(Exercise.level_id == exercise.level_id).all()
    total_exercises = len(level_exercises)
    
    # Get all progress records for this level
    level_progress = db.query(Progress).filter(
        Progress.user_id == request.user_id,
        Progress.level_id == exercise.level_id
    ).first()
    
    if level_progress:
        # Calculate accuracy based on points vs total possible points
        total_possible_points = sum(ex.points for ex in level_exercises)
        accuracy = (level_progress.points / total_possible_points) * 100 if total_possible_points > 0 else 0
        
        if accuracy >= 80:
            level_progress.completed = True
            level_completed = True
        else:
            level_completed = False
    else:
        level_completed = False
    
    # Check if course is completed (all levels in course completed)
    course_levels = db.query(Level).filter(Level.course_id == exercise.course_id).all()
    completed_levels = db.query(Progress).filter(
        Progress.user_id == request.user_id,
        Progress.course_id == exercise.course_id,
        Progress.completed == True
    ).count()
    
    course_completed = completed_levels == len(course_levels)
    
    db.commit()
    
    # Update course progress
    from .course_progression import update_course_progress
    course_progress = update_course_progress(db, int(request.user_id), exercise.course_id)
    
    # Prepare response message
    if is_correct:
        if course_progress.is_completed and not course_completed:
            message = f"🎉 Kurs i përfunduar! Saktësia: {course_progress.accuracy_percentage:.1f}% - Kursi i ardhshëm u hap! 🚀"
        elif level_completed:
            message = f"🎉 Nivel i përfunduar! Saktësia: {accuracy:.1f}%"
        else:
            message = f"✅ Përgjigje e saktë! +{points_earned} pikë"
    else:
        message = f"❌ Përgjigje e gabuar. Provoni sërish!"
    
    return SubmitResult(
        exercise_id=exercise_id,
        is_correct=is_correct,
        score_delta=points_earned,
        new_points=progress.points,
        new_errors=progress.errors,
        stars=progress.stars,
        level_completed=level_completed,
        course_completed=course_progress.is_completed,
        message=message
    )

@router.get("/courses/{course_id}/levels")
async def get_course_levels(course_id: int, db: Session = Depends(get_db)):
    levels = db.query(Level).filter(Level.course_id == course_id).order_by(Level.order_index).all()
    return levels

@router.get("/levels/{level_id}/exercises", response_model=List[ExerciseOut])
async def get_level_exercises(level_id: int, db: Session = Depends(get_db)):
    # Only return fields defined in ExerciseOut (answer is excluded)
    exercises = db.query(Exercise).filter(Exercise.level_id == level_id).order_by(Exercise.order_index).all()
    return exercises

@router.get("/classes")
async def get_classes(user_id: str = None, db: Session = Depends(get_db)):
    # Get top-level classes (parent_class_id is None)
    classes = db.query(Course).filter(Course.parent_class_id == None).order_by(Course.order_index).all()
    
    class_data = []
    user_id_int = int(user_id) if user_id and user_id.isdigit() else None
    
    for i, class_obj in enumerate(classes):
        unlocked = False
        progress_percent = 0.0
        
        if user_id_int:
            # Get all courses under this class
            class_courses = db.query(Course).filter(
                Course.parent_class_id == class_obj.id
            ).order_by(Course.order_index).all()
            
            if class_courses:
                course_ids = [c.id for c in class_courses]
                
                # Calculate progress percentage
                completed_count = db.query(CourseProgress).filter(
                    and_(
                        CourseProgress.user_id == user_id_int,
                        CourseProgress.course_id.in_(course_ids),
                        CourseProgress.is_completed == True
                    )
                ).count()
                
                progress_percent = (completed_count / len(course_ids)) * 100 if course_ids else 0.0
                
                # Check if class should be unlocked
                if i == 0:
                    # First class is always unlocked
                    unlocked = True
                else:
                    # Check if previous class has 80% completion
                    prev_class = classes[i - 1]
                    prev_class_courses = db.query(Course).filter(
                        Course.parent_class_id == prev_class.id
                    ).all()
                    
                    if prev_class_courses:
                        prev_course_ids = [c.id for c in prev_class_courses]
                        prev_completed_count = db.query(CourseProgress).filter(
                            and_(
                                CourseProgress.user_id == user_id_int,
                                CourseProgress.course_id.in_(prev_course_ids),
                                CourseProgress.is_completed == True
                            )
                        ).count()
                        
                        prev_completion_ratio = (prev_completed_count / len(prev_class_courses)) if prev_class_courses else 0.0
                        
                        # Unlock if previous class has 80%+ completion
                        unlocked = prev_completion_ratio >= 0.8
            else:
                # No courses in this class, unlock by default
                unlocked = i == 0
        else:
            # No user_id provided, only first class unlocked
            unlocked = i == 0
        
        class_data.append({
            "id": class_obj.id,
            "name": class_obj.name,
            "description": class_obj.description,
            "order_index": class_obj.order_index,
            "unlocked": unlocked,
            "progress_percent": progress_percent
        })
    
    return class_data

@router.get("/classes/{class_id}/courses")
async def get_class_courses(class_id: int, user_id: str = "1", db: Session = Depends(get_db)):
    # Get courses for the specified class
    courses = db.query(Course).filter(Course.parent_class_id == class_id).order_by(Course.order_index).all()
    
    # Initialize course progress for user if needed
    user_id_int = int(user_id)
    for course in courses:
        existing_progress = db.query(CourseProgress).filter(
            and_(
                CourseProgress.user_id == user_id_int,
                CourseProgress.course_id == course.id
            )
        ).first()
        
        if not existing_progress:
            # First course is unlocked by default
            is_unlocked = course.order_index == 1
            progress = CourseProgress(
                user_id=user_id_int,
                course_id=course.id,
                is_unlocked=is_unlocked
            )
            db.add(progress)
    
    db.commit()
    
    # Get course progress data
    course_data = []
    for course in courses:
        course_progress = db.query(CourseProgress).filter(
            and_(
                CourseProgress.user_id == user_id_int,
                CourseProgress.course_id == course.id
            )
        ).first()
        
        if course_progress:
            # Update progress if needed
            from .course_progression import update_course_progress
            course_progress = update_course_progress(db, user_id_int, course.id)
        
        course_data.append({
            "id": course.id,
            "name": course.name,
            "description": course.description,
            "order_index": course.order_index,
            "category": course.category,
            "required_score": course.required_score,
            "enabled": course_progress.is_unlocked if course_progress else False,
            "parent_class_id": course.parent_class_id,
            "progress": {
                "accuracy_percentage": course_progress.accuracy_percentage if course_progress else 0.0,
                "is_completed": course_progress.is_completed if course_progress else False,
                "total_points": course_progress.total_points if course_progress else 0,
                "completed_exercises": course_progress.completed_exercises if course_progress else 0,
                "total_exercises": course_progress.total_exercises if course_progress else 0
            }
        })
    
    return course_data


