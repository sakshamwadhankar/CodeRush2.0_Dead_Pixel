import base64
import json
import re
import time
import uuid
from pathlib import Path
from typing import Dict, Any, Tuple

from playwright.sync_api import sync_playwright, TimeoutError, Error as PlaywrightError

PROMPT_INJECTION_PATTERNS = [
    r"(?i)ignore\s+previous\s+instructions",
    r"(?i)system\s+override",
    r"(?i)you\s+are\s+now\s+an\s+administrator",
    r"(?i)assistant\s+rewrite",
]

class SecureBrowserController:
    """
    Step B3: Secure, containerized, headless web scraper using Playwright.
    """
    
    def __init__(self, audit_log_path: str | Path = "audit_log.json"):
        self.audit_log_path = Path(audit_log_path).resolve()

    def _write_audit_log(self, entry: Dict[str, Any]) -> None:
        """Logs browser events and security warnings to the central audit JSON."""
        logs = []
        try:
            if self.audit_log_path.exists():
                with open(self.audit_log_path, "r", encoding="utf-8") as f:
                    content = f.read().strip()
                    if content:
                        logs = json.loads(content)
        except Exception:
            logs = []

        logs.append(entry)
        try:
            with open(self.audit_log_path, "w", encoding="utf-8") as f:
                json.dump(logs, f, indent=2)
        except Exception:
            pass

    def sanitize_html_content(self, text: str) -> Tuple[str, bool]:
        """
        Executes a regex-based defensive scan for common prompt injection patterns.
        Returns the neutralized text and a boolean flag indicating if an injection was found.
        """
        injection_detected = False
        sanitized_text = text
        
        for pattern in PROMPT_INJECTION_PATTERNS:
            if re.search(pattern, sanitized_text):
                injection_detected = True
                # Neutralize the offending text
                sanitized_text = re.sub(pattern, "[REDACTED_SECURITY_VIOLATION]", sanitized_text)
                
        return sanitized_text, injection_detected

    def browse_page(self, url: str) -> Dict[str, Any]:
        """
        Extracts clean page content, streams viewport screenshots, and implements defensive text-sanitization barriers.
        """
        start_time = time.time()
        audit_id = str(uuid.uuid4())
        
        result = {
            "status": "pending",
            "url": url,
            "text_content": "",
            "links": [],
            "screenshot_base64": "",
            "metadata": {
                "title": "",
                "status_code": None,
                "latency_ms": 0,
                "injection_detected": False
            }
        }

        try:
            with sync_playwright() as p:
                # Launch Chromium headlessly
                browser = p.chromium.launch(headless=True)
                
                # Session Leakage Prevention: create a clean incognito context
                context = browser.new_context(
                    ignore_https_errors=False,
                    viewport={"width": 1280, "height": 720}
                )
                
                def route_interceptor(route):
                    # Abort heavy multimedia (video/audio) to preserve bandwidth
                    if route.request.resource_type in ["media", "font"]:
                        route.abort()
                    else:
                        route.continue_()
                
                page = context.new_page()
                page.route("**/*", route_interceptor)
                
                try:
                    # Navigate with strict 20s timeout
                    response = page.goto(url, timeout=20000, wait_until="domcontentloaded")
                    status_code = response.status if response else None
                    
                    if response and status_code >= 400:
                        raise Exception(f"Failed to load page. Status Code: {status_code}")
                    elif not response and not url.startswith("data:"):
                        raise Exception(f"Failed to load page. Status Code: None")
                        
                    # Advanced Content Filtering: DOM Ad and Comment Scrubber
                    raw_html = page.content()
                    from bs4 import BeautifulSoup
                    soup = BeautifulSoup(raw_html, "html.parser")
                    
                    # Target classes and IDs typically containing ads, comments, or prompt injections
                    bad_keywords = ["disqus", "comment-box", "sponsor", "sidebar-ads", "ad-container", "comment", "nav", "footer"]
                    for tag in soup.find_all(True):
                        if not hasattr(tag, "attrs") or not tag.attrs:
                            continue
                        cls_val = tag.attrs.get('class', [])
                        cls_str = " ".join(cls_val) if isinstance(cls_val, list) else str(cls_val)
                        id_str = str(tag.attrs.get('id', ''))
                        combined = (cls_str + " " + id_str).lower()
                        if any(kw in combined for kw in bad_keywords):
                            tag.decompose()
                            
                    raw_text = soup.get_text(separator="\n", strip=True)
                    
                    links = page.evaluate("Array.from(document.links).map(a => a.href)") or []
                    title = page.title()
                    
                    # Ensure minimum layout settling time for screenshot accuracy
                    page.wait_for_timeout(500)
                    screenshot_bytes = page.screenshot(type="jpeg", quality=60)
                    screenshot_b64 = base64.b64encode(screenshot_bytes).decode('utf-8')
                    
                    # Sanitize inputs
                    clean_text, injection_flag = self.sanitize_html_content(raw_text)
                    
                    result["status"] = "success"
                    result["text_content"] = clean_text
                    result["links"] = list(set(links))
                    result["screenshot_base64"] = screenshot_b64
                    
                    result["metadata"]["title"] = title
                    result["metadata"]["status_code"] = status_code
                    result["metadata"]["injection_detected"] = injection_flag
                    
                except TimeoutError:
                    result["status"] = "error"
                    result["metadata"]["error"] = "Page load timeout exceeded (20s)"
                except Exception as e:
                    result["status"] = "error"
                    result["metadata"]["error"] = str(e)
                finally:
                    # Purge cookies, cache, and context memory instantly
                    context.close()
                    browser.close()
                    
        except Exception as e:
            result["status"] = "system_error"
            result["metadata"]["error"] = f"Browser Engine Error: {str(e)}"
            
        finally:
            result["metadata"]["latency_ms"] = int((time.time() - start_time) * 1000)
            
            # Record security warning and session metadata
            self._write_audit_log({
                "event_type": "browser_scrape",
                "audit_id": audit_id,
                "url": url,
                "status": result["status"],
                "latency_ms": result["metadata"]["latency_ms"],
                "injection_detected": result["metadata"]["injection_detected"],
                "timestamp": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())
            })
            
        return result
