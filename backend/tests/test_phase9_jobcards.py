from app.agents.job_discovery import connectors

CARD_HTML = """
<div class="mb-2 flex">
  <div class="w-12"><a href="/company/citizenapp"><img alt="Citizen company logo"/></a></div>
  <div class="ml-4 flex-1">
    <div class="mb-1"><a href="/jobs/5008702-senior-backend-engineer">Senior Backend Engineer</a></div>
    <div class="text-sm"><span>Citizen</span><span class="text-gray-700">Citizen &bull; New York &bull; $200k &ndash; $260k &bull; 1 day ago</span></div>
  </div>
</div>
<div><a href="/jobs/5016003-marketing-partnerships">Marketing & Partnerships Manager</a>
  <span class="text-gray-700">Acme Labs &bull; Remote only &bull; 2 days ago</span></div>
<a href="/jobs">Jobs</a>
<a href="/jobs/signup?after_sign_in=%2Fjobs">Create profile</a>
"""

def test_parse_cards_extracts_title_company_location_salary_date():
    jobs = connectors._parse_cards(CARD_HTML, "wellfound", 10)
    titles = [j["title"] for j in jobs]
    assert "Senior Backend Engineer" in titles
    assert "Marketing & Partnerships Manager" in titles
    assert "Jobs" not in titles and "Create profile" not in titles

def test_parse_cards_extracts_metadata():
    jobs = connectors._parse_cards(CARD_HTML, "wellfound", 10)
    first = next(j for j in jobs if j["title"] == "Senior Backend Engineer")
    assert first["company"] == "Citizenapp" or first["company"] == "Citizen"
    assert first["location"] == "New York"
    assert "$200k" in first["salary"]
    assert "1 day ago" in first["posting_date"]
    assert first["url"] == "https://wellfound.com/jobs/5008702-senior-backend-engineer"
    assert first["verified"] == "unverified"

def test_parse_cards_respects_limit():
    jobs = connectors._parse_cards(CARD_HTML, "wellfound", 1)
    assert len(jobs) == 1

def test_dedupe_removes_duplicate_urls():
    jobs = [{"url": "https://x/1"}, {"url": "https://X/1"}, {"url": "https://x/2"}]
    assert len(connectors.dedupe(jobs)) == 2

def test_slug_to_name():
    assert connectors._slug_to_name("citizenapp") == "Citizenapp"
    assert connectors._slug_to_name("well-found-labs") == "Well Found Labs"
