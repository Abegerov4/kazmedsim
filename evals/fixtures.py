"""Fixture sessions for grader regression evals.

Each fixture is a hand-crafted snapshot of a student's appointment, paired
with score ranges we expect any well-tuned grader to land within.

Ranges are intentionally wide (±2 points typically) because LLM grading has
intrinsic noise — the goal is to catch *qualitative* regressions ("our
grader started rewarding bad anamnesis"), not nail an exact number.

Naming convention:
    <scenario_slug>_<quality>  e.g. pneumonia_strong, dka_misdiagnosis
"""
from dataclasses import dataclass


@dataclass
class Fixture:
    name: str
    language: str               # "ru" | "kk" | "en"
    correct_diagnosis: str      # what the scenario says
    student_diagnosis: str
    student_treatment: str
    ordered_tests: list[str]
    examined: bool
    elapsed_seconds: int
    patient_history: str        # anchor
    relevant_tests: list[str]   # anchor
    transcript: list[tuple[str, str]]   # (role, message), role in {student, patient}
    expected: dict[str, tuple[float, float]]  # rubric → (min, max), incl "total"

    def transcript_text(self) -> str:
        speaker = {
            "ru": ("Студент", "Пациент"),
            "kk": ("Студент", "Науқас"),
            "en": ("Student", "Patient"),
        }[self.language]
        out = []
        for role, msg in self.transcript:
            label = speaker[0] if role == "student" else speaker[1]
            out.append(f"{label}: {msg}")
        return "\n".join(out)


# ── Fixtures ──────────────────────────────────────────────────────────────────

FIXTURES: list[Fixture] = [
    # 1. Strong student on pneumonia: full anamnesis, correct dx + tx, empathy.
    Fixture(
        name="pneumonia_strong",
        language="ru",
        correct_diagnosis="J18.1 — Внебольничная долевая пневмония (правосторонняя)",
        student_diagnosis="J18.1 — Внебольничная правосторонняя пневмония",
        student_treatment="Амоксициллин/клавуланат 875/125 мг 2 раза/день 7 дней; Парацетамол при t>38.5",
        ordered_tests=["Рентген ОГК", "Лейкоциты", "Нейтрофилы", "СРБ", "SpO₂"],
        examined=True,
        elapsed_seconds=420,
        patient_history=(
            "Острое начало 4 дня назад: t до 39.2, кашель с жёлто-зелёной мокротой, "
            "боль в правом боку при дыхании. Курит 15 лет по пачке в день. "
            "Хронических болезней нет, аллергий нет."
        ),
        relevant_tests=["Лейкоциты", "Нейтрофилы", "СРБ", "Прокальцитонин", "SpO₂",
                        "Рентген ОГК", "Аускультация лёгких"],
        transcript=[
            ("student", "Здравствуйте! Меня зовут доктор Иван, как могу к вам обращаться?"),
            ("patient", "Серик Ахметов."),
            ("student", "Серик, что вас беспокоит?"),
            ("patient", "Сильный кашель с гнойной мокротой, температура до 39, тяжело дышать. 4 дня уже."),
            ("student", "Какого цвета мокрота? Боль в груди есть?"),
            ("patient", "Жёлто-зелёная. Да, справа болит при вдохе."),
            ("student", "Понимаю что вам тяжело. Курите?"),
            ("patient", "Да, пачку в день, 15 лет."),
            ("student", "Серик, хронические болезни, аллергии есть?"),
            ("patient", "Нет."),
            ("student", "Сейчас назначу рентген и анализы крови, потом обсудим лечение."),
        ],
        expected={
            "anamnesis":     (8, 10),
            "communication": (8, 10),
            "reasoning":     (7, 10),
            "diagnosis":     (8, 10),
            "treatment":     (8, 10),
            "total":         (8.0, 10.0),
        },
    ),

    # 2. Weak student on pneumonia: rushed anamnesis, no empathy, partial tests,
    #    wrong-system dx, wrong tx.
    Fixture(
        name="pneumonia_weak",
        language="ru",
        correct_diagnosis="J18.1 — Внебольничная долевая пневмония (правосторонняя)",
        student_diagnosis="K21.9 — ГЭРБ",
        student_treatment="Омепразол 20 мг 1 раз/день",
        ordered_tests=["ФГДС"],
        examined=False,
        elapsed_seconds=120,
        patient_history=(
            "Острое начало 4 дня назад: t до 39.2, кашель с жёлто-зелёной мокротой, "
            "боль в правом боку при дыхании. Курит 15 лет по пачке в день."
        ),
        relevant_tests=["Лейкоциты", "Нейтрофилы", "СРБ", "Прокальцитонин", "SpO₂",
                        "Рентген ОГК", "Аускультация лёгких"],
        transcript=[
            ("student", "Что у вас?"),
            ("patient", "Кашель и температура."),
            ("student", "Сколько дней?"),
            ("patient", "Четыре."),
            ("student", "Ясно, назначу ФГДС, это рефлюкс."),
        ],
        expected={
            "anamnesis":     (0, 5),
            "communication": (0, 5),
            "reasoning":     (0, 5),
            "diagnosis":     (0, 3),
            "treatment":     (0, 3),
            "total":         (0.0, 4.0),
        },
    ),

    # 3. Mid-quality student on ARVI: correct dx + tx but thin anamnesis,
    #    over-ordered (whole-body MRI) → reasoning should drop.
    Fixture(
        name="arvi_overworked",
        language="ru",
        correct_diagnosis="J06.9 — ОРВИ",
        student_diagnosis="J06.9 — ОРВИ (острая инфекция верхних дыхательных путей)",
        student_treatment="Парацетамол 500 мг при t>38.5; обильное питьё; покой",
        ordered_tests=["МРТ всего тела", "Онкомаркеры (расширенная панель)", "ПЭТ-КТ всего тела"],
        examined=False,
        elapsed_seconds=240,
        patient_history=(
            "Насморк, першение в горле, субфебрильная температура 37.8 второй день, "
            "лёгкое недомогание. Аллергий и хронических болезней нет."
        ),
        relevant_tests=["ОАК", "СРБ", "Мазок из носоглотки", "Осмотр зева"],
        transcript=[
            ("student", "Здравствуйте, что беспокоит?"),
            ("patient", "Насморк, горло першит, температура 37.8."),
            ("student", "Сколько дней?"),
            ("patient", "Второй."),
            ("student", "Понятно, назначу обследование."),
        ],
        expected={
            "anamnesis":     (3, 6),
            "communication": (3, 6),
            "reasoning":     (0, 4),   # penalty for over-ordering distractor tests
            "diagnosis":     (8, 10),
            "treatment":     (7, 10),
            "total":         (4.0, 7.5),
        },
    ),

    # 4. English-language fixture — verifies grader works in EN, not just RU.
    Fixture(
        name="pneumonia_strong_en",
        language="en",
        correct_diagnosis="J18.1 — Community-acquired lobar pneumonia (right-sided)",
        student_diagnosis="J18.1 — Community-acquired right-sided pneumonia",
        student_treatment="Amoxicillin/clavulanate 875/125 mg BID for 7 days; Paracetamol for T>38.5°C",
        ordered_tests=["Chest X-ray", "WBC", "Neutrophils", "CRP", "SpO₂"],
        examined=True,
        elapsed_seconds=420,
        patient_history=(
            "Acute onset 4 days ago: T up to 39.2°C, productive cough with "
            "yellow-green sputum, right-sided chest pain on inspiration. "
            "Smoker 15 years (one pack/day). No chronic illnesses, no allergies."
        ),
        relevant_tests=["WBC", "Neutrophils", "CRP", "Procalcitonin", "SpO₂",
                        "Chest X-ray", "Lung auscultation"],
        transcript=[
            ("student", "Hello! I'm Dr Ivan — what's your name?"),
            ("patient", "Serik Akhmetov."),
            ("student", "Serik, what brings you in today?"),
            ("patient", "Bad cough with thick sputum, fever up to 39, hard to breathe — for 4 days now."),
            ("student", "What colour is the sputum? Any chest pain?"),
            ("patient", "Yellow-green. Yes, right side hurts when I breathe in."),
            ("student", "I understand this is rough. Do you smoke?"),
            ("patient", "Yes, a pack a day for 15 years."),
            ("student", "Serik, any chronic conditions or allergies?"),
            ("patient", "No."),
            ("student", "I'll order a chest X-ray and blood tests now, then we'll discuss treatment."),
        ],
        expected={
            "anamnesis":     (8, 10),
            "communication": (8, 10),
            "reasoning":     (7, 10),
            "diagnosis":     (8, 10),
            "treatment":     (8, 10),
            "total":         (8.0, 10.0),
        },
    ),

    # 5. Misdiagnosis on diabetic ketoacidosis — dangerous miss, grader must
    #    penalize diagnosis + treatment harshly.
    Fixture(
        name="dka_misdiagnosis",
        language="ru",
        correct_diagnosis="E10.1 — Сахарный диабет 1 типа, дебют, кетоацидоз",
        student_diagnosis="K85.9 — Острый панкреатит",
        student_treatment="Дротаверин 40 мг внутрь, голод",
        ordered_tests=["Амилаза"],
        examined=True,
        elapsed_seconds=300,
        patient_history=(
            "18-летний пациент, неделя жажды и полиурии (до 8 раз ночью), потерял 6 кг. "
            "Сегодня тошнота, рвота, боль в животе, заторможен. Запах ацетона изо рта. "
            "Дыхание Куссмауля. Сухие слизистые. Ранее здоров."
        ),
        relevant_tests=["Глюкоза крови", "Кетоны мочи/крови", "pH", "Электролиты",
                        "Газы крови", "ОАМ"],
        transcript=[
            ("student", "Что беспокоит?"),
            ("patient", "Болит живот, тошнит, рвота."),
            ("student", "Когда началось?"),
            ("patient", "Сегодня сильно."),
            ("student", "Похоже на панкреатит, назначу амилазу и спазмолитик."),
        ],
        expected={
            "anamnesis":     (0, 4),
            "communication": (0, 4),
            "reasoning":     (0, 4),
            "diagnosis":     (0, 3),
            "treatment":     (0, 3),
            "total":         (0.0, 3.5),
        },
    ),
]
