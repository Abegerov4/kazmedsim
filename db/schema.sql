CREATE TABLE IF NOT EXISTS scenarios (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  slug TEXT UNIQUE NOT NULL,
  specialty TEXT NOT NULL DEFAULT 'internal_medicine',
  specialty_ru TEXT NOT NULL DEFAULT 'Терапия',
  specialty_kk TEXT NOT NULL DEFAULT 'Терапия',
  icd10 TEXT NOT NULL DEFAULT '',
  card_color TEXT NOT NULL DEFAULT '#FFFFFF',
  urgency TEXT NOT NULL DEFAULT 'routine' CHECK(urgency IN ('routine','urgent')),
  difficulty TEXT NOT NULL CHECK(difficulty IN ('easy','medium','hard')),
  disease_ru TEXT NOT NULL,
  disease_kk TEXT NOT NULL,
  patient_name_ru TEXT NOT NULL,
  patient_name_kk TEXT NOT NULL,
  patient_age INTEGER NOT NULL,
  patient_gender TEXT NOT NULL CHECK(patient_gender IN ('male','female')),
  chief_complaint_ru TEXT NOT NULL,
  chief_complaint_kk TEXT NOT NULL,
  history_ru TEXT NOT NULL,
  history_kk TEXT NOT NULL,
  allergies_ru TEXT DEFAULT 'Нет',
  allergies_kk TEXT DEFAULT 'Жоқ',
  lab_results_json TEXT NOT NULL,
  correct_diagnosis_ru TEXT NOT NULL,
  correct_diagnosis_kk TEXT NOT NULL,
  treatment_protocol_ru TEXT NOT NULL,
  treatment_protocol_kk TEXT NOT NULL,
  sources TEXT NOT NULL,
  created_at DATETIME DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS sessions (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  scenario_id INTEGER NOT NULL REFERENCES scenarios(id),
  student_name TEXT,
  language TEXT NOT NULL DEFAULT 'ru',
  started_at DATETIME DEFAULT CURRENT_TIMESTAMP,
  ended_at DATETIME,
  student_diagnosis_ru TEXT,
  student_diagnosis_kk TEXT,
  score_anamnesis REAL,
  score_communication REAL,
  score_reasoning REAL,
  score_diagnosis REAL,
  score_treatment REAL,
  score_total REAL,
  feedback_json TEXT
);

CREATE TABLE IF NOT EXISTS dialog_log (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  session_id INTEGER NOT NULL REFERENCES sessions(id),
  role TEXT NOT NULL CHECK(role IN ('student','patient')),
  message TEXT NOT NULL,
  timestamp DATETIME DEFAULT CURRENT_TIMESTAMP
);
