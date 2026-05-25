"""Seed the database with clinical scenarios. Run from project root:
   python scripts/seed_db.py
"""
import sqlite3
import json
import os

DB_PATH = os.path.join(os.path.dirname(__file__), "..", "db", "kazmedsim.db")

SPECIALTY_LABELS = {
    "internal_medicine":  {"ru": "Терапия",               "kk": "Терапия"},
    "cardiology":         {"ru": "Кардиология",           "kk": "Кардиология"},
    "pulmonology":        {"ru": "Пульмонология",         "kk": "Пульмонология"},
    "neurology":          {"ru": "Неврология",            "kk": "Неврология"},
    "endocrinology":      {"ru": "Эндокринология",        "kk": "Эндокринология"},
    "gastroenterology":   {"ru": "Гастроэнтерология",     "kk": "Гастроэнтерология"},
    "infectious_disease": {"ru": "Инфекционные болезни",  "kk": "Жұқпалы аурулар"},
}

SCENARIOS = [
    # ── ТЕРАПИЯ ──────────────────────────────────────────────────────────────
    {
        "slug": "arvi_adult",
        "specialty": "internal_medicine",
        "icd10": "J06.9",
        "card_color": "#E8F5E9",
        "urgency": "routine",
        "difficulty": "easy",
        "disease_ru": "ОРВИ у взрослого",
        "disease_kk": "Ересектердегі ЖРВИ",
        "patient_name_ru": "Айгерим Сейткали",
        "patient_name_kk": "Айгерім Сейтқали",
        "patient_age": 28,
        "patient_gender": "female",
        "chief_complaint_ru": "Температура 37.8°C, насморк, боль в горле 2 дня",
        "chief_complaint_kk": "Температура 37.8°C, мұрын ағу, тамақ ауыруы 2 күн",
        "history_ru": "Заболела 2 дня назад после переохлаждения. Общая слабость, "
                      "головная боль, заложенность носа, першение в горле. Кашля нет. "
                      "Хронических заболеваний нет. Аллергии нет.",
        "history_kk": "Суыққа қалғаннан кейін 2 күн бұрын ауырды. Жалпы әлсіздік, "
                      "бас ауруы, мұрын бітелуі. Жөтел жоқ. Созылмалы аурулар жоқ.",
        "allergies_ru": "Нет",
        "allergies_kk": "Жоқ",
        "lab_results_json": json.dumps([
            {"name_ru": "Лейкоциты",  "name_kk": "Лейкоциттер",  "value": 7.2,  "unit": "×10⁹/л", "normal": "4.0–9.0",  "normal_min": 4.0,  "normal_max": 9.0},
            {"name_ru": "СОЭ",        "name_kk": "ЭТЖ",           "value": 18,   "unit": "мм/ч",   "normal": "2–15",     "normal_min": 2,    "normal_max": 15},
            {"name_ru": "СРБ",        "name_kk": "СРБ",           "value": 8,    "unit": "мг/л",   "normal": "<10",      "normal_min": 0,    "normal_max": 10},
            {"name_ru": "Нейтрофилы", "name_kk": "Нейтрофилдер", "value": 58,   "unit": "%",      "normal": "45–70",    "normal_min": 45,   "normal_max": 70},
            {"name_ru": "Лимфоциты",  "name_kk": "Лимфоциттер",  "value": 35,   "unit": "%",      "normal": "20–40",    "normal_min": 20,   "normal_max": 40},
        ]),
        "correct_diagnosis_ru": "J06.9 — Острая инфекция верхних дыхательных путей (ОРВИ)",
        "correct_diagnosis_kk": "J06.9 — Жедел жоғарғы тыныс жолдарының инфекциясы (ЖРВИ)",
        "treatment_protocol_ru": "1. Постельный режим 3-5 дней\n2. Обильное тёплое питьё 1.5-2 л/сут\n3. Парацетамол 500 мг при t>38.5°C\n4. Солевой раствор в нос 3-4 р/день\n5. Антибиотики НЕ показаны",
        "treatment_protocol_kk": "1. 3-5 күн төсектік режим\n2. Мол жылы сұйықтық 1.5-2 л/тәу\n3. t>38.5°C Парацетамол 500 мг\n4. Тұзды ерітінді мұрынға күніне 3-4 рет\n5. Антибиотиктер КЕРЕК ЕМЕС",
        "sources": json.dumps([{"name": "МЗ РК — Протокол ОРВИ, РЦРЗ"}, {"name": "ВОЗ — Острые респираторные инфекции"}]),
    },
    {
        "slug": "iron_deficiency_anemia",
        "specialty": "internal_medicine",
        "icd10": "D50.9",
        "card_color": "#FFF3E0",
        "urgency": "routine",
        "difficulty": "easy",
        "disease_ru": "Железодефицитная анемия",
        "disease_kk": "Темір тапшылығы анемиясы",
        "patient_name_ru": "Айгерим Сейткалиева",
        "patient_name_kk": "Айгерім Сейткалиева",
        "patient_age": 34,
        "patient_gender": "female",
        "chief_complaint_ru": "Слабость и одышка при подъёме по лестнице несколько месяцев",
        "chief_complaint_kk": "Бірнеше айдан бері баспалдақпен көтерілгенде әлсіздік пен ентігу",
        "history_ru": "Менструации обильные, диета бедная мясом. Работает учительницей. Волосы ломкие, кожа бледная.",
        "history_kk": "Етеккір мол, ет аз диета. Мұғалім. Шашы сынғыш, терісі бозғылт.",
        "allergies_ru": "Нет",
        "allergies_kk": "Жоқ",
        "lab_results_json": json.dumps([
            {"name_ru": "Гемоглобин",         "name_kk": "Гемоглобин",         "value": 88,  "unit": "г/л",      "normal": "120-160", "normal_min": 120, "normal_max": 160},
            {"name_ru": "Эритроциты",         "name_kk": "Эритроциттер",       "value": 3.2, "unit": "×10¹²/л", "normal": "3.8-5.2", "normal_min": 3.8, "normal_max": 5.2},
            {"name_ru": "Сывороточное железо","name_kk": "Қан сарысуы темірі", "value": 4.2, "unit": "мкмоль/л","normal": "11-30",   "normal_min": 11,  "normal_max": 30},
            {"name_ru": "Ферритин",           "name_kk": "Ферритин",           "value": 6,   "unit": "нг/мл",   "normal": "20-200",  "normal_min": 20,  "normal_max": 200},
            {"name_ru": "МЦВ",                "name_kk": "ОЭК",                "value": 68,  "unit": "фл",       "normal": "80-100",  "normal_min": 80,  "normal_max": 100},
        ]),
        "correct_diagnosis_ru": "Железодефицитная анемия средней степени тяжести, D50.9",
        "correct_diagnosis_kk": "Орташа ауырлықтағы темір тапшылығы анемиясы, D50.9",
        "treatment_protocol_ru": "Препараты железа per os 200мг/сут × 3 мес, диета богатая железом, контроль ОАК через 1 мес",
        "treatment_protocol_kk": "Темір препараттары per os 200мг/тәу × 3 ай, темірге бай диета, 1 айдан кейін ҚАА бақылауы",
        "sources": json.dumps([{"name": "МЗ РК Протокол D50, 2023"}, {"name": "WHO Anaemia guidelines 2021"}]),
    },
    {
        "slug": "community_pneumonia",
        "specialty": "internal_medicine",
        "icd10": "J18.9",
        "card_color": "#E8F5E9",
        "urgency": "routine",
        "difficulty": "medium",
        "disease_ru": "Внебольничная пневмония",
        "disease_kk": "Аурухана сыртылық пневмония",
        "patient_name_ru": "Серік Нұрланов",
        "patient_name_kk": "Серік Нұрланов",
        "patient_age": 47,
        "patient_gender": "male",
        "chief_complaint_ru": "Кашель с жёлтой мокротой и температура 38.5 пять дней",
        "chief_complaint_kk": "Сары қақырықпен жөтел және бес күн бойы 38.5 температура",
        "history_ru": "Курит 20 лет, работает водителем. Не вакцинирован от пневмококка.",
        "history_kk": "20 жыл темекі шегеді, жүргізуші. Пневмококкқа қарсы вакцина жасатпаған.",
        "allergies_ru": "Нет",
        "allergies_kk": "Жоқ",
        "lab_results_json": json.dumps([
            {"name_ru": "Лейкоциты",     "name_kk": "Лейкоциттер",   "value": 14.2, "unit": "×10⁹/л", "normal": "4-9",   "normal_min": 4,  "normal_max": 9},
            {"name_ru": "СОЭ",           "name_kk": "ЭШЖ",           "value": 42,   "unit": "мм/ч",   "normal": "2-15",  "normal_min": 2,  "normal_max": 15},
            {"name_ru": "СРБ",           "name_kk": "СРБ",           "value": 87,   "unit": "мг/л",   "normal": "<5",    "normal_min": 0,  "normal_max": 5},
            {"name_ru": "Прокальцитонин","name_kk": "Прокальцитонин","value": 0.8,  "unit": "нг/мл",  "normal": "<0.5",  "normal_min": 0,  "normal_max": 0.5},
            {"name_ru": "SpO2",          "name_kk": "SpO2",          "value": 94,   "unit": "%",       "normal": "95-100","normal_min": 95, "normal_max": 100},
            {"name_ru": "Рентген ОГК",   "name_kk": "Кеуде рентгені","value": "Инфильтрация в нижней доле правого лёгкого", "unit": "", "normal": "Лёгочный рисунок не изменён", "is_abnormal": True, "image_url": "/labs/bronchopneumonia.png"},
        ]),
        "correct_diagnosis_ru": "Внебольничная пневмония, средней тяжести, J18.9",
        "correct_diagnosis_kk": "Аурухана сыртылық пневмония, орташа ауырлықта, J18.9",
        "treatment_protocol_ru": "Амоксициллин/клавуланат 875мг ×2/сут × 7 дней, постельный режим, обильное питьё",
        "treatment_protocol_kk": "Амоксициллин/клавуланат 875мг ×2/тәу × 7 күн, төсек режимі, мол сұйықтық",
        "sources": json.dumps([{"name": "МЗ РК Протокол J18, 2023"}, {"name": "NICE NG138 Pneumonia 2023"}]),
    },
    {
        "slug": "hypertension_crisis",
        "specialty": "internal_medicine",
        "icd10": "I10",
        "card_color": "#FCE4EC",
        "urgency": "urgent",
        "difficulty": "medium",
        "disease_ru": "Гипертонический криз",
        "disease_kk": "Гипертониялық дағдарыс",
        "patient_name_ru": "Қадыр Ахметов",
        "patient_name_kk": "Қадыр Ахметов",
        "patient_age": 62,
        "patient_gender": "male",
        "chief_complaint_ru": "Резкая головная боль и головокружение, АД 190/110",
        "chief_complaint_kk": "Күрт бас ауруы және бас айналуы, АҚ 190/110",
        "history_ru": "Гипертония 10 лет, нерегулярно принимает эналаприл. Злоупотребляет солёным.",
        "history_kk": "10 жыл гипертония, эналаприлді тұрақсыз ішеді. Тұзды тамақты көп жейді.",
        "allergies_ru": "Нет",
        "allergies_kk": "Жоқ",
        "lab_results_json": json.dumps([
            {"name_ru": "АД",         "name_kk": "АҚ",        "value": "192/114", "unit": "мм рт.ст.", "normal": "<140/90",    "is_abnormal": True},
            {"name_ru": "ЧСС",        "name_kk": "ЖҮЖ",       "value": 94,        "unit": "уд/мин",    "normal": "60-90",      "normal_min": 60, "normal_max": 90},
            {"name_ru": "Креатинин",  "name_kk": "Креатинин", "value": 118,       "unit": "мкмоль/л",  "normal": "62-115",     "normal_min": 62, "normal_max": 115},
            {"name_ru": "Калий",      "name_kk": "Калий",     "value": 3.4,       "unit": "ммоль/л",   "normal": "3.5-5.0",    "normal_min": 3.5,"normal_max": 5.0},
            {"name_ru": "ЭКГ",        "name_kk": "ЭКГ",       "value": "Гипертрофия ЛЖ", "unit": "", "normal": "Норма", "is_abnormal": True, "image_url": "/labs/ecg_12lead.jpg"},
        ]),
        "correct_diagnosis_ru": "Гипертонический криз без поражения органов-мишеней, I10",
        "correct_diagnosis_kk": "Нысана мүшелерінің зақымдалуынсыз гипертониялық дағдарыс, I10",
        "treatment_protocol_ru": "Каптоприл 25мг сублингвально, мониторинг АД каждые 15 мин, коррекция базисной терапии",
        "treatment_protocol_kk": "Каптоприл 25мг сублингвально, АҚ-ны 15 мин сайын бақылау, базистік терапияны түзету",
        "sources": json.dumps([{"name": "МЗ РК Протокол I10, 2023"}, {"name": "ESC Guidelines Hypertension 2023"}]),
    },
    {
        "slug": "diabetes_t2_debut",
        "specialty": "internal_medicine",
        "icd10": "E11.9",
        "card_color": "#FFF9C4",
        "urgency": "routine",
        "difficulty": "medium",
        "disease_ru": "Дебют сахарного диабета 2 типа",
        "disease_kk": "2 тип қант диабетінің дебюті",
        "patient_name_ru": "Гүлнар Байжанова",
        "patient_name_kk": "Гүлнар Байжанова",
        "patient_age": 58,
        "patient_gender": "female",
        "chief_complaint_ru": "Постоянная жажда, учащённое мочеиспускание и потеря веса на 5 кг за 2 месяца",
        "chief_complaint_kk": "Үнемі шөлдеу, жиі несеп шығару және 2 айда 5 кг салмақ жоғалту",
        "history_ru": "ИМТ 31, мать болела диабетом. Ведёт малоподвижный образ жизни.",
        "history_kk": "ДМИ 31, анасы диабетпен ауырған. Отырықшы өмір салтын жүргізеді.",
        "allergies_ru": "Нет",
        "allergies_kk": "Жоқ",
        "lab_results_json": json.dumps([
            {"name_ru": "Глюкоза натощак",   "name_kk": "Аш қарынға глюкоза", "value": 9.8, "unit": "ммоль/л", "normal": "3.9-6.1", "normal_min": 3.9, "normal_max": 6.1},
            {"name_ru": "HbA1c",             "name_kk": "HbA1c",              "value": 8.2, "unit": "%",       "normal": "<6.5",    "normal_min": 0,   "normal_max": 6.5},
            {"name_ru": "Глюкоза в моче",    "name_kk": "Несептегі глюкоза",  "value": "Положительно", "unit": "", "normal": "Отрицательно", "is_abnormal": True},
            {"name_ru": "Холестерин общий",  "name_kk": "Жалпы холестерин",   "value": 6.1, "unit": "ммоль/л", "normal": "<5.2",    "normal_min": 0,   "normal_max": 5.2},
            {"name_ru": "Триглицериды",      "name_kk": "Триглицеридтер",     "value": 2.8, "unit": "ммоль/л", "normal": "<1.7",    "normal_min": 0,   "normal_max": 1.7},
        ]),
        "correct_diagnosis_ru": "Сахарный диабет 2 типа, впервые выявленный, E11.9",
        "correct_diagnosis_kk": "2 тип қант диабеті, алғаш анықталған, E11.9",
        "treatment_protocol_ru": "Метформин 500мг ×2/сут с едой, диета с ограничением углеводов, направление к эндокринологу",
        "treatment_protocol_kk": "Метформин 500мг ×2/тәу тамақпен, көмірсуды шектейтін диета, эндокринологқа жолдама",
        "sources": json.dumps([{"name": "МЗ РК Протокол E11, 2023"}, {"name": "IDF Diabetes Atlas 2023"}]),
    },
    {
        "slug": "cystitis_female",
        "specialty": "internal_medicine",
        "icd10": "N30.0",
        "card_color": "#E3F2FD",
        "urgency": "routine",
        "difficulty": "easy",
        "disease_ru": "Острый цистит",
        "disease_kk": "Жедел цистит",
        "patient_name_ru": "Жанна Оспанова",
        "patient_name_kk": "Жанна Оспанова",
        "patient_age": 26,
        "patient_gender": "female",
        "chief_complaint_ru": "Жжение при мочеиспускании и частые позывы с вчерашнего дня",
        "chief_complaint_kk": "Кешеден бері несеп шығарғанда күю және жиі дәретке бару",
        "history_ru": "Первый эпизод. Половая жизнь активная. Аллергия на сульфаниламиды.",
        "history_kk": "Бірінші эпизод. Жыныстық өмір белсенді. Сульфаниламидтерге аллергия.",
        "allergies_ru": "Сульфаниламиды",
        "allergies_kk": "Сульфаниламидтер",
        "lab_results_json": json.dumps([
            {"name_ru": "Лейкоциты в моче",  "name_kk": "Несептегі лейкоциттер", "value": "40-50",              "unit": "в п/зр",  "normal": "0-5",          "is_abnormal": True},
            {"name_ru": "Бактерии в моче",   "name_kk": "Несептегі бактериялар", "value": "Большое количество", "unit": "",         "normal": "Нет",          "is_abnormal": True},
            {"name_ru": "Нитриты",           "name_kk": "Нитриттер",            "value": "Положительно",       "unit": "",         "normal": "Отрицательно", "is_abnormal": True},
            {"name_ru": "Эритроциты в моче", "name_kk": "Несептегі эритроциттер","value": "5-8",               "unit": "в п/зр",  "normal": "0-3",          "is_abnormal": True},
            {"name_ru": "Температура тела",  "name_kk": "Дене температурасы",   "value": 36.8,                "unit": "°C",        "normal": "36.0-37.0",    "normal_min": 36.0, "normal_max": 37.0},
        ]),
        "correct_diagnosis_ru": "Острый неосложнённый цистит, N30.0",
        "correct_diagnosis_kk": "Асқынбаған жедел цистит, N30.0",
        "treatment_protocol_ru": "Фурамаг 100мг ×3/сут × 5 дней (учёт аллергии на сульфаниламиды), обильное питьё",
        "treatment_protocol_kk": "Фурамаг 100мг ×3/тәу × 5 күн (сульфаниламид аллергиясын ескеру), мол сұйықтық",
        "sources": json.dumps([{"name": "МЗ РК Протокол N30, 2023"}, {"name": "NICE NG112 UTI 2022"}]),
    },

    # ── КАРДИОЛОГИЯ ──────────────────────────────────────────────────────────
    {
        "slug": "stable_angina",
        "specialty": "cardiology",
        "icd10": "I20.9",
        "card_color": "#FCE4EC",
        "urgency": "routine",
        "difficulty": "medium",
        "disease_ru": "Стабильная стенокардия",
        "disease_kk": "Тұрақты стенокардия",
        "patient_name_ru": "Бейбіт Джаксыбеков",
        "patient_name_kk": "Бейбіт Жақсыбеков",
        "patient_age": 55,
        "patient_gender": "male",
        "chief_complaint_ru": "Давящая боль за грудиной при быстрой ходьбе, проходит в покое через 5 минут",
        "chief_complaint_kk": "Тез жүргенде төс артында басатын ауырсыну, тыныштықта 5 минутта өтеді",
        "history_ru": "Гипертония, курит 25 лет, отец умер от инфаркта в 60 лет.",
        "history_kk": "Гипертония, 25 жыл темекі шегеді, әкесі 60 жасында инфарктан қайтыс болды.",
        "allergies_ru": "Нет",
        "allergies_kk": "Жоқ",
        "lab_results_json": json.dumps([
            {"name_ru": "Тропонин I",    "name_kk": "Тропонин I",    "value": 0.01, "unit": "нг/мл",    "normal": "<0.04",   "normal_min": 0, "normal_max": 0.04},
            {"name_ru": "ЭКГ в покое",  "name_kk": "Тыныштықтағы ЭКГ","value": "Норма", "unit": "",   "normal": "Норма",   "is_abnormal": False, "image_url": "/labs/ecg_12lead.jpg"},
            {"name_ru": "Холестерин ЛПНП","name_kk": "ТТЛП холестерин","value": 4.2, "unit": "ммоль/л", "normal": "<2.6",   "normal_min": 0, "normal_max": 2.6},
            {"name_ru": "Глюкоза",      "name_kk": "Глюкоза",       "value": 5.8,  "unit": "ммоль/л",  "normal": "3.9-6.1", "normal_min": 3.9, "normal_max": 6.1},
            {"name_ru": "АД",           "name_kk": "АҚ",            "value": "148/92", "unit": "мм рт.ст.", "normal": "<140/90", "is_abnormal": True},
        ]),
        "correct_diagnosis_ru": "ИБС: стабильная стенокардия напряжения II ФК, I20.9",
        "correct_diagnosis_kk": "ЖИА: II ФК тұрақты стенокардия, I20.9",
        "treatment_protocol_ru": "Аспирин 100мг/сут, бисопролол 5мг/сут, аторвастатин 40мг/вечер, нитроглицерин при приступе",
        "treatment_protocol_kk": "Аспирин 100мг/тәу, бисопролол 5мг/тәу, аторвастатин 40мг/кеш, ұстамада нитроглицерин",
        "sources": json.dumps([{"name": "МЗ РК Протокол I20, 2023"}, {"name": "ESC Chronic Coronary Syndromes 2023"}]),
    },
    {
        "slug": "heart_failure",
        "specialty": "cardiology",
        "icd10": "I50.9",
        "card_color": "#EDE7F6",
        "urgency": "urgent",
        "difficulty": "hard",
        "disease_ru": "Хроническая сердечная недостаточность",
        "disease_kk": "Созылмалы жүрек жетіспеушілігі",
        "patient_name_ru": "Роза Сатыбалдиева",
        "patient_name_kk": "Роза Сатыбалдиева",
        "patient_age": 68,
        "patient_gender": "female",
        "chief_complaint_ru": "Одышка при малейшей нагрузке, отёки ног, не могу лежать — сплю сидя",
        "chief_complaint_kk": "Ең аз жүктемеде ентігу, аяқ ісінуі, жата алмаймын — отырып ұйықтаймын",
        "history_ru": "Перенесла инфаркт 3 года назад, мерцательная аритмия, принимает варфарин.",
        "history_kk": "3 жыл бұрын инфаркт өткерді, жыпылықтаушы аритмия, варфарин ішеді.",
        "allergies_ru": "Нет",
        "allergies_kk": "Жоқ",
        "lab_results_json": json.dumps([
            {"name_ru": "NT-proBNP", "name_kk": "NT-proBNP", "value": 2840, "unit": "пг/мл",    "normal": "<125",  "normal_min": 0, "normal_max": 125},
            {"name_ru": "Натрий",   "name_kk": "Натрий",     "value": 132,  "unit": "ммоль/л",  "normal": "136-145","normal_min": 136,"normal_max": 145},
            {"name_ru": "Креатинин","name_kk": "Креатинин",  "value": 142,  "unit": "мкмоль/л", "normal": "44-97", "normal_min": 44, "normal_max": 97},
            {"name_ru": "ЭКГ",      "name_kk": "ЭКГ",        "value": "Фибрилляция предсердий", "unit": "", "normal": "Синусовый ритм", "is_abnormal": True, "image_url": "/labs/ecg_12lead.jpg"},
            {"name_ru": "SpO2",     "name_kk": "SpO2",       "value": 91,   "unit": "%",         "normal": "95-100","normal_min": 95, "normal_max": 100},
            {"name_ru": "Рентген ОГК","name_kk": "Кеуде рентгені","value": "Кардиомегалия, застойные явления в лёгких", "unit": "", "normal": "Норма", "is_abnormal": True, "image_url": "/labs/cardiomegaly.png"},
        ]),
        "correct_diagnosis_ru": "ХСН II-III ФК (NYHA), систолическая дисфункция, I50.9",
        "correct_diagnosis_kk": "СЖЖ II-III ФК (NYHA), систолалық дисфункция, I50.9",
        "treatment_protocol_ru": "Фуросемид 40мг утром, эналаприл 5мг ×2/сут, карведилол 3.125мг ×2/сут, госпитализация",
        "treatment_protocol_kk": "Фуросемид 40мг таңертең, эналаприл 5мг ×2/тәу, карведилол 3.125мг ×2/тәу, ауруханаға жатқызу",
        "sources": json.dumps([{"name": "МЗ РК Протокол I50, 2023"}, {"name": "ESC Heart Failure Guidelines 2023"}]),
    },

    # ── ПУЛЬМОНОЛОГИЯ ─────────────────────────────────────────────────────────
    {
        "slug": "copd_exacerbation",
        "specialty": "pulmonology",
        "icd10": "J44.1",
        "card_color": "#E0F2F1",
        "urgency": "urgent",
        "difficulty": "hard",
        "disease_ru": "Обострение ХОБЛ",
        "disease_kk": "СОЗТ өршуі",
        "patient_name_ru": "Марат Есенов",
        "patient_name_kk": "Марат Есенов",
        "patient_age": 64,
        "patient_gender": "male",
        "chief_complaint_ru": "Резкое усиление одышки и кашель с гнойной мокротой 3 дня",
        "chief_complaint_kk": "3 күн бойы ентігудің күрт күшеюі және іріңді қақырықпен жөтел",
        "history_ru": "ХОБЛ III стадии, курит 40 лет (40 пачко-лет). Использует сальбутамол.",
        "history_kk": "III сатылы СОЗТ, 40 жыл темекі шегеді (40 пачка-жыл). Сальбутамол қолданады.",
        "allergies_ru": "Нет",
        "allergies_kk": "Жоқ",
        "lab_results_json": json.dumps([
            {"name_ru": "SpO2",        "name_kk": "SpO2",        "value": 88,   "unit": "%",             "normal": "95-100", "normal_min": 95, "normal_max": 100},
            {"name_ru": "Лейкоциты",   "name_kk": "Лейкоциттер", "value": 13.8, "unit": "×10⁹/л",        "normal": "4-9",   "normal_min": 4,  "normal_max": 9},
            {"name_ru": "СРБ",         "name_kk": "СРБ",         "value": 64,   "unit": "мг/л",           "normal": "<5",    "normal_min": 0,  "normal_max": 5},
            {"name_ru": "pCO2",        "name_kk": "pCO2",        "value": 52,   "unit": "мм рт.ст.",      "normal": "35-45", "normal_min": 35, "normal_max": 45},
            {"name_ru": "ОФВ1",        "name_kk": "ӨСЖ1",        "value": 38,   "unit": "% от должного",  "normal": ">50%",  "normal_min": 50, "normal_max": 100},
            {"name_ru": "Рентген ОГК", "name_kk": "Кеуде рентгені","value": "Гиперинфляция, уплощение диафрагмы", "unit": "", "normal": "Норма", "is_abnormal": True, "image_url": "/labs/copd_exacerbation.jpg"},
        ]),
        "correct_diagnosis_ru": "ХОБЛ III, обострение средней тяжести, J44.1",
        "correct_diagnosis_kk": "СОЗТ III, орташа ауырлықтағы өршу, J44.1",
        "treatment_protocol_ru": "Ипратропий+сальбутамол небулайзер, преднизолон 40мг/сут × 5 дней, амоксициллин/клавуланат, O2 терапия до SpO2 88-92%",
        "treatment_protocol_kk": "Ипратропий+сальбутамол небулайзер, преднизолон 40мг/тәу × 5 күн, амоксициллин/клавуланат, O2 SpO2 88-92%-ке дейін",
        "sources": json.dumps([{"name": "МЗ РК Протокол J44, 2023"}, {"name": "GOLD COPD Report 2024"}]),
    },

    # ── ИНФЕКЦИОННЫЕ БОЛЕЗНИ ──────────────────────────────────────────────────
    {
        "slug": "brucellosis",
        "specialty": "infectious_disease",
        "icd10": "A23.9",
        "card_color": "#FFF3E0",
        "urgency": "routine",
        "difficulty": "hard",
        "disease_ru": "Бруцеллёз острый",
        "disease_kk": "Жедел бруцеллёз",
        "patient_name_ru": "Нурлан Байжанов",
        "patient_name_kk": "Нұрлан Байжанов",
        "patient_age": 38,
        "patient_gender": "male",
        "chief_complaint_ru": "Волнообразная лихорадка 2 недели, боли в суставах, потливость",
        "chief_complaint_kk": "2 аптадан бері толқынды қызба, буын ауруы және түнгі терлеу",
        "history_ru": "Фермер, работает со скотом. Пьёт некипячёное молоко. Живёт в Алматинской области.",
        "history_kk": "Фермер, малмен жұмыс істейді. Қайнатылмаған сүт ішеді. Алматы облысында тұрады.",
        "allergies_ru": "Нет",
        "allergies_kk": "Жоқ",
        "lab_results_json": json.dumps([
            {"name_ru": "Реакция Райта",    "name_kk": "Райт реакциясы",    "value": "1:400",        "unit": "", "normal": "<1:100",      "is_abnormal": True},
            {"name_ru": "Реакция Хеддлсона","name_kk": "Хеддлсон реакциясы","value": "Положительно","unit": "", "normal": "Отрицательно","is_abnormal": True},
            {"name_ru": "Лейкоциты",        "name_kk": "Лейкоциттер",       "value": 3.2,            "unit": "×10⁹/л", "normal": "4-9",  "normal_min": 4,  "normal_max": 9},
            {"name_ru": "СОЭ",              "name_kk": "ЭШЖ",               "value": 38,             "unit": "мм/ч",   "normal": "2-15", "normal_min": 2,  "normal_max": 15},
            {"name_ru": "АЛТ",              "name_kk": "АЛТ",               "value": 68,             "unit": "Ед/л",   "normal": "<45",  "normal_min": 0,  "normal_max": 45},
        ]),
        "correct_diagnosis_ru": "Бруцеллёз острый, средней тяжести, A23.9",
        "correct_diagnosis_kk": "Жедел бруцеллёз, орташа ауырлықта, A23.9",
        "treatment_protocol_ru": "Доксициклин 100мг ×2/сут + рифампицин 600мг/сут × 6 недель, уведомление СЭС",
        "treatment_protocol_kk": "Доксициклин 100мг ×2/тәу + рифампицин 600мг/тәу × 6 апта, СЭС-ке хабарлау",
        "sources": json.dumps([{"name": "МЗ РК Протокол A23, 2023"}, {"name": "ВОЗ Бруцеллёз 2023"}, {"name": "РЦРЗ Казахстан"}]),
    },

    # ── ЭНДОКРИНОЛОГИЯ ────────────────────────────────────────────────────────
    {
        "slug": "hypothyroidism",
        "specialty": "endocrinology",
        "icd10": "E03.9",
        "card_color": "#E8EAF6",
        "urgency": "routine",
        "difficulty": "medium",
        "disease_ru": "Гипотиреоз первичный",
        "disease_kk": "Бастапқы гипотиреоз",
        "patient_name_ru": "Динара Мусина",
        "patient_name_kk": "Динара Мусина",
        "patient_age": 42,
        "patient_gender": "female",
        "chief_complaint_ru": "Постоянная усталость, набор веса на 8 кг за год и чувство холода",
        "chief_complaint_kk": "Үнемі шаршау, бір жылда 8 кг салмақ қосу және суық сезіну",
        "history_ru": "Аутоиммунный тиреоидит у матери. Волосы ломкие, кожа сухая.",
        "history_kk": "Анасында аутоиммунды тиреоидит. Шаштары сынғыш, тері құрғақ.",
        "allergies_ru": "Нет",
        "allergies_kk": "Жоқ",
        "lab_results_json": json.dumps([
            {"name_ru": "ТТГ",               "name_kk": "ТТГ",               "value": 12.4, "unit": "мЕд/л",  "normal": "0.4-4.0", "normal_min": 0.4, "normal_max": 4.0},
            {"name_ru": "Свободный Т4",      "name_kk": "Еркін Т4",          "value": 8.2,  "unit": "пмоль/л","normal": "12-22",   "normal_min": 12,  "normal_max": 22},
            {"name_ru": "Антитела к ТПО",    "name_kk": "ТПО-ға антиденелер","value": 420,  "unit": "МЕ/мл",  "normal": "<35",     "normal_min": 0,   "normal_max": 35},
            {"name_ru": "Холестерин общий",  "name_kk": "Жалпы холестерин",  "value": 6.8,  "unit": "ммоль/л","normal": "<5.2",    "normal_min": 0,   "normal_max": 5.2},
            {"name_ru": "Гемоглобин",        "name_kk": "Гемоглобин",        "value": 108,  "unit": "г/л",    "normal": "120-160", "normal_min": 120, "normal_max": 160},
        ]),
        "correct_diagnosis_ru": "Первичный гипотиреоз на фоне АИТ, E03.9",
        "correct_diagnosis_kk": "АИТ фонындағы бастапқы гипотиреоз, E03.9",
        "treatment_protocol_ru": "Левотироксин 50 мкг/сут натощак, контроль ТТГ через 6-8 недель, направление к эндокринологу",
        "treatment_protocol_kk": "Левотироксин 50 мкг/тәу аш қарынға, 6-8 аптадан кейін ТТГ бақылауы, эндокринологқа жолдама",
        "sources": json.dumps([{"name": "МЗ РК Протокол E03, 2023"}, {"name": "ETA Guidelines Hypothyroidism 2023"}]),
    },

    # ── НЕВРОЛОГИЯ ────────────────────────────────────────────────────────────
    {
        "slug": "migraine",
        "specialty": "neurology",
        "icd10": "G43.0",
        "card_color": "#F3E5F5",
        "urgency": "routine",
        "difficulty": "easy",
        "disease_ru": "Мигрень без ауры",
        "disease_kk": "Аурасыз мигрень",
        "patient_name_ru": "Асель Токтарова",
        "patient_name_kk": "Әсел Тоқтарова",
        "patient_age": 29,
        "patient_gender": "female",
        "chief_complaint_ru": "Пульсирующая боль в правой половине головы с тошнотой, 2 раза в месяц",
        "chief_complaint_kk": "Айына 2 рет жүрек айнуымен бірге оң жақ басымда соғып тұратын ауырсыну",
        "history_ru": "Приступы с 18 лет. Боль усиливается от света и звуков. Мать тоже страдает мигренью.",
        "history_kk": "18 жасынан бері ұстамалар. Жарық пен дыбыстан ауырсыну күшейеді. Анасы да мигреньмен ауырады.",
        "allergies_ru": "Нет",
        "allergies_kk": "Жоқ",
        "lab_results_json": json.dumps([
            {"name_ru": "Неврологический осмотр","name_kk": "Неврологиялық тексеру","value": "Без патологии","unit": "","normal": "Норма","is_abnormal": False},
            {"name_ru": "АД",                    "name_kk": "АҚ",                  "value": "118/74",      "unit": "мм рт.ст.", "normal": "<140/90", "is_abnormal": False},
            {"name_ru": "Общий анализ крови",    "name_kk": "ЖАН",                 "value": "Норма",       "unit": "", "normal": "Норма", "is_abnormal": False},
            {"name_ru": "МРТ головного мозга",   "name_kk": "Бас мидың МРТ",       "value": "Не требуется при типичной клинике", "unit": "", "normal": "-", "is_abnormal": False},
        ]),
        "correct_diagnosis_ru": "Мигрень без ауры, эпизодическая, G43.0",
        "correct_diagnosis_kk": "Аурасыз мигрень, эпизодтық, G43.0",
        "treatment_protocol_ru": "Суматриптан 50мг при приступе, ибупрофен 400мг при слабых приступах, дневник головной боли",
        "treatment_protocol_kk": "Ұстама кезінде суматриптан 50мг, жеңіл ұстамаларда ибупрофен 400мг, бас ауруы күнделігі",
        "sources": json.dumps([{"name": "МЗ РК Протокол G43, 2023"}, {"name": "EFNS Guidelines Migraine 2022"}]),
    },

    # ── ГАСТРОЭНТЕРОЛОГИЯ ─────────────────────────────────────────────────────
    {
        "slug": "peptic_ulcer",
        "specialty": "gastroenterology",
        "icd10": "K25.9",
        "card_color": "#FFF8E1",
        "urgency": "routine",
        "difficulty": "medium",
        "disease_ru": "Язвенная болезнь желудка",
        "disease_kk": "Асқазан ойық жарасы",
        "patient_name_ru": "Ержан Сабитов",
        "patient_name_kk": "Ержан Сәбитов",
        "patient_age": 44,
        "patient_gender": "male",
        "chief_complaint_ru": "Боль в эпигастрии через 30 минут после еды, изжога, иногда тёмный стул",
        "chief_complaint_kk": "Тамақтан 30 минут өткен соң эпигастрий ауруы, өрт өту, кейде қара нәжіс",
        "history_ru": "Принимает диклофенак по поводу болей в спине год. Курит, пьёт крепкий чай.",
        "history_kk": "Бір жылдан бері арқа ауруына байланысты диклофенак ішеді. Темекі шегеді, күшті шай ішеді.",
        "allergies_ru": "Нет",
        "allergies_kk": "Жоқ",
        "lab_results_json": json.dumps([
            {"name_ru": "H.pylori (тест)", "name_kk": "H.pylori (тест)",  "value": "Положительно",       "unit": "",    "normal": "Отрицательно",   "is_abnormal": True},
            {"name_ru": "Кал скрытая кровь","name_kk": "Жасырын қан нәжіс","value": "Положительно",      "unit": "",    "normal": "Отрицательно",   "is_abnormal": True},
            {"name_ru": "Гемоглобин",      "name_kk": "Гемоглобин",       "value": 112,                  "unit": "г/л", "normal": "130-170",        "normal_min": 130, "normal_max": 170},
            {"name_ru": "ФГДС",            "name_kk": "ФЭГДС",            "value": "Язва антрума 1.2см", "unit": "",    "normal": "Норма слизистой","is_abnormal": True},
        ]),
        "correct_diagnosis_ru": "Язвенная болезнь желудка, H.pylori-ассоциированная, K25.9",
        "correct_diagnosis_kk": "H.pylori-байланысты асқазан ойық жарасы, K25.9",
        "treatment_protocol_ru": "Тройная терапия: омепразол 20мг + кларитромицин 500мг + амоксициллин 1г — ×2/сут × 14 дней. Отменить НПВС.",
        "treatment_protocol_kk": "Үштік терапия: омепразол 20мг + кларитромицин 500мг + амоксициллин 1г — ×2/тәу × 14 күн. ҚҚЕД тоқтату.",
        "sources": json.dumps([{"name": "МЗ РК Протокол K25, 2023"}, {"name": "Маастрихт VI консенсус H.pylori 2022"}]),
    },
]

# Slugs that already exist in DB but need new column values updated
EXISTING_UPDATES = {
    "arvi_adult": {
        "specialty": "internal_medicine", "icd10": "J06.9",
        "card_color": "#E8F5E9", "urgency": "routine",
    },
    "pneumonia_community": {
        "specialty": "internal_medicine", "icd10": "J18.1",
        "card_color": "#E8F5E9", "urgency": "routine",
        "lab_results_json": json.dumps([
            {"name_ru": "Лейкоциты",     "name_kk": "Лейкоциттер",   "value": 18.4, "unit": "×10⁹/л", "normal": "4-9",    "normal_min": 4,  "normal_max": 9},
            {"name_ru": "Нейтрофилы",    "name_kk": "Нейтрофилдер",  "value": 88,   "unit": "%",       "normal": "45-70",  "normal_min": 45, "normal_max": 70},
            {"name_ru": "СОЭ",           "name_kk": "ЭШЖ",           "value": 48,   "unit": "мм/ч",    "normal": "2-15",   "normal_min": 2,  "normal_max": 15},
            {"name_ru": "СРБ",           "name_kk": "СРБ",           "value": 124,  "unit": "мг/л",    "normal": "<5",     "normal_min": 0,  "normal_max": 5},
            {"name_ru": "Прокальцитонин","name_kk": "Прокальцитонин","value": 2.4,  "unit": "нг/мл",   "normal": "<0.5",   "normal_min": 0,  "normal_max": 0.5},
            {"name_ru": "SpO₂",          "name_kk": "SpO₂",          "value": 92,   "unit": "%",        "normal": "95-100", "normal_min": 95, "normal_max": 100},
            {"name_ru": "Рентген ОГК",   "name_kk": "Кеуде рентгені","value": "Долевое затемнение в нижних отделах правого лёгкого", "unit": "", "normal": "Лёгочный рисунок не изменён", "is_abnormal": True, "image_url": "/labs/pneumonia_lobar.jpg"},
        ]),
    },
    "brucellosis": {
        "specialty": "infectious_disease", "icd10": "A23.9",
        "card_color": "#FFF3E0", "urgency": "routine",
    },
}


def _migrate(cur):
    """Add new columns to scenarios if they don't exist yet."""
    new_cols = [
        ("specialty",    "TEXT NOT NULL DEFAULT 'internal_medicine'"),
        ("specialty_ru", "TEXT NOT NULL DEFAULT 'Терапия'"),
        ("specialty_kk", "TEXT NOT NULL DEFAULT 'Терапия'"),
        ("icd10",        "TEXT NOT NULL DEFAULT ''"),
        ("card_color",   "TEXT NOT NULL DEFAULT '#FFFFFF'"),
        ("urgency",      "TEXT NOT NULL DEFAULT 'routine'"),
    ]
    existing = {row[1] for row in cur.execute("PRAGMA table_info(scenarios)").fetchall()}
    for col, definition in new_cols:
        if col not in existing:
            cur.execute(f"ALTER TABLE scenarios ADD COLUMN {col} {definition}")
            print(f"  migrated: added column {col}")


def seed():
    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()

    _migrate(cur)

    # Update existing rows with new fields
    for slug, fields in EXISTING_UPDATES.items():
        row = cur.execute("SELECT id FROM scenarios WHERE slug = ?", (slug,)).fetchone()
        if row:
            sp = fields["specialty"]
            if "lab_results_json" in fields:
                cur.execute(
                    "UPDATE scenarios SET specialty=?, specialty_ru=?, specialty_kk=?, icd10=?, card_color=?, urgency=?, lab_results_json=? WHERE slug=?",
                    (sp, SPECIALTY_LABELS[sp]["ru"], SPECIALTY_LABELS[sp]["kk"],
                     fields["icd10"], fields["card_color"], fields["urgency"], fields["lab_results_json"], slug)
                )
            else:
                cur.execute(
                    "UPDATE scenarios SET specialty=?, specialty_ru=?, specialty_kk=?, icd10=?, card_color=?, urgency=? WHERE slug=?",
                    (sp, SPECIALTY_LABELS[sp]["ru"], SPECIALTY_LABELS[sp]["kk"],
                     fields["icd10"], fields["card_color"], fields["urgency"], slug)
                )
            print(f"  updated: {slug}")

    inserted = 0
    for s in SCENARIOS:
        existing = cur.execute("SELECT id FROM scenarios WHERE slug = ?", (s["slug"],)).fetchone()
        if existing:
            sp = s["specialty"]
            cur.execute(
                "UPDATE scenarios SET specialty=?, specialty_ru=?, specialty_kk=?, icd10=?, card_color=?, urgency=?, lab_results_json=? WHERE slug=?",
                (sp, SPECIALTY_LABELS[sp]["ru"], SPECIALTY_LABELS[sp]["kk"],
                 s["icd10"], s["card_color"], s["urgency"], s["lab_results_json"], s["slug"])
            )
            print(f"  updated fields: {s['slug']}")
            continue

        sp = s["specialty"]
        cur.execute(
            """INSERT INTO scenarios (
                slug, specialty, specialty_ru, specialty_kk,
                icd10, card_color, urgency, difficulty,
                disease_ru, disease_kk,
                patient_name_ru, patient_name_kk,
                patient_age, patient_gender,
                chief_complaint_ru, chief_complaint_kk,
                history_ru, history_kk,
                allergies_ru, allergies_kk,
                lab_results_json,
                correct_diagnosis_ru, correct_diagnosis_kk,
                treatment_protocol_ru, treatment_protocol_kk,
                sources
            ) VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)""",
            (
                s["slug"], sp, SPECIALTY_LABELS[sp]["ru"], SPECIALTY_LABELS[sp]["kk"],
                s["icd10"], s["card_color"], s["urgency"], s["difficulty"],
                s["disease_ru"], s["disease_kk"],
                s["patient_name_ru"], s["patient_name_kk"],
                s["patient_age"], s["patient_gender"],
                s["chief_complaint_ru"], s["chief_complaint_kk"],
                s["history_ru"], s["history_kk"],
                s.get("allergies_ru", "Нет"), s.get("allergies_kk", "Жоқ"),
                s["lab_results_json"],
                s["correct_diagnosis_ru"], s["correct_diagnosis_kk"],
                s["treatment_protocol_ru"], s["treatment_protocol_kk"],
                s["sources"],
            ),
        )
        print(f"  inserted: {s['slug']}")
        inserted += 1

    conn.commit()
    conn.close()
    print(f"\nDone. Inserted {inserted} new scenario(s).")


if __name__ == "__main__":
    seed()
