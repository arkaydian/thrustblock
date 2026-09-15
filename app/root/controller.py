import viktor as vkt
import pandas as pd
from pathlib import Path
from app.civeng1.calculations.thrust_block_calculation import (
    VerticalDownturnBendThrustBlock,
    VerticalUpturnBendThrustBlock,
    build_metallic_flange,
    fitting_from_params,
)
from openpyxl import load_workbook
from openpyxl.styles import Font, Alignment

class ProjectsRootParametrization(vkt.Parametrization):
    projects = vkt.ChildEntityManager("Project")

class ProjectsRoot(vkt.Controller):
    label = "Projects"
    children = ["Project"]
    show_children_as = "Cards"
    parametrization = ProjectsRootParametrization # type: ignore

class ProjectParametrization(vkt.Parametrization):
    thrust_restraint = vkt.ChildEntityManager("ThrustRestraint")

class Project(vkt.Controller):
    label = "Project"
    children = ["ThrustRestraint"]
    show_children_as = "Cards"
    parametrization = ProjectParametrization # type: ignore

class QuickCalc(vkt.Controller):
    label = "Quick Calc"
    children = ["AnchorBlock", "ThrustBlock"]
    show_children_as = "Cards"

class ReleaseNotes(vkt.Controller):
    label = "Release Notes"
    children = ["ReleaseNotes"]

class ThrustRestraintParametrization(vkt.Parametrization):
    producer_name = vkt.TextField("Producer", default="Arcadian 1")
    project_title = vkt.TextField("Project Title", default="Warton AMP8 - Growth")
    report_date = vkt.DateField("Report Date")
    client_name = vkt.TextField("Client Name", default="Severn Trent")
    client_representative = vkt.TextField("Client Representative", description="The client representative for the project")
    version_history = vkt.DynamicArray("Version History", copylast=True, default=[
        {
            "issue": "P01",
            "revision_number.": "v1.0",
            "date_issued": "",
            "checked_by": "",
            "reviewed_by": "",
            "approved_by": "",
            "status": "Draft",
            "comments": ""
        }
    ], description="`Add new row` for each issue. Do not overwrite previous version as it will not be included in future report extractions")
    version_history.issue = vkt.TextField("Phase/Milestone", default="")
    version_history.revision_number = vkt.TextField("Version", default="v1.0")
    version_history.date_issued = vkt.DateField("Issue Date")
    version_history.checked_by = vkt.TextField("Checked By")
    version_history.reviewed_by = vkt.TextField("Reviewed By")
    version_history.approved_by = vkt.TextField("Approved By")
    version_history.status = vkt.OptionField("Status", options=["Draft", "Checked", "Reviewed", "Approved", "Rejected"], default="Draft")

    # Download button for Word document
    lb = vkt.LineBreak()
    download_pdf = vkt.DownloadButton("Download PDF Report", method="download_pdf_document")
    download_excel = vkt.DownloadButton("Download Excel Report", method="export_to_excel")
    download_word = vkt.DownloadButton("Download Word Report", method="download_word_document")


# Project
# │
# ├── owns project/report metadata
# │
# ├── contains ThrustBlock and AnchorBlock entities
# │
# ├── retrieves children's saved parameters
# │
# ├── rebuilds engineering calculation objects
# │
# ├── aggregates results
# │
# └── produces views and reports
class ThrustRestraint(vkt.Controller):
    label = "Thrust Restraint"
    children = ["ThrustBlock", "AnchorBlock"]
    show_children_as = "Table"
    parametrization = ThrustRestraintParametrization  # type: ignore

    # ---------------------------------------------------------------------------
    # Helper data preparation
    # ---------------------------------------------------------------------------
    def get_version_history_table_data(self, params, **kwargs):
        """Convert the project version history into a plain row-based structure.

        Purpose
        -------
        This helper prepares the version metadata stored in ``params.version_history`` into
        the row shape expected by VIKTOR tables and the Word template.

        Data flow
        ---------
        The data originates in the ``ProjectParametrization`` dynamic array and is read one
        version entry at a time. Each row is normalised to a list containing issue,
        revision, date, reviewer fields, and status.

        Returns
        -------
        list[list[object]]
            A list of row lists, each row corresponding to one project issue or revision.

        Notes
        -----
        This method is used both for the VIKTOR version-history table and when filling the
        Word report's version table. The logic deliberately keeps the same data structure for
        both consumers.
        """

        table_data = []
        for version in params.version_history:
            row = [
                version.issue,
                version.revision_number,
                version.date_issued,
                version.checked_by or "-",
                version.reviewed_by or "-",
                version.approved_by or "-",
                version.status,
            ]
            table_data.append(row)

        return table_data

    # ---------------------------------------------------------------------------
    # Child entity retrieval
    # ---------------------------------------------------------------------------
    def get_thrust_block_children(self, params, **kwargs) -> list[vkt.api_v1.Entity]:
        """Return the direct ``ThrustBlock`` child entities for the current project.

        Purpose
        -------
        This is a helper method used throughout the controller to avoid repeating the same
        child-discovery logic. It is responsible for locating all direct children that are
        thrust-block calculation entities.

        Data flow
        ---------
        VIKTOR passes the current entity identifier through ``kwargs`` when the method is
        invoked from a controller action or view. The code reads ``entity_id`` and requests
        all direct child entities from the VIKTOR API.

        ``vkt.api_v1.API().get_entity_children(entity_id)`` returns the complete direct child
        set of the current project entity. The list is then filtered to keep only children
        whose ``entity_type.name`` equals ``"ThrustBlock"``.

        Returns
        -------
        list[vkt.api_v1.Entity]
            Direct child entities that represent thrust-block calculations.

        Notes
        -----
        A VIKTOR ``Entity`` is the persisted object representing a node in the project tree.
        The same pattern is used for both thrust blocks and anchor blocks so child entities
        can be discovered consistently across views and export workflows.
        """

        entity_id = kwargs["entity_id"]
        children = vkt.api_v1.API().get_entity_children(entity_id)
        thrust_blocks = [child for child in children if child.entity_type.name == "ThrustBlock"]

        return thrust_blocks

    def get_anchor_block_children(self, params, **kwargs) -> list[vkt.api_v1.Entity]:
        """Return the direct ``AnchorBlock`` child entities for the current project.

        Purpose
        -------
        This helper mirrors ``get_thrust_block_children`` but selects anchor-block entities
        instead. It centralises the repeated child-discovery logic used by reporting and
        summary methods.

        Data flow
        ---------
        The method reads the current VIKTOR ``entity_id`` from ``kwargs`` and requests all
        direct children from the VIKTOR API. It then filters the list to keep only entities
        whose ``entity_type.name`` matches ``"AnchorBlock"``.

        Returns
        -------
        list[vkt.api_v1.Entity]
            Direct child entities that represent anchor-block calculations.

        Notes
        -----
        These helper methods are used throughout the rest of the controller so the code does
        not repeatedly discover the same child entity sets in every view or export.
        """

        entity_id = kwargs["entity_id"]
        children = vkt.api_v1.API().get_entity_children(entity_id)
        anchor_blocks = [child for child in children if child.entity_type.name == "AnchorBlock"]

        return anchor_blocks

    # ---------------------------------------------------------------------------
    # Data aggregation helpers
    # ---------------------------------------------------------------------------
    def export_to_excel(self, params, **kwargs):
        """Export the project's thrust-block calculation output to an Excel workbook.

        Purpose
        -------
        This method creates a workbook from the project template, copies one template sheet
        for each thrust-block child, and fills the worksheet with the calculation workflow
        results produced by the domain objects.

        Data flow
        ---------
        The method opens the Arcadis template workbook, finds all ``ThrustBlock`` children,
        and for each child reads the saved parameter set from ``child.last_saved_params``.
        That persisted parameter set is the authoritative state saved on the VIKTOR child
        entity. The parent project then reconstructs the engineering calculation object using
        ``fitting_from_params``.

        The workbook then copies the template sheet named ``Thrust Block 1`` and renames it
        after the child entity. The calculation rows in ``fitting_type.fitting_workflow_res``
        are written into the relevant spreadsheet cells.

        Returns
        -------
        vkt.DownloadResult
            A downloadable Excel file with the project title used in the output filename.

        Notes
        -----
        This workflow is intentionally driven by the saved child parameter state rather than
        by recomputing from the parent entity. The individual fields written are:

        - ``entry["label"]``: row label text;
        - ``entry["formula_xls"]``: spreadsheet formula or formula text;
        - ``entry["output"]``: calculated result;
        - ``entry["si_unit"]``: unit used in the output;
        - ``entry["reference"]``: reference/source text.

        The original blank template sheet is removed before saving so only the filled child
        sheets remain in the final workbook.
        """

        template_path = Path(__file__).parent / "files" / "arcadis_calculation_sheet_template.xlsx"
        wb = load_workbook(template_path)

        thrust_blocks = self.get_thrust_block_children(params, **kwargs)
        for child in thrust_blocks:
            # ``child.last_saved_params`` is the persisted/saved parametrization for the
            # child VIKTOR entity. The parent project needs it to reconstruct the same
            # calculation state that was saved with the child.
            child_params = child.last_saved_params
            ws = wb.copy_worksheet(wb["Thrust Block 1"])
            ws.title = f"{child.name}"

            fitting_type = fitting_from_params(params=child_params)
            for i, entry in enumerate(fitting_type.fitting_workflow_res):
                num = 7
                row = num + i
                ws[f"A{row}"] = entry["label"]
                ws[f"B{row}"] = entry["formula_xls"]
                ws[f"F{row}"] = entry["output"]
                ws[f"I{row}"] = entry["si_unit"]
                ws[f"J{row}"] = entry["reference"]

        wb.remove(wb["Thrust Block 1"])
        from io import BytesIO

        buffer = BytesIO()
        wb.save(buffer)
        buffer.seek(0)

        excel_file = vkt.File.from_data(buffer.read())

        return vkt.DownloadResult(excel_file, f"{params.project_title}_thrust_restraint_calculation.xlsx")

    def block_safety_table(self, params, **kwargs):
        """Aggregate safety and pass/fail statuses for each child calculation.

        Purpose
        -------
        This method turns each child calculation into a compact summary row that can be used
        in UI tables and Word reports. It records the child name, fitting type, chainage,
        and the result of several engineering checks.

        Data flow
        ---------
        The method finds all thrust-block and anchor-block children, reads each child's saved
        parameter set, and reconstructs a domain calculation object. For thrust blocks the
        code checks the standard thrust pass-through behaviour, plus vertical downturn and
        vertical upturn specific checks when relevant. For anchor blocks the logic builds a
        metallic flange object and evaluates its corresponding checks.

        Returns
        -------
        list[dict]
            A list of summary rows where each row contains the child name, fitting type,
            pass/fail values, and chainage.

        Notes
        -----
        The method intentionally yields values of ``Pass``, ``Fail``, or ``N/A`` depending on
        the relevant calculation type and available checks. This preserves the existing
        reporting behaviour even though the logic is repeated and somewhat type-specific.
        """

        thrust_blocks = self.get_thrust_block_children(params, **kwargs)
        anchor_blocks = self.get_anchor_block_children(params, **kwargs)

        data_rows = []
        for child in thrust_blocks:
            # ``child.last_saved_params`` stores the persisted input state for this child.
            # The project rehydrates the calculation object so it can report its checks.
            child_params = child.last_saved_params

            fitting_type = fitting_from_params(params=child_params)
            if isinstance(fitting_type, VerticalDownturnBendThrustBlock):
                uplift_test = "Pass" if fitting_type.uplift_safety_check else "Fail"
            else:
                uplift_test = "N/A"

            if isinstance(fitting_type, VerticalUpturnBendThrustBlock):
                vertical_thrust = "Pass" if fitting_type.vertical_force_check else "Fail"
            else:
                vertical_thrust = "N/A"

            if isinstance(fitting_type, VerticalUpturnBendThrustBlock):
                overturning_moment_check = "N/A"
            else:
                overturning_moment_check = "Pass" if fitting_type.overturning_check else "Fail"

            row = {
                "name": child.name,
                "fitting_type": child_params.fitting_section.fitting_type,
                "thrust_pass_through_check": "Pass" if fitting_type.thrust_pass_through_check else "Fail",
                "overturning_moment_check": overturning_moment_check,
                "vertical_thrust_check": vertical_thrust,
                "uplift_check": uplift_test,
                "chainage": child_params.fitting_section.chainage,
            }
            data_rows.append(row)

        for child in anchor_blocks:
            # ``child.last_saved_params`` is still the persisted child configuration; this
            # workflow reconstructs a metallic flange domain object from that saved state.
            child_params = child.last_saved_params
            metallic_flange = build_metallic_flange(child_params)
            row = {
                "name": child.name,
                "fitting_type": child_params.pipe_section.pipe_material,
                "thrust_pass_through_check": "Pass" if metallic_flange.thrust_pass_through_check else "Fail",
                "overturning_moment_check": "Pass" if metallic_flange.overturning_check else "Fail",
                "vertical_thrust_check": "N/A",
                "uplift_check": "N/A",
                "chainage": child_params.pipe_section.chainage,
            }
            data_rows.append(row)

        return data_rows

    def get_block_workflows(self, params, **kwargs):
        """Build appendix-style workflow tables from each child calculation object.

        Purpose
        -------
        This method converts the calculation object's ``fitting_workflow_res`` rows into a
        report-friendly structure for the Word template appendices.

        Data flow
        ---------
        Each child is resolved from its saved parameter set and rebuilt into a calculation
        object. The object exposes ``fitting_workflow_res`` which contains entries such as
        ``label``, ``formula_html``, and ``reference``. These rows are copied into simpler
        dictionaries so they can be inserted into the Word document.

        Returns
        -------
        list[dict]
            One appendix entry per child calculation. Each entry contains a title and a
            list of workflow rows.

        Notes
        -----
        The important fields are:

        - ``label``: human-readable description of the calculation line;
        - ``formula_html``: formula rendered for the report;
        - ``reference``: supporting reference text.

        Each child calculation becomes an appendix entry with a title such as
        ``"<fitting type> Calculation"`` or ``"<material> Contraction Calculation"``.
        """

        thrust_blocks = self.get_thrust_block_children(params, **kwargs)
        anchor_blocks = self.get_anchor_block_children(params, **kwargs)

        appendices = []
        for child in thrust_blocks:
            # ``child.last_saved_params`` is the persisted child input state. This saved data
            # is used to reconstruct the calculation object and its reporting workflow.
            child_params = child.last_saved_params

            fitting_type = fitting_from_params(params=child_params)
            table4 = []
            for row in fitting_type.fitting_workflow_res:
                table4.append({
                    "label": row["label"],
                    "formula": row["formula_html"],
                    "reference": row["reference"],
                })

            appendices.append({
                "title": f"{child_params.fitting_section.fitting_type} Calculation",
                "table4": table4,  # type: ignore
            })

        for child in anchor_blocks:
            child_params = child.last_saved_params

            fitting_type = build_metallic_flange(child_params)
            table4 = []
            for row in fitting_type.fitting_workflow_res:
                table4.append({
                    "label": row["label"],
                    "formula": row["formula_html"],
                    "reference": row["reference"],
                })

            appendices.append({
                "title": f"{child_params.pipe_section.pipe_material} Contraction Calculation",
                "table4": table4,  # type: ignore
            })

        return appendices

    def get_thrust_block_params(self, params, **kwargs):
        """Build the sequential dimension table used in the report summary.

        Purpose
        -------
        This helper returns a list of rows containing both thrust-block and anchor-block
        geometry information for the report. It is used to populate the dimension table in
        the Word document and similar summaries.

        Data flow
        ---------
        The method locates thrust-block and anchor-block children, reads each child's saved
        parameter state, and extracts the relevant geometric values such as chainage,
        fitting/material type, height, width, length, and depth.

        Returns
        -------
        list[list[object]]
            A table list whose rows contain a sequential numbering field and block geometry.

        Notes
        -----
        ``num = 1`` is used as the row counter and is incremented across both child types so
        the numbering remains sequential in the combined summary table. The method deliberately
        preserves the current ordering: thrust blocks first, then anchor blocks.
        """

        thrust_blocks = self.get_thrust_block_children(params, **kwargs)
        anchor_blocks = self.get_anchor_block_children(params, **kwargs)

        num = 1

        data_rows = []
        for child in thrust_blocks:
            # ``child.last_saved_params`` contains the saved child geometry and fitting info.
            child_params = child.last_saved_params

            row = [
                child_params.fitting_section.chainage,
                child_params.fitting_section.fitting_type,
                child_params.block_section.height,
                child_params.block_section.width,
                child_params.block_section.length,
                child_params.block_section.depth,
                num,
            ]
            data_rows.append(row)
            num += 1

        for child in anchor_blocks:
            child_params = child.last_saved_params

            row = [
                child_params.pipe_section.chainage,
                child_params.pipe_section.pipe_material,
                child_params.block_section.height,
                child_params.block_section.width,
                child_params.block_section.length,
                child_params.block_section.depth,
                num,
            ]
            data_rows.append(row)
            num += 1

        return data_rows

    # ---------------------------------------------------------------------------
    # VIKTOR views
    # ---------------------------------------------------------------------------
    @vkt.TableView("Version History")
    def view_version_history(self, params, **kwargs):
        """Render the project version history as a VIKTOR table.

        Purpose
        -------
        This view shows the project revision history in the VIKTOR UI using a colour-coded
        table. It is the user-visible summary of the ``version_history`` metadata.

        Data flow
        ---------
        The method reads each version entry from ``params.version_history`` and converts it
        into a table row. It also maps the status field to a background colour so Approved,
        Reviewed, Checked, Reject, and Draft states are visually distinct.

        Returns
        -------
        vkt.TableResult
            A VIKTOR table containing the version rows and configured column headers.

        Notes
        -----
        The ``@vkt.TableView("Version History")`` decorator exposes this method as a table
        view in the VIKTOR interface. The returned ``TableResult`` is what the user sees in
        the project UI.
        """

        headers = [
            vkt.TableHeader("Issue", align="center"),
            vkt.TableHeader("Revision No.", align="left"),
            vkt.TableHeader("Date Issued", align="center"),
            vkt.TableHeader("Checked By", align="left"),
            vkt.TableHeader("Reviewed By", align="left"),
            vkt.TableHeader("Approved By", align="left"),
            vkt.TableHeader("Status", align="center"),
        ]

        table_data = []
        for version in params.version_history:
            status_cell = vkt.TableCell(
                version.status,
                background_color=vkt.Color(144, 238, 144) if version.status == "Approved" else
                                vkt.Color(255, 255, 153) if version.status == "Reviewed" else
                                vkt.Color(173, 216, 230) if version.status == "Checked" else
                                vkt.Color(255, 182, 193) if version.status == "Rejected" else
                                vkt.Color(211, 211, 211),
            )

            row = [
                version.issue,
                version.revision_number,
                version.date_issued,
                version.checked_by or "-",
                version.reviewed_by or "-",
                version.approved_by or "-",
                status_cell,
            ]
            table_data.append(row)

        return vkt.TableResult(table_data, column_headers=headers)

    @vkt.TableView("Block Dimensions")
    def export_view(self, params, **kwargs):
        """Render summary dimensions for all child blocks as a VIKTOR table.

        Purpose
        -------
        This view lists the geometry of all thrust-block and anchor-block child entities in a
        compact summary table.

        Data flow
        ---------
        The method retrieves the current project's child entities, filters them by entity type,
        and reads each child's saved parameter state. It then records each child name, block
        type, and dimensions into a DataFrame that VIKTOR can render as a table.

        Returns
        -------
        vkt.TableResult
            A ``TableResult`` based on a pandas DataFrame of block dimensions.

        Notes
        -----
        The ``@vkt.TableView("Block Dimensions")`` decorator exposes this method in the VIKTOR
        interface as a standard table view. The returned table is for display and export; it
        is not the same as the Word report data model.
        """

        entity_id = kwargs["entity_id"]
        children = vkt.api_v1.API().get_entity_children(entity_id)
        thrust_blocks = [child for child in children if child.entity_type.name == "ThrustBlock"]
        anchor_blocks = [child for child in children if child.entity_type.name == "AnchorBlock"]
        all_blocks = thrust_blocks + anchor_blocks

        data_rows = []
        for child in all_blocks:
            child_params = child.last_saved_params
            block_type = "Thrust Block" if child.entity_type.name == "ThrustBlock" else "AnchorBlock"

            row = {
                "Name": child.name,
                "Type": block_type,
                "Height (m)": child_params.block_section.height,
                "Length (m)": child_params.block_section.length,
                "Width (m)": child_params.block_section.width,
            }
            data_rows.append(row)

        df = pd.DataFrame(data_rows)
        return vkt.TableResult(df)

    @vkt.TableView("Block Checks")
    def thrust_table(self, params, **kwargs):
        """Render the engineering check summary for thrust-block children as a table.

        Purpose
        -------
        This method exposes the most important thrust-block safety-check results in the VIKTOR
        UI without requiring the user to open the full engineering calculation data.

        Data flow
        ---------
        The method reads the project child entities, filters to thrust blocks, then reads the
        saved parameters for each child and reconstructs the relevant calculation object. The
        method builds a row of pass/fail values based on the calculation's check results and
        returns those rows as a table.

        Returns
        -------
        vkt.TableResult
            A table summarising the name, type, and safety check status for the thrust-block
            entries in the project.

        Notes
        -----
        The checks are intentionally represented as ``Pass``, ``Fail``, and ``N/A`` to match
        the engineering logic already used elsewhere in the controller. This view is a UI
        summary only; it is not the source of truth for the calculations.
        """

        entity_id = kwargs["entity_id"]
        children = vkt.api_v1.API().get_entity_children(entity_id)
        thrust_blocks = [child for child in children if child.entity_type.name == "ThrustBlock"]
        anchor_blocks = [child for child in children if child.entity_type.name == "AnchorBlock"]

        data_rows = []
        for child in thrust_blocks:
            child_params = child.last_saved_params

            fitting_type = fitting_from_params(params=child_params)
            if isinstance(fitting_type, VerticalDownturnBendThrustBlock):
                uplift_test = "Pass" if fitting_type.uplift_safety_check else "Fail"
            else:
                uplift_test = "N/A"

            if isinstance(fitting_type, VerticalUpturnBendThrustBlock):
                vertical_thrust = "Pass" if fitting_type.vertical_force_check else "Fail"
            else:
                vertical_thrust = "N/A"

            if isinstance(fitting_type, VerticalUpturnBendThrustBlock):
                overturning_moment_check = "N/A"
            else:
                overturning_moment_check = "Pass" if fitting_type.overturning_check else "Fail"

            row = {
                "Name": child.name,
                "Fitting Type": child_params.fitting_section.fitting_type,
                "Thrust Pass Through Check": "Pass" if fitting_type.thrust_pass_through_check else "Fail",
                "Overturning Moment Check": overturning_moment_check,
                "Vertical Thrust": vertical_thrust,
                "Uplift Check": uplift_test,
            }
            data_rows.append(row)

        df = pd.DataFrame(data_rows)
        return vkt.TableResult(df)

    # ---------------------------------------------------------------------------
    # Report generation and downloads
    # ---------------------------------------------------------------------------
    def generate_word_document(self, params, **kwargs):
        """Build the Word report for the project using the Arcadis template.

        Purpose
        -------
        This method assembles the project metadata, version history, safety checks, block
        dimensions, and calculation appendices into a ``WordFileTag`` collection, which is
        then rendered into the configured report template.

        Data flow
        ---------
        The method begins with project-level metadata such as title, date, producer, and
        client. It then collects the version-history rows, block safety summary rows, and the
        block geometry summary rows. Finally it resolves each calculation appendix from the
        child calculation objects and passes the whole collection to ``render_word_file``.

        The template mechanism uses ``WordFileTag`` objects to map placeholder names in the
        document to the data values. The tags are expected to correspond to fields such as:

        - ``report_title``;
        - ``report_date``;
        - ``producer_name``;
        - ``client_name``;
        - ``client_job``;
        - ``table1``;
        - ``table2``;
        - ``table3``;
        - ``appendices``.

        Returns
        -------
        Word document object
            The rendered VIKTOR Word file built from the Arcadis template.

        Notes
        -----
        The method intentionally keeps the tag names and the template file path exactly as
        defined in the current implementation. The report generation is a composition step: a
        data model is assembled and then rendered into the document template.
        """

        components = []

        components.append(vkt.word.WordFileTag("report_title", params.project_title))
        components.append(vkt.word.WordFileTag("report_date", str(params.report_date)))
        components.append(vkt.word.WordFileTag("producer_name", params.producer_name))
        components.append(vkt.word.WordFileTag("client_name", params.client_name))
        components.append(vkt.word.WordFileTag("client_job", params.client_representative))

        version_table_data = self.get_version_history_table_data(params, **kwargs)

        version_table_rows = []
        for row in version_table_data:
            version_table_rows.append({
                "issue": row[0],
                "revision_number": row[1],
                "date_issued": str(row[2]),
                "checked_by": row[3],
                "reviewed_by": row[4],
                "approved_by": row[5],
                "status": row[6],
            })

        components.append(vkt.word.WordFileTag("table1", version_table_rows))

        thrust_safety_checks = self.block_safety_table(params, **kwargs)

        thrust_safety_checks_rows = []
        for row in thrust_safety_checks:
            thrust_safety_checks_rows.append({
                "chainage": row["chainage"],
                "fitting_type": row["fitting_type"],
                "thrust_pass_through_check": row["thrust_pass_through_check"],
                "overturning_moment_check": row["overturning_moment_check"],
                "vertical_thrust_check": row["vertical_thrust_check"],
                "uplift_check": row["uplift_check"],
            })
        components.append(vkt.word.WordFileTag("table2", thrust_safety_checks_rows))

        fitting_table_data = self.get_thrust_block_params(params, **kwargs)

        fitting_table_rows = []
        for row in fitting_table_data:
            fitting_table_rows.append({
                "chainage": row[0],
                "fitting_type": row[1],
                "height": row[2],
                "width": row[3],
                "length": row[4],
                "depth": row[5],
                "num": row[6],
            })
        components.append(vkt.word.WordFileTag("table3", fitting_table_rows))

        appendices = self.get_block_workflows(params, **kwargs)
        components.append(vkt.word.WordFileTag("appendices", appendices))

        template_path = Path(__file__).parent / "files" / "arcadis_template.docx"
        with open(template_path, "rb") as template:
            word_file = vkt.word.render_word_file(template, components)

        return word_file

    def download_pdf_document(self, params, **kwargs):
        """Generate the Word report and convert it to a downloadable PDF file.

        Purpose
        -------
        This method wraps the normal report-generation flow and uses VIKTOR's Word-to-PDF
        conversion to make a PDF copy of the report available to the user.

        Data flow
        ---------
        The method first generates the Word report through ``generate_word_document`` and
        then reads that file as binary. It passes the binary stream to
        ``vkt.convert_word_to_pdf`` and returns the resulting PDF as a ``DownloadResult``.

        Returns
        -------
        vkt.DownloadResult
            A downloadable PDF report with the project title in the filename.

        Notes
        -----
        The process is intentionally: Word report -> PDF conversion -> download. The method
        does not change the output naming or file structure from the current implementation.
        """

        word_file = self.generate_word_document(params, **kwargs)

        with word_file.open_binary() as f1:
            pdf_file = vkt.convert_word_to_pdf(f1)

        return vkt.DownloadResult(pdf_file, f"{params.project_title} thrust_restraint_calculation.pdf")

    def download_word_document(self, params, **kwargs):
        """Generate and return the Word report as a VIKTOR download.

        Purpose
        -------
        This method creates the project Word document and exposes it as a downloadable asset
        without converting it to PDF first.

        Data flow
        ---------
        The method delegates to ``generate_word_document`` and then wraps the resulting Word
        file in a ``vkt.DownloadResult`` for download from the VIKTOR UI.

        Returns
        -------
        vkt.DownloadResult
            A downloadable Word document generated from the Arcadis template.
        """

        word_file = self.generate_word_document(params, **kwargs)

        return vkt.DownloadResult(word_file, f"{params.project_title} thrust_restraint_calculation.docx")

    @vkt.PDFView("PDF viewer", duration_guess=5)
    def pdf_view(self, params, **kwargs):
        """Render the generated report as a PDF preview in the VIKTOR UI.

        Purpose
        -------
        This method is exposed as a PDF view so users can preview the report inside VIKTOR.

        Data flow
        ---------
        The method generates the Word report and then converts it to PDF in memory before
        returning a ``vkt.PDFResult``.

        Returns
        -------
        vkt.PDFResult
            A PDF preview object for the generated report.

        Notes
        -----
        The distinction in this application is that ``DownloadResult`` is used for file
        downloads, while ``PDFResult`` is used for in-UI preview rendering.
        """

        word_file = self.generate_word_document(params, **kwargs)

        with word_file.open_binary() as f1:
            pdf_file = vkt.convert_word_to_pdf(f1)
            return vkt.PDFResult(file=pdf_file)