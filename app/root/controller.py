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


class Controller(vkt.Controller):
    label = "Root"
    children = ["Project"]  # Allow MyFolder entities at top level
    show_children_as = "Cards"

class ProjectParametrization(vkt.Parametrization):
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

class Project(vkt.Controller):
    label = "Project"
    children = ["ThrustBlock", "AnchorBlock"]
    show_children_as = "Table"
    parametrization = ProjectParametrization #type: ignore

    def get_version_history_table_data(self, params, **kwargs):
        """
        Helper method to generate version history table data.
        Returns headers and rows that can be used in both TableView and Word export.
        
        Returns:
            list[list[Any]]: table_data where table_data is a list of row lists
        """
       
        # Build table rows from version history
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
    
    def get_thrust_block_children(self, params, **kwargs) -> list[vkt.api_v1.Entity]:
        # Collect child entity params
        entity_id = kwargs['entity_id']
        
        # Access child entities using the API
        # This gets all children of the current entity
        children = vkt.api_v1.API().get_entity_children(entity_id) 
        
        # Filter by entity type
        thrust_blocks = [child for child in children if child.entity_type.name == 'ThrustBlock']

        return thrust_blocks
    
    def get_anchor_block_children(self, params, **kwargs) -> list[vkt.api_v1.Entity]:
        # Collect child entity params
        entity_id = kwargs['entity_id']
        
        # Access child entities using the API
        # This gets all children of the current entity
        children = vkt.api_v1.API().get_entity_children(entity_id) 
        
        # Filter by entity type
        anchor_blocks = [child for child in children if child.entity_type.name == 'AnchorBlock']

        return anchor_blocks
    
    def export_to_excel(self, params, **kwargs):
        """Export the dimensions to an Excel file."""
        # Create a new workbook and select the active sheet
        template_path =  Path(__file__).parent / "files" / "arcadis_calculation_sheet_template.xlsx"
        wb = load_workbook(template_path)

        thrust_blocks = self.get_thrust_block_children(params, **kwargs)
        for child in thrust_blocks:
            child_params = child.last_saved_params  # Get the saved parameters
            ws = wb.copy_worksheet(wb["Thrust Block 1"])
            ws.title = f"{child.name}"

            fitting_type = fitting_from_params(params=child_params)
            for i, entry in enumerate(fitting_type.fitting_workflow_res):
                num = 7
                # Add the dimension data
                row = num + i
                ws[f"A{row}"] = entry["label"]
                ws[f"B{row}"] = entry["formula_xls"]
                ws[f"F{row}"] = entry["output"]
                ws[f"I{row}"] = entry["si_unit"]
                ws[f"J{row}"] = entry["reference"]
        
        wb.remove(wb["Thrust Block 1"])
        # Save the workbook to a file
        from io import BytesIO
        buffer = BytesIO()
        wb.save(buffer)
        buffer.seek(0)

        excel_file = vkt.File.from_data(buffer.read())
        
        return vkt.DownloadResult(excel_file, f'{params.project_title}_thrust_restraint_calculation.xlsx')
    
    def block_safety_table(self, params, **kwargs):
        thrust_blocks = self.get_thrust_block_children(params, **kwargs)
        anchor_blocks = self.get_anchor_block_children(params, **kwargs)

        data_rows = []
        for child in thrust_blocks:
            child_params = child.last_saved_params  # Get the saved parameters

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
            # Access specific fields from the child's parametrization
            row = {
                "name": child.name,
                "fitting_type": child_params.fitting_section.fitting_type,
                "thrust_pass_through_check": "Pass" if fitting_type.thrust_pass_through_check else "Fail", 
                "overturning_moment_check": overturning_moment_check,
                "vertical_thrust_check": vertical_thrust,
                "uplift_check": uplift_test,
                "chainage": child_params.fitting_section.chainage
                # Add more fields as needed
            }
            data_rows.append(row)

        for child in anchor_blocks:
            child_params = child.last_saved_params  # Get the saved parameters
            metallic_flange = build_metallic_flange(child_params)
            row = {
                "name": child.name,
                "fitting_type": child_params.pipe_section.pipe_material,
                "thrust_pass_through_check": "Pass" if metallic_flange.thrust_pass_through_check else "Fail", 
                "overturning_moment_check": "Pass" if metallic_flange.overturning_check else "Fail",
                "vertical_thrust_check": "N/A",
                "uplift_check": "N/A",
                "chainage": child_params.pipe_section.chainage
                # Add more fields as needed
            }
            data_rows.append(row)

        return data_rows
    
    def get_block_workflows(self, params, **kwargs):
        thrust_blocks = self.get_thrust_block_children(params, **kwargs)
        anchor_blocks = self.get_anchor_block_children(params, **kwargs)

        appendices = []
        for child in thrust_blocks:
            child_params = child.last_saved_params  # Get the saved parameters

            fitting_type = fitting_from_params(params=child_params)
            table4 = []
            for row in fitting_type.fitting_workflow_res:
                table4.append({
                    "label": row['label'],
                    "formula": row['formula_html'],
                    "reference": row['reference'],
                })

            appendices.append({
                "title": f"{child_params.fitting_section.fitting_type} Calculation",
                "table4": table4 #type: ignore
            })

        for child in anchor_blocks:
            child_params = child.last_saved_params  # Get the saved parameters

            fitting_type = build_metallic_flange(child_params)
            table4 = []
            for row in fitting_type.fitting_workflow_res:
                table4.append({
                    "label": row['label'],
                    "formula": row['formula_html'],
                    "reference": row['reference'],
                })

            appendices.append({
                "title": f"{child_params.pipe_section.pipe_material} Contraction Calculation",
                "table4": table4 #type: ignore
            })
            
        return appendices
    
    def get_thrust_block_params(self, params, **kwargs):
        """
        Helper method to generate child entity thrust block parameters.
        Returns headers and rows that can be used in both TableView and Word export.
        
        Returns:
            list[list[Any]]: table_data where data_rows is a list of row lists
        """
        
        # Filter by entity type
        thrust_blocks = self.get_thrust_block_children(params, **kwargs)
        anchor_blocks = self.get_anchor_block_children(params, **kwargs)

        num = 1
        
        # Access parameters of each child
        data_rows = []
        for child in thrust_blocks:
            child_params = child.last_saved_params  # Get the saved parameters
            
            # Access specific fields from the child's parametrization
            row = [
                child_params.fitting_section.chainage,
                child_params.fitting_section.fitting_type,
                child_params.block_section.height,
                child_params.block_section.width,       
                child_params.block_section.length,
                child_params.block_section.depth,
                num
                # Add more fields as needed
            ]
            data_rows.append(row)
            num += 1

        for child in anchor_blocks:
            child_params = child.last_saved_params

                        # Access specific fields from the child's parametrization
            row = [
                child_params.pipe_section.chainage,
                child_params.pipe_section.pipe_material,
                child_params.block_section.height,
                child_params.block_section.width,       
                child_params.block_section.length,
                child_params.block_section.depth,
                num
                # Add more fields as needed
            ]
            data_rows.append(row)
            num += 1
        
        return data_rows

    @vkt.TableView("Version History")
    def view_version_history(self, params, **kwargs):
        """
        Display the check, review, approve version history in a table.
        """
        # Define table headers
        headers = [
            vkt.TableHeader("Issue", align="center"),
            vkt.TableHeader("Revision No.", align="left"),
            vkt.TableHeader("Date Issued", align="center"),
            vkt.TableHeader("Checked By", align="left"),
            vkt.TableHeader("Reviewed By", align="left"),
            vkt.TableHeader("Approved By", align="left"),
            vkt.TableHeader("Status", align="center"),
        ]
        
        # Build table rows from version history
        table_data = []
        for version in params.version_history:
            # Apply color coding based on status
            status_cell = vkt.TableCell(
                version.status,
                background_color=vkt.Color(144, 238, 144) if version.status == "Approved" else
                                vkt.Color(255, 255, 153) if version.status == "Reviewed" else
                                vkt.Color(173, 216, 230) if version.status == "Checked" else
                                vkt.Color(255, 182, 193) if version.status == "Rejected" else
                                vkt.Color(211, 211, 211)  # Draft
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
        # Get the current entity (the Root/parent entity)
        entity_id = kwargs['entity_id']
        
        # Access child entities using the API
        children = vkt.api_v1.API().get_entity_children(entity_id) 
        
        # Filter by entity type
        thrust_blocks = [child for child in children if child.entity_type.name == 'ThrustBlock']
        anchor_blocks = [child for child in children if child.entity_type.name == 'AnchorBlock'] 
        
        # Combine both block types for iteration
        all_blocks = thrust_blocks + anchor_blocks
        
        data_rows = []
        for child in all_blocks:
            child_params = child.last_saved_params
            
            # Determine block type dynamically
            block_type = 'Thrust Block' if child.entity_type.name == 'ThrustBlock' else 'AnchorBlock'
            
            row = {
                'Name': child.name,
                'Type': block_type,
                'Height (m)': child_params.block_section.height,
                'Length (m)': child_params.block_section.length,
                'Width (m)': child_params.block_section.width,
            }
            data_rows.append(row)
        
        df = pd.DataFrame(data_rows)
        return vkt.TableResult(df)
    
    @vkt.TableView("Block Checks")
    def thrust_table(self, params, **kwargs):
        # Get the current entity (the Root/parent entity)
        entity_id = kwargs['entity_id']
        
        # Access child entities using the API
        # This gets all children of the current entity
        children = vkt.api_v1.API().get_entity_children(entity_id) 
        
        # Filter by entity type
        thrust_blocks = [child for child in children if child.entity_type.name == 'ThrustBlock']
        anchor_blocks = [child for child in children if child.entity_type.name == 'AnchorBlock'] 
        
        # Access parameters of each child
        data_rows = []
        for child in thrust_blocks:
            child_params = child.last_saved_params  # Get the saved parameters

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
            # Access specific fields from the child's parametrization
            row = {
                "Name": child.name,
                "Fitting Type": child_params.fitting_section.fitting_type,
                "Thrust Pass Through Check": "Pass" if fitting_type.thrust_pass_through_check else "Fail", 
                "Overturning Moment Check": overturning_moment_check,
                "Vertical Thrust": vertical_thrust,
                "Uplift Check": uplift_test,
                # Add more fields as needed
            }
            data_rows.append(row)
        
        # Convert to DataFrame for export
        df = pd.DataFrame(data_rows)
        return vkt.TableResult(df)
    
    def generate_word_document(self, params, **kwargs):
        # Create emtpy components list to be filled later
        components = []

        # Fill components list with data
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


        # thrust block safety check params
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

        # thrust block dimension entry
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

        # Get path to template and render word file
        template_path = Path(__file__).parent / "files" / "arcadis_template.docx"
        with open(template_path, 'rb') as template:
            word_file = vkt.word.render_word_file(template, components)

        return word_file
    
    def download_pdf_document(self, params, **kwargs):
        word_file = self.generate_word_document(params, **kwargs)

        with word_file.open_binary() as f1:
            pdf_file = vkt.convert_word_to_pdf(f1)

        return vkt.DownloadResult(pdf_file, f'{params.project_title} thrust_restraint_calculation.pdf')
    
    def download_word_document(self, params, **kwargs):
        word_file = self.generate_word_document(params, **kwargs)


        return vkt.DownloadResult(word_file, f'{params.project_title} thrust_restraint_calculation.docx')
    
    @vkt.PDFView("PDF viewer", duration_guess=5)
    def pdf_view(self, params, **kwargs):
        word_file = self.generate_word_document(params, **kwargs)

        with word_file.open_binary() as f1:
            pdf_file = vkt.convert_word_to_pdf(f1)

            return vkt.PDFResult(file=pdf_file)