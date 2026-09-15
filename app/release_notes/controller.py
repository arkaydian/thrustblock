import base64
import datetime
import logging

import viktor as vkt

logger = logging.getLogger("viktor")



# ---------------------------------------------------------------------------
# Release notes data — edit this list to maintain your version history.
# Each entry has:
#   version  : semantic version string
#   date     : release date (ISO format recommended)
#   changes  : dict mapping category label → list of change strings
# ---------------------------------------------------------------------------
RELEASE_NOTES = [
    {
        "version": "1.0.0",
        "date": "18-08-2026",
        "changes": {
            "🚀 New Features": [
                "Initial release of the application.",
                "Project based calculations for Thrust restraint, Soil Embedment (To be implemented) and Hydraulics (Not yet implemented)",
                "Quick calculation available as well."
                "PDF report generation for multiple thrust restraint.",
            ],
        },
    },
]

# ---------------------------------------------------------------------------
# Category badge colours (background, text)
# ---------------------------------------------------------------------------
# ---------------------------------------------------------------------------
# Known issues data — edit this list to maintain known issues.
# Each entry has:
#   id       : unique issue identifier string
#   title    : short title of the issue
#   severity : "High" | "Medium" | "Low"
#   status   : "Open" | "In Progress" | "Resolved"
#   description : detailed description of the issue
# ---------------------------------------------------------------------------
KNOWN_ISSUES = [
    {
        "id": "KI-002",
        "title": "Sketches for Blank End, Control Valve and Tee fittings not implemented",
        "severity": "Medium",
        "status": "Open",
        "description": "These are yet to be implemented",
    },
    {
        "id": "KI-001",
        "title": "Taper Thrust section not reflecting true depth of block",
        "severity": "Low",
        "status": "Open",
        "description": "The section drawing for a Taper Thrust is not true to parameters as of now.",
    },
]

CATEGORY_COLORS = {
    "🚀 New Features":  ("#e8f5e9", "#2e7d32"),
    "✨ Improvements":  ("#e3f2fd", "#1565c0"),
    "🐛 Bug Fixes":     ("#fff3e0", "#e65100"),
}
DEFAULT_BADGE_COLORS = ("#f3e5f5", "#6a1b9a")

# Severity badge colours for known issues
SEVERITY_COLORS = {
    "High":   ("#fdecea", "#c62828"),
    "Medium": ("#fff8e1", "#f57f17"),
    "Low":    ("#e8f5e9", "#2e7d32"),
}

# Status badge colours for known issues
STATUS_COLORS = {
    "Open":        ("#fce4ec", "#880e4f"),
    "In Progress": ("#e3f2fd", "#1565c0"),
    "Resolved":    ("#e8f5e9", "#2e7d32"),
}


def _shared_html_wrapper(title: str, subtitle: str, body: str) -> str:
    """Wrap page body in a shared HTML shell with consistent styling."""
    return f"""
    <!DOCTYPE html>
    <html lang="en">
    <head>
      <meta charset="UTF-8">
      <meta name="viewport" content="width=device-width, initial-scale=1.0">
      <title>{title}</title>
      <style>
        * {{ box-sizing: border-box; }}
        body {{
          margin: 0;
          padding: 24px 32px;
          background: #f0f4f8;
          font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
        }}
        ul {{ list-style-type: disc; }}
      </style>
    </head>
    <body>
      <div style="margin-bottom:28px;">
        <h1 style="margin:0 0 6px 0;font-size:28px;font-weight:800;color:#1a237e;">
          {title}
        </h1>
        <p style="margin:0;font-size:15px;color:#607d8b;">{subtitle}</p>
      </div>
      {body}
    </body>
    </html>
    """


def _build_html() -> str:
    """Build the full HTML string for the release notes page."""

    # --- individual version cards ---
    cards_html = ""
    for i, entry in enumerate(RELEASE_NOTES):
        is_latest = i == 0
        latest_badge = (
            '<span style="'
            "display:inline-block;margin-left:12px;padding:2px 10px;"
            "background:#1976d2;color:#fff;border-radius:12px;"
            'font-size:12px;font-weight:600;vertical-align:middle;">LATEST</span>'
            if is_latest
            else ""
        )

        # Build change categories
        categories_html = ""
        for category, items in entry["changes"].items():
            bg, fg = CATEGORY_COLORS.get(category, DEFAULT_BADGE_COLORS)
            items_html = "".join(
                f'<li style="margin:6px 0;color:#37474f;font-size:14px;line-height:1.6;">{item}</li>'
                for item in items
            )
            categories_html += f"""
            <div style="margin-bottom:18px;">
              <span style="
                display:inline-block;padding:3px 12px;border-radius:12px;
                background:{bg};color:{fg};font-size:12px;font-weight:700;
                letter-spacing:0.4px;margin-bottom:8px;">
                {category}
              </span>
              <ul style="margin:0;padding-left:20px;">
                {items_html}
              </ul>
            </div>
            """

        border_style = "border-left:4px solid #1976d2;" if is_latest else "border-left:4px solid #cfd8dc;"
        cards_html += f"""
        <div style="
          background:#ffffff;border-radius:10px;padding:24px 28px;
          margin-bottom:20px;box-shadow:0 2px 8px rgba(0,0,0,0.07);
          {border_style}">
          <div style="display:flex;align-items:center;margin-bottom:4px;">
            <h2 style="margin:0;font-size:20px;font-weight:700;color:#1a237e;">
              v{entry['version']}
            </h2>
            {latest_badge}
          </div>
          <p style="margin:0 0 16px 0;font-size:13px;color:#90a4ae;font-weight:500;">
            Released on {entry['date']}
          </p>
          {categories_html}
        </div>
        """

    return _shared_html_wrapper(
        title="📋 Release Notes",
        subtitle="A full history of changes, improvements, and fixes across all versions.",
        body=cards_html,
    )


def _build_known_issues_html() -> str:
    """Build the HTML for the Known Issues page."""

    # --- known issues table ---
    def _issue_rows() -> str:
        if not KNOWN_ISSUES:
            return '<tr><td colspan="4" style="padding:12px;color:#90a4ae;font-style:italic;">No known issues.</td></tr>'
        rows = ""
        for idx, issue in enumerate(KNOWN_ISSUES):
            row_bg = "#fafafa" if idx % 2 == 0 else "#ffffff"
            sev_bg, sev_fg = SEVERITY_COLORS.get(issue["severity"], ("#f5f5f5", "#333"))
            sta_bg, sta_fg = STATUS_COLORS.get(issue["status"], ("#f5f5f5", "#333"))
            rows += f"""
            <tr style="background:{row_bg};">
              <td style="padding:10px 14px;font-size:13px;color:#546e7a;white-space:nowrap;font-weight:600;">
                {issue['id']}
              </td>
              <td style="padding:10px 14px;font-size:14px;color:#37474f;line-height:1.5;">
                {issue['title']}<br>
                <span style="font-size:12px;color:#90a4ae;">{issue['description']}</span>
              </td>
              <td style="padding:10px 14px;white-space:nowrap;">
                <span style="display:inline-block;padding:2px 10px;border-radius:10px;
                             background:{sev_bg};color:{sev_fg};font-size:12px;font-weight:600;">
                  {issue['severity']}
                </span>
              </td>
              <td style="padding:10px 14px;white-space:nowrap;">
                <span style="display:inline-block;padding:2px 10px;border-radius:10px;
                             background:{sta_bg};color:{sta_fg};font-size:12px;font-weight:600;">
                  {issue['status']}
                </span>
              </td>
            </tr>"""
        return rows

    known_issues_table = f"""
    <div style="background:#fff;border-radius:10px;box-shadow:0 2px 8px rgba(0,0,0,0.07);
                margin-bottom:28px;overflow:hidden;border-left:4px solid #6a1b9a;">
      <div style="padding:16px 20px;background:#f3e5f5;">
        <h2 style="margin:0;font-size:17px;font-weight:700;color:#6a1b9a;">⚠️ Known Issues</h2>
      </div>
      <table style="width:100%;border-collapse:collapse;">
        <thead>
          <tr style="background:#eceff1;">
            <th style="padding:10px 14px;text-align:left;font-size:12px;color:#607d8b;
                       font-weight:600;letter-spacing:0.5px;width:80px;">ID</th>
            <th style="padding:10px 14px;text-align:left;font-size:12px;color:#607d8b;
                       font-weight:600;letter-spacing:0.5px;">ISSUE</th>
            <th style="padding:10px 14px;text-align:left;font-size:12px;color:#607d8b;
                       font-weight:600;letter-spacing:0.5px;width:90px;">SEVERITY</th>
            <th style="padding:10px 14px;text-align:left;font-size:12px;color:#607d8b;
                       font-weight:600;letter-spacing:0.5px;width:110px;">STATUS</th>
          </tr>
        </thead>
        <tbody>{_issue_rows()}</tbody>
      </table>
    </div>
    """

    body = known_issues_table

    return _shared_html_wrapper(
        title="⚠️ Known Issues",
        subtitle="A list of currently tracked issues, their severity, and resolution status.",
        body=body,
    )


def _build_issue_confirmation_html(title: str, description: str, has_image: bool) -> str:
    """Build a confirmation HTML page shown after an issue is submitted."""
    image_note = "📎 An image was attached to this report." if has_image else "No image attached."
    submitted_at = datetime.datetime.now().strftime("%Y-%m-%d %H:%M")
    return _shared_html_wrapper(
        title="✅ Issue Submitted",
        subtitle="Thank you for your report. The development team will review it shortly.",
        body=f"""
        <div style="background:#fff;border-radius:10px;padding:28px;
                    box-shadow:0 2px 8px rgba(0,0,0,0.07);border-left:4px solid #2e7d32;
                    max-width:700px;">
          <h2 style="margin:0 0 16px 0;font-size:18px;color:#2e7d32;">Issue Report Received</h2>
          <p style="margin:0 0 8px 0;font-size:14px;color:#546e7a;">
            <strong>Title:</strong> {title or '(no title)'}
          </p>
          <p style="margin:0 0 8px 0;font-size:14px;color:#546e7a;">
            <strong>Submitted at:</strong> {submitted_at}
          </p>
          <p style="margin:0 0 16px 0;font-size:14px;color:#546e7a;">
            <strong>Attachment:</strong> {image_note}
          </p>
          <div style="background:#f9f9f9;border-radius:8px;padding:16px;border:1px solid #e0e0e0;">
            <p style="margin:0 0 6px 0;font-size:12px;color:#90a4ae;font-weight:600;
                      letter-spacing:0.4px;">DESCRIPTION</p>
            <p style="margin:0;font-size:14px;color:#37474f;line-height:1.6;white-space:pre-wrap;">
              {description or '(no description provided)'}
            </p>
          </div>
        </div>
        """,
    )


class ReleaseNotesParametrization(vkt.Parametrization):
    """Three pages: Release Notes, Issue Tracker, and Raise an Issue."""

    # ------------------------------------------------------------------
    # Page 1 — Release Notes (view only)
    # ------------------------------------------------------------------
    page_notes = vkt.Page("📋 Release Notes", views=["release_notes_view"])
    page_notes.intro = vkt.Text(
        "This page shows the full version history of the application. "
    )

    # ------------------------------------------------------------------
    # Page 2 — Known Issues (view only)
    # ------------------------------------------------------------------
    page_tracker = vkt.Page("⚠️ Known Issues", views=["tracker_view"])
    page_tracker.intro = vkt.Text(
        "A list of currently tracked known issues with severity and status. "
    )

    # ------------------------------------------------------------------
    # Page 3 — Raise an Issue
    # ------------------------------------------------------------------
    page_raise = vkt.Page("🐞 Raise an Issue", views=["raise_issue_view"])
    page_raise.issue_title = vkt.TextField(
        "Issue Title",
        description="A short, descriptive title for the issue (max 200 chars).",
    )
    page_raise.description = vkt.TextAreaField(
        "Description",
        description="Describe the issue in detail: steps to reproduce, expected vs actual behaviour, etc.",
    )
    page_raise.screenshot = vkt.FileField(
        "Attach Screenshot / Image (optional)",
        file_types=[".png", ".jpg", ".jpeg", ".gif", ".webp"],
        description="Upload a screenshot or image that illustrates the issue.",
    )

class ReleaseNotesController(vkt.Controller):
    parametrization = ReleaseNotesParametrization # type: ignore

    @vkt.WebView("Release Notes")
    def release_notes_view(self, params, **kwargs) -> vkt.WebResult:
        """Render the release notes as a styled HTML page."""
        html = _build_html()
        return vkt.WebResult(html=html)

    @vkt.WebView("Known Issues")
    def tracker_view(self, params, **kwargs) -> vkt.WebResult:
        """Render the known issues table."""
        html = _build_known_issues_html()
        return vkt.WebResult(html=html)

    @vkt.WebView("Raise an Issue")
    def raise_issue_view(self, params, **kwargs) -> vkt.WebResult:
        """Show a confirmation summary of the issue the user has filled in."""
        issue_title = params.page_raise.issue_title or ""
        description = params.page_raise.description or ""
        has_image = params.page_raise.screenshot is not None

        logger.info(f"🐞 Issue preview — title: '{issue_title}', has_image: {has_image}")

        # If nothing has been filled in yet, show a prompt
        if not issue_title and not description:
            html = _shared_html_wrapper(
                title="🐞 Raise an Issue",
                subtitle="Fill in the fields on the left to preview your issue report.",
                body="""
                <div style="background:#fff;border-radius:10px;padding:32px;
                            box-shadow:0 2px 8px rgba(0,0,0,0.07);
                            border-left:4px solid #cfd8dc;max-width:600px;text-align:center;">
                  <p style="font-size:40px;margin:0 0 12px 0;">📝</p>
                  <p style="font-size:16px;color:#607d8b;margin:0;">
                    Start filling in the form to see a live preview of your issue report here.
                  </p>
                </div>
                """,
            )
            return vkt.WebResult(html=html)

        html = _build_issue_confirmation_html(issue_title, description, has_image)
        return vkt.WebResult(html=html)
