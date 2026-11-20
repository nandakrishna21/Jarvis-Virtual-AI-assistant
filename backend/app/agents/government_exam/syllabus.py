"""Seed syllabus for supported exams. Topic lists are a study aid, not an official notification.
Verify exam dates/notifications from the official exam authority site."""

SYLLABUS = {
    "SSC CGL": {
        "sections": {
            "Quantitative Aptitude": ["Number System", "Percentage", "Profit and Loss", "Ratio and Proportion",
                                       "Average", "Interest", "Time and Work", "Speed and Distance",
                                       "Geometry", "Mensuration", "Trigonometry", "Algebra", "Data Interpretation"],
            "Reasoning Ability": ["Analogy", "Classification", "Series", "Coding-Decoding", "Blood Relations",
                                  "Direction and Sense", "Syllogism", "Seating Arrangement", "Puzzle", "Inequality"],
            "English Language": ["Grammar", "Vocabulary", "Sentence Correction", "Fill in the Blanks",
                                  "Reading Comprehension", "Idioms and Phrases", "One Word Substitution",
                                  "Active and Passive Voice", "Spotting Errors"],
            "General Awareness": ["Indian Polity", "History", "Geography", "Economy", "Science and Technology",
                                  "Static GK", "Current Affairs"],
        },
        "question_count": 50,
    },
    "SSC CHSL": {
        "sections": {
            "Numerical Ability": ["Number System", "Percentage", "Ratio and Proportion", "Interest", "Time and Work",
                                  "Speed and Distance", "Algebra", "Geometry", "Mensuration", "Trigonometry"],
            "Reasoning Ability": ["Analogy", "Series", "Coding-Decoding", "Blood Relations", "Direction and Sense",
                                  "Syllogism", "Seating Arrangement", "Puzzle"],
            "English Language": ["Grammar", "Vocabulary", "Sentence Correction", "Reading Comprehension",
                                  "Idioms and Phrases", "Active and Passive Voice"],
            "General Awareness": ["Indian Polity", "History", "Geography", "Economy", "Static GK", "Current Affairs"],
        },
        "question_count": 50,
    },
    "RBI Assistant": {
        "sections": {
            "Reasoning Ability": ["Puzzle", "Syllogism", "Inequality", "Seating Arrangement", "Coding-Decoding",
                                  "Direction and Sense", "Blood Relations", "Order and Ranking", "Series"],
            "Quantitative Aptitude": ["Number System", "Simplification", "Data Interpretation", "Percentage",
                                       "Ratio", "Average", "Interest", "Time and Work", "Speed and Distance",
                                       "Mensuration", "Geometry"],
            "English Language": ["Grammar", "Vocabulary", "Sentence Rearrangement", "Reading Comprehension",
                                  "Fill in the Blanks", "Sentence Correction", "Idioms and Phrases"],
            "General Awareness": ["Economy", "Banking", "Financial Awareness", "Static GK", "Current Affairs"],
        },
        "question_count": 50,
    },
    "IBPS PO": {
        "sections": {
            "English Language": ["Reading Comprehension", "Vocabulary", "Grammar", "Sentence Correction",
                                  "Fill in the Blanks", "Idioms and Phrases", "Sentence Rearrangement"],
            "Quantitative Aptitude": ["Number System", "Simplification", "Data Interpretation", "Percentage",
                                       "Ratio", "Average", "Interest", "Time and Work", "Speed and Distance",
                                       "Quadratic Equations", "Mensuration", "Geometry", "Permutation and Combination"],
            "Reasoning Ability": ["Puzzle", "Syllogism", "Inequality", "Seating Arrangement", "Coding-Decoding",
                                  "Direction and Sense", "Blood Relations", "Order and Ranking", "Input-Output"],
            "General/Economy/Banking Awareness": ["Indian Economy", "Banking Basics", "Financial Awareness", "Static GK"],
        },
        "question_count": 100,
    },
}

def exam_names() -> list[str]:
    return sorted(SYLLABUS.keys())

def topics_for(exam: str) -> list[str]:
    data = SYLLABUS.get(exam)
    if not data:
        return []
    return [t for section in data["sections"].values() for t in section]

def sections_for(exam: str) -> dict:
    return SYLLABUS.get(exam, {}).get("sections", {})
