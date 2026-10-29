from app.main import index


def test_home_page_serves_the_analyst_workspace_and_real_api_routes():
    html = index()
    for marker in (
        "AI_DataPilot",
        'id="dataset"',
        'id="question"',
        'id="evidence"',
        'id="diagnostics"',
        "function parseCSV(text)",
        "function errorMessage(data,status)",
        "fetch('/api/health')",
        "request('/api/analyze'",
        "request('/api/diagnose-pricing'",
    ):
        assert marker in html


def test_dataset_values_are_rendered_as_text_not_html():
    html = index()
    assert "td.textContent=values[i]??''" in html
    assert "val.textContent=String(value)" in html
