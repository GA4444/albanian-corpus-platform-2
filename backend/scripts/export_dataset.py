import argparse
import csv
import json
import os
import sys
import secrets
import hashlib
from datetime import datetime
from typing import Any, Dict, Iterable, List, Optional

# Ensure backend/ is on sys.path when running as a script (python scripts/export_dataset.py)
BACKEND_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
if BACKEND_DIR not in sys.path:
	sys.path.insert(0, BACKEND_DIR)

from app.database import SessionLocal  # noqa: E402
from app import models  # noqa: E402


def _now_slug() -> str:
	return datetime.utcnow().strftime("%Y%m%d_%H%M%S")


def _ensure_dir(path: str) -> None:
	os.makedirs(path, exist_ok=True)


def _sha256_hex(value: str) -> str:
	return hashlib.sha256(value.encode("utf-8")).hexdigest()


def _user_pseudo(user_id: str, salt: str) -> str:
	# stable within one export (salted)
	return _sha256_hex(f"{salt}::user::{user_id}")[:16]


def _write_jsonl(path: str, rows: Iterable[Dict[str, Any]]) -> int:
	count = 0
	with open(path, "w", encoding="utf-8") as f:
		for r in rows:
			f.write(json.dumps(r, ensure_ascii=False) + "\n")
			count += 1
	return count


def _write_csv(path: str, rows: List[Dict[str, Any]]) -> int:
	if not rows:
		with open(path, "w", encoding="utf-8") as f:
			f.write("")
		return 0
	fieldnames = sorted({k for r in rows for k in r.keys()})
	with open(path, "w", encoding="utf-8", newline="") as f:
		w = csv.DictWriter(f, fieldnames=fieldnames)
		w.writeheader()
		for r in rows:
			w.writerow(r)
	return len(rows)


def main():
	parser = argparse.ArgumentParser(description="Export ALBLingo dataset from the local DB.")
	parser.add_argument("--out", default=f"dataset_export/{_now_slug()}", help="Output directory")
	parser.add_argument("--format", choices=["jsonl", "csv"], default="jsonl", help="Export format")
	parser.add_argument("--include-attempts", action="store_true", help="Include attempts (anonymized)")
	parser.add_argument("--include-progress", action="store_true", help="Include progress and course_progress (anonymized)")
	parser.add_argument("--include-users", action="store_true", help="Include users (PII excluded, user ids anonymized)")
	parser.add_argument("--salt", default=None, help="Salt used for anonymization (stored in output; keep it private)")
	args = parser.parse_args()

	out_dir = os.path.abspath(args.out)
	_ensure_dir(out_dir)

	salt = args.salt or secrets.token_hex(16)
	with open(os.path.join(out_dir, "ANONYMIZATION_SALT.txt"), "w", encoding="utf-8") as f:
		f.write(salt + "\n")

	db = SessionLocal()
	try:
		# COURSES (includes 'classes' as those with parent_class_id == None)
		courses = db.query(models.Course).all()
		courses = sorted(
			courses,
			key=lambda c: (0 if c.parent_class_id is None else 1, c.parent_class_id or 0, c.order_index or 0, c.id),
		)
		course_rows: List[Dict[str, Any]] = []
		for c in courses:
			course_rows.append({
				"id": c.id,
				"name": c.name,
				"description": c.description,
				"order_index": c.order_index,
				"category": c.category.value if c.category else None,
				"required_score": c.required_score,
				"enabled": bool(c.enabled),
				"parent_class_id": c.parent_class_id,
				"is_class": c.parent_class_id is None,
			})

		# LEVELS
		levels = db.query(models.Level).order_by(models.Level.course_id.asc(), models.Level.order_index.asc()).all()
		level_rows: List[Dict[str, Any]] = []
		for l in levels:
			level_rows.append({
				"id": l.id,
				"course_id": l.course_id,
				"name": l.name,
				"description": l.description,
				"order_index": l.order_index,
				"required_score": l.required_score,
				"enabled": bool(l.enabled),
			})

		# EXERCISES
		exercises = db.query(models.Exercise).order_by(models.Exercise.level_id.asc(), models.Exercise.order_index.asc()).all()
		ex_rows: List[Dict[str, Any]] = []
		for e in exercises:
			ex_rows.append({
				"id": e.id,
				"course_id": e.course_id,
				"level_id": e.level_id,
				"order_index": e.order_index,
				"category": e.category.value if e.category else None,
				"prompt": e.prompt,
				"answer": e.answer,
				"data": e.data,
				"rule": e.rule,
				"points": e.points,
				"enabled": bool(e.enabled),
			})

		user_map: Dict[str, str] = {}
		def pseudo(uid: Any) -> str:
			uid_str = str(uid)
			if uid_str not in user_map:
				user_map[uid_str] = _user_pseudo(uid_str, salt)
			return user_map[uid_str]

		# ATTEMPTS (anonymized)
		attempt_rows: List[Dict[str, Any]] = []
		if args.include_attempts:
			attempts = db.query(models.Attempt).order_by(models.Attempt.id.asc()).all()
			for a in attempts:
				attempt_rows.append({
					"id": a.id,
					"user_id": pseudo(a.user_id),
					"exercise_id": a.exercise_id,
					"response": a.response,
					"is_correct": bool(a.is_correct),
					"score_delta": a.score_delta,
				})

		# PROGRESS + COURSE_PROGRESS (anonymized, coarse)
		progress_rows: List[Dict[str, Any]] = []
		course_progress_rows: List[Dict[str, Any]] = []
		if args.include_progress:
			progress = db.query(models.Progress).order_by(models.Progress.user_id.asc(), models.Progress.level_id.asc()).all()
			for p in progress:
				progress_rows.append({
					"id": p.id,
					"user_id": pseudo(p.user_id),
					"category": p.category.value if p.category else None,
					"course_id": p.course_id,
					"level_id": p.level_id,
					"points": p.points,
					"errors": p.errors,
					"stars": p.stars,
					"completed": bool(p.completed),
				})

			cp = db.query(models.CourseProgress).order_by(models.CourseProgress.user_id.asc(), models.CourseProgress.course_id.asc()).all()
			for row in cp:
				course_progress_rows.append({
					"id": row.id,
					"user_id": pseudo(row.user_id),
					"course_id": row.course_id,
					"accuracy_percentage": row.accuracy_percentage,
					"completed_exercises": row.completed_exercises,
					"total_exercises": row.total_exercises,
					"correct_answers": row.correct_answers,
					"total_points": row.total_points,
					"is_completed": bool(row.is_completed),
					"is_unlocked": bool(row.is_unlocked),
				})

		# USERS (PII excluded, anonymized)
		user_rows: List[Dict[str, Any]] = []
		if args.include_users:
			users = db.query(models.User).order_by(models.User.id.asc()).all()
			for u in users:
				user_rows.append({
					"user_id": pseudo(u.id),
					"age": u.age,
					"is_active": bool(u.is_active),
					"is_admin": bool(u.is_admin),
					"created_at": u.created_at.isoformat() if u.created_at else None,
				})

		# Write files
		manifest = {
			"generated_at_utc": datetime.utcnow().isoformat() + "Z",
			"database": "sqlite:///./dev.db (default)",
			"format": args.format,
			"tables": {},
			"privacy": {
				"users_included": args.include_users,
				"attempts_included": args.include_attempts,
				"progress_included": args.include_progress,
				"user_ids_anonymized": True,
				"note": "Keep ANONYMIZATION_SALT.txt private if sharing datasets publicly.",
			},
		}

		def write_table(name: str, rows: List[Dict[str, Any]]):
			if args.format == "jsonl":
				path = os.path.join(out_dir, f"{name}.jsonl")
				n = _write_jsonl(path, rows)
			else:
				path = os.path.join(out_dir, f"{name}.csv")
				n = _write_csv(path, rows)
			manifest["tables"][name] = {"rows": n, "path": os.path.basename(path)}

		write_table("courses", course_rows)
		write_table("levels", level_rows)
		write_table("exercises", ex_rows)
		if args.include_attempts:
			write_table("attempts", attempt_rows)
		if args.include_progress:
			write_table("progress", progress_rows)
			write_table("course_progress", course_progress_rows)
		if args.include_users:
			write_table("users", user_rows)

		with open(os.path.join(out_dir, "manifest.json"), "w", encoding="utf-8") as f:
			json.dump(manifest, f, ensure_ascii=False, indent=2)

		readme = """\
ALBLingo Dataset Export

This folder was generated by backend/scripts/export_dataset.py.

Files:
- courses: classes + sub-courses (classes have parent_class_id = null)
- levels
- exercises (your Albanian spelling corpus content)
- attempts (optional, anonymized)
- progress + course_progress (optional, anonymized)
- users (optional, anonymized; no email/username/password)

Notes:
- Token ANONYMIZATION_SALT.txt is required to reproduce the same pseudonyms. Keep it private.
"""
		with open(os.path.join(out_dir, "README.txt"), "w", encoding="utf-8") as f:
			f.write(readme)

		print("✅ Dataset export completed.")
		print("Output:", out_dir)
		print("Manifest:", os.path.join(out_dir, "manifest.json"))
	finally:
		db.close()


if __name__ == "__main__":
	main()

