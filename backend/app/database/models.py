from sqlalchemy import Column, Integer, String, Text, Float, DateTime, ForeignKey, Boolean
from sqlalchemy.orm import declarative_base, relationship
from datetime import datetime

Base = declarative_base()

class ResumeProfile(Base):
    __tablename__ = "resume_profiles"
    id = Column(Integer, primary_key=True)
    file_path = Column(String)
    raw_text = Column(Text)
    extracted_skills = Column(Text)
    is_active = Column(Boolean, default=False)
    created_at = Column(DateTime, default=datetime.utcnow)

class Job(Base):
    __tablename__ = "jobs"
    id = Column(Integer, primary_key=True)
    title = Column(String, nullable=False)
    company = Column(String)
    location = Column(String)
    job_type = Column(String)  # remote/hybrid/on-site
    url = Column(String, unique=True, nullable=False)
    description = Column(Text)
    required_skills = Column(Text)
    salary = Column(String)
    experience = Column(String)
    posting_date = Column(String)
    source = Column(String)
    verified = Column(String, default="unverified")
    seniority = Column(String)  # entry/mid/senior/executive
    tags = Column(Text)
    employment_type = Column(String)
    feedback = Column(String)  # good/bad - user feedback used to retune ranking
    created_at = Column(DateTime, default=datetime.utcnow)

class JobMatch(Base):
    __tablename__ = "job_matches"
    id = Column(Integer, primary_key=True)
    job_id = Column(Integer, ForeignKey("jobs.id"), nullable=False)
    resume_id = Column(Integer, ForeignKey("resume_profiles.id"))
    score = Column(Float)
    matching_skills = Column(Text)
    missing_skills = Column(Text)
    components = Column(Text)
    notes = Column(Text)
    created_at = Column(DateTime, default=datetime.utcnow)

class Application(Base):
    __tablename__ = "applications"
    id = Column(Integer, primary_key=True)
    job_id = Column(Integer, ForeignKey("jobs.id"), nullable=False)
    status = Column(String, default="Discovered")
    resume_version = Column(String)
    cover_letter = Column(Text)
    answers = Column(Text)
    notes = Column(Text)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow)

class ApplicationHistory(Base):
    __tablename__ = "application_history"
    id = Column(Integer, primary_key=True)
    application_id = Column(Integer, ForeignKey("applications.id"), nullable=False)
    from_status = Column(String)
    to_status = Column(String)
    note = Column(Text)
    created_at = Column(DateTime, default=datetime.utcnow)

class Approval(Base):
    __tablename__ = "approvals"
    id = Column(Integer, primary_key=True)
    application_id = Column(Integer, ForeignKey("applications.id"), nullable=False)
    action = Column(String)
    content_snapshot = Column(Text)
    status = Column(String, default="pending")  # pending/approved/rejected
    created_at = Column(DateTime, default=datetime.utcnow)
    decided_at = Column(DateTime)

class Email(Base):
    __tablename__ = "emails"
    id = Column(Integer, primary_key=True)
    gmail_id = Column(String, unique=True, nullable=False)
    sender = Column(String)
    subject = Column(String)
    snippet = Column(Text)
    body = Column(Text)
    received_at = Column(String)
    category = Column(String)  # recruiter/interview/assessment/job_alert/spam/other
    company = Column(String)
    job_role = Column(String)
    important_details = Column(Text)
    created_at = Column(DateTime, default=datetime.utcnow)

class EmailDraft(Base):
    __tablename__ = "email_drafts"
    id = Column(Integer, primary_key=True)
    email_id = Column(Integer, ForeignKey("emails.id"))
    recipient = Column(String)
    cc = Column(String)
    bcc = Column(String)
    subject = Column(String)
    body = Column(Text)
    attachments = Column(Text)
    status = Column(String, default="draft")  # draft/approved/sent/rejected
    created_at = Column(DateTime, default=datetime.utcnow)

class EmailApproval(Base):
    __tablename__ = "email_approvals"
    id = Column(Integer, primary_key=True)
    draft_id = Column(Integer, ForeignKey("email_drafts.id"), nullable=False)
    action = Column(String, default="send_email")
    content_snapshot = Column(Text)
    status = Column(String, default="pending")
    created_at = Column(DateTime, default=datetime.utcnow)
    decided_at = Column(DateTime)

class HiringNews(Base):
    __tablename__ = "hiring_news"
    id = Column(Integer, primary_key=True)
    title = Column(String, nullable=False)
    company = Column(String)
    role = Column(String)
    location = Column(String)
    experience = Column(String)
    salary = Column(String)
    posting_date = Column(String)
    source = Column(String)
    official_source = Column(String)
    application_url = Column(String, unique=True)
    relevance = Column(Integer, default=0)
    is_current = Column(Boolean, default=False)
    dedupe_key = Column(String, unique=True, index=True)
    created_at = Column(DateTime, default=datetime.utcnow)

class StudyPlan(Base):
    __tablename__ = "study_plans"
    id = Column(Integer, primary_key=True)
    exam = Column(String, nullable=False)
    plan_date = Column(String, nullable=False)
    topic = Column(String)
    section = Column(String)
    status = Column(String, default="planned")
    created_at = Column(DateTime, default=datetime.utcnow)

class StudyTopic(Base):
    __tablename__ = "study_topics"
    id = Column(Integer, primary_key=True)
    exam = Column(String, nullable=False)
    section = Column(String)
    topic = Column(String, nullable=False)
    mastery = Column(Integer, default=0)
    attempts = Column(Integer, default=0)
    correct = Column(Integer, default=0)
    last_reviewed = Column(String)

class QuizResult(Base):
    __tablename__ = "quiz_results"
    id = Column(Integer, primary_key=True)
    exam = Column(String)
    topic = Column(String)
    question = Column(Text)
    options = Column(Text)
    correct_option = Column(String)
    user_answer = Column(String)
    is_correct = Column(Boolean, default=False)
    explanation = Column(Text)
    created_at = Column(DateTime, default=datetime.utcnow)

class Task(Base):
    __tablename__ = "tasks"
    id = Column(Integer, primary_key=True)
    title = Column(String, nullable=False)
    notes = Column(Text)
    category = Column(String, default="general")  # general/study/job/follow-up
    due_date = Column(String)
    due_time = Column(String)
    priority = Column(Integer, default=2)
    status = Column(String, default="pending")  # pending/completed
    completed_at = Column(String)
    created_at = Column(DateTime, default=datetime.utcnow)

class Reminder(Base):
    __tablename__ = "reminders"
    id = Column(Integer, primary_key=True)
    task_id = Column(Integer, ForeignKey("tasks.id"), nullable=False)
    remind_at = Column(String, nullable=False)
    message = Column(String)
    status = Column(String, default="scheduled")  # scheduled/fired/cancelled
    created_at = Column(DateTime, default=datetime.utcnow)

class Schedule(Base):
    __tablename__ = "schedules"
    id = Column(Integer, primary_key=True)
    name = Column(String, nullable=False)
    job_type = Column(String, nullable=False)  # morning_report/job_discovery/gmail_review/study_reminder
    time_of_day = Column(String)
    enabled = Column(Boolean, default=False)
    interval_minutes = Column(Integer)
    last_run = Column(String)
    created_at = Column(DateTime, default=datetime.utcnow)

class AgentRun(Base):
    __tablename__ = "agent_runs"
    id = Column(Integer, primary_key=True)
    agent = Column(String, nullable=False)
    action = Column(String)
    status = Column(String, default="success")
    detail = Column(Text)
    duration_ms = Column(Integer)
    created_at = Column(DateTime, default=datetime.utcnow)

class ActionProposal(Base):
    """A plan JARVIS wants to execute. Nothing runs until the user approves it."""
    __tablename__ = "action_proposals"
    id = Column(Integer, primary_key=True)
    action_type = Column(String, nullable=False)
    title = Column(String, nullable=False)
    reason = Column(Text)
    plan = Column(Text)  # JSON list of human readable steps
    payload = Column(Text)  # JSON parameters for the handler
    status = Column(String, default="pending")  # pending/approved/rejected/executed/failed
    source = Column(String, default="chat")  # chat/quick_command/page/automation
    result = Column(Text)  # JSON execution result
    error = Column(Text)
    payload_hash = Column(String)
    created_at = Column(DateTime, default=datetime.utcnow)
    decided_at = Column(DateTime)
    executed_at = Column(DateTime)

class Interview(Base):
    __tablename__ = "interviews"
    id = Column(Integer, primary_key=True)
    application_id = Column(Integer, ForeignKey("applications.id"))
    company = Column(String)
    role = Column(String)
    interview_date = Column(String)
    interview_time = Column(String)
    mode = Column(String, default="online")  # online/onsite/phone
    interviewer = Column(String)
    notes = Column(Text)
    status = Column(String, default="scheduled")  # scheduled/completed/cancelled/no_response
    reminder_sent = Column(Boolean, default=False)
    created_at = Column(DateTime, default=datetime.utcnow)

class UserPreference(Base):
    __tablename__ = "user_preferences"
    id = Column(Integer, primary_key=True)
    name = Column(String)
    location = Column(String)
    markets = Column(Text)  # JSON list
    target_categories = Column(Text)  # JSON list
    salary = Column(String)
    employment_types = Column(Text)  # JSON list
    work_modes = Column(Text)  # JSON list
    experience_levels = Column(Text)  # JSON list
    search_interval_minutes = Column(Integer, default=240)
    resume_path = Column(String)
    updated_at = Column(DateTime, default=datetime.utcnow)

class Notification(Base):
    __tablename__ = "notifications"
    id = Column(Integer, primary_key=True)
    kind = Column(String, default="info")  # info/success/warning/error
    title = Column(String, nullable=False)
    body = Column(Text)
    link = Column(String)
    is_read = Column(Boolean, default=False)
    created_at = Column(DateTime, default=datetime.utcnow)

class WorkflowRun(Base):
    __tablename__ = "workflow_runs"
    id = Column(Integer, primary_key=True)
    workflow = Column(String, nullable=False)
    engine = Column(String, default="n8n")
    status = Column(String, default="success")
    detail = Column(Text)
    duration_ms = Column(Integer)
    created_at = Column(DateTime, default=datetime.utcnow)

class ResumeSection(Base):
    """A structured block of a resume: summary, job, education, project."""
    __tablename__ = "resume_sections"
    id = Column(Integer, primary_key=True)
    resume_id = Column(Integer, ForeignKey("resume_profiles.id"), nullable=False)
    section_type = Column(String, nullable=False)  # summary/experience/education/projects/skills/custom
    title = Column(String)
    organization = Column(String)
    location = Column(String)
    start_date = Column(String)
    end_date = Column(String)
    description = Column(Text)
    position = Column(Integer, default=0)
    created_at = Column(DateTime, default=datetime.utcnow)

class DocumentVersion(Base):
    """A stored, versioned document generated for a specific job."""
    __tablename__ = "document_versions"
    id = Column(Integer, primary_key=True)
    resume_id = Column(Integer, ForeignKey("resume_profiles.id"))
    job_id = Column(Integer, ForeignKey("jobs.id"))
    application_id = Column(Integer, ForeignKey("applications.id"))
    doc_type = Column(String, nullable=False)  # resume/cover_letter
    version = Column(Integer, default=1)
    content = Column(Text)
    file_path = Column(String)
    match_score = Column(Float)
    highlights = Column(Text)  # JSON list
    created_at = Column(DateTime, default=datetime.utcnow)

class AppSetting(Base):
    """Non-secret runtime settings that can be changed from the UI."""
    __tablename__ = "app_settings"
    id = Column(Integer, primary_key=True)
    key = Column(String, nullable=False, unique=True)
    value = Column(Text)
    updated_at = Column(DateTime, default=datetime.utcnow)
