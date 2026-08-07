import os
from pathlib import Path
import pytest

LANDING_DIR = Path(__file__).parent.parent / "landing"

def test_landing_files_exist():
    assert (LANDING_DIR / "index.html").exists(), "index.html must exist"
    assert (LANDING_DIR / "chat.html").exists(), "chat.html must exist"
    assert (LANDING_DIR / "styles.css").exists(), "styles.css must exist"
    assert (LANDING_DIR / "app.js").exists(), "app.js must exist"
    assert (LANDING_DIR / "server.py").exists(), "server.py must exist"
    assert (LANDING_DIR / "agentation-bundle.js").exists(), "agentation-bundle.js must exist"

def test_html_structure_and_seo():
    html_content = (LANDING_DIR / "index.html").read_text(encoding="utf-8")
    
    # SEO Checks
    assert "<title>" in html_content, "Page must have title tag"
    assert 'name="description"' in html_content, "Page must have meta description"
    assert html_content.count("<h1") == 1, "Page must have exactly one <h1> tag"
    assert "START CHAT" in html_content, "Header CTA button must say START CHAT"
    assert "flip-word-container" in html_content, "Hero display heading must contain flip-word-container"
    
    # Required Unique IDs for Interactive Browser Testing
    required_ids = [
        "main-nav",
        "brand-logo",
        "nav-links",
        "header-cta-btn",
        "hero",
        "hero-heading",
        "hero-btn-primary",
        "hero-btn-ghost",
        "demo",
        "query-input",
        "run-demo-btn",
        "reset-demo-btn",
        "execution-timeline",
        "preset-1",
        "preset-2",
        "preset-3",
        "features",
        "architecture",
        "use-cases",
        "faq",
        "faq-1"
    ]
    for element_id in required_ids:
        assert f'id="{element_id}"' in html_content, f"Element id='{element_id}' must exist in index.html"

def test_css_design_system_tokens():
    css_content = (LANDING_DIR / "styles.css").read_text(encoding="utf-8")
    
    # Token checks from DESIGN (3).md
    tokens = [
        "--color-carbon-black: #000000;",
        "--color-warm-canvas: #e5e5e5;",
        "--color-mint-chip: #d1ffca;",
        "--color-voltage-yellow: #fff100;",
        "--font-display:",
        "--font-body:",
        "--font-mono:",
        "--radius-nav-pill: 48px;",
        "--radius-tag: 64px;",
        "box-shadow: none",
        "moveGrid"
    ]
    for token in tokens:
        assert token in css_content, f"CSS token '{token}' must be defined in styles.css"

def test_javascript_interactive_logic():
    js_content = (LANDING_DIR / "app.js").read_text(encoding="utf-8")
    assert "query-input" in js_content
    assert "run-demo-btn" in js_content
    assert "execution-timeline" in js_content
    assert "faq-item" in js_content
