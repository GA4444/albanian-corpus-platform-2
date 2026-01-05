#!/usr/bin/env python3
"""
Initialize gamification system: create tables and seed achievements
"""
import sys
import os

# Add parent directory to path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from app.database import SessionLocal, engine, Base
from app import models


def init_tables():
	"""Create all tables (including new gamification tables)"""
	print("Creating database tables...")
	Base.metadata.create_all(bind=engine)
	print("✅ Tables created.")


def seed_achievements():
	"""Seed initial achievements"""
	db = SessionLocal()
	
	achievements_data = [
		# Beginner achievements
		{
			"code": "first_exercise",
			"name": "Hapi i Parë",
			"description": "Përfundo ushtrimin e parë!",
			"icon": "🎯",
			"category": "progress",
			"requirement_value": 1,
			"points_reward": 10,
		},
		{
			"code": "first_perfect_score",
			"name": "Perfeksion!",
			"description": "Merr rezultat perfekt në një ushtrim",
			"icon": "⭐",
			"category": "accuracy",
			"requirement_value": 1,
			"points_reward": 25,
		},
		# Streak achievements
		{
			"code": "streak_3",
			"name": "Angazhim i Mirë",
			"description": "Vazhdo streak 3-ditësh",
			"icon": "🔥",
			"category": "streak",
			"requirement_value": 3,
			"points_reward": 30,
		},
		{
			"code": "streak_7",
			"name": "Javë Perfekte",
			"description": "Vazhdo streak 7-ditësh",
			"icon": "🔥",
			"category": "streak",
			"requirement_value": 7,
			"points_reward": 75,
		},
		{
			"code": "streak_30",
			"name": "Mjeshtër i Zakoneve",
			"description": "Vazhdo streak 30-ditësh",
			"icon": "🔥",
			"category": "streak",
			"requirement_value": 30,
			"points_reward": 250,
		},
		{
			"code": "streak_100",
			"name": "Legjendë e Vazhdueshme",
			"description": "Vazhdo streak 100-ditësh",
			"icon": "🔥",
			"category": "streak",
			"requirement_value": 100,
			"points_reward": 1000,
		},
		# Accuracy achievements
		{
			"code": "perfect_level",
			"name": "Nivel Perfekt",
			"description": "Përfundo një nivel me 100% saktësi",
			"icon": "💯",
			"category": "accuracy",
			"requirement_value": 1,
			"points_reward": 50,
		},
		{
			"code": "accuracy_master",
			"name": "Mjeshtër i Saktësisë",
			"description": "Arri 95%+ saktësi me të paktën 50 ushtrime",
			"icon": "🎓",
			"category": "accuracy",
			"requirement_value": 95,
			"points_reward": 100,
		},
		# Progress achievements
		{
			"code": "class_master",
			"name": "Mjeshtër i Klasës",
			"description": "Përfundo një klasë të plotë",
			"icon": "👑",
			"category": "progress",
			"requirement_value": 1,
			"points_reward": 200,
		},
		{
			"code": "speed_demon",
			"name": "Shpejtësi Maksimale",
			"description": "Përfundo 20+ ushtrime në një ditë",
			"icon": "⚡",
			"category": "progress",
			"requirement_value": 20,
			"points_reward": 75,
		},
		{
			"code": "night_owl",
			"name": "Bufë e Natës",
			"description": "Përfundo ushtrime pas mesnatës",
			"icon": "🦉",
			"category": "special",
			"requirement_value": 1,
			"points_reward": 20,
		},
		{
			"code": "early_bird",
			"name": "Zog i Hershëm",
			"description": "Përfundo ushtrime para orës 7:00",
			"icon": "🌅",
			"category": "special",
			"requirement_value": 1,
			"points_reward": 20,
		},
		# Milestone achievements
		{
			"code": "milestone_100",
			"name": "Qind Ushtrime",
			"description": "Përfundo 100 ushtrime",
			"icon": "📚",
			"category": "progress",
			"requirement_value": 100,
			"points_reward": 100,
		},
		{
			"code": "milestone_500",
			"name": "Pesëqind Ushtrime",
			"description": "Përfundo 500 ushtrime",
			"icon": "📚",
			"category": "progress",
			"requirement_value": 500,
			"points_reward": 250,
		},
		{
			"code": "milestone_1000",
			"name": "Mijë Ushtrime",
			"description": "Përfundo 1000 ushtrime",
			"icon": "🏆",
			"category": "progress",
			"requirement_value": 1000,
			"points_reward": 500,
		},
	]
	
	print("Seeding achievements...")
	for data in achievements_data:
		# Check if already exists
		existing = db.query(models.Achievement).filter(models.Achievement.code == data["code"]).first()
		if existing:
			print(f"  ⏭️  Achievement '{data['code']}' already exists, skipping.")
			continue
		
		achievement = models.Achievement(**data)
		db.add(achievement)
		print(f"  ✅ Added achievement: {data['name']} ({data['code']})")
	
	db.commit()
	print("✅ Achievements seeded.")
	db.close()


def main():
	print("=" * 60)
	print("Gamification System Initialization")
	print("=" * 60)
	
	init_tables()
	seed_achievements()
	
	print("\n" + "=" * 60)
	print("✅ Gamification system initialized successfully!")
	print("=" * 60)


if __name__ == "__main__":
	main()
