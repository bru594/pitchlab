"""
PitchLab - Website Audit Engine
Scrapes and scores a business website on: speed, mobile, SEO, design quality.
Produces a structured audit + plain-English sales summary.
"""

import asyncio
import re
import time
from typing import Dict, Any, List, Optional
from urllib.parse import urlparse
import httpx
from bs4 import BeautifulSoup

from app.core.config import settings


# ─── Issue severity constants ─────────────────────────────────────────────────

CRITICAL = "critical"
WARNING  = "warning"
INFO     = "info"


# ─── Scoring helpers ──────────────────────────────────────────────────────────

def _score_from_issues(issues: List[Dict], max_score: int = 100) -> int:
    """Deduct points based on issue severity."""
    deductions = {CRITICAL: 25, WARNING: 10, INFO: 3}
    total_deduction = sum(deductions.get(i["severity"], 0) for i in issues)
    return max(0, max_score - total_deduction)


# ─── Individual audit checks ──────────────────────────────────────────────────

async def _audit_speed(url: str, response_time_ms: float, html: str) -> Dict:
    """Score page speed based on response time and HTML size."""
    issues = []
    html_size_kb = len(html.encode()) / 1024

    if response_time_ms > 3000:
        issues.append({"severity": CRITICAL, "message": f"Page loaded in {response_time_ms:.0f}ms — very slow (ideal is under 1000ms)"})
    elif response_time_ms > 1500:
        issues.append({"severity": WARNING, "message": f"Page loaded in {response_time_ms:.0f}ms — could be faster"})

    if html_size_kb > 500:
        issues.append({"severity": WARNING, "message": f"Page HTML is {html_size_kb:.0f}KB — consider minification"})

    # Check for render-blocking scripts
    soup = BeautifulSoup(html, "html.parser")
    blocking_scripts = soup.find_all("script", src=True)
    blocking_scripts = [s for s in blocking_scripts if not s.get("async") and not s.get("defer")]
    if len(blocking_scripts) > 3:
        issues.append({"severity": WARNING, "message": f"{len(blocking_scripts)} render-blocking scripts found (no async/defer)"})

    return {"score": _score_from_issues(issues), "issues": issues, "response_time_ms": response_time_ms}


def _audit_mobile(html: str) -> Dict:
    """Check for mobile-friendliness signals."""
    issues = []
    soup = BeautifulSoup(html, "html.parser")

    # Viewport meta tag
    viewport = soup.find("meta", attrs={"name": re.compile("viewport", re.I)})
    if not viewport:
        issues.append({"severity": CRITICAL, "message": "No viewport meta tag — page is NOT mobile-friendly"})
    else:
        content = viewport.get("content", "")
        if "width=device-width" not in content:
            issues.append({"severity": WARNING, "message": "Viewport tag missing 'width=device-width'"})

    # Font size: look for tiny fixed-px fonts in inline styles
    tiny_fonts = re.findall(r'font-size\s*:\s*([0-9]+)px', html)
    small_count = sum(1 for f in tiny_fonts if int(f) < 12)
    if small_count > 0:
        issues.append({"severity": WARNING, "message": f"{small_count} instances of very small text (under 12px) found"})

    # Fixed-width layouts
    fixed_widths = re.findall(r'width\s*:\s*([0-9]+)px', html)
    wide = [w for w in fixed_widths if int(w) > 900]
    if len(wide) > 2:
        issues.append({"severity": WARNING, "message": "Fixed-width containers detected — may not scale on mobile"})

    return {"score": _score_from_issues(issues), "issues": issues}


def _audit_seo(url: str, html: str) -> Dict:
    """Check basic on-page SEO signals."""
    issues = []
    soup = BeautifulSoup(html, "html.parser")

    # Title tag
    title = soup.find("title")
    if not title or not title.get_text(strip=True):
        issues.append({"severity": CRITICAL, "message": "No <title> tag found — search engines can't rank this page"})
    elif len(title.get_text(strip=True)) > 70:
        issues.append({"severity": WARNING, "message": f"Title tag is {len(title.get_text())} chars — ideal is under 60"})
    elif len(title.get_text(strip=True)) < 20:
        issues.append({"severity": WARNING, "message": "Title tag is too short — add more descriptive keywords"})

    # Meta description
    meta_desc = soup.find("meta", attrs={"name": re.compile("description", re.I)})
    if not meta_desc or not meta_desc.get("content", "").strip():
        issues.append({"severity": CRITICAL, "message": "No meta description — this appears blank in Google results"})
    elif len(meta_desc.get("content", "")) > 160:
        issues.append({"severity": WARNING, "message": "Meta description too long — gets cut off in search results"})

    # H1 tag
    h1_tags = soup.find_all("h1")
    if not h1_tags:
        issues.append({"severity": CRITICAL, "message": "No H1 heading found — Google uses this to understand page topic"})
    elif len(h1_tags) > 1:
        issues.append({"severity": WARNING, "message": f"{len(h1_tags)} H1 tags found — page should have exactly one"})

    # Images without alt text
    images = soup.find_all("img")
    no_alt = [i for i in images if not i.get("alt")]
    if no_alt:
        issues.append({"severity": WARNING, "message": f"{len(no_alt)} images missing alt text — hurts accessibility and SEO"})

    # Canonical tag
    canonical = soup.find("link", rel="canonical")
    if not canonical:
        issues.append({"severity": INFO, "message": "No canonical tag — may cause duplicate content issues"})

    return {"score": _score_from_issues(issues), "issues": issues,
            "title": title.get_text(strip=True) if title else None,
            "meta_description": meta_desc.get("content", "") if meta_desc else None}


def _audit_design(url: str, html: str) -> Dict:
    """
    Heuristic design quality check.
    Detects cheap builders, outdated patterns, and missing modern elements.
    """
    issues = []
    html_lower = html.lower()

    # Cheap site builder detection
    cheap_builders = {
        "wix.com":           "Built on Wix",
        "weebly.com":        "Built on Weebly",
        "squarespace.com":   "Built on Squarespace",
        "godaddy.com":       "Built on GoDaddy Website Builder",
        "yolasite.com":      "Built on Yola",
        "jimdo.com":         "Built on Jimdo",
        "homestead.com":     "Built on Homestead",
        "site123.com":       "Built on Site123",
    }
    for domain, label in cheap_builders.items():
        if domain in html_lower:
            issues.append({"severity": WARNING, "message": f"{label} — template-based sites rarely rank well or convert visitors"})
            break

    # Check for SSL (via URL)
    if not url.startswith("https://"):
        issues.append({"severity": CRITICAL, "message": "Site is not using HTTPS — Chrome shows 'Not Secure' warning to visitors"})

    # No favicon
    soup = BeautifulSoup(html, "html.parser")
    favicon = soup.find("link", rel=re.compile("icon", re.I))
    if not favicon:
        issues.append({"severity": INFO, "message": "No favicon found — small trust signal missing"})

    # No contact info visible
    has_phone = bool(re.search(r'\(?\d{3}\)?[-.\s]\d{3}[-.\s]\d{4}', html))
    if not has_phone:
        issues.append({"severity": WARNING, "message": "No phone number detected on homepage — customers can't easily call"})

    # Tables used for layout (very outdated)
    layout_tables = soup.find_all("table")
    if len(layout_tables) > 2:
        issues.append({"severity": WARNING, "message": "HTML tables used for layout — outdated approach affecting mobile experience"})

    # Flash / old tech
    if "swfobject" in html_lower or ".swf" in html_lower:
        issues.append({"severity": CRITICAL, "message": "Flash content detected — no longer supported in any modern browser"})

    # Copyright year check
    copyright_match = re.search(r'(?:copyright|©)\s*(\d{4})', html_lower)
    if copyright_match:
        year = int(copyright_match.group(1))
        if year < 2020:
            issues.append({"severity": INFO, "message": f"Copyright year shows {year} — site appears outdated"})

    return {"score": _score_from_issues(issues), "issues": issues,
            "uses_https": url.startswith("https://")}


def _generate_sales_summary(audit_data: Dict, business_name: str) -> str:
    """
    Generate a plain-English sales summary from audit findings.
    This is designed to be used directly in a pitch conversation.
    """
    score = audit_data["overall_score"]
    all_issues = audit_data["all_issues"]
    critical = [i for i in all_issues if i["severity"] == CRITICAL]
    warnings = [i for i in all_issues if i["severity"] == WARNING]

    grade = "D" if score < 40 else "C" if score < 60 else "B" if score < 80 else "A"

    summary_parts = [
        f"I ran a quick audit on {business_name}'s website and it scored {score}/100 (Grade {grade}).",
        "",
    ]

    if not audit_data.get("reachable"):
        summary_parts.append("⚠️ The site isn't loading properly — customers trying to visit it may see errors.")
        summary_parts.append("")

    if critical:
        summary_parts.append("🔴 Critical Issues Found:")
        for issue in critical[:3]:  # top 3 critical
            summary_parts.append(f"  • {issue['message']}")
        summary_parts.append("")

    if warnings:
        summary_parts.append("🟡 Problems That Are Hurting Them:")
        for issue in warnings[:3]:
            summary_parts.append(f"  • {issue['message']}")
        summary_parts.append("")

    summary_parts.append(
        "The bottom line: their current site is likely costing them customers every week. "
        "A modern, fast, mobile-friendly site built for local SEO could make a real difference."
    )

    return "\n".join(summary_parts)


# ─── Main audit function ──────────────────────────────────────────────────────

async def audit_website(url: str, business_name: str = "") -> Dict[str, Any]:
    """
    Full website audit pipeline.
    Returns structured scores, issues, and a sales summary.
    """
    # Normalize URL
    if not url.startswith(("http://", "https://")):
        url = "https://" + url

    result = {
        "url": url,
        "reachable": False,
        "overall_score": 0,
        "speed_score": 0,
        "mobile_score": 0,
        "seo_score": 0,
        "design_score": 0,
        "all_issues": [],
        "issues_by_category": {},
        "sales_summary": "",
        "raw_data": {},
    }

    # Fetch the page
    html = ""
    response_time_ms = 9999.0

    try:
        start = time.monotonic()
        async with httpx.AsyncClient(timeout=10.0, follow_redirects=True) as client:
            headers = {"User-Agent": "Mozilla/5.0 (compatible; PitchLabBot/1.0)"}
            resp = await client.get(url, headers=headers)
            response_time_ms = (time.monotonic() - start) * 1000
            html = resp.text
            result["reachable"] = resp.status_code < 400
    except Exception as e:
        result["sales_summary"] = f"Could not reach {url} — {str(e)}"
        return result

    # Run all audit modules
    speed_result  = await _audit_speed(url, response_time_ms, html)
    mobile_result = _audit_mobile(html)
    seo_result    = _audit_seo(url, html)
    design_result = _audit_design(url, html)

    # Aggregate
    result["speed_score"]  = speed_result["score"]
    result["mobile_score"] = mobile_result["score"]
    result["seo_score"]    = seo_result["score"]
    result["design_score"] = design_result["score"]
    result["overall_score"] = int(
        result["speed_score"] * 0.25 +
        result["mobile_score"] * 0.25 +
        result["seo_score"] * 0.30 +
        result["design_score"] * 0.20
    )

    # Flatten all issues
    all_issues = (
        speed_result["issues"] +
        mobile_result["issues"] +
        seo_result["issues"] +
        design_result["issues"]
    )
    result["all_issues"] = all_issues
    result["issues_by_category"] = {
        "speed":  speed_result["issues"],
        "mobile": mobile_result["issues"],
        "seo":    seo_result["issues"],
        "design": design_result["issues"],
    }

    result["raw_data"] = {
        "response_time_ms": response_time_ms,
        "html_size_kb": len(html.encode()) / 1024,
        "title":            seo_result.get("title"),
        "meta_description": seo_result.get("meta_description"),
        "uses_https":       design_result.get("uses_https"),
    }

    # Generate sales pitch summary
    result["sales_summary"] = _generate_sales_summary(result, business_name)

    return result


# ─── Mock audit for leads without websites ───────────────────────────────────

def mock_no_website_audit(business_name: str) -> Dict[str, Any]:
    """Generate audit data for a business with NO website."""
    return {
        "url": None,
        "reachable": False,
        "overall_score": 0,
        "speed_score": 0,
        "mobile_score": 0,
        "seo_score": 0,
        "design_score": 0,
        "all_issues": [
            {"severity": CRITICAL, "message": "No website found — business is invisible to online searches"},
            {"severity": CRITICAL, "message": "Missing from Google Maps website listing"},
            {"severity": CRITICAL, "message": "No way for customers to find info online before calling"},
        ],
        "issues_by_category": {"speed": [], "mobile": [], "seo": [], "design": []},
        "sales_summary": (
            f"{business_name} has no website at all.\n\n"
            "🔴 Critical: They're completely invisible online.\n"
            "  • Customers searching Google won't find them\n"
            "  • No way to showcase services, reviews, or contact info\n"
            "  • Competitors with websites are winning every search\n\n"
            "This is actually a huge opportunity — they need a website badly, "
            "and you can be the person who solves that problem for them."
        ),
        "raw_data": {},
    }
