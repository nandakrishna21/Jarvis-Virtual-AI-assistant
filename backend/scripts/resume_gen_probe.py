"""Try the resume generator with a sample job description."""
import os
import sys

sys.path.insert(0, r"C:\JARVIS\backend")

from app.database.session import SessionLocal
from app.database.models import ResumeProfile, ResumeSection
from app.services import resume_generator

JD = """
Python Backend Developer
Company: Acme Technologies
Location: Hyderabad, India (Hybrid)

About the role
We are hiring a Python Backend Developer to build and scale our APIs.

Requirements
- Strong Python and FastAPI experience
- Experience with Django or Flask
- Solid SQL and PostgreSQL knowledge
- REST API design and Docker
- Git, Linux and CI/CD
- 1-3 years of experience
- Machine learning exposure is a plus

Responsibilities
- Design, build and maintain backend services with Python and FastAPI
- Write unit tests with pytest and review code in pull requests
- Work with Docker, Git and CI/CD to ship services
- Collaborate with the frontend team on REST API contracts
"""


def main() -> int:
    db = SessionLocal()
    try:
        profile = db.query(ResumeProfile).order_by(ResumeProfile.id.desc()).first()
        if not profile:
            print("no resume profile in the database")
            return 1
        db.query(ResumeSection).filter(ResumeSection.resume_id == profile.id).delete()
        db.add(ResumeSection(resume_id=profile.id, section_type="summary", title="Summary",
                             description="Python backend developer focused on FastAPI and Django APIs.",
                             position=0))
        db.add(ResumeSection(resume_id=profile.id, section_type="experience", title="Backend Developer",
                             organization="Previous Employer", start_date="2024", end_date="",
                             description=("- Built REST APIs with FastAPI and PostgreSQL\n"
                                          "- Wrote pytest unit tests for API endpoints\n"
                                          "- Containerised services with Docker on Linux\n"
                                          "- Worked with Git and CI/CD pipelines\n"
                                          "- Designed SQL schemas and optimised queries"),
                             position=1))
        db.add(ResumeSection(resume_id=profile.id, section_type="education", title="B.Tech",
                             organization="University", start_date="2020", end_date="2024",
                             description="Computer Science", position=2))
        db.commit()

        import asyncio
        built = asyncio.run(resume_generator.build_resume_from_jd(db, profile.id, JD, polish_summary=False))
        print("---- ANALYSIS ----")
        for key, value in built["analysis"].items():
            print(f"{key}: {value}")
        print("---- RESUME ----")
        print(built["content"])
        print("---- HIGHLIGHTS ----")
        for h in built["highlights"]:
            print("-", h)
    finally:
        db.close()
    return 0


if __name__ == "__main__":
    sys.exit(main())
