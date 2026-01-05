from fastapi import APIRouter, UploadFile, File, Form, HTTPException, Depends
from sqlalchemy.orm import Session
from ..database import get_db
from .. import models
from pydantic import BaseModel
from typing import List, Optional, Dict, Any, Tuple
from io import BytesIO
import re
import unicodedata
import time

try:
	from PIL import Image
	import pytesseract
except ImportError:
	Image = None
	pytesseract = None

router = APIRouter()

# In-process cache for lexicon (keeps OCR fast). Safe for a single-process dev server.
_LEXICON_CACHE: Optional[set] = None
_BUCKETS_CACHE: Optional[Dict[Tuple[str, int], List[str]]] = None
_LEXICON_CACHE_AT: float = 0.0
_LEXICON_TTL_SECONDS: float = 300.0


class OCRAnalysisOut(BaseModel):
	extracted_text: str
	errors: List[Dict[str, Any]]
	suggestions: List[str]
	issues: List[Dict[str, Any]] = []
	meta: Dict[str, Any] = {}


def _norm_text(s: str) -> str:
	return re.sub(r"\s+", " ", unicodedata.normalize("NFKC", s or "").strip())


def _tokenize_sq(text: str) -> List[str]:
	# Albanian letters are covered by Unicode alpha + explicit ë/ç cases
	return re.findall(r"[A-Za-zËÇëç]+", text, flags=re.UNICODE)


def _preprocess_for_ocr(img: "Image.Image") -> "Image.Image":
	# Light preprocessing that helps Tesseract on scanned/phone images
	gray = img.convert("L")
	try:
		from PIL import ImageOps, ImageFilter
		gray = ImageOps.autocontrast(gray)
		gray = gray.filter(ImageFilter.MedianFilter(size=3))
	except Exception:
		pass
	# Simple threshold
	bw = gray.point(lambda x: 255 if x > 180 else 0, mode="1")
	return bw.convert("L")


def _levenshtein(a: str, b: str, max_dist: int = 2) -> int:
	# Bounded Levenshtein to keep it fast
	if a == b:
		return 0
	if abs(len(a) - len(b)) > max_dist:
		return max_dist + 1
	previous = list(range(len(b) + 1))
	for i, ca in enumerate(a, start=1):
		current = [i]
		min_row = current[0]
		for j, cb in enumerate(b, start=1):
			ins = current[j - 1] + 1
			delete = previous[j] + 1
			sub = previous[j - 1] + (0 if ca == cb else 1)
			val = min(ins, delete, sub)
			current.append(val)
			if val < min_row:
				min_row = val
		previous = current
		if min_row > max_dist:
			return max_dist + 1
	return previous[-1]


def _build_lexicon(db: Session) -> Tuple[set, Dict[Tuple[str, int], List[str]]]:
	# Use existing corpus (exercise prompts + answers) as an in-project "dictionary"
	global _LEXICON_CACHE, _BUCKETS_CACHE, _LEXICON_CACHE_AT
	now = time.time()
	if _LEXICON_CACHE is not None and _BUCKETS_CACHE is not None and (now - _LEXICON_CACHE_AT) < _LEXICON_TTL_SECONDS:
		return _LEXICON_CACHE, _BUCKETS_CACHE

	lex = set()
	buckets: Dict[Tuple[str, int], List[str]] = {}

	rows = db.query(models.Exercise.prompt, models.Exercise.answer).filter(models.Exercise.enabled == True).all()
	for prompt, answer in rows:
		for src in [prompt or "", answer or ""]:
			for tok in _tokenize_sq(_norm_text(src).lower()):
				w = tok.lower()
				if len(w) < 2:
					continue
				lex.add(w)

	for w in lex:
		key = (w[0], len(w))
		buckets.setdefault(key, []).append(w)

	_LEXICON_CACHE = lex
	_BUCKETS_CACHE = buckets
	_LEXICON_CACHE_AT = now
	return lex, buckets


def _issue_meta(issue_type: str, conf: Optional[float], has_suggestions: bool) -> Dict[str, Any]:
	"""
	Attach professional metadata:
	- source: 'ocr' or 'orthography'
	- severity: info/warning/error
	- likelihood: probability-like score that it's truly a spelling issue
	"""
	if issue_type == "low_confidence":
		return {"source": "ocr", "severity": "warning", "likelihood": 0.2}
	if issue_type == "mismatch_expected":
		return {"source": "orthography", "severity": "error", "likelihood": 0.95}
	if issue_type in ("diacritics_suspected", "double_consonant_suspected"):
		return {"source": "orthography", "severity": "warning", "likelihood": 0.8}
	if issue_type in ("ending_ë_suspected", "ç_suspected"):
		return {"source": "orthography", "severity": "warning", "likelihood": 0.85}
	if issue_type == "unknown_word":
		return {"source": "orthography", "severity": "warning" if has_suggestions else "info", "likelihood": 0.6 if has_suggestions else 0.35}
	return {"source": "orthography", "severity": "info", "likelihood": 0.5}


def _rule_based_candidates(token: str, lexicon: set) -> List[str]:
	"""
	Albanian-aware, conservative candidates based on frequent orthography/OCR patterns.
	Returns candidates that exist in lexicon.
	"""
	w = token.lower().strip()
	if not w:
		return []

	cands = []

	# 1) ë at the end is often missed (e.g., "shtepi" -> "shtëpi" not possible without dictionary,
	# but "e" -> "ë" at ending can still help in many cases)
	if w.endswith("e"):
		cands.append(w[:-1] + "ë")
	if not w.endswith("ë"):
		cands.append(w + "ë")

	# 2) ç vs c confusion (single replacement positions)
	for i, ch in enumerate(w):
		if ch == "c":
			cands.append(w[:i] + "ç" + w[i + 1 :])

	# 3) collapse double consonants (OCR repeats letters)
	cands.append(_collapse_double_consonants(w))

	# Dedupe, keep only present in lexicon
	out = []
	seen = set()
	for c in cands:
		if not c or c == w:
			continue
		if c in lexicon and c not in seen:
			seen.add(c)
			out.append(c)
	return out[:5]


def _suggest_from_lexicon(token: str, buckets: Dict[Tuple[str, int], List[str]], max_suggestions: int = 5) -> List[str]:
	t = token.lower()
	if not t:
		return []
	first = t[0]
	candidates: List[str] = []
	for ln in range(max(2, len(t) - 2), len(t) + 3):
		candidates.extend(buckets.get((first, ln), []))

	scored = []
	for c in candidates:
		d = _levenshtein(t, c, max_dist=2)
		if d <= 2:
			scored.append((d, c))
	scored.sort(key=lambda x: (x[0], x[1]))
	out = []
	for _, c in scored:
		if c not in out:
			out.append(c)
		if len(out) >= max_suggestions:
			break
	return out


def _collapse_double_consonants(word: str) -> str:
	# Reduce any double letters (e.g., tt -> t). Conservative but helpful for OCR noise.
	return re.sub(r"([A-Za-zËÇëç])\1+", r"\1", word, flags=re.UNICODE)


def _diacritics_normalize(word: str) -> str:
	return word.replace("ë", "e").replace("ç", "c")


def _is_diacritics_variant(a: str, b: str) -> bool:
	return _diacritics_normalize(a) == _diacritics_normalize(b) and a != b


def _extract_tokens_with_confidence(img: "Image.Image") -> Tuple[List[Dict[str, Any]], float]:
	"""
	Extract tokens with OCR confidence using Tesseract's image_to_data.
	Returns (tokens, avg_confidence).
	"""
	if not pytesseract:
		return [], 0.0
	try:
		output_type = getattr(pytesseract, "Output", None)
		data = pytesseract.image_to_data(
			img,
			lang="sqi",
			config="--oem 1 --psm 6 -c preserve_interword_spaces=1",
			output_type=(output_type.DICT if output_type else None),
		)
	except Exception:
		return [], 0.0

	texts = data.get("text", []) if isinstance(data, dict) else []
	confs = data.get("conf", []) if isinstance(data, dict) else []
	tokens: List[Dict[str, Any]] = []
	conf_values: List[float] = []

	for raw, conf in zip(texts, confs):
		raw = (raw or "").strip()
		if not raw:
			continue
		m = re.search(r"[A-Za-zËÇëç]+", raw, flags=re.UNICODE)
		if not m:
			continue
		token = m.group(0)
		try:
			c = float(conf)
		except Exception:
			c = -1.0
		if c >= 0:
			conf_values.append(c)
		tokens.append({"token": token, "raw": raw, "confidence": c})

	avg_conf = sum(conf_values) / len(conf_values) if conf_values else 0.0
	return tokens, avg_conf


@router.post("/ocr/analyze", response_model=OCRAnalysisOut)
async def analyze_dictation(
	image: UploadFile = File(...),
	expected_text: Optional[str] = Form(None),
	db: Session = Depends(get_db)
):
	"""Run OCR on an uploaded Albanian dictation image and analyze spelling (drejtshkrim)."""

	if not pytesseract or not Image:
		raise HTTPException(
			status_code=501,
			detail="OCR libraries not installed. Install pillow and pytesseract with system-level tesseract."
		)

	content = await image.read()
	try:
		ocr_image = Image.open(BytesIO(content))
	except Exception as exc:
		raise HTTPException(status_code=400, detail="Invalid image file") from exc

	ocr_ready = _preprocess_for_ocr(ocr_image)
	token_objs, avg_conf = _extract_tokens_with_confidence(ocr_ready)
	try:
		extracted = pytesseract.image_to_string(
			ocr_ready,
			lang="sqi",
			config="--oem 1 --psm 6 -c preserve_interword_spaces=1",
		).strip()
	except Exception:
		try:
			extracted = pytesseract.image_to_string(
				ocr_ready,
				config="--oem 1 --psm 6 -c preserve_interword_spaces=1",
			).strip()
		except Exception as exc:
			raise HTTPException(status_code=500, detail="OCR processing failed") from exc

	errors: List[Dict[str, Any]] = []
	suggestions: List[str] = []
	issues: List[Dict[str, Any]] = []

	extracted_norm = _norm_text(extracted)
	extracted_tokens = [t["token"] for t in token_objs] if token_objs else _tokenize_sq(extracted_norm)
	expected_norm = _norm_text(expected_text) if expected_text else ""
	expected_tokens = _tokenize_sq(expected_norm) if expected_text else []

	lexicon, buckets = _build_lexicon(db)

	if expected_text:
		# Compare token-by-token against expected reference text (orthography check)
		max_len = max(len(extracted_tokens), len(expected_tokens))
		for idx in range(max_len):
			rec_word = extracted_tokens[idx] if idx < len(extracted_tokens) else ""
			exp_word = expected_tokens[idx] if idx < len(expected_tokens) else ""
			if rec_word.lower() != exp_word.lower():
				errors.append({"position": idx + 1, "expected": exp_word, "recognized": rec_word})
				issues.append({
					"position": idx + 1,
					"token": rec_word or exp_word,
					"type": "mismatch_expected",
					"message": "Fjala nuk përputhet me tekstin e pritur.",
					"expected": exp_word,
					"recognized": rec_word,
					"suggestions": [exp_word] if exp_word else [],
					"ocr_confidence": (token_objs[idx]["confidence"] if token_objs and idx < len(token_objs) else None),
					**_issue_meta("mismatch_expected", None, bool(exp_word)),
				})
				if exp_word:
					suggestions.append(exp_word)
	else:
		# No reference text: run Albanian spelling heuristics using corpus lexicon
		for idx, tok in enumerate(extracted_tokens, start=1):
			w = tok.lower()
			if len(w) < 2:
				continue

			conf = None
			if token_objs and (idx - 1) < len(token_objs):
				conf = token_objs[idx - 1].get("confidence")

			# Flag low OCR-confidence tokens separately (often OCR noise, not orthography)
			if conf is not None and conf >= 0 and conf < 60:
				issues.append({
					"position": idx,
					"token": tok,
					"type": "low_confidence",
					"message": "Besueshmëri e ulët nga OCR — kontrollo manualisht këtë fjalë (mund të jetë gabim i nxjerrjes, jo i drejtshkrimit).",
					"expected": None,
					"recognized": tok,
					"suggestions": [],
					"ocr_confidence": conf,
					**_issue_meta("low_confidence", conf, False),
				})

			if w in lexicon:
				continue
			# Albanian-aware checks
			collapsed = _collapse_double_consonants(w)
			sugs: List[str] = []
			issue_type = "unknown_word"
			msg = "Fjalë e panjohur në korpus; mund të jetë gabim drejtshkrimi ose emër i përveçëm."

			# First: rule-based corrections (fast + Albanian-specific)
			rule_sugs = _rule_based_candidates(w, lexicon)
			if rule_sugs:
				sugs = rule_sugs
				# Determine which rule likely triggered
				if any(s.endswith("ë") and not w.endswith("ë") for s in rule_sugs):
					issue_type = "ending_ë_suspected"
					msg = "Dyshohet mungesë e 'ë' (shpesh në fund të fjalës). Shiko sugjerimet."
				elif any("ç" in s and "c" in w for s in rule_sugs):
					issue_type = "ç_suspected"
					msg = "Dyshohet gabim te 'ç' / 'c'. Shiko sugjerimet."
				elif collapsed != w and collapsed in lexicon:
					issue_type = "double_consonant_suspected"
					msg = "Dyshohet shkronjë e dyfishtë (shpesh gabim OCR ose gabim drejtshkrimi)."
			else:
				# Second: distance-based suggestions from corpus
				sugs = _suggest_from_lexicon(w, buckets, max_suggestions=5)
				if sugs and _is_diacritics_variant(w, sugs[0]):
					issue_type = "diacritics_suspected"
					msg = "Dyshohet gabim te ë/e ose ç/c. Shiko sugjerimet."
				elif sugs:
					msg = "Mund të ketë gabim drejtshkrimi. Shiko sugjerimet."
			issues.append({
				"position": idx,
				"token": tok,
				"type": issue_type,
				"message": msg,
				"expected": None,
				"recognized": tok,
				"suggestions": sugs,
				"ocr_confidence": conf,
				**_issue_meta(issue_type, conf, bool(sugs)),
			})

	return OCRAnalysisOut(
		extracted_text=extracted_norm,
		errors=errors,
		suggestions=suggestions,
		issues=issues,
		meta={
			"language": "sqi",
			"expected_provided": bool(expected_text),
			"tokens_extracted": len(extracted_tokens),
			"issues_found": len(issues),
			"ocr_confidence_avg": avg_conf,
		},
	)
