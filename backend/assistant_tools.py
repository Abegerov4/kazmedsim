"""Tools available to the AI medical assistant on /patients.

Three deterministic functions the LLM can call to ground its answers:
    1) search_medical_protocol(condition)
    2) clinical_calculator(name, params)
    3) drug_interactions(drugs)

Pure functions — no DB writes, no side effects. Safe to call any number of times.
"""
from __future__ import annotations

import json
import os
import sqlite3
from typing import Any


DB_PATH = os.environ.get(
    "DB_PATH",
    os.path.join(os.path.dirname(__file__), "..", "db", "kazmedsim.db"),
)


# ── 1) Medical protocols ─────────────────────────────────────────────────────

# Conditions NOT covered by scenarios DB — common emergencies / topics.
EXTRA_PROTOCOLS: dict[str, dict[str, str]] = {
    "анафилаксия": {
        "icd10": "T78.2",
        "name": "Анафилактический шок",
        "criteria": "Острое начало, поражение кожи/слизистых + (дыхательная недостаточность ИЛИ гипотензия) после контакта с триггером",
        "treatment": "1. АДРЕНАЛИН 0.3–0.5 мг в/м в наружную поверхность бедра, повторять каждые 5–15 мин при необходимости\n2. Уложить, поднять ноги. Кислород 8–10 л/мин\n3. Инфузия 0.9% NaCl 1–2 л быстро при гипотензии\n4. Гидрокортизон 200 мг в/в, дифенгидрамин 25–50 мг в/в (адъювант, НЕ заменяет адреналин)\n5. Сальбутамол при бронхоспазме\n6. Госпитализация, наблюдение 6–24 ч",
        "source": "МЗ РК Протокол T78, Resuscitation Council 2021",
    },
    "сердечно-лёгочная реанимация": {
        "icd10": "I46",
        "name": "СЛР у взрослого",
        "criteria": "Отсутствие сознания + отсутствие нормального дыхания (агональные вдохи не считаются)",
        "treatment": "1. Вызов реанимационной бригады, дефибриллятор\n2. Компрессии 30:2 (если без подготовки — только компрессии), частота 100–120/мин, глубина 5–6 см\n3. Минимизировать паузы\n4. Дефибрилляция при ФЖ/ЖТ — 120–200 Дж бифазный\n5. Адреналин 1 мг в/в каждые 3–5 мин\n6. Амиодарон 300 мг при ФЖ/ЖТ устойчивой к 3-му разряду\n7. Лечение обратимых причин: 4H+4T (гипоксия, гиповолемия, гипо/гиперкалиемия, гипотермия; тромбоз, тампонада, токсины, пневмоторакс)",
        "source": "AHA ACLS 2020, ERC 2021",
    },
    "септический шок": {
        "icd10": "R57.2",
        "name": "Септический шок",
        "criteria": "Сепсис + персистирующая гипотензия (АДср<65 после инфузии) + лактат >2 ммоль/л",
        "treatment": "1. Hour-1 bundle: лактат, посев крови, антибиотик широкого спектра, инфузия 30 мл/кг кристаллоид\n2. Норадреналин при сохраняющейся гипотензии (цель АДср ≥65)\n3. Вазопрессин 0.03 ЕД/мин — второй вазопрессор\n4. Гидрокортизон 200 мг/сут при рефрактерном шоке\n5. Источник-контроль (дренаж, удаление инфицированного материала)\n6. ОРИТ, инвазивный мониторинг",
        "source": "Surviving Sepsis Campaign 2021, МЗ РК Протокол R57",
    },
    "острая декомпенсация хсн": {
        "icd10": "I50.9",
        "name": "Острая декомпенсация ХСН",
        "criteria": "Прогрессирующая одышка, ортопноэ, отёки, влажные хрипы, NT-proBNP↑",
        "treatment": "1. Положение сидя, кислород при SpO₂<92%\n2. Фуросемид 20–80 мг в/в болюсно, при необходимости инфузия\n3. Нитраты при САД>110 (изосорбид-динитрат в/в)\n4. CPAP/BiPAP при отёке лёгких\n5. Поиск триггера: ОИМ, аритмия, инфекция, несоблюдение терапии\n6. Госпитализация",
        "source": "ESC Acute HF 2021, МЗ РК Протокол I50",
    },
    "острая почечная травма": {
        "icd10": "N17.9",
        "name": "Острое повреждение почек (AKI)",
        "criteria": "Креатинин ↑ ≥26.5 мкмоль/л за 48 ч ИЛИ ↑×1.5 от исходного за 7 дней ИЛИ диурез <0.5 мл/кг/ч ≥6 ч",
        "treatment": "1. Поиск и устранение причины: дегидратация, обструкция, нефротоксины (НПВП, аминогликозиды, контраст)\n2. Регидратация при преренальном AKI\n3. Отмена нефротоксичных препаратов и пересчёт доз по СКФ\n4. УЗИ почек для исключения постренальной обструкции\n5. Контроль K, ацидоза, объёмной перегрузки\n6. Заместительная почечная терапия (ЗПТ) при отёке лёгких, гиперкалиемии, ацидозе устойчивых к терапии",
        "source": "KDIGO AKI 2012, МЗ РК Протокол N17",
    },
}


def search_medical_protocol(condition: str) -> dict[str, Any]:
    """Find a clinical protocol matching `condition` (RU / KZ / EN phrase).

    Hybrid retrieval:
      1. **RAG** — semantic search across the indexed MoH RK protocol PDFs
         (vector embeddings, see backend/rag.py). Returns the top chunks
         verbatim with page citations.
      2. **Scenarios DB** — keyword scan of the 49 scenario rows, used as a
         fallback when RAG is unavailable or finds nothing relevant.
      3. **Extra catalog** — small hand-curated emergencies (anaphylaxis,
         CPR, septic shock, decompensated HF, AKI) not yet in the PDF index.
    """
    q = (condition or "").strip()
    if not q:
        return {"found": False, "message": "Empty query"}

    # 1) RAG over real MoH RK protocol PDFs.
    try:
        from backend.rag import search_protocols
        hits = search_protocols(q, k=4, min_score=0.30)
    except Exception:
        hits = []

    if hits:
        # Group hits by document so the LLM sees coherent excerpts.
        by_doc: dict[str, list[dict]] = {}
        for h in hits:
            by_doc.setdefault(h["doc_title"], []).append(h)
        top_doc = next(iter(by_doc))
        top_doc_hits = by_doc[top_doc]
        return {
            "found":  True,
            "source": "rag",
            "name":   top_doc,
            "icd10":  "",       # not stored in chunks; the LLM reads it from excerpt text
            "excerpts": [
                {
                    "doc":    h["doc_title"],
                    "pages":  (f"{h['page_start']}–{h['page_end']}"
                               if h["page_start"] != h["page_end"]
                               else str(h["page_start"])),
                    "score":  h["score"],
                    "text":   h["text"],
                }
                for h in hits
            ],
            "citation_format": "Цитируй как: «Протокол МЗ РК — <название>, стр. <pages>»",
        }

    # 2) Fallback — keyword scan of scenarios DB.
    import re
    q_lower = q.lower()
    tokens = [t for t in re.split(r"[\s,/;.()-]+", q_lower) if len(t) >= 4]
    search_terms = list({*tokens, q_lower})
    rows = []
    try:
        conn = sqlite3.connect(DB_PATH)
        conn.row_factory = sqlite3.Row
        clauses, params = [], []
        for t in search_terms:
            like = f"%{t}%"
            clauses.append(
                "LOWER(disease_ru) LIKE ? OR LOWER(disease_kk) LIKE ? "
                "OR LOWER(correct_diagnosis_ru) LIKE ? OR LOWER(icd10) LIKE ?"
            )
            params.extend([like, like, like, like])
        where = " OR ".join(f"({c})" for c in clauses) if clauses else "1=0"
        rows = conn.execute(
            f"""SELECT icd10, disease_ru, correct_diagnosis_ru, treatment_protocol_ru, sources
                FROM scenarios WHERE {where} LIMIT 5""",
            params,
        ).fetchall()
        conn.close()
    except Exception:
        rows = []

    if rows:
        r = rows[0]
        return {
            "found":     True,
            "source":    "scenarios_db",
            "icd10":     r["icd10"],
            "name":      r["disease_ru"],
            "diagnosis": r["correct_diagnosis_ru"],
            "treatment": r["treatment_protocol_ru"],
            "sources":   json.loads(r["sources"]) if r["sources"] else [],
        }

    # 3) Extra catalog of emergencies.
    for key, proto in EXTRA_PROTOCOLS.items():
        if key in q_lower or any(word in q_lower for word in key.split()):
            return {"found": True, "source": "extra_catalog", **proto}

    return {
        "found": False,
        "message": (
            f"Протокол для «{condition}» не найден в RAG-индексе, в БД сценариев и в "
            "справочнике неотложных состояний. Уточни запрос или укажи МКБ-10."
        ),
    }


# ── 2) Clinical calculators ──────────────────────────────────────────────────

def _cha2ds2vasc(p: dict) -> dict:
    """CHA₂DS₂-VASc — риск инсульта при ФП."""
    score = 0
    score += 1 if p.get("chf") else 0
    score += 1 if p.get("hypertension") else 0
    age = int(p.get("age", 0))
    score += 2 if age >= 75 else (1 if age >= 65 else 0)
    score += 1 if p.get("diabetes") else 0
    score += 2 if p.get("stroke_tia") else 0
    score += 1 if p.get("vascular_disease") else 0
    score += 1 if p.get("sex_female") else 0

    if score == 0:
        rec = "Антикоагулянты не показаны"
    elif score == 1 and not p.get("sex_female"):
        rec = "Рассмотреть антикоагулянт (NOAC); индивидуальное решение"
    elif score == 1 and p.get("sex_female"):
        rec = "Антикоагулянты не показаны (балл за пол не учитывать как единственный)"
    else:
        rec = "Показан пероральный антикоагулянт (NOAC предпочтительнее варфарина)"

    return {"score": score, "interpretation": f"CHA₂DS₂-VASc = {score}", "recommendation": rec}


def _wells_dvt(p: dict) -> dict:
    """Wells score для ТГВ."""
    score = 0
    score += 1 if p.get("active_cancer") else 0
    score += 1 if p.get("paralysis_paresis_immobilization") else 0
    score += 1 if p.get("bedridden_recent_surgery") else 0
    score += 1 if p.get("tenderness_along_veins") else 0
    score += 1 if p.get("entire_leg_swollen") else 0
    score += 1 if p.get("calf_swelling_3cm") else 0
    score += 1 if p.get("pitting_edema") else 0
    score += 1 if p.get("collateral_veins") else 0
    score += 1 if p.get("previous_dvt") else 0
    score -= 2 if p.get("alternative_diagnosis_likely") else 0

    if score >= 3:
        risk, action = "Высокая вероятность ТГВ", "УЗДГ вен. При недоступности — антикоагулянт до результата"
    elif score >= 1:
        risk, action = "Средняя вероятность", "D-димер; если повышен — УЗДГ"
    else:
        risk, action = "Низкая вероятность", "D-димер для исключения. Если в норме — ТГВ исключён"

    return {"score": score, "interpretation": f"Wells DVT = {score} ({risk})", "recommendation": action}


def _qsofa(p: dict) -> dict:
    """qSOFA — быстрый скрининг сепсиса."""
    score = 0
    score += 1 if int(p.get("respiratory_rate", 0)) >= 22 else 0
    score += 1 if int(p.get("systolic_bp", 999)) <= 100 else 0
    score += 1 if p.get("altered_mental_status") else 0

    if score >= 2:
        rec = "Высокий риск сепсиса/неблагоприятного исхода. Lactate, посев, инфузия 30 мл/кг, антибиотик в течение 1 часа"
    else:
        rec = "Низкий риск, но не исключает сепсис. Клиническая оценка обязательна"

    return {"score": score, "interpretation": f"qSOFA = {score}/3", "recommendation": rec}


def _ckd_epi(p: dict) -> dict:
    """eGFR по CKD-EPI 2021 (без учёта расы)."""
    creat_umol = float(p.get("creatinine_umol", 0))
    age = float(p.get("age", 0))
    sex_female = bool(p.get("sex_female"))
    if creat_umol <= 0 or age <= 0:
        return {"error": "Нужны creatinine_umol и age >0"}

    creat_mg = creat_umol / 88.4
    if sex_female:
        kappa, alpha, sex_factor = 0.7, -0.241, 1.012
    else:
        kappa, alpha, sex_factor = 0.9, -0.302, 1.0

    ratio = creat_mg / kappa
    egfr = 142 * (min(ratio, 1) ** alpha) * (max(ratio, 1) ** -1.200) * (0.9938 ** age) * sex_factor

    if egfr >= 90:
        stage = "G1 — норма или повышенная (требуется маркёр повреждения для ХБП)"
    elif egfr >= 60:
        stage = "G2 — лёгкое снижение"
    elif egfr >= 45:
        stage = "G3a — умеренное снижение"
    elif egfr >= 30:
        stage = "G3b — умеренно-тяжёлое снижение"
    elif egfr >= 15:
        stage = "G4 — тяжёлое снижение"
    else:
        stage = "G5 — терминальная почечная недостаточность"

    return {
        "egfr_ml_min_173m2": round(egfr, 1),
        "interpretation": f"eGFR = {round(egfr, 1)} мл/мин/1.73м², {stage}",
        "recommendation": "Учесть при дозировании нефротоксичных и почечно-выводимых препаратов",
    }


def _heart_score(p: dict) -> dict:
    """HEART score для боли в груди в приёмном."""
    score = 0
    history = int(p.get("history", 0))   # 0 slightly / 1 moderately / 2 highly suspicious
    ecg = int(p.get("ecg", 0))            # 0 normal / 1 nonspec / 2 significant ST
    age = float(p.get("age", 0))
    age_pts = 0 if age < 45 else (1 if age < 65 else 2)
    risk_factors = int(p.get("risk_factors", 0))  # 0 / 1 / 2 (число факторов: HTN, DM, dyslip, smoking, фам.анамнез ИБС, ИМТ>30)
    rf_pts = 0 if risk_factors == 0 else (1 if risk_factors <= 2 else 2)
    troponin = int(p.get("troponin", 0))  # 0 normal / 1 1-3×ULN / 2 >3×ULN

    score = history + ecg + age_pts + rf_pts + troponin

    if score <= 3:
        rec = "Низкий риск (≤3): MACE 1.7%. Возможна выписка с амбулаторным наблюдением"
    elif score <= 6:
        rec = "Средний риск (4–6): MACE 16.6%. Наблюдение, повтор тропонина 3 ч, кардиолог"
    else:
        rec = "Высокий риск (≥7): MACE 50.1%. Госпитализация, инвазивная стратегия"

    return {"score": score, "interpretation": f"HEART = {score}/10", "recommendation": rec}


_CALCULATORS = {
    "cha2ds2vasc": _cha2ds2vasc,
    "wells_dvt": _wells_dvt,
    "qsofa": _qsofa,
    "ckd_epi": _ckd_epi,
    "heart_score": _heart_score,
}


def clinical_calculator(name: str, params: dict | None = None) -> dict:
    """Compute one of the supported clinical scores."""
    fn = _CALCULATORS.get((name or "").strip().lower())
    if not fn:
        return {
            "error": f"Калькулятор «{name}» не поддерживается",
            "available": list(_CALCULATORS.keys()),
        }
    try:
        return fn(params or {})
    except Exception as e:
        return {"error": f"Ошибка вычисления: {e}"}


# ── 3) Drug interactions ─────────────────────────────────────────────────────

# Each entry: ("drug A keyword", "drug B keyword") → (severity, mechanism, action)
# Drug "keyword" matches if it appears as substring (case-insensitive) in any
# of the provided drug names. Both directions match.
_INTERACTIONS: list[tuple[str, str, str, str, str]] = [
    ("варфарин", "нпвп",            "major",    "Усиление антикоагуляции + гастроэрозивный эффект", "Избегать. При необходимости — парацетамол; если НПВП обязателен, ИПП + контроль INR"),
    ("варфарин", "аспирин",         "major",    "Двойной риск кровотечения",                       "Только по строгим показаниям, контроль INR, ИПП"),
    ("варфарин", "амиодарон",       "major",    "Амиодарон тормозит CYP2C9 — ↑INR в 2–3 раза",     "Снизить варфарин на 30–50%, контроль INR через 3–5 дней"),
    ("варфарин", "кларитромицин",   "major",    "↑INR, риск кровотечения",                         "Заменить антибиотик; если нельзя — частый контроль INR"),
    ("варфарин", "флуконазол",      "major",    "↑INR",                                            "Снизить варфарин на 30%, контроль INR"),
    ("апф",      "спиронолактон",   "moderate", "Гиперкалиемия",                                   "Контроль K каждые 1–2 нед, избегать препаратов K"),
    ("апф",      "нпвп",            "moderate", "Снижение эффекта ИАПФ, риск ОПП",                 "Парацетамол вместо НПВП при возможности"),
    ("сартан",   "спиронолактон",   "moderate", "Гиперкалиемия",                                   "Контроль K"),
    ("аспирин",  "клопидогрел",     "moderate", "Двойная антитромбоцитарная — риск кровотечения",  "Только по показаниям (ОКС, ЧКВ), ИПП, ограничить длительность"),
    ("статин",   "кларитромицин",   "major",    "Ингибирование CYP3A4 → ↑концентрация статина → рабдомиолиз", "Отменить статин на курс или заменить АБ (азитромицин безопаснее)"),
    ("статин",   "эритромицин",     "major",    "Рабдомиолиз",                                     "Заменить АБ"),
    ("статин",   "грейпфрут",       "moderate", "↑концентрация статина",                            "Избегать грейпфрута"),
    ("симвастатин","амиодарон",     "major",    "Рабдомиолиз",                                     "Симвастатин ≤20 мг/сут или заменить на правастатин/розувастатин"),
    ("метформин","контраст",        "major",    "Лактоацидоз при ОПП",                             "Отменить метформин на 48 ч до и после контраста, контроль СКФ"),
    ("ссиоз",    "трамадол",        "major",    "Серотониновый синдром",                           "Избегать сочетания, заменить анальгетик"),
    ("ссиоз",    "линезолид",       "major",    "Серотониновый синдром",                           "Не сочетать, перерыв ≥2 нед после СИОЗС"),
    ("дигоксин", "амиодарон",       "major",    "↑концентрация дигоксина в 1.7×",                  "Снизить дигоксин на 50%, контроль уровня"),
    ("дигоксин", "верапамил",       "major",    "↑концентрация дигоксина",                         "Снизить дигоксин, контроль уровня"),
    ("дигоксин", "гипокалиемия",    "major",    "↑токсичность дигоксина",                          "Контроль и коррекция K"),
    ("нпвп",     "гкс",             "moderate", "Гастроэрозивный риск, желудочное кровотечение",   "ИПП защита, оценить необходимость"),
    ("гкс",      "нпвп",            "moderate", "Гастроэрозивный риск",                            "ИПП защита"),
    ("ципрофлоксацин","теофиллин",  "major",    "↑концентрация теофиллина — судороги, аритмии",    "Заменить АБ или снизить дозу теофиллина"),
    ("ципрофлоксацин","варфарин",   "moderate", "↑INR",                                            "Контроль INR"),
    ("макролид", "qt-удлиняющ",     "major",    "Удлинение QT, torsades",                          "Проверять QTc, избегать комбинаций"),
    ("апф",      "литий",           "moderate", "↑Li, токсичность",                                "Контроль уровня лития, гидратация"),
    ("нпвп",     "диуретик",        "moderate", "Снижение эффекта диуретика, ОПП у пожилых",       "Парацетамол, контроль креатинина"),
    ("опиоид",   "бензодиазепин",   "major",    "Депрессия дыхания, риск смерти",                  "Избегать одновременного приёма"),
]

# Class synonyms — substring match (case-insensitive).
_CLASS_SYNONYMS: dict[str, list[str]] = {
    "нпвп":        ["ибупрофен", "диклофенак", "кеторолак", "мелоксикам", "напроксен", "индометацин", "кетопрофен", "нпвп", "nsaid"],
    "апф":         ["эналаприл", "лизиноприл", "рамиприл", "периндоприл", "каптоприл", "иапф", "апф", "ace"],
    "сартан":      ["лозартан", "валсартан", "телмисартан", "ирбесартан", "кандесартан", "сартан"],
    "статин":      ["аторвастатин", "розувастатин", "симвастатин", "правастатин", "питавастатин", "статин"],
    "ссиоз":       ["сертралин", "флуоксетин", "пароксетин", "циталопрам", "эсциталопрам", "ссиоз", "ssri"],
    "макролид":    ["азитромицин", "кларитромицин", "эритромицин", "макролид"],
    "гкс":         ["преднизолон", "дексаметазон", "гидрокортизон", "метилпреднизолон", "будесонид", "гкс", "глюкокортикоид"],
    "диуретик":    ["фуросемид", "торасемид", "гидрохлортиазид", "индапамид", "диуретик"],
    "опиоид":      ["морфин", "фентанил", "трамадол", "оксикодон", "опиоид"],
    "бензодиазепин":["диазепам", "лоразепам", "клоназепам", "альпразолам", "мидазолам", "бензодиазепин"],
    "qt-удлиняющ":  ["хинидин", "соталол", "галоперидол", "ондансетрон", "qt"],
    "контраст":    ["йод", "контраст"],
}


def _drug_matches(token: str, drug_name: str) -> bool:
    """Token matches drug_name if drug_name contains token directly, or contains
    any synonym mapped from token (class)."""
    name = drug_name.lower()
    if token in name:
        return True
    for syn in _CLASS_SYNONYMS.get(token, []):
        if syn in name:
            return True
    return False


def drug_interactions(drugs: list[str]) -> dict:
    """Check given drug list for pairwise interactions from a local catalog."""
    if not drugs or not isinstance(drugs, list):
        return {"warnings": [], "message": "Список препаратов пуст"}

    names = [d.lower().strip() for d in drugs if isinstance(d, str) and d.strip()]
    warnings = []

    for token_a, token_b, severity, mechanism, action in _INTERACTIONS:
        # Find at least one drug matching A and a DIFFERENT drug matching B
        matched_a = [d for d in names if _drug_matches(token_a, d)]
        matched_b = [d for d in names if _drug_matches(token_b, d)]
        pairs = [(a, b) for a in matched_a for b in matched_b if a != b]
        if pairs:
            a, b = pairs[0]
            warnings.append({
                "drug_a": a,
                "drug_b": b,
                "severity": severity,
                "mechanism": mechanism,
                "action": action,
            })

    if not warnings:
        return {"warnings": [], "message": "Значимых взаимодействий не обнаружено в локальном справочнике"}
    return {
        "warnings": warnings,
        "summary": f"Найдено {len(warnings)} взаимодействий: " +
                   ", ".join(f"{w['severity']}" for w in warnings),
    }


# ── Tool schemas (OpenAI function-calling format) ────────────────────────────

TOOL_SCHEMAS: list[dict] = [
    {
        "type": "function",
        "function": {
            "name": "search_medical_protocol",
            "description": (
                "Найти клинический протокол МЗ РК по нозологии, симптому или "
                "конкретному вопросу. Использовать ВСЕГДА когда студент спрашивает "
                "о лечении заболевания, дозах препаратов, тактике, критериях "
                "диагноза или сравнении препаратов. Возвращает релевантные "
                "выдержки из реальных PDF протоколов МЗ РК с номерами страниц. "
                "ОБЯЗАТЕЛЬНО цитируй excerpts в ответе и указывай источник "
                "(название протокола + страница)."
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "condition": {
                        "type": "string",
                        "description": (
                            "Запрос свободной формой — нозология, симптом, "
                            "вопрос о лечении или код МКБ-10. Чем конкретнее "
                            "вопрос, тем точнее retrieval (напр. 'антибиотик "
                            "первой линии при внебольничной пневмонии' лучше "
                            "чем просто 'пневмония')."
                        ),
                    },
                },
                "required": ["condition"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "clinical_calculator",
            "description": "Рассчитать клиническую шкалу. Использовать когда вопрос связан с риском, тяжестью или стратификацией. ВСЕГДА вызывать вместо ответа от себя если упомянут CHA₂DS₂-VASc, Wells, qSOFA, eGFR, CKD-EPI, HEART.",
            "parameters": {
                "type": "object",
                "properties": {
                    "name": {
                        "type": "string",
                        "enum": ["cha2ds2vasc", "wells_dvt", "qsofa", "ckd_epi", "heart_score"],
                        "description": "Идентификатор шкалы",
                    },
                    "params": {
                        "type": "object",
                        "description": (
                            "Параметры. Для cha2ds2vasc: {age, sex_female, chf, hypertension, "
                            "diabetes, stroke_tia, vascular_disease}. "
                            "Для wells_dvt: {active_cancer, paralysis_paresis_immobilization, "
                            "bedridden_recent_surgery, tenderness_along_veins, entire_leg_swollen, "
                            "calf_swelling_3cm, pitting_edema, collateral_veins, previous_dvt, "
                            "alternative_diagnosis_likely}. "
                            "Для qsofa: {respiratory_rate, systolic_bp, altered_mental_status}. "
                            "Для ckd_epi: {creatinine_umol, age, sex_female}. "
                            "Для heart_score: {history (0-2), ecg (0-2), age, risk_factors (0-N), troponin (0-2)}."
                        ),
                    },
                },
                "required": ["name", "params"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "drug_interactions",
            "description": "Проверить список препаратов на клинически значимые лекарственные взаимодействия. ВСЕГДА вызывать когда студент перечисляет несколько препаратов или спрашивает 'можно ли назначать X и Y вместе'.",
            "parameters": {
                "type": "object",
                "properties": {
                    "drugs": {
                        "type": "array",
                        "items": {"type": "string"},
                        "description": "Список МНН препаратов на русском (напр. ['варфарин', 'ибупрофен', 'омепразол'])",
                    },
                },
                "required": ["drugs"],
            },
        },
    },
]


# Registry used by the endpoint loop
TOOL_IMPLS = {
    "search_medical_protocol": lambda args: search_medical_protocol(**args),
    "clinical_calculator":     lambda args: clinical_calculator(**args),
    "drug_interactions":       lambda args: drug_interactions(**args),
}
