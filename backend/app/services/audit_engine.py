"""
PitchLab - Website Audit Engine
Scrapes and scores a business website: speed, mobile, SEO, design.
Generates a UNIQUE AI-written sales summary via Groq every time.
"""

import asyncio
import re
import time
from typing import Dict, Any, List, Optional
import httpx
from bs4 import BeautifulSoup

from app.core.config import settings

CRITICAL = "critical"
WARNING  = "warning"
INFO     = "info"


# ─── AI summary generation ────────────────────────────────────────────────────

async def _generate_ai_summary(
    business_name: str,
    url: Optional[str],
    score: int,
    issues: List[Dict],
    raw_data: Dict,
) -> str:
    """
    Call Groq to write a unique, specific sales summary for this business.
    Falls back to template if no API key.
    """
    if not settings.GROQ_API_KEY:
        return _template_summary(business_name, url, score, issues)

    critical = [i["message"] for i in issues if i.get("severity") == CRITICAL]
    warnings = [i["message"] for i in issues if i.get("severity") == WARNING]
    grade = "F" if score < 35 else "D" if score < 50 else "C" if score < 65 else "B" if score < 80 else "A"

    issues_text = "\n".join(f"- {m}" for m in (critical + warnings)[:5])
    site_info = f"URL: {url}" if url else "No website found"
    response_time = raw_data.get("response_time_ms")
    rt_text = f"Page load time: {response_time:.0f}ms" if response_time else ""
    title = raw_data.get("title", "")
    title_text = f"Page title: {title}" if title else "No title tag found"

    prompt = f"""You are a web designer writing a sales audit summary for a potential client.

Business: {business_name}
{site_info}
Overall Score: {score}/100 (Grade {grade})
{rt_text}
{title_text}

Issues found:
{issues_text if issues_text else "No website — completely invisible online"}

Write a SHORT (5-8 sentence), conversational audit summary that:
1. Opens with one specific observation about THIS business (not generic)
2. Names 2-3 of their biggest problems in plain English
3. Explains what those problems cost them in real terms (lost customers, lower Google ranking)
4. Ends with one sentence about what a better site would do for them

Tone: friendly local expert, not corporate. Write as if talking to the owner directly.
Do NOT use bullet points. Write in flowing paragraphs. Be specific to this business."""

    try:
        async with httpx.AsyncClient(timeout=20.0) as client:
            resp = await client.post(
                "https://api.groq.com/openai/v1/chat/completions",
                headers={
                    "Authorization": f"Bearer {settings.GROQ_API_KEY}",
                    "Content-Type": "application/json",
                },
                json={
                    "model": settings.GROQ_MODEL,
                    "messages": [{"role": "user", "content": prompt}],
                    "max_tokens": 400,
                    "temperature": 0.8,
                },
            )
            resp.raise_for_status()
            return resp.json()["choices"][0]["message"]["content"].strip()
    except Exception as e:
        print(f"[Audit AI] Groq failed: {e}")
        return _template_summary(business_name, url, score, issues)


def _template_summary(
    business_name: str,
    url: Optional[str],
    score: int,
    issues: List[Dict],
) -> str:
    """Fallback template summary when no AI key is available."""
    if not url:
        return (
            f"{business_name} has no website — they're completely invisible to anyone searching online. "
            "Every day without a site is customers going to a competitor instead. "
            "A simple, fast website with their services, location, and contact info could change that immediately."
        )

    grade = "F" if score < 35 else "D" if score < 50 else "C" if score < 65 else "B" if score < 80 else "A"
    critical = [i["message"] for i in issues if i.get("severity") == CRITICAL]
    warnings = [i["message"] for i in issues if i.get("severity") == WARNING]
    top = (critical + warnings)[:3]

    lines = [
        f"I ran a quick audit on {business_name}'s website and it scored {score}/100 (Grade {grade}).",
        "",
    ]

    if top:
        lines.append("Here's what's hurting them:")
        for issue in top:
            lines.append(f"  • {issue}")
        lines.append("")

    lines.append(
        "These issues mean they're likely losing customers to competitors with better sites. "
        "A modern, fast website built for local search could make a real difference for their business."
    )

    return "\n".join(lines)


# ─── Audit sub-checks ────────────────────────────────────────────────────────

def _score_from_issues(issues: List[Dict], max_score: int = 100) -> int:
    deductions = {CRITICAL: 25, WARNING: 10, INFO: 3}
    total = sum(deductions.get(i["severity"], 0) for i in issues)
    return max(0, max_score - total)


async def _audit_speed(url: str, response_time_ms: float, html: str) -> Dict:
    issues = []
    html_size_kb = len(html.encode()) / 1024

    if response_time_ms > 3000:
        issues.append({"severity": CRITICAL, "message": f"Page loaded in {response_time_ms:.0f}ms — very slow (ideal is under 1000ms)"})
    elif response_time_ms > 1500:
        issues.append({"severity": WARNING, "message": f"Page loaded in {response_time_ms:.0f}ms — could be faster"})

    if html_size_kb > 500:
        issues.append({"severity": WARNING, "message": f"Page HTML is {html_size_kb:.0f}KB — consider minification"})

    soup = BeautifulSoup(html, "html.parser")
    blocking = [s for s in soup.find_all("script", src=True)
                if not s.get("async") and not s.get("defer")]
    if len(blocking) > 3:
        issues.append({"severity": WARNING, "message": f"{len(blocking)} render-blocking scripts (no async/defer)"})

    return {"score": _score_from_issues(issues), "issues": issues, "response_time_ms": response_time_ms}


def _audit_mobile(html: str) -> Dict:
    issues = []
    soup = BeautifulSoup(html, "html.parser")

    viewport = soup.find("meta", attrs={"name": re.compile("viewport", re.I)})
    if not viewport:
        issues.append({"severity": CRITICAL, "message": "No viewport meta tag — page is not mobile-friendly"})
    elif "width=device-width" not in viewport.get("content", ""):
        issues.append({"severity": WARNING, "message": "Viewport tag missing 'width=device-width'"})

    tiny = sum(1 for f in re.findall(r'font-size\s*:\s*([0-9]+)px', html) if int(f) < 12)
    if tiny:
        issues.append({"severity": WARNING, "message": f"{tiny} instances of very small text (under 12px)"})

    wide = [w for w in re.findall(r'width\s*:\s*([0-9]+)px', html) if int(w) > 900]
    if len(wide) > 2:
        issues.append({"severity": WARNING, "message": "Fixed-width containers detected — may not scale on mobile"})

    return {"score": _score_from_issues(issues), "issues": issues}


def _audit_seo(url: str, html: str) -> Dict:
    issues = []
    soup = BeautifulSoup(html, "html.parser")

    title = soup.find("title")
    if not title or not title.get_text(strip=True):
        issues.append({"severity": CRITICAL, "message": "No <title> tag — search engines can't rank this page"})
    elif len(title.get_text(strip=True)) > 70:
        issues.append({"severity": WARNING, "message": f"Title tag is {len(title.get_text())} chars — ideal is under 60"})

    meta_desc = soup.find("meta", attrs={"name": re.compile("description", re.I)})
    if not meta_desc or not meta_desc.get("content", "").strip():
        issues.append({"severity": CRITICAL, "message": "No meta description — appears blank in Google results"})

    h1_tags = soup.find_all("h1")
    if not h1_tags:
        issues.append({"severity": CRITICAL, "message": "No H1 heading — Google can't determine page topic"})
    elif len(h1_tags) > 1:
        issues.append({"severity": WARNING, "message": f"{len(h1_tags)} H1 tags found — should have exactly one"})

    no_alt = [i for i in soup.find_all("img") if not i.get("alt")]
    if no_alt:
        issues.append({"severity": WARNING, "message": f"{len(no_alt)} images missing alt text"})

    if not soup.find("link", rel="canonical"):
        issues.append({"severity": INFO, "message": "No canonical tag — may cause duplicate content issues"})

    return {
        "score": _score_from_issues(issues),
        "issues": issues,
        "title": title.get_text(strip=True) if title else None,
        "meta_description": meta_desc.get("content", "") if meta_desc else None,
    }


def _audit_design(url: str, html: str) -> Dict:
    issues = []
    html_lower = html.lower()
    soup = BeautifulSoup(html, "html.parser")

    cheap_builders = {
        "wix.com": "Built on Wix",
        "weebly.com": "Built on Weebly",
        "squarespace.com": "Built on Squarespace",
        "godaddy.com": "Built on GoDaddy Website Builder",
        "yolasite.com": "Built on Yola",
        "jimdo.com": "Built on Jimdo",
        "site123.com": "Built on Site123",
    }
    for domain, label in cheap_builders.items():
        if domain in html_lower:
            issues.append({"severity": WARNING, "message": f"{label} — template sites rarely rank well or convert"})
            break

    if not url.startswith("https://"):
        issues.append({"severity": CRITICAL, "message": "Not using HTTPS — browsers show 'Not Secure' to visitors"})

    if not soup.find("link", rel=re.compile("icon", re.I)):
        issues.append({"severity": INFO, "message": "No favicon found"})

    if not re.search(r'\(?\d{3}\)?[-.\s]\d{3}[-.\s]\d{4}', html):
        issues.append({"severity": WARNING, "message": "No phone number on homepage — customers can't easily call"})

    if len(soup.find_all("table")) > 2:
        issues.append({"severity": WARNING, "message": "HTML tables used for layout — outdated, hurts mobile"})

    if "swfobject" in html_lower or ".swf" in html_lower:
        issues.append({"severity": CRITICAL, "message": "Flash content detected — not supported in any modern browser"})

    match = re.search(r'(?:copyright|©)\s*(\d{4})', html_lower)
    if match and int(match.group(1)) < 2020:
        issues.append({"severity": INFO, "message": f"Copyright year shows {match.group(1)} — site appears outdated"})

    return {"score": _score_from_issues(issues), "issues": issues, "uses_https": url.startswith("https://")}


# ─── Main audit function ──────────────────────────────────────────────────────

async def audit_website(url: str, business_name: str = "") -> Dict[str, Any]:
    if not url.startswith(("http://", "https://")):
        url = "https://" + url

    result = {
        "url": url, "reachable": False,
        "overall_score": 0, "speed_score": 0, "mobile_score": 0,
        "seo_score": 0, "design_score": 0,
        "all_issues": [], "issues_by_category": {},
        "sales_summary": "", "raw_data": {},
    }

    html = ""
    response_time_ms = 9999.0

    try:
        start = time.monotonic()
        async with httpx.AsyncClient(timeout=10.0, follow_redirects=True) as client:
            resp = await client.get(url, headers={"User-Agent": "Mozilla/5.0 (compatible; PitchLabBot/1.0)"})
            response_time_ms = (time.monotonic() - start) * 1000
            html = resp.text
            result["reachable"] = resp.status_code < 400
    except Exception as e:
        result["sales_summary"] = f"Could not reach {url}: {str(e)}"
        return result

    speed_r  = await _audit_speed(url, response_time_ms, html)
    mobile_r = _audit_mobile(html)
    seo_r    = _audit_seo(url, html)
    design_r = _audit_design(url, html)

    result["speed_score"]  = speed_r["score"]
    result["mobile_score"] = mobile_r["score"]
    result["seo_score"]    = seo_r["score"]
    result["design_score"] = design_r["score"]
    result["overall_score"] = int(
        result["speed_score"]  * 0.25 +
        result["mobile_score"] * 0.25 +
        result["seo_score"]    * 0.30 +
        result["design_score"] * 0.20
    )

    all_issues = (
        speed_r["issues"] + mobile_r["issues"] +
        seo_r["issues"]   + design_r["issues"]
    )
    result["all_issues"] = all_issues
    result["issues_by_category"] = {
        "speed": speed_r["issues"], "mobile": mobile_r["issues"],
        "seo": seo_r["issues"], "design": design_r["issues"],
    }
    result["raw_data"] = {
        "response_time_ms": response_time_ms,
        "html_size_kb": len(html.encode()) / 1024,
        "title": seo_r.get("title"),
        "meta_description": seo_r.get("meta_description"),
        "uses_https": design_r.get("uses_https"),
    }

    # AI-generated unique summary
    result["sales_summary"] = await _generate_ai_summary(
        business_name=business_name,
        url=url,
        score=result["overall_score"],
        issues=all_issues,
        raw_data=result["raw_data"],
    )

    return result


def mock_no_website_audit(business_name: str) -> Dict[str, Any]:
    """For businesses with no website."""
    return {
        "url": None, "reachable": False,
        "overall_score": 0, "speed_score": 0, "mobile_score": 0,
        "seo_score": 0, "design_score": 0,
        "all_issues": [
            {"severity": CRITICAL, "message": "No website — completely invisible to online searches"},
            {"severity": CRITICAL, "message": "Missing from Google Maps website listing"},
            {"severity": CRITICAL, "message": "No way for customers to find info online before calling"},
        ],
        "issues_by_category": {"speed": [], "mobile": [], "seo": [], "design": []},
        "sales_summary": (
            f"{business_name} doesn't have a website at all, which means they're completely "
            f"invisible to anyone searching online for their services. Every time a potential "
            f"customer Googles a local option, {business_name} isn't even in the running. "
            f"Competitors with even a basic website are winning those searches by default. "
            f"A simple, fast site with their services, location, phone number, and a few "
            f"reviews would put them on the map immediately — literally."
        ),
        "raw_data": {},
    }
