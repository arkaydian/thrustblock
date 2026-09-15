import viktor as vkt

# ── Shared HTML helpers ────────────────────────────────────────────────────────

CSS = """
    <style>
        *, *::before, *::after { box-sizing: border-box; margin: 0; padding: 0; }

        body {
            font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, Helvetica, Arial, sans-serif;
            background: #f5f7fa;
            color: #2d3748;
            line-height: 1.7;
            padding: 2.5rem 1.5rem;
        }

        .container { max-width: 860px; margin: 0 auto; }

        /* ── Header ── */
        .header {
            background: linear-gradient(135deg, #1a365d 0%, #2b6cb0 100%);
            color: #fff;
            border-radius: 12px;
            padding: 2.5rem 2.5rem 2rem;
            margin-bottom: 2rem;
        }
        .header h1 { font-size: 2rem; font-weight: 700; letter-spacing: -0.5px; margin-bottom: 0.5rem; }
        .header p  { font-size: 1.05rem; opacity: 0.88; max-width: 640px; }

        .badge {
            display: inline-block;
            background: rgba(255,255,255,0.2);
            border: 1px solid rgba(255,255,255,0.35);
            border-radius: 20px;
            font-size: 0.78rem;
            font-weight: 600;
            letter-spacing: 0.5px;
            padding: 0.2rem 0.75rem;
            margin-bottom: 1rem;
            text-transform: uppercase;
        }

        /* ── Section divider ── */
        .section-title {
            font-size: 0.72rem;
            font-weight: 700;
            letter-spacing: 1.2px;
            text-transform: uppercase;
            color: #718096;
            margin: 2rem 0 0.75rem 0.25rem;
        }

        /* ── Cards ── */
        .card {
            background: #fff;
            border-radius: 10px;
            padding: 1.75rem 2rem;
            margin-bottom: 1.25rem;
            box-shadow: 0 1px 4px rgba(0,0,0,0.07), 0 4px 16px rgba(0,0,0,0.04);
            border-left: 4px solid #2b6cb0;
        }
        .card.accent-green  { border-left-color: #276749; }
        .card.accent-orange { border-left-color: #c05621; }
        .card.accent-grey   { border-left-color: #718096; }

        .card h2 {
            font-size: 1.1rem;
            font-weight: 700;
            color: #1a365d;
            margin-bottom: 0.85rem;
            display: flex;
            align-items: center;
            gap: 0.5rem;
        }
        .card p { color: #4a5568; margin-bottom: 0.6rem; }
        .card p:last-child { margin-bottom: 0; }

        /* ── Steps list ── */
        ol.steps { padding-left: 1.4rem; color: #4a5568; }
        ol.steps li { margin-bottom: 0.55rem; padding-left: 0.3rem; }
        ol.steps li strong { color: #2d3748; }

        /* ── Tag pills ── */
        .tags { display: flex; flex-wrap: wrap; gap: 0.5rem; margin-top: 0.6rem; }
        .tag {
            background: #ebf4ff;
            color: #2b6cb0;
            border-radius: 20px;
            font-size: 0.8rem;
            font-weight: 600;
            padding: 0.2rem 0.75rem;
        }

        /* ── Note / warning box ── */
        .note {
            background: #fffbeb;
            border: 1px solid #f6e05e;
            border-radius: 8px;
            padding: 1rem 1.25rem;
            font-size: 0.9rem;
            color: #744210;
            margin-top: 0.75rem;
        }
        .note-info {
            background: #ebf8ff;
            border: 1px solid #90cdf4;
            border-radius: 8px;
            padding: 1rem 1.25rem;
            font-size: 0.9rem;
            color: #2c5282;
            margin-top: 0.75rem;
        }
        .wip {
            background: #fff5f5;
            border: 1px solid #fc8181;
            border-radius: 8px;
            padding: 1rem 1.25rem;
            font-size: 0.9rem;
            color: #742a2a;
            margin-top: 0.75rem;
        }

        /* ── Release table ── */
        table.release { width: 100%; border-collapse: collapse; margin-top: 0.5rem; font-size: 0.9rem; }
        table.release th {
            text-align: left;
            background: #ebf4ff;
            color: #1a365d;
            padding: 0.55rem 0.85rem;
            font-weight: 700;
        }
        table.release td { padding: 0.5rem 0.85rem; border-bottom: 1px solid #e2e8f0; color: #4a5568; }
        table.release tr:last-child td { border-bottom: none; }

        /* ── Footer ── */
        .footer {
            text-align: center;
            font-size: 0.82rem;
            color: #a0aec0;
            margin-top: 2.5rem;
            padding-top: 1.5rem;
            border-top: 1px solid #e2e8f0;
        }
    </style>
"""

FOOTER = """
    <div class="footer">
        Built with <strong>VIKTOR</strong> &mdash; replace with your organisation name &amp; version.
    </div>
"""

def _page(title: str, body: str) -> str:
    """Wrap body content in a full HTML document with shared CSS."""
    return f"""<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>{title}</title>
    {CSS}
</head>
<body>
<div class="container">
{body}
{FOOTER}
</div>
</body>
</html>"""


# ── Parametrization ────────────────────────────────────────────────────────────

class DocumentationParametrization(vkt.Parametrization):

    # Page 1 — Main: three separate views
    main = vkt.Page("Main", views=["view_project", "view_quick_calc"])

    # Page 2 — Thrust Restraint: two separate views
    thrust = vkt.Page("Thrust Restraint", views=["view_thrust_block", "view_anchor_block"])

    # Page 3 — Soil Embedment (work in progress)
    soil = vkt.Page("Soil Embedment", views=["view_soil"])


# ── Controller ────────────────────────────────────────────────────────────────

class DocumentationController(vkt.Controller):
    parametrization = DocumentationParametrization #type: ignore

    # ── Page 1a: Project ──────────────────────────────────────────────────────

    @vkt.WebView("Project")
    def view_project(self, params, **kwargs):
        """Main page — Project overview and scope."""

        body = """
        <!-- Header -->
        <div class="header">
            <div class="badge">Main &rsaquo; Project</div>
            <h1>&#128193; Project</h1>
            <p>
                Welcome to Water D&E's CivEng hub. The app consists of 4 main pages: Projects, Quick Calc, Release Notes and Documentation (where you are now if you haven't noticed)
            </p>
        </div>

        <div class="section-title">&#128269; Overview</div>

        <div class="card">
            <h2>&#128269; Project Overview</h2>
            <p>
                The Projects module of the app allows users to calculate a number of engineering workflows such as Thrust Restraint, Soil Embedment (to be implemented) and Hydraulics at a consistent project-wide level.
            </p>
        </div>

        <div class="card">
            <h2>&#127775; Scope &amp; Objectives</h2>
            <p><strong>Scope:</strong> Create a project such as <b>Lewisham STW</b> and then begin implementing any number of thrust restraint components.</p>
            <p><strong>Objectives: </strong>Keep all of thrust restraint components within a project so you can extract a report which will consist of calculations, arrangement sketches and references.</p>
        </div>
        """

        return vkt.WebResult(html=_page("Project", body))

    # ── Page 1b: Quick Calc ───────────────────────────────────────────────────

    @vkt.WebView("Quick Calc")
    def view_quick_calc(self, params, **kwargs):
        """Main page — Quick Calc guide."""

        body = """
        <!-- Header -->
        <div class="header">
            <div class="badge">Main &rsaquo; Quick Calc</div>
            <h1>&#9889; Quick Calc</h1>
            <p>
                A rapid calculation workflow for common scenarios.
                Follow the steps below to get results quickly.
            </p>
        </div>

        <div class="section-title">&#9654; How to Use</div>

        <div class="card accent-green">
            <h2>&#9654; How to Use — Quick Calc</h2>
            <ol class="steps">
                <li><strong>Step 1 — </strong> Describe the first action (e.g. select a pipe diameter or material).</li>
                <li><strong>Step 2 — </strong> Fill in the required input parameters.</li>
                <li><strong>Step 3 — </strong> Review the automatically updated results in the view panel.</li>
                <li><strong>Step 4 — </strong> Automated sketches and calculations</li>
            </ol>
        </div>

        <div class="section-title">&#128165; Inputs &amp; Outputs</div>

        <div class="card accent-green">
            <h2>&#128165; Inputs &amp; Outputs</h2>
            <p><strong>Inputs:</strong> List the key input parameters the user must provide for the quick calculation.</p>
            <p><strong>Outputs:</strong> Describe the results, plots, or tables the quick calc produces.</p>
            <div class="note-info">
                &#8505;&#65039; <strong>Tip:</strong> Add any helpful hints or assumptions specific to the Quick Calc workflow here.
            </div>
        </div>
        """

        return vkt.WebResult(html=_page("Quick Calc", body))

    # ── Page 2a: Thrust Block ─────────────────────────────────────────────────

    @vkt.WebView("Thrust Block")
    def view_thrust_block(self, params, **kwargs):
        """Thrust Restraint page — Thrust Block sub-section."""

        body = """
        <!-- Header -->
        <div class="header">
            <div class="badge">Thrust Restraint &rsaquo; Thrust Block</div>
            <h1>&#9632; Thrust Block</h1>
            <p>
                Documentation for the thrust block design method, covering bearing area
                calculations and block dimensioning.
            </p>
        </div>

        <div class="section-title">&#128269; Overview</div>

        <div class="card">
            <h2>&#128269; Overview</h2>
            <p>
                Describe the thrust block design method used in this app — e.g. passive soil
                resistance, bearing area calculation, applicable pipe sizes and pressure classes.
            </p>
            <p>
                Reference the relevant standard or design guide (e.g. AWWA M11, DIPRA, etc.).
            </p>
        </div>

        <div class="section-title">&#9654; How to Use</div>

        <div class="card">
            <h2>&#9654; How to Use — Thrust Block</h2>
            <ol class="steps">
                <li><strong>Step 1 — </strong> Select the pipe diameter and deflection angle.</li>
                <li><strong>Step 2 — </strong> Enter the design pressure and soil bearing capacity.</li>
                <li><strong>Step 3 — </strong> Review the required bearing area and block dimensions.</li>
                <li><strong>Step 4 — </strong> Download the calculation report if required.</li>
            </ol>
        </div>

        <div class="section-title">&#128165; Inputs &amp; Outputs</div>

        <div class="card">
            <h2>&#128165; Inputs &amp; Outputs</h2>
            <p><strong>Inputs:</strong> Pipe diameter, deflection angle, design pressure, soil bearing capacity, safety factor.</p>
            <p><strong>Outputs:</strong> Required bearing area, recommended block dimensions, utilisation ratio.</p>
            <div class="note">
                &#9888;&#65039; <strong>Note:</strong> Add any assumptions or limitations specific to the thrust block calculation here.
            </div>
        </div>
        """

        return vkt.WebResult(html=_page("Thrust Block", body))

    # ── Page 2b: Anchor Block ─────────────────────────────────────────────────

    @vkt.WebView("Anchor Block")
    def view_anchor_block(self, params, **kwargs):
        """Thrust Restraint page — Anchor Block sub-section."""

        body = """
        <!-- Header -->
        <div class="header">
            <div class="badge">Thrust Restraint &rsaquo; Anchor Block</div>
            <h1>&#9875; Anchor Block</h1>
            <p>
                Documentation for the anchor block design method, covering restrained joint
                design, tie rod sizing, and applicable fittings.
            </p>
        </div>

        <div class="section-title">&#128269; Overview</div>

        <div class="card accent-green">
            <h2>&#128269; Overview</h2>
            <p>
                Describe the anchor block design method — e.g. restrained joint design,
                tie rod sizing, applicable fittings (bends, tees, reducers, end caps).
            </p>
            <p>
                Reference the relevant standard or design guide used for this method.
            </p>
        </div>

        <div class="section-title">&#9654; How to Use</div>

        <div class="card accent-green">
            <h2>&#9654; How to Use — Anchor Block</h2>
            <ol class="steps">
                <li><strong>Step 1 — </strong> Select the fitting type and pipe diameter.</li>
                <li><strong>Step 2 — </strong> Enter the design pressure and restraint length parameters.</li>
                <li><strong>Step 3 — </strong> Review the required anchor block size and tie rod arrangement.</li>
                <li><strong>Step 4 — </strong> Download the calculation report if required.</li>
            </ol>
        </div>

        <div class="section-title">&#128165; Inputs &amp; Outputs</div>

        <div class="card accent-green">
            <h2>&#128165; Inputs &amp; Outputs</h2>
            <p><strong>Inputs:</strong> Fitting type, pipe diameter, design pressure, soil friction angle, restraint length.</p>
            <p><strong>Outputs:</strong> Anchor block dimensions, tie rod count and diameter, utilisation ratio.</p>
            <div class="note">
                &#9888;&#65039; <strong>Note:</strong> Add any assumptions or limitations specific to the anchor block calculation here.
            </div>
        </div>
        """

        return vkt.WebResult(html=_page("Anchor Block", body))

    # ── Page 3: Soil Embedment ────────────────────────────────────────────────

    @vkt.WebView("Documentation")
    def view_soil(self, params, **kwargs):
        """Soil Embedment page — placeholder for a module yet to be implemented."""

        body = """
        <!-- Header -->
        <div class="header">
            <div class="badge">Soil Embedment</div>
            <h1>&#127758; Soil Embedment</h1>
            <p>
                Documentation for the soil embedment design module.
                This section will be updated once the module is implemented.
            </p>
        </div>

        <!-- WIP notice -->
        <div class="card accent-grey">
            <h2>&#128679; Work in Progress</h2>
            <div class="wip">
                &#128679; <strong>Not yet implemented.</strong> This module is currently under development.
                The documentation below is a placeholder — replace it with real content once the
                module is ready.
            </div>
        </div>

        <!-- ── PLANNED SCOPE ── -->
        <div class="section-title">&#128196; Planned Scope</div>

        <div class="card accent-grey">
            <h2>&#128269; Overview</h2>
            <p>
                Describe the intended scope of the soil embedment module here — e.g. flexible
                pipe deflection, soil stiffness, installation class, cover depth requirements.
            </p>
            <p>
                Reference the relevant standard or design guide (e.g. AS/NZS 2566, AWWA M45, etc.).
            </p>
        </div>

        <div class="card accent-grey">
            <h2>&#128165; Planned Inputs &amp; Outputs</h2>
            <p><strong>Inputs:</strong> Pipe stiffness, soil type, installation class, cover depth, live load.</p>
            <p><strong>Outputs:</strong> Predicted deflection, allowable deflection check, embedment recommendation.</p>
            <div class="note-info">
                &#8505;&#65039; <strong>Note:</strong> These inputs and outputs are indicative only and may change during development.
            </div>
        </div>
        """

        return vkt.WebResult(html=_page("Soil Embedment", body))
