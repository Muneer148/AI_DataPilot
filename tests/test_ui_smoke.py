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
        'id="validate-prepare"',
        'id="approve-preparation"',
        "request('/api/preview'",
        "requestUpload('/api/preview-upload'",
        "requestUpload('/api/analyze-upload'",
        "request('/api/analyze'",
        "request('/api/diagnose-pricing'",
        "requestUpload('/api/diagnose-pricing-upload'",
        "fetch('/api/health')",
    ):
        assert marker in html


def test_dataset_values_are_rendered_as_text_not_html():
    html = index()
    assert "td.textContent=values[i]??''" in html
    assert "val.textContent=String(value)" in html



def test_home_page_requires_preview_and_approval_before_analysis():
    html = index()
    assert "if(!previewApproval||!lastPreparation||lastPreparation.ready!==true)" in html
    assert "prepare:true" in html
    assert "dataset changed. Run the server-side preview again." in html.lower()
