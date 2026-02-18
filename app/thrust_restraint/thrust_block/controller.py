import viktor as vkt
from app.civeng1.hydraulics import fittings
from app.civeng1.soils.soil_mechanics import SoilType, SoilConsistency, SoilCategory, Soil, SOIL_PROPERTIES, WaterCondition
from app.civeng1.structures.concrete import create_thrust_block, ThrustBlock
import base64
from pathlib import Path
from openpyxl import load_workbook
from openpyxl.styles import Font, Alignment
from pathlib import Path

#--- utils ---
fitting_list = fittings.FITTING_LABELS

soil_list = [st.label for st in SoilType]
soil_category = [sc for sc in SoilCategory]
coarse_consistency = [cc.label for cc in SoilConsistency if cc.category ==  SoilCategory.COARSE]
fine_consistency = [fc.label for fc in SoilConsistency if fc.category ==  SoilCategory.FINE]

#--- refactor below to civeng module ---
def get_soil_type_by_label(label: str) -> SoilType:
    """
    Args:
        label (str): The label to look up (e.g., "Very Loose").

    Returns:
        SoilConsistency: The value associated with the matching SoilConsistency enum member.

    Raises:
        ValueError: If the label does not match any SoilConsistency member.
    """
    for soil_type in SoilType:
        if soil_type.label.lower() == label.lower():
            return soil_type
    raise ValueError(f"No SoilConsistency found for label: {label}")

def get_soil_category_by_label(label: str) -> SoilCategory:
    """
    Returns the SoilCategory for a given soil label.

    Args:
        label (str): Soil type label (e.g., "Gravel").

    Returns:
        SoilCategory: The corresponding category for the label.

    Raises:
        ValueError: If the label does not match any SoilType.
    """
    for soil_type in SoilType:
        if soil_type.label.lower() == label.lower():
            return soil_type.category
    raise ValueError(f"No SoilType found for label: {label}")

def get_soil_consistency_value_by_label(label: str) -> SoilConsistency:
    """
    Args:
        label (str): The label to look up (e.g., "Very Loose").

    Returns:
        SoilConsistency: The value associated with the matching SoilConsistency enum member.

    Raises:
        ValueError: If the label does not match any SoilConsistency member.
    """
    for consistency in SoilConsistency:
        if consistency.label.lower() == label.lower():
            return consistency
    raise ValueError(f"No SoilConsistency found for label: {label}")

def get_water_condition(condition: str) -> WaterCondition:
    for water_condition in WaterCondition:
        if water_condition.value.lower() == condition.lower():
            return water_condition
    raise ValueError(f"No WaterCondition found for label: {condition}")

def max_soil_params(params, **kwargs):
    soil_category = get_soil_category_by_label(params.soil_section.soil_type)
    if soil_category == SoilCategory.COARSE:
        soil_consistency = get_soil_consistency_value_by_label(params.soil_section.coarse_soil_consistency)
        coarse_angle = SOIL_PROPERTIES[soil_category][soil_consistency]["friction_angle"][1]
        return coarse_angle
    elif soil_category == SoilCategory.FINE:
        soil_consistency = get_soil_consistency_value_by_label(params.soil_section.fine_soil_consistency)
        fine_strength = SOIL_PROPERTIES[soil_category][soil_consistency]["undrained_shear_strength"][1]
        return fine_strength
    
def min_soil_params(params, **kwargs):
    soil_category = get_soil_category_by_label(params.soil_section.soil_type)
    if soil_category == SoilCategory.COARSE:
        soil_consistency = get_soil_consistency_value_by_label(params.soil_section.coarse_soil_consistency)
        return SOIL_PROPERTIES[soil_category][soil_consistency]["friction_angle"][0]
    elif soil_category == SoilCategory.FINE:
        soil_consistency = get_soil_consistency_value_by_label(params.soil_section.fine_soil_consistency)
        return SOIL_PROPERTIES[soil_category][soil_consistency]["undrained_shear_strength"][0]


def max_passive_soil_displacement_factor(params, **kwargs):
    soil_category = get_soil_category_by_label(params.soil_section.soil_type)
    if soil_category == SoilCategory.COARSE:
        soil_consistency = get_soil_consistency_value_by_label(params.soil_section.coarse_soil_consistency)
        coarse_angle = SOIL_PROPERTIES[soil_category][soil_consistency]["soil_passive_resistance_factor"][1]
        return coarse_angle
    elif soil_category == SoilCategory.FINE:
        soil_consistency = get_soil_consistency_value_by_label(params.soil_section.fine_soil_consistency)
        fine_strength = SOIL_PROPERTIES[soil_category][soil_consistency]["soil_passive_resistance_factor"][1]
        return fine_strength
    
def min_passive_soil_displacement_factor(params, **kwargs):
    soil_category = get_soil_category_by_label(params.soil_section.soil_type)
    if soil_category == SoilCategory.COARSE:
        soil_consistency = get_soil_consistency_value_by_label(params.soil_section.coarse_soil_consistency)
        coarse_angle = SOIL_PROPERTIES[soil_category][soil_consistency]["soil_sliding_resistance_factor"][0]
        return coarse_angle
    elif soil_category == SoilCategory.FINE:
        soil_consistency = get_soil_consistency_value_by_label(params.soil_section.fine_soil_consistency)
        fine_strength = SOIL_PROPERTIES[soil_category][soil_consistency]["soil_sliding_resistance_factor"][0]
        return fine_strength
    
def max_active_soil_displacement_factor(params, **kwargs):
    soil_category = get_soil_category_by_label(params.soil_section.soil_type)
    if soil_category == SoilCategory.COARSE:
        soil_consistency = get_soil_consistency_value_by_label(params.soil_section.coarse_soil_consistency)
        coarse_angle = SOIL_PROPERTIES[soil_category][soil_consistency]["soil_passive_resistance_factor"][1]
        return coarse_angle
    elif soil_category == SoilCategory.FINE:
        soil_consistency = get_soil_consistency_value_by_label(params.soil_section.fine_soil_consistency)
        fine_strength = SOIL_PROPERTIES[soil_category][soil_consistency]["soil_passive_resistance_factor"][1]
        return fine_strength
    
def min_active_soil_displacement_factor(params, **kwargs):
    soil_category = get_soil_category_by_label(params.soil_section.soil_type)
    if soil_category == SoilCategory.COARSE:
        soil_consistency = get_soil_consistency_value_by_label(params.soil_section.coarse_soil_consistency)
        coarse_angle = SOIL_PROPERTIES[soil_category][soil_consistency]["soil_sliding_resistance_factor"][0]
        return coarse_angle
    elif soil_category == SoilCategory.FINE:
        soil_consistency = get_soil_consistency_value_by_label(params.soil_section.fine_soil_consistency)
        fine_strength = SOIL_PROPERTIES[soil_category][soil_consistency]["soil_sliding_resistance_factor"][0]
        return fine_strength
    
#--- end refactor ---
    
#--- visibility conditions ---

pipe_outside_param = vkt.Or(
    vkt.IsEqual(vkt.Lookup("fitting_section.fitting_type"), "Horizontal Bend"),
    vkt.IsEqual(vkt.Lookup("fitting_section.fitting_type"), "Vertical Downturn Bend"),
    vkt.IsEqual(vkt.Lookup("fitting_section.fitting_type"), "Vertical Upturn Bend"),
    vkt.IsEqual(vkt.Lookup("fitting_section.fitting_type"), "Blank End"),
    vkt.IsEqual(vkt.Lookup("fitting_section.fitting_type"), "Closed Valve"),
)
bend_direction = vkt.Or(
    vkt.IsEqual(vkt.Lookup("fitting_section.fitting_type"), "Vertical Bend"),
)
pipe_outside_larger_end = vkt.IsEqual(vkt.Lookup("fitting_section.fitting_type"), "Taper Thrust")
pipe_outside_smaller_end = vkt.IsEqual(vkt.Lookup("fitting_section.fitting_type"), "Taper Thrust")
pipe_diameter_main = vkt.Or(
    vkt.IsEqual(vkt.Lookup("fitting_section.fitting_type"), "Tee"),
    vkt.IsEqual(vkt.Lookup("fitting_section.fitting_type"), "Angle Branch"),
)
pipe_diameter_branch = vkt.Or(
    vkt.IsEqual(vkt.Lookup("fitting_section.fitting_type"), "Tee"),
    vkt.IsEqual(vkt.Lookup("fitting_section.fitting_type"), "Angle Branch"),
)
bend_angle = vkt.Or(
    vkt.IsEqual(vkt.Lookup("fitting_section.fitting_type"), "Horizontal Bend"),
    vkt.IsEqual(vkt.Lookup("fitting_section.fitting_type"), "Vertical Downturn Bend"),
    vkt.IsEqual(vkt.Lookup("fitting_section.fitting_type"), "Vertical Upturn Bend"),
    vkt.IsEqual(vkt.Lookup("fitting_section.fitting_type"), "Angle Branch")
)

coarse_soil_consistency = vkt.Or(
    vkt.IsEqual(vkt.Lookup("soil_section.soil_type"), "Gravel"),
    vkt.IsEqual(vkt.Lookup("soil_section.soil_type"), "Sand"),
)
fine_soil_consistency = vkt.Or(
    vkt.IsEqual(vkt.Lookup("soil_section.soil_type"), "Silt"),
    vkt.IsEqual(vkt.Lookup("soil_section.soil_type"), "Clay"),
)

undrained_shear_strength = vkt.Or(
    vkt.IsEqual(vkt.Lookup("soil_section.soil_type"), "Silt"),
    vkt.IsEqual(vkt.Lookup("soil_section.soil_type"), "Clay"),
)

friction_angle = vkt.Or(
    vkt.IsEqual(vkt.Lookup("soil_section.soil_type"), "Gravel"),
    vkt.IsEqual(vkt.Lookup("soil_section.soil_type"), "Sand"),
)

ground_water_level = vkt.IsEqual(vkt.Lookup("soil_section.ground_condition"), "Below Water")

# taper thrust arrangement visibility
taper_thrust_arrangement_1 = vkt.And(
    vkt.IsEqual(vkt.Lookup("fitting_section.fitting_type"), "Taper Thrust"),
    vkt.IsEqual(vkt.Lookup("block_section.arrangement"), "1"),
)
taper_thrust_arrangement_2 = vkt.And(
    vkt.IsEqual(vkt.Lookup("fitting_section.fitting_type"), "Taper Thrust"),
    vkt.IsEqual(vkt.Lookup("block_section.arrangement"), "2"),
)
# blank end arrangement visibility
blank_end_arrangement_1 = vkt.And(
    vkt.IsEqual(vkt.Lookup("fitting_section.fitting_type"), "Blank End"),
    vkt.Or(vkt.IsEqual(vkt.Lookup("block_section.arrangement"), "1"),
           vkt.IsEqual(vkt.Lookup("block_section.arrangement"), "2"),
    )
)
# closed valve arrangement visibility
closed_valve_arrangement_1 = vkt.And(
    vkt.IsEqual(vkt.Lookup("fitting_section.fitting_type"), "Closed Valve"),
    vkt.IsEqual(vkt.Lookup("block_section.arrangement"), "1"),
)
closed_valve_arrangement_2 = vkt.And(
    vkt.IsEqual(vkt.Lookup("fitting_section.fitting_type"), "Closed Valve"),
    vkt.IsEqual(vkt.Lookup("block_section.arrangement"), "2"),
)
# tee arrangement visibility
tee_arrangement_1 = vkt.And(
    vkt.IsEqual(vkt.Lookup("fitting_section.fitting_type"), "Tee"),
    vkt.IsEqual(vkt.Lookup("block_section.arrangement"), "1"),
)
tee_arrangement_2 = vkt.And(
    vkt.IsEqual(vkt.Lookup("fitting_section.fitting_type"), "Tee"),
    vkt.IsEqual(vkt.Lookup("block_section.arrangement"), "2"),
)
# vertical downturn arrangement visibility
vertical_downturn_arrangement_1 = vkt.And(
    vkt.IsEqual(vkt.Lookup("fitting_section.fitting_type"), "Vertical Downturn Bend"),
    vkt.Or(vkt.IsEqual(vkt.Lookup("block_section.arrangement"), "1"),
           vkt.IsEqual(vkt.Lookup("block_section.arrangement"), "2"),
    )
)
# vertical upturn arrangement visibility
vertical_upturn_arrangement_1 = vkt.And(
    vkt.IsEqual(vkt.Lookup("fitting_section.fitting_type"), "Vertical Upturn Bend"),
    vkt.IsEqual(vkt.Lookup("block_section.arrangement"), "1"),
)
vertical_upturn_arrangement_2 = vkt.And(
    vkt.IsEqual(vkt.Lookup("fitting_section.fitting_type"), "Vertical Upturn Bend"),
    vkt.IsEqual(vkt.Lookup("block_section.arrangement"), "2"),
)
# horizontal bend arrangement visibility
horizontal_bend_arrangement_1 = vkt.And(
    vkt.IsEqual(vkt.Lookup("fitting_section.fitting_type"), "Horizontal Bend"),
    vkt.IsEqual(vkt.Lookup("block_section.arrangement"), "1"),
)
horizontal_bend_arrangement_2 = vkt.And(
    vkt.IsEqual(vkt.Lookup("fitting_section.fitting_type"), "Horizontal Bend"),
    vkt.IsEqual(vkt.Lookup("block_section.arrangement"), "2"),
)



#--- ui logic ---

class Parametrization(vkt.Parametrization):
    # fitting logic
    fitting_section = vkt.Section('Fitting Type Parameters', initially_expanded=True)
    fitting_section.fitting_type = vkt.OptionField('Select fitting type', flex=35, options=fitting_list, default="Taper Thrust") #type: ignore
    fitting_section.crown_depth = vkt.NumberField('Depth to Pipe Crown (m)', flex=30, default=1) #type: ignore
    fitting_section.maximum_design_pressure = vkt.NumberField('Maximum Design Pressure (kPa)', flex=35, default=1200) #type: ignore
    fitting_section.lb_2 = vkt.LineBreak()
    fitting_section.outside_diameter = vkt.NumberField("Pipe outside diameter (m)", flex=35, visible=pipe_outside_param, default=0.8)
    fitting_section.outside_diameter_large = vkt.NumberField("Pipe outside diameter – larger end (m)", flex=40, visible=pipe_outside_larger_end, default=0.63)
    fitting_section.outside_diameter_small = vkt.NumberField("Pipe outside diameter – smaller end (m)", flex=40, visible=pipe_outside_smaller_end, default=0.43)
    fitting_section.outside_diameter_main = vkt.NumberField("Pipe outside diameter – main (m)", flex=40, visible=pipe_diameter_main, default=0.43)
    fitting_section.outside_diameter_branch = vkt.NumberField("Branch Pipe outside diameter (m)", flex=40, visible=pipe_diameter_branch, default=0.63)
    fitting_section.angle = vkt.NumberField("Bend Radius (°)", flex=20, visible=bend_angle, default=45)
    fitting_section.turn_direction = vkt.OptionField("Turn Direction", options=["upturn", "downturn"], flex=20, visible=bend_direction, default="downturn")

    # soil params 1
    soil_section = vkt.Section("Soil Type Parameters", initially_expanded=True)
    soil_section.soil_type = vkt.OptionField("Soil Type", flex=18, options=soil_list, default="Gravel") #type: ignore
    soil_section.coarse_soil_consistency = vkt.OptionField("Soil Consistency", flex=25, options=coarse_consistency, visible=coarse_soil_consistency, default="Medium Dense") #type: ignore
    soil_section.fine_soil_consistency = vkt.OptionField("Soil Consistency", flex=25, options=fine_consistency, visible=fine_soil_consistency, default="Firm") #type: ignore
    soil_section.friction_angle = vkt.NumberField("Friction Angle", flex=25, visible=friction_angle, default=33, step=0.1, max=max_soil_params, min=min_soil_params)
    soil_section.undrained_shear_strength = vkt.NumberField("Undrained Shear Strength", flex=25, visible=undrained_shear_strength, default=50, step=0.1, max=max_soil_params, min=min_soil_params)
    soil_section.lb = vkt.LineBreak()
    soil_section.soil_passive_factor = vkt.NumberField("DFp", flex=10, default=3, max=max_passive_soil_displacement_factor, min=min_passive_soil_displacement_factor, description="Passive resistance displacement limitation factor - Table 3.6")
    soil_section.soil_sliding_factor = vkt.NumberField("DFs", flex=10, default=2.25, max=max_active_soil_displacement_factor, min=min_active_soil_displacement_factor, description="Sliding resistance displacement limitation factor - Table 3.6")
    # soil params 2
    soil_section.lb_2 = vkt.LineBreak()
    soil_section.ground_condition = vkt.OptionField("Ground Condition", flex=18, options=["Above Water", "Below Water"], default="Below Water") #type: ignore
    soil_section.groundwater_level = vkt.NumberField("Ground level depth (m)", flex=25, visible=ground_water_level, default=0.8)
    
    # thrust block geometry
    block_section = vkt.Section("Thrust Block Parameters", initially_expanded=True)
    ## taper thrust arrangement images
    block_section.taper_thrust_plan_1 = vkt.Image(path="taper_thrust_plan_1.png", align="left", flex=40, visible=taper_thrust_arrangement_1)
    block_section.taper_thrust_section_1 = vkt.Image(path="taper_thrust_section_1.png", align="right", flex=40, visible=taper_thrust_arrangement_1)
    block_section.taper_thrust_plan_2 = vkt.Image(path="taper_thrust_plan_2.png", align="left", flex=40, visible=taper_thrust_arrangement_2)
    block_section.taper_thrust_section_2 = vkt.Image(path="taper_thrust_section_2.png", align="left", flex=40, visible=taper_thrust_arrangement_2)
    ## blank end arrangement images
    block_section.blank_end_plan_1 = vkt.Image(path="blank_end_plan_1.png", align="left", flex=40, visible=blank_end_arrangement_1)
    block_section.blank_end_section_1 = vkt.Image(path="blank_end_section_1.png", align="right", flex=40, visible=blank_end_arrangement_1)
    # closed valve block arrangement
    block_section.closed_valve_section_1 = vkt.Image(path="closed_valve_section_1.png", align="right", flex=40, visible=closed_valve_arrangement_1)
    block_section.closed_valve_section_2 = vkt.Image(path="closed_valve_section_2.png", align="right", flex=40, visible=closed_valve_arrangement_2)
    # tee arrangement images
    block_section.tee_plan_1 = vkt.Image(path="tee_plan_1.png", align="left", flex=40, visible=tee_arrangement_1)
    block_section.tee_section_1 = vkt.Image(path="tee_section_1.png", align="right", flex=40, visible=tee_arrangement_1)
    block_section.tee_plan_2 = vkt.Image(path="tee_plan_2.png", align="left", flex=40, visible=tee_arrangement_2)
    block_section.tee_section_2 = vkt.Image(path="tee_section_2.png", align="left", flex=40, visible=tee_arrangement_2)
    # vertical downturn images
    block_section.vertical_downturn_bend_section_1 = vkt.Image(path="vertical_downturn_bend_section_1.png", align="right", flex=40, visible=vertical_downturn_arrangement_1)
    # vertical upturn images
    block_section.vertical_upturn_bend_section_1 = vkt.Image(path="vertical_upturn_bend_section_1.png", align="right", flex=40, visible=vertical_upturn_arrangement_1)
    block_section.vertical_upturn_bend_section_2 = vkt.Image(path="vertical_upturn_bend_section_2.png", align="right", flex=40, visible=vertical_upturn_arrangement_2)
    # horizontal bend images
    block_section.horizontal_bend_plan_1 = vkt.Image(path="horizontal_bend_plan_1.png", align="left", flex=40, visible=horizontal_bend_arrangement_1)
    block_section.horizontal_bend_section_1 = vkt.Image(path="horizontal_bend_section_1.png", align="right", flex=40, visible=horizontal_bend_arrangement_1)
    block_section.horizontal_bend_plan_2 = vkt.Image(path="horizontal_bend_plan_2.png", align="left", flex=40, visible=horizontal_bend_arrangement_2)
    block_section.horizontal_bend_section_2 = vkt.Image(path="horizontal_bend_section_2.png", align="left", flex=40, visible=horizontal_bend_arrangement_2)
    block_section.lb = vkt.LineBreak()
    block_section.height = vkt.NumberField("Thrust Block Height (H)", flex=25, default=1.8, step=0.1)
    block_section.width = vkt.NumberField("Thrust Block Width (W)", flex=25, default=3.5, step=0.1)
    block_section.length = vkt.NumberField("Thrust Block Length (L)", flex=25, default=2.5, step=0.1)
    block_section.depth = vkt.NumberField("Thrust Block Depth (Zb)", flex=25, default=2.3, step=0.1)
    block_section.arrangement = vkt.OptionField("Block Arrangement", flex=20, options=["1", "2"], default="1") #type: ignore
    block_section.lb_2 = vkt.LineBreak()
    block_section.download_pdf = vkt.DownloadButton("Export to Excel", method="export_to_excel", flex=24)

class ThrustBlockController(vkt.Controller):
    parametrization = Parametrization(width=40)

    def render_workflow_html(self, params):
        fitting_type = fittings.fitting_from_params(params=params)
        dims=   f"""<div class="label">Pressure fixed by the designer </div>
            <div class="result">P = <b>{params.fitting_section.maximum_design_pressure} kN/m2</b></div>
            <div class="reference">Section 2.3</div>
            <div class="label">Height</div>
            <div class="result">H = {params.block_section.height} m</div>
            <div class="reference"> - </div>
            <div class="label">Width </div>
            <div class="result">W = {params.block_section.width} m</div>
            <div class="reference"> - </div>
            <div class="label">Length </div>
            <div class="result">L = {params.block_section.length} m</div>
            <div class="reference"> - </div>
            """
        rows = []
        for item in fitting_type.fitting_workflow_res:
            row_html = f"""
            <div class="label">{item['label']}</div>
            <div class="result">{item['formula_html']}</div>
            <div class ="reference">{(item['reference'])}</div>
            """
            rows.append(row_html)
        return dims + "\n".join(rows)
    
    def export_to_excel(self, params, **kwargs):
        """Export the dimensions to an Excel file."""
        # Create a new workbook and select the active sheet
        template_path =  Path(__file__).parent / 'arcadis_calculation_sheet_template.xlsx'
        wb = load_workbook(template_path)
        ws = wb["Thrust Block 1"]

        thrust_block = fittings.fitting_from_params(params=params)

        for i, entry in enumerate(thrust_block.fitting_workflow_res):

            num = 7
            # Add the dimension data
            row = num + i
            ws[f"A{row}"] = entry["label"]
            ws[f"B{row}"] = entry["formula_xls"]
            ws[f"F{row}"] = entry["output"]
            ws[f"I{row}"] = entry["si_unit"]
            ws[f"J{row}"] = entry["reference"]
        
        # Save the workbook to a file
        from io import BytesIO
        buffer = BytesIO()
        wb.save(buffer)
        buffer.seek(0)

        excel_file = vkt.File.from_data(buffer.read())
        
        return vkt.DownloadResult(excel_file, 'dimensions.xlsx')
    
    @vkt.WebView("Thrust Block Analysis Report")
    def analyze_tb(self, params, **kwargs):

        image_path = Path(__file__).parent.parent / "assets" / "Arcadis_logo.png"
        with open(image_path, "rb") as img_file:
            img_base64 = base64.b64encode(img_file.read()).decode()

        """Generates a thrust stability check HTML report."""
        html = f"""
        <!DOCTYPE html>
        <html lang="en">
        <html>
        <head>
        <meta charset="UTF-8">
        <style>
            body {{
                font-family: Arial, sans-serif;
                background-color: #FFFFFF;
                margin: 0;
                padding: 20px;
            }}

            /* Full-width header with underline */
            .header-fullwidth {{
                width: 100%;
                border-bottom: 4px solid #FF6600; /* full-width underline */
                padding-bottom: 10px;
                box-sizing: border-box;
            }}
            .header-inner {{
                display: flex;
                justify-content: space-between;
                border-bottom: 3px solid #FF6600;
                align-items: center;
                gap: 16px;
                width: 100%;
            }}

            /* Title (no border here — wrapper provides the underline) */
            h1 {{
                color: #FF6600;
                font-size: 36px;
                font-weight: bold;
                margin: 0;
                padding: 0;
            }}

            h2 {{
                color: #FF6600;
                font-size: 16px;
                font-weight: bold;
                border-bottom: 1px solid #FF6600;
                padding-bottom: 10px;
                margin-top: 20px;
                margin-bottom: 0;
            }}

            .pb-12 {{ padding-bottom: 12px; }}

            .row {{
                display: grid;
                grid-template-columns: auto auto auto;
                align-items: baseline;
                gap: 12px;
            }}
            .label     {{ justify-self: start; }}
            .result    {{ justify-self: start; text-align: left; }}
            .reference {{ justify-self: end; text-align: right; }}

            .image-container {{
                text-align: center;
                margin: 20px 0;
            }}
            .image-container img {{
                max-width: 100%;
                height: auto;
                border: 1px solid #ddd;
                border-radius: 4px;
                padding: 5px;
            }}

            /* logo sizing — responsive */
            .logo {{
                max-width: 200px;
                height: auto;
            }}
            @media (max-width: 600px) {{
                .logo {{ max-width: 120px; }}
                 h1 {{ font-size: 28px; }}
            }}
        </style>
        </head>
        <body>
        <div class="header-inner">
            <h1>Thrust block sizing - CLOSED BETA</h1>
            <img src="data:image/png;base64,{img_base64}" alt="Arcadis Logo" class="logo">
        </div>
            <h2> {params.fitting_section.fitting_type} block</h2>
            <br>
            <div class="row">
                {self.render_workflow_html(params=params)}
            </div>
        </body>
        </html>
        """
        
        return vkt.WebResult(html=html)

    @vkt.GeometryView("3D Arrangement (To be implemented)", duration_guess=1, x_axis_to_right=True)
    def visualize_thrust_block(self, params, **kwargs):
        """Generate 3D visualization of the concrete thrust block."""
        # Extract dimensions from user inputs
        height = params.block_section.block_height
        length = params.block_section.block_length
        width = params.block_section.block_width
        
        # Create the thrust block as a rectangular extrusion
        # Define the base point at origin
        base_point = vkt.Point(0, 0, 0)
        
        # Create a vertical line representing the height of the block
        vertical_line = vkt.Line(base_point, vkt.Point(0, 0, height))
        
        # Create concrete material with typical gray color
        concrete_material = vkt.Material('Concrete', color=vkt.Color(169, 169, 169))
        
        # Create the rectangular thrust block using RectangularExtrusion
        thrust_block = vkt.RectangularExtrusion(
            width=width,
            height=length,
            line=vertical_line,
            material=concrete_material
        )
        
        return vkt.GeometryResult(thrust_block)