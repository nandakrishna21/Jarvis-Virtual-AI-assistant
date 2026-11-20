import json, re
from datetime import date, timedelta
from app.database.session import SessionLocal
from app.database.models import StudyPlan, StudyTopic, QuizResult
from app.agents.government_exam.syllabus import SYLLABUS, exam_names, topics_for, sections_for

QUESTION_BANK = {
    "Percentage": [
        {"q": "What is 15% of 240?", "options": ["30", "36", "40", "45"], "answer": "B", "explanation": "15/100 * 240 = 36."},
        {"q": "A number increased by 20% and then decreased by 20% equals the original number?", "options": ["True", "False"], "answer": "B", "explanation": "1.2 * 0.8 = 0.96, so it is 4% less."},
        {"q": "25% of 40% of 500 equals?", "options": ["40", "50", "60", "75"], "answer": "B", "explanation": "0.25 * 0.40 * 500 = 50."},
    ],
    "Profit and Loss": [
        {"q": "An item bought for 400 is sold for 500. Profit percentage is?", "options": ["20%", "25%", "30%", "15%"], "answer": "B", "explanation": "100/400 * 100 = 25%."},
        {"q": "Selling price is 660 and profit is 10%, cost price is?", "options": ["600", "620", "640", "660"], "answer": "A", "explanation": "660/1.1 = 600."},
    ],
    "Ratio and Proportion": [
        {"q": "If A:B = 2:3 and B:C = 4:5, then A:C is?", "options": ["8:15", "2:5", "3:5", "6:15"], "answer": "A", "explanation": "B=12, A=8, C=15, so A:C = 8:15."},
    ],
    "Number System": [
        {"q": "The smallest number divisible by 12, 15 and 18 is?", "options": ["90", "120", "180", "360"], "answer": "C", "explanation": "LCM(12,15,18) = 180."},
        {"q": "What is the remainder when 1234 is divided by 7?", "options": ["2", "3", "4", "5"], "answer": "A", "explanation": "7 * 176 = 1232, remainder 2."},
    ],
    "Time and Work": [
        {"q": "A can do a work in 12 days, B in 24 days. Together they finish in?", "options": ["6 days", "8 days", "9 days", "10 days"], "answer": "B", "explanation": "1/12 + 1/24 = 3/24 = 1/8, so 8 days."},
    ],
    "Speed and Distance": [
        {"q": "A car covers 240 km in 4 hours. Speed is?", "options": ["50 km/h", "60 km/h", "70 km/h", "80 km/h"], "answer": "B", "explanation": "240/4 = 60 km/h."},
    ],
    "Interest": [
        {"q": "Simple interest on 5000 at 8% per annum for 2 years is?", "options": ["400", "600", "800", "1000"], "answer": "C", "explanation": "5000 * 0.08 * 2 = 800."},
    ],
    "Average": [
        {"q": "Average of 5 numbers is 20. If one number 30 is replaced by 10, new average is?", "options": ["16", "18", "19", "20"], "answer": "A", "explanation": "Total is 5*20 = 100. After replacing 30 with 10 the total is 80, so 80/5 = 16."},
    ],
    "Simplification": [
        {"q": "15% of 50% of 200 is?", "options": ["10", "15", "20", "25"], "answer": "B", "explanation": "0.15 * 0.5 * 200 = 15."},
    ],
    "Data Interpretation": [
        {"q": "In a class of 40, 25 study Science. What percentage do not study Science?", "options": ["25%", "37.5%", "40%", "62.5%"], "answer": "B", "explanation": "15/40 = 37.5%."},
    ],
    "Algebra": [
        {"q": "Solve for x: 2x + 7 = 19", "options": ["5", "6", "7", "13"], "answer": "B", "explanation": "2x = 12, x = 6."},
    ],
    "Geometry": [
        {"q": "Area of a circle with radius 7 (pi = 22/7) is?", "options": ["154", "144", "1540", "150"], "answer": "A", "explanation": "22/7 * 49 = 154."},
    ],
    "Mensuration": [
        {"q": "Volume of a cube with side 5 is?", "options": ["25", "75", "125", "150"], "answer": "C", "explanation": "5^3 = 125."},
    ],
    "Trigonometry": [
        {"q": "sin 30 degrees equals?", "options": ["0", "1", "1/2", "sqrt(3)/2"], "answer": "C", "explanation": "sin 30 = 0.5."},
    ],
    "Permutation and Combination": [
        {"q": "Number of ways to arrange 4 distinct items is?", "options": ["12", "16", "24", "64"], "answer": "C", "explanation": "4! = 24."},
    ],
    "Quadratic Equations": [
        {"q": "Roots of x^2 - 5x + 6 = 0 are?", "options": ["1 and 6", "2 and 3", "3 and 4", "2 and 4"], "answer": "B", "explanation": "x^2 - 5x + 6 = (x-2)(x-3)."},
    ],
    "Analogy": [
        {"q": "Doctor : Hospital :: Teacher : ?", "options": ["Student", "School", "Book", "Subject"], "answer": "B", "explanation": "A doctor works in a hospital; a teacher works in a school."},
    ],
    "Coding-Decoding": [
        {"q": "If CAT is coded as DBU, how is DOG coded (same rule: each letter +1)?", "options": ["EPH", "DPE", "EPF", "FPH"], "answer": "A", "explanation": "D->E, O->P, G->H."},
    ],
    "Syllogism": [
        {"q": "All cats are animals. All animals are living. Therefore all cats are living. This is:", "options": ["Definitely true", "Definitely false", "Cannot be determined"], "answer": "A", "explanation": "Valid deduction."},
    ],
    "Puzzle": [
        {"q": "Five people A-E sit in a row. C is at the extreme end. A sits next to B. D sits at the other extreme. Who can be at the second position from right?", "options": ["Only E", "Only B", "B or E", "A or D"], "answer": "C", "explanation": "D at one end, C at the other; remaining A, B, E fill the middle three with A next to B."},
    ],
    "Inequality": [
        {"q": "If P > Q >= R and S > R, which conclusion is definitely true?", "options": ["P > S", "P > R", "S > P", "P = S"], "answer": "B", "explanation": "P > Q >= R implies P > R."},
    ],
    "Direction and Sense": [
        {"q": "A person walks 3 km north, then 4 km east. How far is he from the start?", "options": ["5 km", "6 km", "7 km", "12 km"], "answer": "A", "explanation": "Straight-line distance = sqrt(3^2 + 4^2) = 5 km."},
    ],
    "Blood Relations": [
        {"q": "Pointing to a photo, a man says, 'He is the only son of my mother's only son.' How is the man related to the boy?", "options": ["Father", "Brother", "Uncle", "Grandfather"], "answer": "A", "explanation": "Mother's only son is the man himself, so the boy is his son."},
    ],
    "Seating Arrangement": [
        {"q": "In a row of 5, if A is exactly in the middle, how many positions are to the left of A?", "options": ["1", "2", "3", "4"], "answer": "B", "explanation": "Middle of 5 is position 3, so 2 positions on the left."},
    ],
    "Series": [
        {"q": "Next number in 2, 6, 12, 20, 30, ?", "options": ["36", "40", "42", "44"], "answer": "C", "explanation": "n(n+1): 6*7 = 42."},
    ],
    "Classification": [
        {"q": "Which one is different: 12, 18, 24, 30, 33?", "options": ["12", "18", "24", "33"], "answer": "D", "explanation": "33 is not divisible by 6."},
    ],
    "Order and Ranking": [
        {"q": "In a row of 45 students, Ravi is 12th from the left. What is his position from the right?", "options": ["33rd", "34th", "35th", "36th"], "answer": "B", "explanation": "45 - 12 + 1 = 34."},
    ],
    "Input-Output": [
        {"q": "If input is 246 and the rule is 'reverse the digits', output is?", "options": ["624", "642", "462", "264"], "answer": "B", "explanation": "Reverse of 246 is 642."},
    ],
    "Vocabulary": [
        {"q": "Synonym of 'MITIGATE':", "options": ["Aggravate", "Alleviate", "Accelerate", "Allocate"], "answer": "B", "explanation": "Mitigate means to make less severe."},
        {"q": "Antonym of 'FRUGAL':", "options": ["Thrifty", "Economical", "Extravagant", "Careful"], "answer": "C", "explanation": "Opposite of frugal."},
    ],
    "Grammar": [
        {"q": "Choose the correct form: 'Neither of the boys ___ present.'", "options": ["are", "is", "were", "be"], "answer": "B", "explanation": "'Neither' is singular."},
    ],
    "Sentence Correction": [
        {"q": "Identify: 'He has completed the work yesterday.'", "options": ["No error", "has completed -> completed", "work -> works", "yesterday -> today"], "answer": "B", "explanation": "Past tense marker 'yesterday' requires simple past."},
    ],
    "Fill in the Blanks": [
        {"q": "Fill: 'She has been working here ___ 2019.'", "options": ["for", "from", "since", "by"], "answer": "C", "explanation": "'Since' is used with a point in time."},
    ],
    "Reading Comprehension": [
        {"q": "Reading: 'Remote work reduces office costs.' The main idea is:", "options": ["Office work is costly", "Remote work lowers cost", "Work from home trends", "Companies save time"], "answer": "B", "explanation": "Directly stated in the passage."},
    ],
    "Idioms and Phrases": [
        {"q": "'To let the cat out of the bag' means:", "options": ["To escape", "To reveal a secret", "To start a fight", "To make a mistake"], "answer": "B", "explanation": "Revealing a secret."},
    ],
    "One Word Substitution": [
        {"q": "One word for 'one who hates mankind':", "options": ["Misanthrope", "Philanthropist", "Altruist", "Introvert"], "answer": "A", "explanation": "Misanthrope."},
    ],
    "Active and Passive Voice": [
        {"q": "Passive of 'They are building a house.' is:", "options": ["A house is built by them", "A house is being built by them", "They were building a house", "A house has been built"], "answer": "B", "explanation": "Present continuous passive."},
    ],
    "Spotting Errors": [
        {"q": "Spot the error: 'Each of the players have submitted their form.'", "options": ["Each", "players", "have", "their"], "answer": "C", "explanation": "'Each' is singular, so 'has' is correct."},
    ],
    "Sentence Rearrangement": [],
    "Current Affairs": [],
    "Indian Polity": [],
    "History": [],
    "Geography": [],
    "Economy": [],
    "Science and Technology": [],
    "Static GK": [],
    "Banking": [],
    "Financial Awareness": [],
    "Indian Economy": [],
    "Banking Basics": [],
    "General Awareness": [],
}

def seed_syllabus() -> dict:
    db = SessionLocal()
    added = 0
    try:
        for exam, data in SYLLABUS.items():
            for section, topics in data["sections"].items():
                for topic in topics:
                    row = db.query(StudyTopic).filter(StudyTopic.exam==exam, StudyTopic.topic==topic).first()
                    if not row:
                        db.add(StudyTopic(exam=exam, section=section, topic=topic))
                        added += 1
        db.commit()
    finally:
        db.close()
    return {"exams": exam_names(), "topics_added": added}

def get_or_create_plan(exam: str, plan_date: str | None = None) -> list[dict]:
    db = SessionLocal()
    try:
        d = plan_date or date.today().isoformat()
        rows = db.query(StudyPlan).filter(StudyPlan.exam==exam, StudyPlan.plan_date==d).all()
        if not rows:
            plan = build_daily_plan(exam, d, len(rows))
            for p in plan:
                db.add(StudyPlan(exam=exam, plan_date=d, topic=p["topic"], section=p["section"]))
            db.commit()
            rows = db.query(StudyPlan).filter(StudyPlan.exam==exam, StudyPlan.plan_date==d).all()
        return [{"topic": r.topic, "section": r.section, "status": r.status} for r in rows]
    finally:
        db.close()

def build_daily_plan(exam: str, plan_date: str, existing_count: int = 0) -> list[dict]:
    sections = sections_for(exam)
    if not sections:
        return []
    db = SessionLocal()
    try:
        topics = db.query(StudyTopic).filter(StudyTopic.exam==exam).order_by(StudyTopic.mastery.asc(), StudyTopic.id.asc()).all()
    finally:
        db.close()
    if not topics:
        topics = [type("T", (), {"topic": t, "section": s, "mastery": 0})()
                  for s, ts in sections.items() for t in ts]
    start = existing_count % max(len(topics), 1)
    picked = [topics[(start + i) % len(topics)] for i in range(min(3, len(topics)))]
    return [{"topic": t.topic, "section": t.section} for t in picked]

def get_question(topic: str) -> dict | None:
    bank = QUESTION_BANK.get(topic)
    if not bank:
        return None
    import random
    return random.choice(bank)

def record_answer(exam: str, topic: str, question: dict, user_answer: str) -> dict:
    is_correct = (user_answer or "").strip().upper() == question["answer"].upper()
    db = SessionLocal()
    try:
        db.add(QuizResult(exam=exam, topic=topic, question=question["q"],
                          options=json.dumps(question["options"]), correct_option=question["answer"],
                          user_answer=user_answer, is_correct=is_correct, explanation=question["explanation"]))
        t = db.query(StudyTopic).filter(StudyTopic.exam==exam, StudyTopic.topic==topic).first()
        if t:
            t.attempts += 1
            t.correct += 1 if is_correct else 0
            t.mastery = int(round(100 * t.correct / t.attempts)) if t.attempts else 0
            t.last_reviewed = date.today().isoformat()
        db.commit()
    finally:
        db.close()
    return {"correct": is_correct, "correct_option": question["answer"],
            "explanation": question["explanation"],
            "message": "Correct." if is_correct else "Incorrect. Review the explanation."}

def progress(exam: str | None = None) -> dict:
    db = SessionLocal()
    try:
        q = db.query(StudyTopic)
        if exam:
            q = q.filter(StudyTopic.exam == exam)
        topics = q.all()
        weak = sorted([t for t in topics if t.attempts > 0 and t.mastery < 60],
                      key=lambda t: t.mastery)
        total_attempts = sum(t.attempts for t in topics)
        total_correct = sum(t.correct for t in topics)
        return {
            "exam": exam or "all",
            "topics_tracked": len(topics),
            "topics_practised": len([t for t in topics if t.attempts > 0]),
            "total_attempts": total_attempts,
            "accuracy": round(100 * total_correct / total_attempts, 1) if total_attempts else 0,
            "weak_topics": [{"exam": t.exam, "topic": t.topic, "mastery": t.mastery,
                             "attempts": t.attempts} for t in weak[:10]],
            "strong_topics": [{"exam": t.exam, "topic": t.topic, "mastery": t.mastery}
                              for t in sorted([x for x in topics if x.attempts > 0], key=lambda x: -x.mastery)[:5]],
        }
    finally:
        db.close()
