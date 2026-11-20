STATUSES = ["Discovered","Shortlisted","Under review","Ready for approval","Approved","Submitted",
            "Assessment","Interview","Rejected","Offer","Withdrawn"]

def build_materials(job: dict, resume_skills: list[str], match: dict | None) -> dict:
    matching = (match or {}).get("matching_skills","")
    missing = (match or {}).get("missing_skills","")
    skills_line = f"Relevant skills: {', '.join(resume_skills) if resume_skills else 'none extracted'}"
    cover = (
        f"Application draft for {job.get('title','')} at {job.get('company') or 'the company'}.\n\n"
        f"{skills_line}\n"
        f"Matching skills: {matching or 'none'}. Gaps (do not fabricate): {missing or 'none'}.\n\n"
        "This draft is for your review only. Fill in your real experience, dates and achievements before submitting."
    )
    answers = {
        "why_fit": f"I match on: {matching or 'no extracted overlap'}. Current gaps: {missing or 'none'}.",
        "location": job.get("location") or "check job posting",
        "notice": "TODO: add your real notice period/availability.",
    }
    return {"cover_letter": cover, "answers": "; ".join(f"{k}: {v}" for k,v in answers.items()), "answers_dict": answers}
