import React, { useState, useEffect } from 'react'
import {
	getAdminStats,
	getAllUsers,
	getAllClasses,
	getAllLevels,
	getAllExercises,
	createClass,
	createLevel,
	createExercise,
	updateUser,
	updateClass,
	updateLevel,
	updateExercise,
	deleteUser,
	deleteClass,
	deleteLevel,
	deleteExercise,
	getCourseLevels,
	type UserOut,
	type AdminStats,
	type ClassData,
	type LevelOut,
	type ExerciseOut,
	type Category
} from './api'
import './AdminDashboard.css'

interface AdminDashboardProps {
	userId: number
	onLogout: () => void
}

export default function AdminDashboard({ userId, onLogout }: AdminDashboardProps) {
	const [activeTab, setActiveTab] = useState<'stats' | 'users' | 'classes' | 'levels' | 'exercises'>('stats')
	const [stats, setStats] = useState<AdminStats | null>(null)
	const [users, setUsers] = useState<UserOut[]>([])
	const [classes, setClasses] = useState<ClassData[]>([])
	const [levels, setLevels] = useState<LevelOut[]>([])
	const [exercises, setExercises] = useState<ExerciseOut[]>([])
	const [selectedClass, setSelectedClass] = useState<number | null>(null)
	const [selectedLevel, setSelectedLevel] = useState<number | null>(null)
	const [loading, setLoading] = useState(false)
	const [editingUser, setEditingUser] = useState<UserOut | null>(null)
	const [editingClass, setEditingClass] = useState<ClassData | null>(null)
	const [editingLevel, setEditingLevel] = useState<LevelOut | null>(null)
	const [editingExercise, setEditingExercise] = useState<ExerciseOut | null>(null)
	const [showCreateModal, setShowCreateModal] = useState<'class' | 'level' | 'exercise' | null>(null)

	useEffect(() => {
		loadData()
		// eslint-disable-next-line react-hooks/exhaustive-deps
	}, [activeTab, selectedClass, selectedLevel])

	const loadData = async () => {
		setLoading(true)
		try {
			if (activeTab === 'stats') {
				const statsData = await getAdminStats(userId)
				setStats(statsData)
			} else if (activeTab === 'users') {
				const usersData = await getAllUsers(userId)
				setUsers(usersData)
			} else if (activeTab === 'classes') {
				const classesData = await getAllClasses(userId)
				setClasses(classesData)
				
				// Load levels for all courses in all classes to enable global numbering
				// This is done in the background to not block the UI
				Promise.all(
					classesData.map(async (classData: ClassData) => {
						try {
							const coursesWithLevels = await Promise.all(
								(classData.courses || []).map(async (course) => {
									try {
										// Fetch levels for this course
										const levels = await getCourseLevels(course.id)
										return { ...course, levels }
									} catch (error) {
										console.error(`Error fetching levels for course ${course.id}:`, error)
										return { ...course, levels: [] }
									}
								})
							)
							return { ...classData, courses: coursesWithLevels }
						} catch (error) {
							console.error(`Error loading levels for class ${classData.id}:`, error)
							return classData
						}
					})
				).then(classesWithLevels => {
					setClasses(classesWithLevels)
				}).catch(error => {
					console.error('Error loading levels for classes:', error)
				})
			} else if (activeTab === 'levels') {
				const levelsData = await getAllLevels(userId, selectedClass || undefined)
				setLevels(levelsData)
			} else if (activeTab === 'exercises') {
				const exercisesData = await getAllExercises(userId, selectedLevel || undefined, selectedClass || undefined)
				setExercises(exercisesData)
			}
		} catch (error) {
			console.error('Error loading data:', error)
			alert('Gabim në ngarkimin e të dhënave')
		} finally {
			setLoading(false)
		}
	}

	const handleCreateClass = async (name: string, description?: string) => {
		try {
			await createClass(userId, { name, description, order_index: classes.length + 1 })
			await loadData()
			setShowCreateModal(null)
		} catch (error) {
			alert('Gabim në krijimin e klasës')
		}
	}

	const handleCreateLevel = async (courseId: number, name: string, description?: string) => {
		try {
			await createLevel(userId, { course_id: courseId, name, description, order_index: levels.length + 1 })
			await loadData()
			setShowCreateModal(null)
		} catch (error) {
			alert('Gabim në krijimin e nivelit')
		}
	}

	const handleCreateExercise = async (exerciseData: {
		category: Category
		course_id: number
		level_id: number
		prompt: string
		answer: string
		data?: string
		points?: number
	}) => {
		try {
			await createExercise(userId, exerciseData)
			await loadData()
			setShowCreateModal(null)
		} catch (error) {
			alert('Gabim në krijimin e ushtrimit')
		}
	}

	const handleDeleteUser = async (targetUserId: number) => {
		if (confirm('Jeni të sigurt që dëshironi të fshini këtë përdorues?')) {
			try {
				await deleteUser(userId, targetUserId)
				await loadData()
			} catch (error) {
				alert('Gabim në fshirjen e përdoruesit')
			}
		}
	}

	const handleDeleteClass = async (classId: number) => {
		if (confirm('Jeni të sigurt që dëshironi të fshini këtë klasë?')) {
			try {
				await deleteClass(userId, classId)
				await loadData()
			} catch (error) {
				alert('Gabim në fshirjen e klasës')
			}
		}
	}

	const handleDeleteLevel = async (levelId: number) => {
		if (confirm('Jeni të sigurt që dëshironi të fshini këtë nivel?')) {
			try {
				await deleteLevel(userId, levelId)
				await loadData()
			} catch (error) {
				alert('Gabim në fshirjen e nivelit')
			}
		}
	}

	const handleDeleteExercise = async (exerciseId: number) => {
		if (confirm('Jeni të sigurt që dëshironi të fshini këtë ushtrim?')) {
			try {
				await deleteExercise(userId, exerciseId)
				await loadData()
			} catch (error) {
				alert('Gabim në fshirjen e ushtrimit')
			}
		}
	}

	const handleUpdateUser = async (userData: Partial<UserOut>) => {
		if (!editingUser) return
		try {
			await updateUser(userId, editingUser.id, userData)
			await loadData()
			setEditingUser(null)
		} catch (error) {
			alert('Gabim në përditësimin e përdoruesit')
		}
	}

	const handleUpdateClass = async (classData: Partial<ClassData>) => {
		if (!editingClass) return
		try {
			await updateClass(userId, editingClass.id, classData)
			await loadData()
			setEditingClass(null)
		} catch (error) {
			alert('Gabim në përditësimin e klasës')
		}
	}

	const handleUpdateLevel = async (levelData: Partial<LevelOut>) => {
		if (!editingLevel) return
		try {
			await updateLevel(userId, editingLevel.id, levelData)
			await loadData()
			setEditingLevel(null)
		} catch (error) {
			alert('Gabim në përditësimin e nivelit')
		}
	}

	const handleUpdateExercise = async (exerciseData: Partial<ExerciseOut>) => {
		if (!editingExercise) return
		try {
			await updateExercise(userId, editingExercise.id, exerciseData)
			await loadData()
			setEditingExercise(null)
		} catch (error) {
			alert('Gabim në përditësimin e ushtrimit')
		}
	}

	const handleEditClass = (cls: ClassData) => {
		setEditingClass(cls)
	}

	const handleEditLevel = (level: LevelOut) => {
		setEditingLevel(level)
	}

	// Helper function to get class name for a level
	const getLevelClassName = (level: LevelOut): string => {
		// Find the course for this level
		const course = classes.flatMap(cls => cls.courses || []).find(c => c.id === level.course_id)
		if (course && course.parent_class_id) {
			// Find the class
			const classData = classes.find(cls => cls.id === course.parent_class_id)
			if (classData) {
				return classData.name
			}
		}
		return '-'
	}

	// Helper function to get level display name with class (global numbering across all classes)
	const getLevelDisplayName = (level: LevelOut): string => {
		// Find the course for this level
		const course = classes.flatMap(cls => cls.courses || []).find(c => c.id === level.course_id)
		if (course && course.parent_class_id) {
			// Find the class
			const classData = classes.find(cls => cls.id === course.parent_class_id)
			if (classData) {
				// Calculate global level number: sum of all levels in previous classes + levels in current class before this level
				let globalLevelNumber = 0
				// Sort classes by order_index
				const sortedClasses = [...classes].sort((a, b) => a.order_index - b.order_index)
				
				for (const cls of sortedClasses) {
					if (cls.id === classData.id) {
						// We're in the current class
						// Sort courses by order_index
						const sortedCourses = [...(cls.courses || [])].sort((a, b) => a.order_index - b.order_index)
						
						for (const c of sortedCourses) {
							if (c.id === course.id) {
								// We're in the current course
								// Sort levels by order_index
								const sortedLevels = [...(c.levels || [])].sort((a, b) => a.order_index - b.order_index)
								// Find the position of current level
								const levelIndex = sortedLevels.findIndex(l => l.id === level.id)
								globalLevelNumber += levelIndex + 1
								break
							} else {
								// Add all levels from this previous course in the same class
								const courseLevels = c.levels || []
								globalLevelNumber += courseLevels.length
							}
						}
						break
					} else {
						// Add all levels from this previous class
						// Sort courses by order_index and count all levels
						const sortedCourses = [...(cls.courses || [])].sort((a, b) => a.order_index - b.order_index)
						for (const c of sortedCourses) {
							const courseLevels = c.levels || []
							globalLevelNumber += courseLevels.length
						}
					}
				}
				
				// Get class number with fallback to prevent "undefined"
				const classNumber = classData.order_index || classes.findIndex(c => c.id === classData.id) + 1 || 1
				return `Niveli ${globalLevelNumber} Klasa ${classNumber}`
			}
		}
		// Fallback to original name if class not found
		return level.name
	}

	return (
		<div className="admin-dashboard">
			<div className="admin-header">
				<h1>🛡️ Admin Dashboard</h1>
				<button className="admin-logout-btn" onClick={onLogout}>Dil</button>
			</div>

			<div className="admin-tabs">
				<button className={activeTab === 'stats' ? 'active' : ''} onClick={() => setActiveTab('stats')}>
					📊 Statistika
				</button>
				<button className={activeTab === 'users' ? 'active' : ''} onClick={() => setActiveTab('users')}>
					👥 Përdoruesit
				</button>
				<button className={activeTab === 'classes' ? 'active' : ''} onClick={() => setActiveTab('classes')}>
					🏫 Klasat
				</button>
				<button className={activeTab === 'levels' ? 'active' : ''} onClick={() => setActiveTab('levels')}>
					📚 Nivelet
				</button>
				<button className={activeTab === 'exercises' ? 'active' : ''} onClick={() => setActiveTab('exercises')}>
					✏️ Ushtrimet
				</button>
			</div>

			<div className="admin-content">
				{loading ? (
					<div className="admin-loading">Duke ngarkuar...</div>
				) : (
					<>
						{activeTab === 'stats' && stats && (
							<div className="stats-grid">
								<div className="stat-card">
									<div className="stat-icon">👥</div>
									<div className="stat-value">{stats.total_users}</div>
									<div className="stat-label">Përdorues</div>
								</div>
								<div className="stat-card">
									<div className="stat-icon">🏫</div>
									<div className="stat-value">{stats.total_classes}</div>
									<div className="stat-label">Klasa</div>
								</div>
								<div className="stat-card">
									<div className="stat-icon">📚</div>
									<div className="stat-value">{stats.total_courses}</div>
									<div className="stat-label">Kurse</div>
								</div>
								<div className="stat-card">
									<div className="stat-icon">📖</div>
									<div className="stat-value">{stats.total_levels}</div>
									<div className="stat-label">Nivele</div>
								</div>
								<div className="stat-card">
									<div className="stat-icon">✏️</div>
									<div className="stat-value">{stats.total_exercises}</div>
									<div className="stat-label">Ushtrime</div>
								</div>
								<div className="stat-card">
									<div className="stat-icon">🎯</div>
									<div className="stat-value">{stats.total_attempts}</div>
									<div className="stat-label">Përpjekje</div>
								</div>
							</div>
						)}

						{activeTab === 'users' && (
							<div className="admin-table-container">
								<div className="table-header">
									<h2>Përdoruesit</h2>
								</div>
								<table className="admin-table">
									<thead>
										<tr>
											<th>ID</th>
											<th>Username</th>
											<th>Email</th>
											<th>Moshë</th>
											<th>Status</th>
											<th>Admin</th>
											<th>Veprime</th>
										</tr>
									</thead>
									<tbody>
										{users.map(user => (
											<tr key={user.id}>
												<td>{user.id}</td>
												<td>{user.username}</td>
												<td>{user.email}</td>
												<td>{user.age || '-'}</td>
												<td>{user.is_active ? '✅ Aktiv' : '❌ Jo aktiv'}</td>
												<td>{user.is_admin ? '🛡️ Admin' : '👤 User'}</td>
												<td>
													<button onClick={() => setEditingUser(user)}>✏️ Edito</button>
													<button onClick={() => handleDeleteUser(user.id)}>🗑️ Fshi</button>
												</td>
											</tr>
										))}
									</tbody>
								</table>
							</div>
						)}

						{activeTab === 'classes' && (
							<div className="admin-table-container">
								<div className="table-header">
									<h2>Klasat</h2>
									<button className="create-btn" onClick={() => setShowCreateModal('class')}>+ Shto Klasë</button>
								</div>
								<table className="admin-table">
									<thead>
										<tr>
											<th>ID</th>
											<th>Emër</th>
											<th>Përshkrim</th>
											<th>Kurse</th>
											<th>Status</th>
											<th>Veprime</th>
										</tr>
									</thead>
									<tbody>
										{classes.map(cls => (
											<tr key={cls.id}>
												<td>{cls.id}</td>
												<td>{cls.name}</td>
												<td>{cls.description || '-'}</td>
												<td>{(cls.courses || []).length}</td>
												<td>{cls.enabled ? '✅ Aktiv' : '❌ Jo aktiv'}</td>
												<td>
													<button onClick={() => handleEditClass(cls)}>✏️ Edito</button>
													<button onClick={() => handleDeleteClass(cls.id)}>🗑️ Fshi</button>
												</td>
											</tr>
										))}
									</tbody>
								</table>
							</div>
						)}

						{activeTab === 'levels' && (
							<div className="admin-table-container">
								<div className="table-header">
									<h2>Nivelet</h2>
									<div>
										<select value={selectedClass || ''} onChange={(e) => setSelectedClass(e.target.value ? parseInt(e.target.value) : null)}>
											<option value="">Të gjitha klasat</option>
											{classes.map(cls => (
												<option key={cls.id} value={cls.id}>{cls.name}</option>
											))}
										</select>
										<button className="create-btn" onClick={() => setShowCreateModal('level')}>+ Shto Nivel</button>
									</div>
								</div>
								<table className="admin-table">
									<thead>
										<tr>
											<th>ID</th>
											<th>Emër</th>
											<th>Klasa</th>
											<th>Përshkrim</th>
											<th>Kurs ID</th>
											<th>Status</th>
											<th>Veprime</th>
										</tr>
									</thead>
									<tbody>
										{levels.map(level => (
											<tr key={level.id}>
												<td>{level.id}</td>
												<td>{getLevelDisplayName(level)}</td>
												<td>{getLevelClassName(level)}</td>
												<td>{level.description || '-'}</td>
												<td>{level.course_id}</td>
												<td>{level.enabled ? '✅ Aktiv' : '❌ Jo aktiv'}</td>
												<td>
													<button onClick={() => handleEditLevel(level)}>✏️ Edito</button>
													<button onClick={() => handleDeleteLevel(level.id)}>🗑️ Fshi</button>
												</td>
											</tr>
										))}
									</tbody>
								</table>
							</div>
						)}

						{activeTab === 'exercises' && (
							<div className="admin-table-container">
								<div className="table-header">
									<h2>Ushtrimet</h2>
									<div>
										<select value={selectedLevel || ''} onChange={(e) => setSelectedLevel(e.target.value ? parseInt(e.target.value) : null)}>
											<option value="">Të gjitha nivelet</option>
											{levels.map(level => (
												<option key={level.id} value={level.id}>
													{getLevelDisplayName(level)} - {getLevelClassName(level)}
												</option>
											))}
										</select>
										<button className="create-btn" onClick={() => setShowCreateModal('exercise')}>+ Shto Ushtrim</button>
									</div>
								</div>
								<table className="admin-table">
									<thead>
										<tr>
											<th>ID</th>
											<th>Prompt</th>
											<th>Kategori</th>
											<th>Nivel ID</th>
											<th>Pikë</th>
											<th>Veprime</th>
										</tr>
									</thead>
									<tbody>
										{exercises.map(exercise => (
											<tr key={exercise.id}>
												<td>{exercise.id}</td>
												<td>{exercise.prompt.substring(0, 50)}...</td>
												<td>{exercise.category}</td>
												<td>{exercise.level_id}</td>
												<td>{exercise.points}</td>
												<td>
													<button onClick={() => setEditingExercise(exercise)}>✏️ Edito</button>
													<button onClick={() => handleDeleteExercise(exercise.id)}>🗑️ Fshi</button>
												</td>
											</tr>
										))}
									</tbody>
								</table>
							</div>
						)}
					</>
				)}
			</div>

			{/* Modals for create/edit */}
			{showCreateModal && (
				<CreateModal
					type={showCreateModal}
					onClose={() => setShowCreateModal(null)}
					onCreate={showCreateModal === 'class' ? handleCreateClass : showCreateModal === 'level' ? handleCreateLevel : handleCreateExercise}
					classes={classes}
					levels={levels}
					getLevelDisplayName={getLevelDisplayName}
					getLevelClassName={getLevelClassName}
				/>
			)}

			{editingUser && (
				<EditUserModal
					user={editingUser}
					onClose={() => setEditingUser(null)}
					onSave={handleUpdateUser}
				/>
			)}

			{editingClass && (
				<EditClassModal
					classData={editingClass}
					onClose={() => setEditingClass(null)}
					onSave={handleUpdateClass}
				/>
			)}

			{editingLevel && (
				<EditLevelModal
					level={editingLevel}
					onClose={() => setEditingLevel(null)}
					onSave={handleUpdateLevel}
					classes={classes}
				/>
			)}

			{editingExercise && (
				<EditExerciseModal
					exercise={editingExercise}
					onClose={() => setEditingExercise(null)}
					onSave={handleUpdateExercise}
				/>
			)}
		</div>
	)
}

// Modal components
function CreateModal({ type, onClose, onCreate, classes, levels, getLevelDisplayName, getLevelClassName }: {
	type: 'class' | 'level' | 'exercise'
	onClose: () => void
	onCreate: any
	classes: ClassData[]
	levels: LevelOut[]
	getLevelDisplayName: (level: LevelOut) => string
	getLevelClassName: (level: LevelOut) => string
}) {
	const [formData, setFormData] = useState<any>({})

	const handleSubmit = (e: React.FormEvent) => {
		e.preventDefault()
		if (type === 'class') {
			onCreate(formData.name, formData.description)
		} else if (type === 'level') {
			onCreate(formData.course_id, formData.name, formData.description)
		} else {
			onCreate(formData)
		}
	}

	return (
		<div className="modal-overlay" onClick={onClose}>
			<div className="modal-content" onClick={(e) => e.stopPropagation()}>
				<h2>Shto {type === 'class' ? 'Klasë' : type === 'level' ? 'Nivel' : 'Ushtrim'}</h2>
				<form onSubmit={handleSubmit}>
					{type === 'class' && (
						<>
							<input placeholder="Emër" value={formData.name || ''} onChange={(e) => setFormData({...formData, name: e.target.value})} required />
							<textarea placeholder="Përshkrim" value={formData.description || ''} onChange={(e) => setFormData({...formData, description: e.target.value})} />
						</>
					)}
					{type === 'level' && (
						<>
							<select value={formData.course_id || ''} onChange={(e) => setFormData({...formData, course_id: parseInt(e.target.value)})} required>
								<option value="">Zgjidh Kurs</option>
								{classes.flatMap((c: ClassData) => c.courses).map((c: any) => (
									<option key={c.id} value={c.id}>{c.name}</option>
								))}
							</select>
							<input placeholder="Emër" value={formData.name || ''} onChange={(e) => setFormData({...formData, name: e.target.value})} required />
							<textarea placeholder="Përshkrim" value={formData.description || ''} onChange={(e) => setFormData({...formData, description: e.target.value})} />
						</>
					)}
					{type === 'exercise' && (
						<>
							<select value={formData.level_id || ''} onChange={(e) => setFormData({...formData, level_id: parseInt(e.target.value)})} required>
								<option value="">Zgjidh Nivel</option>
								{levels.map((l: LevelOut) => (
									<option key={l.id} value={l.id}>
										{getLevelDisplayName(l)} - {getLevelClassName(l)}
									</option>
								))}
							</select>
							<input placeholder="Prompt" value={formData.prompt || ''} onChange={(e) => setFormData({...formData, prompt: e.target.value})} required />
							<input placeholder="Përgjigje" value={formData.answer || ''} onChange={(e) => setFormData({...formData, answer: e.target.value})} required />
							<input type="number" placeholder="Pikë" value={formData.points || ''} onChange={(e) => setFormData({...formData, points: parseInt(e.target.value)})} />
						</>
					)}
					<div className="modal-actions">
						<button type="submit">Krijo</button>
						<button type="button" onClick={onClose}>Anulo</button>
					</div>
				</form>
			</div>
		</div>
	)
}

function EditUserModal({ user, onClose, onSave }: {
	user: UserOut
	onClose: () => void
	onSave: (data: Partial<UserOut>) => void
}) {
	const [formData, setFormData] = useState(user)

	const handleSubmit = (e: React.FormEvent) => {
		e.preventDefault()
		onSave(formData)
	}

	return (
		<div className="modal-overlay" onClick={onClose}>
			<div className="modal-content" onClick={(e) => e.stopPropagation()}>
				<h2>Edito Përdorues</h2>
				<form onSubmit={handleSubmit}>
					<input value={formData.username} onChange={(e) => setFormData({...formData, username: e.target.value})} />
					<input type="email" value={formData.email} onChange={(e) => setFormData({...formData, email: e.target.value})} />
					<input type="number" value={formData.age || ''} onChange={(e) => setFormData({...formData, age: parseInt(e.target.value)})} />
					<label>
						<input type="checkbox" checked={formData.is_active} onChange={(e) => setFormData({...formData, is_active: e.target.checked})} />
						Aktiv
					</label>
					<label>
						<input type="checkbox" checked={formData.is_admin} onChange={(e) => setFormData({...formData, is_admin: e.target.checked})} />
						Admin
					</label>
					<div className="modal-actions">
						<button type="submit">Ruaj</button>
						<button type="button" onClick={onClose}>Anulo</button>
					</div>
				</form>
			</div>
		</div>
	)
}

function EditClassModal({ classData, onClose, onSave }: {
	classData: ClassData
	onClose: () => void
	onSave: (data: Partial<ClassData>) => void
}) {
	const [formData, setFormData] = useState<Partial<ClassData>>({
		name: classData.name,
		description: classData.description || '',
		enabled: classData.enabled
	})

	const handleSubmit = (e: React.FormEvent) => {
		e.preventDefault()
		onSave(formData)
	}

	return (
		<div className="modal-overlay" onClick={onClose}>
			<div className="modal-content" onClick={(e) => e.stopPropagation()}>
				<h2>Edito Klasë</h2>
				<form onSubmit={handleSubmit}>
					<label>
						Emër:
						<input 
							value={formData.name || ''} 
							onChange={(e) => setFormData({...formData, name: e.target.value})} 
							required 
						/>
					</label>
					<label>
						Përshkrim:
						<textarea 
							value={formData.description || ''} 
							onChange={(e) => setFormData({...formData, description: e.target.value})} 
						/>
					</label>
					<label>
						<input 
							type="checkbox" 
							checked={formData.enabled !== false} 
							onChange={(e) => setFormData({...formData, enabled: e.target.checked})} 
						/>
						Aktiv
					</label>
					<div className="modal-actions">
						<button type="submit">Ruaj</button>
						<button type="button" onClick={onClose}>Anulo</button>
					</div>
				</form>
			</div>
		</div>
	)
}

function EditLevelModal({ level, onClose, onSave, classes }: {
	level: LevelOut
	onClose: () => void
	onSave: (data: Partial<LevelOut>) => void
	classes: ClassData[]
}) {
	const [formData, setFormData] = useState<Partial<LevelOut>>({
		name: level.name,
		description: level.description || '',
		course_id: level.course_id,
		enabled: level.enabled,
		required_score: level.required_score
	})

	const handleSubmit = (e: React.FormEvent) => {
		e.preventDefault()
		onSave(formData)
	}

	// Get all courses from all classes
	const allCourses = classes.flatMap(cls => cls.courses || [])

	return (
		<div className="modal-overlay" onClick={onClose}>
			<div className="modal-content" onClick={(e) => e.stopPropagation()}>
				<h2>Edito Nivel</h2>
				<form onSubmit={handleSubmit}>
					<label>
						Kurs:
						<select 
							value={formData.course_id || ''} 
							onChange={(e) => setFormData({...formData, course_id: parseInt(e.target.value)})} 
							required
						>
							<option value="">Zgjidh Kurs</option>
							{allCourses.map(course => (
								<option key={course.id} value={course.id}>{course.name}</option>
							))}
						</select>
					</label>
					<label>
						Emër:
						<input 
							value={formData.name || ''} 
							onChange={(e) => setFormData({...formData, name: e.target.value})} 
							required 
						/>
					</label>
					<label>
						Përshkrim:
						<textarea 
							value={formData.description || ''} 
							onChange={(e) => setFormData({...formData, description: e.target.value})} 
						/>
					</label>
					<label>
						Pikë të Kërkuara (%):
						<input 
							type="number" 
							min="0" 
							max="100"
							value={formData.required_score || 0} 
							onChange={(e) => setFormData({...formData, required_score: parseInt(e.target.value)})} 
						/>
					</label>
					<label>
						<input 
							type="checkbox" 
							checked={formData.enabled !== false} 
							onChange={(e) => setFormData({...formData, enabled: e.target.checked})} 
						/>
						Aktiv
					</label>
					<div className="modal-actions">
						<button type="submit">Ruaj</button>
						<button type="button" onClick={onClose}>Anulo</button>
					</div>
				</form>
			</div>
		</div>
	)
}

function EditExerciseModal({ exercise, onClose, onSave }: {
	exercise: ExerciseOut
	onClose: () => void
	onSave: (data: Partial<ExerciseOut & { answer?: string }>) => void
}) {
	const [formData, setFormData] = useState<ExerciseOut & { answer?: string }>({ ...exercise, answer: '' })

	const handleSubmit = (e: React.FormEvent) => {
		e.preventDefault()
		onSave(formData)
	}

	return (
		<div className="modal-overlay" onClick={onClose}>
			<div className="modal-content" onClick={(e) => e.stopPropagation()}>
				<h2>Edito Ushtrim</h2>
				<form onSubmit={handleSubmit}>
					<label>
						Prompt:
						<textarea 
							value={formData.prompt} 
							onChange={(e) => setFormData({...formData, prompt: e.target.value})} 
							required
						/>
					</label>
					<label>
						Përgjigje:
						<input 
							value={formData.answer || ''} 
							onChange={(e) => setFormData({...formData, answer: e.target.value})} 
							required
						/>
					</label>
					<label>
						Pikë:
						<input 
							type="number" 
							min="1"
							value={formData.points} 
							onChange={(e) => setFormData({...formData, points: parseInt(e.target.value)})} 
						/>
					</label>
					<label>
						Kategori:
						<select 
							value={formData.category} 
							onChange={(e) => setFormData({...formData, category: e.target.value as Category})}
						>
							<option value="listen_write">Dëgjo dhe Shkruaj</option>
							<option value="word_from_description">Fjalë nga Përshkrimi</option>
							<option value="synonyms_antonyms">Sinonime/Antonime</option>
							<option value="albanian_or_loanword">Shqip ose Huazim</option>
							<option value="missing_letter">Shkronjë e Munguar</option>
							<option value="wrong_letter">Shkronjë e Gabuar</option>
							<option value="build_word">Ndërtim Fjalë</option>
							<option value="number_to_word">Numër në Fjalë</option>
							<option value="phrases">Fraza</option>
							<option value="spelling_punctuation">Drejtshkrim dhe Pikësim</option>
							<option value="abstract_concrete">Abstrakt/Konkrete</option>
							<option value="build_sentence">Ndërtim Fjali</option>
						</select>
					</label>
					<div className="modal-actions">
						<button type="submit">Ruaj</button>
						<button type="button" onClick={onClose}>Anulo</button>
					</div>
				</form>
			</div>
		</div>
	)
}

