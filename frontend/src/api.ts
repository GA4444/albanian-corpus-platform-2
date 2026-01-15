import axios from 'axios'

export type Category =
	| 'listen_write'
	| 'word_from_description'
	| 'synonyms_antonyms'
	| 'albanian_or_loanword'
	| 'missing_letter'
	| 'wrong_letter'
	| 'build_word'
	| 'number_to_word'
	| 'phrases'
	| 'spelling_punctuation'
	| 'abstract_concrete'
	| 'build_sentence'
	| 'vocabulary'
	| 'spelling'
	| 'grammar'
	| 'numbers'
	| 'punctuation'

export interface CourseOut {
	id: number
	name: string
	description?: string | null
	order_index: number
	category: Category
	required_score: number
	enabled: boolean
	parent_class_id?: number | null
	levels?: LevelOut[]
	progress?: {
		accuracy_percentage: number
		is_completed: boolean
		total_points: number
		completed_exercises: number
		total_exercises: number
	}
}

export interface LevelOut {
	id: number
	course_id: number
	name: string
	description?: string | null
	order_index: number
	required_score: number
	enabled: boolean
}

export interface ExerciseOut {
	id: number
	category: Category
	course_id: number
	level_id: number
	prompt: string
	data?: string | null
	points: number
	rule?: string | null
	order_index: number
}

export interface SubmitRequest {
	user_id: string
	response: string
}

export interface SubmitResult {
	exercise_id: number
	is_correct: boolean
	score_delta: number
	new_points: number
	new_errors: number
	stars: number
	level_completed: boolean
	course_completed: boolean
	message: string
}

export interface ProgressOut {
	category: Category
	course_id: number
	level_id: number
	points: number
	errors: number
	stars: number
	completed: boolean
}

export interface CategoryStatusOut {
  category: Category
  total_attempts: number
  correct_attempts: number
  accuracy: number
  can_advance: boolean
}

export interface CourseProgressOut {
	course: CourseOut
	levels: LevelOut[]
	progress: ProgressOut[]
	unlocked: boolean
	completed: boolean
	overall_score: number
}

export interface UserProgressOut {
	user_id: string
	total_points: number
	total_stars: number
	courses: CourseProgressOut[]
}

export interface ClassData {
	id: number
	name: string
	description: string
	order_index: number
	enabled: boolean
	courses?: CourseOut[]  // Optional: not always loaded from API
	unlocked: boolean
	completed: boolean
	progress_percent?: number
}

export interface OCRAnalysisResponse {
	extracted_text: string
	refined_text?: string | null  // LLM-refined text
	errors: {
		position: number
		expected: string
		recognized: string
	}[]
	suggestions: string[]
	issues?: {
		position: number
		token: string
		type: string
		source?: 'ocr' | 'orthography'
		severity?: 'info' | 'warning' | 'error'
		likelihood?: number
		message: string
		expected?: string | null
		recognized?: string | null
		suggestions: string[]
		ocr_confidence?: number | null
	}[]
	llm_corrections?: {
		original: string
		corrected: string
		reason: string
	}[]
	meta?: {
		language?: string
		expected_provided?: boolean
		tokens_extracted?: number
		issues_found?: number
		ocr_confidence_avg?: number
		ocr_engine?: string
		llm_enabled?: boolean
		llm_model?: string
		llm_confidence?: number
		llm_processing_time_ms?: number
		pipeline_version?: string
		[key: string]: any
	}
}

export interface PersonalizedPracticeRequest {
	user_id: string
	class_id: number
	level_id: number
}

export interface AIPracticeExercise {
	id: string
	prompt: string
	answer: string
	category: Category | 'spelling'
	hint?: string
	order_index: number
}

export interface PersonalizedPracticeResponse {
	exercises: AIPracticeExercise[]
	message: string
}

export interface AICoachRequest {
	user_id: string
	level_id?: number | null
}

export interface AICoachMistakePattern {
	type: string
	count: number
	examples: string[]
}

export interface AICoachResponse {
	user_id: string
	level_id?: number | null
	total_attempts_analyzed: number
	incorrect_attempts_analyzed: number
	patterns: AICoachMistakePattern[]
	micro_lessons: string[]
	drill_plan: string[]
}

// Get API base URL from environment variable or use relative path for development
const API_BASE_URL = import.meta.env.VITE_API_BASE_URL || ''
const client = axios.create({ baseURL: API_BASE_URL })
client.interceptors.request.use((config) => {
  const token = localStorage.getItem('token')
  if (token) {
    config.headers = config.headers ?? {}
    ;(config.headers as any).Authorization = `Bearer ${token}`
  }
  return config
})

export async function fetchCourses() {
	const { data } = await client.get<CourseOut[]>('/api/courses')
	return data
}

export async function fetchLevels(courseId: number) {
	const { data } = await client.get<LevelOut[]>(`/api/courses/${courseId}/levels`)
	return data
}

export async function fetchExercisesByLevel(levelId: number) {
	const { data } = await client.get<ExerciseOut[]>(`/api/levels/${levelId}/exercises`)
	return data
}

export async function fetchExercises(category: Category) {
	const { data } = await client.get<ExerciseOut[]>(`/api/exercises/${category}`)
	return data
}

export async function submitAnswer(exerciseId: number, body: SubmitRequest) {
	const { data } = await client.post<SubmitResult>(`/api/${exerciseId}/submit`, body)
	return data
}

export async function fetchProgress(userId: string) {
	const { data } = await client.get<ProgressOut[]>(`/api/progress/${userId}`)
	return data
}

export async function fetchStatus(userId: string) {
  const { data } = await client.get<CategoryStatusOut[]>(`/api/progress/${userId}/status`)
  return data
}

export async function fetchUserOverview(userId: string) {
	const { data } = await client.get<UserProgressOut>(`/api/progress/${userId}/overview`)
	return data
}

export async function fetchCourseProgress(courseId: number, userId: string) {
	const { data } = await client.get<CourseProgressOut>(`/api/courses/${courseId}/progress/${userId}`)
	return data
}

export async function fetchLevelProgress(courseId: number, levelId: number, userId: string) {
	const { data } = await client.get<ProgressOut>(`/api/courses/${courseId}/levels/${levelId}/progress/${userId}`)
	return data
}

// AI-powered endpoints
export async function getAIRecommendations(userId: string) {
	const { data } = await client.get(`/api/ai/recommendations/${userId}`)
	return data
}

export async function getAdaptiveDifficulty(userId: string) {
	const { data } = await client.get(`/api/ai/adaptive-difficulty/${userId}`)
	return data
}

export async function getLearningPath(userId: string) {
	const { data } = await client.get(`/api/ai/learning-path/${userId}`)
	return data
}

export async function fetchAIPersonalizedPractice(body: PersonalizedPracticeRequest) {
	const { data } = await client.post<PersonalizedPracticeResponse>('/api/ai/personalized-practice', body)
	return data
}

export async function fetchAICoach(body: AICoachRequest) {
	const { data } = await client.post<AICoachResponse>('/api/ai/coach', body)
	return data
}

export async function analyzeOCR(formData: FormData) {
	const { data } = await client.post<OCRAnalysisResponse>('/api/ocr/analyze', formData, {
		headers: {
			'Content-Type': 'multipart/form-data'
		}
	})
	return data
}

export async function getSmartHints(exerciseId: number, userId: string) {
	const { data } = await client.get(`/api/ai/smart-hints/${exerciseId}/${userId}`)
	return data
}

export async function getProgressInsights(userId: string) {
	const { data } = await client.get(`/api/ai/progress-insights/${userId}`)
	return data
}

export async function login(username: string, password: string) {
	const { data } = await client.post('/api/login', { username, password })
	return data
}

export async function register(
	username: string,
	email: string,
	password: string,
	age?: number
) {
	const { data } = await client.post('/api/register', {
		username,
		email,
		password,
		age
	})
	return data
}

export async function getClasses(userId?: string) {
	const url = userId ? `/api/classes?user_id=${userId}` : '/api/classes'
	const { data } = await client.get(url)
	return data
}

export async function getClassCourses(classId: number, userId: string) {
	const { data } = await client.get(`/api/classes/${classId}/courses?user_id=${userId}`)
	return data
}

export async function getCourseLevels(courseId: number) {
	const { data } = await client.get<LevelOut[]>(`/api/courses/${courseId}/levels`)
	return data
}

export async function getLevelExercises(levelId: number) {
	const { data } = await client.get<ExerciseOut[]>(`/api/levels/${levelId}/exercises`)
	return data
}

export interface PublicStats {
	total_classes: number
	total_courses: number
	total_levels: number
	total_exercises: number
	total_categories: number
}

export async function getPublicStats() {
	const { data } = await client.get<PublicStats>('/api/public-stats')
	return data
}

export interface LeaderboardEntry {
	rank: number
	user_id: number
	username: string
	total_points: number
	total_correct: number
	total_attempts: number
	accuracy: number
	completed_courses: number
	level: number
}

export async function getLeaderboard(limit: number = 0) {
	// limit=0 -> fetch all users
	const { data } = await client.get<LeaderboardEntry[]>(`/api/leaderboard?limit=${limit}`)
	return data
}

export async function getUserRank(userId: number) {
	const { data } = await client.get(`/api/leaderboard/${userId}/rank`)
	return data
}

// Admin API interfaces and functions
export interface UserOut {
	id: number
	username: string
	email: string
	age?: number | null
	date_of_birth?: string | null
	address?: string | null
	phone_number?: string | null
	created_at: string
	last_login?: string | null
	is_active: boolean
	is_admin: boolean
}

export interface AdminStats {
	total_users: number
	total_classes: number
	total_courses: number
	total_levels: number
	total_exercises: number
	total_attempts: number
}

export async function createAdminUser(userData: { username: string; email: string; password: string; age?: number }) {
	const { data } = await client.post('/api/admin/create-admin-user', userData)
	return data
}

export async function getAdminStats(userId: number) {
	const { data } = await client.get<AdminStats>(`/api/admin/stats?user_id=${userId}`)
	return data
}

export async function getAllUsers(userId: number) {
	const { data } = await client.get<UserOut[]>(`/api/admin/users?user_id=${userId}`)
	return data
}

export async function getUser(userId: number, targetUserId: number) {
	const { data } = await client.get<UserOut>(`/api/admin/users/${targetUserId}?user_id=${userId}`)
	return data
}

export async function getUserProfile(userId: number) {
	const { data } = await client.get<UserOut>(`/api/user/${userId}`)
	return data
}

export interface UserProfileUpdate {
	email?: string
	age?: number
	date_of_birth?: string
	address?: string
	phone_number?: string
}

export async function updateUserProfile(userId: number, profileUpdate: UserProfileUpdate) {
	const { data } = await client.put<UserOut>(`/api/user/${userId}/profile`, profileUpdate)
	return data
}

export async function updateUser(userId: number, targetUserId: number, userUpdate: Partial<UserOut>) {
	const { data } = await client.put(`/api/admin/users/${targetUserId}?user_id=${userId}`, userUpdate)
	return data
}

export async function deleteUser(userId: number, targetUserId: number) {
	const { data } = await client.delete(`/api/admin/users/${targetUserId}?user_id=${userId}`)
	return data
}

export async function getAllClasses(userId: number) {
	const { data } = await client.get<ClassData[]>(`/api/admin/classes?user_id=${userId}`)
	return data
}

export async function createClass(userId: number, classData: { name: string; description?: string; order_index?: number; enabled?: boolean }) {
	const { data } = await client.post<CourseOut>(`/api/admin/classes?user_id=${userId}`, classData)
	return data
}

export async function updateClass(userId: number, classId: number, classUpdate: Partial<ClassData>) {
	const { data } = await client.put<CourseOut>(`/api/admin/classes/${classId}?user_id=${userId}`, classUpdate)
	return data
}

export async function deleteClass(userId: number, classId: number) {
	const { data } = await client.delete(`/api/admin/classes/${classId}?user_id=${userId}`)
	return data
}

export async function getAllLevels(userId: number, courseId?: number) {
	const url = courseId 
		? `/api/admin/levels?user_id=${userId}&course_id=${courseId}`
		: `/api/admin/levels?user_id=${userId}`
	const { data } = await client.get<LevelOut[]>(url)
	return data
}

export async function createLevel(userId: number, levelData: { course_id: number; name: string; description?: string; order_index?: number; required_score?: number; enabled?: boolean }) {
	const { data } = await client.post<LevelOut>(`/api/admin/levels?user_id=${userId}`, levelData)
	return data
}

export async function updateLevel(userId: number, levelId: number, levelUpdate: Partial<LevelOut>) {
	const { data } = await client.put<LevelOut>(`/api/admin/levels/${levelId}?user_id=${userId}`, levelUpdate)
	return data
}

export async function deleteLevel(userId: number, levelId: number) {
	const { data } = await client.delete(`/api/admin/levels/${levelId}?user_id=${userId}`)
	return data
}

export async function getAllExercises(userId: number, levelId?: number, courseId?: number) {
	let url = `/api/admin/exercises?user_id=${userId}`
	if (levelId) url += `&level_id=${levelId}`
	if (courseId) url += `&course_id=${courseId}`
	const { data } = await client.get<ExerciseOut[]>(url)
	return data
}

export async function getExercise(userId: number, exerciseId: number) {
	const { data } = await client.get<ExerciseOut>(`/api/admin/exercises/${exerciseId}?user_id=${userId}`)
	return data
}

export async function createExercise(userId: number, exerciseData: { category: Category; course_id: number; level_id: number; prompt: string; data?: string; answer: string; points?: number; rule?: string; order_index?: number; enabled?: boolean }) {
	const { data } = await client.post<ExerciseOut>(`/api/admin/exercises?user_id=${userId}`, exerciseData)
	return data
}

export async function updateExercise(userId: number, exerciseId: number, exerciseUpdate: Partial<ExerciseOut>) {
	const { data } = await client.put<ExerciseOut>(`/api/admin/exercises/${exerciseId}?user_id=${userId}`, exerciseUpdate)
	return data
}

export async function deleteExercise(userId: number, exerciseId: number) {
	const { data } = await client.delete(`/api/admin/exercises/${exerciseId}?user_id=${userId}`)
	return data
}

// ============================================================================
// GAMIFICATION API
// ============================================================================

export interface Achievement {
	id: number
	code: string
	name: string
	description: string | null
	icon: string | null
	category: string | null
	requirement_value: number | null
	points_reward: number
}

export interface UserAchievement extends Achievement {
	earned_at: string
}

export interface UserAchievementsResponse {
	total_achievements: number
	achievements: UserAchievement[]
}

export interface StreakData {
	current_streak: number
	longest_streak: number
	last_activity_date: string | null
}

export interface DailyChallenge {
	id: number
	date: string
	challenge_type: string
	target_value: number | null
	description: string
	points_reward: number
	level_id: number | null
	user_progress?: {
		current_value: number
		completed: boolean
		completed_at: string | null
	}
}

export interface SRSCard {
	id: number
	exercise_id: number
	word: string
	next_review_date: string
	ease_factor: number
	interval_days: number
	total_reviews: number
	correct_reviews: number
}

export interface SRSDueCardsResponse {
	due_count: number
	cards: SRSCard[]
}

export interface SRSStatsResponse {
	total_cards: number
	due_cards: number
	total_reviews: number
	correct_reviews: number
	accuracy: number
}

export interface SRSReviewResponse {
	card_id: number
	next_review_date: string
	interval_days: number
	ease_factor: number
	repetitions: number
}

// Get all possible achievements
export async function getAllAchievements() {
	const { data } = await client.get<Achievement[]>('/api/gamification/achievements')
	return data
}

// Get user's earned achievements
export async function getUserAchievements(userId: string) {
	const { data } = await client.get<UserAchievementsResponse>(`/api/gamification/achievements/${userId}`)
	return data
}

// Get user's streak data
export async function getUserStreak(userId: string) {
	const { data } = await client.get<StreakData>(`/api/gamification/streak/${userId}`)
	return data
}

// Get today's daily challenge
export async function getDailyChallenge(userId?: string) {
	const url = userId ? `/api/gamification/daily-challenge?user_id=${userId}` : '/api/gamification/daily-challenge'
	const { data } = await client.get<DailyChallenge>(url)
	return data
}

// Get SRS cards due for review
export async function getDueSRSCards(userId: string, limit: number = 10) {
	const { data } = await client.get<SRSDueCardsResponse>(`/api/gamification/srs/due/${userId}?limit=${limit}`)
	return data
}

// Review an SRS card
export async function reviewSRSCard(cardId: number, quality: number) {
	const { data } = await client.post<SRSReviewResponse>('/api/gamification/srs/review', { card_id: cardId, quality })
	return data
}

// Get SRS statistics
export async function getSRSStats(userId: string) {
	const { data } = await client.get<SRSStatsResponse>(`/api/gamification/srs/stats/${userId}`)
	return data
}

// ============================================================================
// CHATBOT API
// ============================================================================

export interface ChatMessage {
	message: string
	user_id?: string
	context?: Record<string, any>
}

export interface ChatResponse {
	response: string
	suggestions?: string[]
	related_topics?: string[]
	timestamp: string
}

export interface ChatTopic {
	title: string
	icon: string
	questions: string[]
}

export interface ChatTopicsResponse {
	topics: ChatTopic[]
}

export interface ChatSuggestionsResponse {
	suggestions: string[]
}

// Ask chatbot a question
export async function askChatbot(message: ChatMessage) {
	const { data } = await client.post<ChatResponse>('/api/chatbot/ask', message)
	return data
}

// Get quick suggestions
export async function getChatSuggestions() {
	const { data } = await client.get<ChatSuggestionsResponse>('/api/chatbot/suggestions')
	return data
}

// Get available topics
export async function getChatTopics() {
	const { data } = await client.get<ChatTopicsResponse>('/api/chatbot/topics')
	return data
}