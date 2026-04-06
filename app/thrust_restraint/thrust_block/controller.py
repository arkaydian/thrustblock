import viktor as vkt
from app.civeng1.calculations.thrust_block_calculation import (
    FITTING_LABELS,
    fitting_from_params,
)
from app.civeng1.soils.soil_mechanics import SoilType, SoilConsistency, SoilCategory, SOIL_PROPERTIES
import base64
from pathlib import Path
from openpyxl import load_workbook
import app.utils

#--- utils ---
fitting_list = FITTING_LABELS

soil_list = [st.label for st in SoilType]
coarse_consistency = [cc.label for cc in SoilConsistency if cc.category ==  SoilCategory.COARSE]
fine_consistency = [fc.label for fc in SoilConsistency if fc.category ==  SoilCategory.FINE]

#--- refactor below to civeng module ---
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

def _get_section_soil_property_limit(section, property_name: str, bound_index: int):
    soil_category = get_soil_category_by_label(section.soil_type)
    if soil_category == SoilCategory.COARSE:
        consistency = get_soil_consistency_value_by_label(section.coarse_soil_consistency)
    else:
        consistency = get_soil_consistency_value_by_label(section.fine_soil_consistency)

    return SOIL_PROPERTIES[soil_category][consistency][property_name][bound_index]

def max_soil_params(params, **kwargs):
    section = params.soil_section
    property_name = "friction_angle" if get_soil_category_by_label(section.soil_type) == SoilCategory.COARSE else "undrained_shear_strength"
    return _get_section_soil_property_limit(section, property_name, 1)
    
def min_soil_params(params, **kwargs):
    section = params.soil_section
    property_name = "friction_angle" if get_soil_category_by_label(section.soil_type) == SoilCategory.COARSE else "undrained_shear_strength"
    return _get_section_soil_property_limit(section, property_name, 0)


def max_passive_soil_displacement_factor(params, **kwargs):
    return _get_section_soil_property_limit(params.soil_section, "soil_passive_resistance_factor", 1)
    
def min_passive_soil_displacement_factor(params, **kwargs):
    return _get_section_soil_property_limit(params.soil_section, "soil_passive_resistance_factor", 0)
    
def max_active_soil_displacement_factor(params, **kwargs):
    return _get_section_soil_property_limit(params.soil_section, "soil_sliding_resistance_factor", 1)
    
def min_active_soil_displacement_factor(params, **kwargs):
    return _get_section_soil_property_limit(params.soil_section, "soil_sliding_resistance_factor", 0)
    
#--- end refactor ---
    
#--- visibility conditions ---

def _is_equal_any(lookup_path: str, *values: str):
    return vkt.Or(*[vkt.IsEqual(vkt.Lookup(lookup_path), value) for value in values])

pipe_outside_param = _is_equal_any(
    "fitting_section.fitting_type",
    "Horizontal Bend",
    "Vertical Downturn Bend",
    "Vertical Upturn Bend",
    "Blank End",
    "Closed Valve",
    "Line Stop"
)
# bend_direction = vkt.Or(
#     vkt.IsEqual(vkt.Lookup("fitting_section.fitting_type"), "Vertical Bend"),
# )
pipe_outside_larger_end = vkt.IsEqual(vkt.Lookup("fitting_section.fitting_type"), "Taper Thrust")
pipe_outside_smaller_end = vkt.IsEqual(vkt.Lookup("fitting_section.fitting_type"), "Taper Thrust")
pipe_diameter_main = _is_equal_any("fitting_section.fitting_type", "Tee", "Angle Branch")
pipe_diameter_branch = pipe_diameter_main
bend_angle = _is_equal_any("fitting_section.fitting_type", "Horizontal Bend", "Vertical Downturn Bend", "Vertical Upturn Bend", "Angle Branch")

coarse_soil_consistency = _is_equal_any("soil_section.soil_type", "Gravel", "Sand")
fine_soil_consistency = _is_equal_any("soil_section.soil_type", "Silt", "Clay")

undrained_shear_strength = fine_soil_consistency

friction_angle = coarse_soil_consistency

ground_water_level = vkt.IsEqual(vkt.Lookup("soil_section.ground_condition"), "Below Water")

# taper thrust arrangement visibility
def is_taper_thrust_trenchless(params, **kwargs) -> bool:
    return params.fitting_section.fitting_type == "Taper Thrust" \
    and (params.block_section.depth or 0) - (params.block_section.height or 0) \
    > (params.fitting_section.crown_depth or 0) + (params.fitting_section.outside_diameter_large or 0)

def is_taper_thrust_trench(params, **kwargs) -> bool:
    return params.fitting_section.fitting_type == "Taper Thrust" \
    and (params.block_section.depth or 0) - (params.block_section.height or 0) \
    < (params.fitting_section.crown_depth) + (params.fitting_section.outside_diameter_large or 0)

# blank end arrangement visibility
blank_end_arrangement_1 = vkt.And(
    vkt.IsEqual(vkt.Lookup("fitting_section.fitting_type"), "Blank End"),
    )
# closed valve arrangement visibility

def is_closed_valve_trenchless(params, **kwargs) -> bool:
    return params.fitting_section.fitting_type == "Closed Valve" \
    and (params.block_section.depth or 0) - (params.block_section.height or 0) \
    > (params.fitting_section.crown_depth) + (params.fitting_section.outside_diameter or 0) \
    and params.block_section.is_key == "No"

def is_closed_valve_trench(params, **kwargs) -> bool:
    return params.fitting_section.fitting_type == "Closed Valve" \
    and (params.block_section.depth or 0) - (params.block_section.height or 0) \
    < (params.fitting_section.crown_depth) + (params.fitting_section.outside_diameter or 0)

def is_closed_valve_trenchless_key(params, **kwargs) -> bool:
    return params.fitting_section.fitting_type == "Closed Valve" \
    and (params.block_section.depth or 0) - (params.block_section.height or 0) \
    > (params.fitting_section.crown_depth) + (params.fitting_section.outside_diameter or 0) \
    and params.block_section.is_key == "Yes"

# tee arrangement visibility
tee_arrangement_1 = vkt.And(
    vkt.IsEqual(vkt.Lookup("fitting_section.fitting_type"), "Tee"),
    vkt.IsEqual(vkt.Lookup("block_section.is_key"), "No"),
)
tee_arrangement_2 = vkt.And(
    vkt.IsEqual(vkt.Lookup("fitting_section.fitting_type"), "Tee"),
    vkt.IsEqual(vkt.Lookup("block_section.is_key"), "Yes"),
)
# vertical downturn arrangement visibility
vertical_downturn_arrangement_1 = vkt.And(
    vkt.IsEqual(vkt.Lookup("fitting_section.fitting_type"), "Vertical Downturn Bend")
)
# vertical upturn arrangement visibility
vertical_upturn_arrangement_1 = vkt.And(
    vkt.IsEqual(vkt.Lookup("fitting_section.fitting_type"), "Vertical Upturn Bend"),
    vkt.IsEqual(vkt.Lookup("block_section.is_key"), "No"),
)
vertical_upturn_arrangement_2 = vkt.And(
    vkt.IsEqual(vkt.Lookup("fitting_section.fitting_type"), "Vertical Upturn Bend"),
    vkt.IsEqual(vkt.Lookup("block_section.is_key"), "Yes"),
)
# horizontal bend arrangement visibility
horizontal_bend_arrangement_1 = vkt.And(
    vkt.IsEqual(vkt.Lookup("fitting_section.fitting_type"), "Horizontal Bend"),
    vkt.IsEqual(vkt.Lookup("block_section.is_key"), "No"),
)
horizontal_bend_arrangement_2 = vkt.And(
    vkt.IsEqual(vkt.Lookup("fitting_section.fitting_type"), "Horizontal Bend"),
    vkt.IsEqual(vkt.Lookup("block_section.is_key"), "Yes"),
)

line_stop_arrangement = _is_equal_any("fitting_section.fitting_type", "Line Stop")

key_visibility = _is_equal_any("block_section.is_key", "Yes")

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
    # fitting_section.turn_direction = vkt.OptionField("Turn Direction", options=["upturn", "downturn"], flex=20, visible=bend_direction, default="downturn")
    fitting_section.chainage = vkt.NumberField("Chainage", flex=40, default=0)

    # soil params 1
    soil_section = vkt.Section("Soil Type Parameters", initially_expanded=True)
    soil_section.soil_type = vkt.OptionField("Soil Type", flex=18, options=soil_list, default="Gravel") #type: ignore
    soil_section.coarse_soil_consistency = vkt.OptionField("Soil Consistency", flex=25, options=coarse_consistency, visible=coarse_soil_consistency, default="Medium Dense", description="Refer to `Ciria816, Table 3.2` for `Soil Consistency`") #type: ignore
    soil_section.fine_soil_consistency = vkt.OptionField("Soil Consistency", flex=25, options=fine_consistency, visible=fine_soil_consistency, default="Firm", description="Refer to `Ciria816, Table 3.2` for `Soil Consistency`") #type: ignore
    soil_section.friction_angle = vkt.NumberField("Friction Angle", flex=25, visible=friction_angle, default=33, step=0.1, max=max_soil_params, min=min_soil_params, description="Refer to `Ciria816, Table 3.2` for `Friction Angle`")
    soil_section.undrained_shear_strength = vkt.NumberField("Undrained Shear Strength", flex=30, visible=undrained_shear_strength, default=50, step=0.1, max=max_soil_params, min=min_soil_params, description="Refer to `Ciria816, Table 3.2` for `Undrained Shear Strength`")
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
    block_section.taper_thrust_plan_1 = vkt.Image(path="taper_thrust_trench.png", align="left", flex=100, visible=is_taper_thrust_trench)
    block_section.taper_thrust_plan_2 = vkt.Image(path="taper_thrust.png", align="left", flex=100, visible=is_taper_thrust_trenchless)
    ## blank end arrangement images
    block_section.blank_end_plan_1 = vkt.Image(path="blank_end_plan_1.png", align="left", flex=40, visible=blank_end_arrangement_1)
    block_section.blank_end_section_1 = vkt.Image(path="blank_end_section_1.png", align="right", flex=40, visible=blank_end_arrangement_1)
    # closed valve block arrangement
    block_section.closed_valve_section_1 = vkt.Image(path="closed_valve_section_1.png", align="right", flex=100, visible=is_closed_valve_trenchless)
    block_section.closed_valve_section_2 = vkt.Image(path="closed_valve_section_2.png", align="right", flex=100, visible=is_closed_valve_trench)
    block_section.closed_valve_section_3 = vkt.Image(path="closed_valve_section_3.png", align="right", flex=100, visible=is_closed_valve_trenchless_key)
    # tee arrangement images
    block_section.tee_plan_1 = vkt.Image(path="tee_plan_1.png", align="left", flex=40, visible=tee_arrangement_1)
    block_section.tee_section_1 = vkt.Image(path="tee_section_1.png", align="right", flex=40, visible=tee_arrangement_1)
    block_section.tee_plan_2 = vkt.Image(path="tee_plan_2.png", align="left", flex=40, visible=tee_arrangement_2)
    block_section.tee_section_2 = vkt.Image(path="tee_section_2.png", align="left", flex=40, visible=tee_arrangement_2)
    # vertical downturn images
    block_section.vertical_downturn_bend_section_1 = vkt.Image(path="vertical_downturn_bend.png", align="right", flex=100, visible=vertical_downturn_arrangement_1)
    # vertical upturn images
    block_section.vertical_upturn_bend_section_1 = vkt.Image(path="vertical_upturn_bend.png", align="right", flex=100, visible=vertical_upturn_arrangement_1)
    block_section.vertical_upturn_bend_section_2 = vkt.Image(path="vertical_upturn_bend_section_2.png", align="right", flex=80, visible=vertical_upturn_arrangement_2)
    # horizontal bend images
    block_section.horizontal_bend_plan_1 = vkt.Image(path="horizontal_bend_plan_standard.png", align="left", flex=100, visible=horizontal_bend_arrangement_1)
    block_section.horizontal_bend_plan_2 = vkt.Image(path="horizontal_bend_plan_2.png", align="left", flex=40, visible=horizontal_bend_arrangement_2)
    block_section.horizontal_bend_section_2 = vkt.Image(path="horizontal_bend_section_2.png", align="left", flex=40, visible=horizontal_bend_arrangement_2)
    # linestop image
    block_section.line_stop_section = vkt.Image(path="line_stop.png", align="left", flex=100, visible=line_stop_arrangement)
    block_section.lb = vkt.LineBreak()
    block_section.height = vkt.NumberField("Thrust Block Height (H)", flex=25, default=1.8, step=0.1)
    block_section.width = vkt.NumberField("Thrust Block Width (W)", flex=25, default=3.5, step=0.1)
    block_section.length = vkt.NumberField("Thrust Block Length (L)", flex=25, default=2.5, step=0.1)
    block_section.depth = vkt.NumberField("Thrust Block Depth (Zb)", flex=25, default=2.3, step=0.1)
    block_section.lb_2 = vkt.LineBreak()
    block_section.is_key = vkt.OptionField("Thrust Block Key:", options=["Yes", "No"], default="No", variant="radio")
    block_section.lb_3 = vkt.LineBreak()
    block_section.key_height = vkt.NumberField("Height of Key", flex=30, default=0, visible=key_visibility)
    block_section.key_length = vkt.NumberField("Length of Key", flex=30, default=0, visible=key_visibility)
    block_section.lb_4 = vkt.LineBreak()
    # block_section.download_excel = vkt.DownloadButton("Export to Excel", method="export_to_excel", flex=24)

class ThrustBlockController(vkt.Controller):
    parametrization = Parametrization(width=40)

    def render_workflow_html(self, params):
        fitting_type = fitting_from_params(params=params)
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
    
    # def export_to_excel(self, params, **kwargs):
    #     """Export the dimensions to an Excel file."""
    #     # Create a new workbook and select the active sheet
    #     template_path =  Path(__file__).parent.parent / 'arcadis_calculation_sheet_template.xlsx'
    #     wb = load_workbook(template_path)
    #     ws = wb["Thrust Block 1"]

    #     thrust_block = fitting_from_params(params=params)

    #     for i, entry in enumerate(thrust_block.fitting_workflow_res):

    #         num = 7
    #         # Add the dimension data
    #         row = num + i
    #         ws[f"A{row}"] = entry["label"]
    #         ws[f"B{row}"] = entry["formula_xls"]
    #         ws[f"F{row}"] = entry["output"]
    #         ws[f"I{row}"] = entry["si_unit"]
    #         ws[f"J{row}"] = entry["reference"]
        
    #     # Save the workbook to a file
    #     from io import BytesIO
    #     buffer = BytesIO()
    #     wb.save(buffer)
    #     buffer.seek(0)

    #     excel_file = vkt.File.from_data(buffer.read())
        
    #     return vkt.DownloadResult(excel_file, 'dimensions.xlsx')

    @vkt.WebView("Plan and Section View")   # Decorator: renders the return value as an HTML/SVG web view
    def view_svg(self, params, **kwargs):
        """Render the SVG plan view for the selected fitting type."""
        fitting_type = params.fitting_type   # Read the selected fitting type from the dropdown

        # Read user-defined canvas size, falling back to sensible defaults if empty
        canvas_w = 1100   # SVG canvas width in pixels
        canvas_h = 420    # SVG canvas height in pixels

    @vkt.WebView("Thrust Restraint Safety Checks")
    def thrust_force_view(self, params, **kwargs):
        """Render a card grid with dynamic color coding based on thrust force vs. block resistance."""

        # Build one card per row in the DynamicArray

        fitting_type = fitting_from_params(params=params)
        cards_html = ""
        for row in fitting_type.safety_report:
            title = row["title"]
            shot_title = row["shot_title"] 
            shot = row["shot"]
            goal_title = row["goal_title"] 
            goal = row["goal"]
            unit = row["unit"]

            # Determine color and status: red if thrust exceeds resistance, green if safe
            if shot > goal:
                bg_color = "#4CAF50"        # green — block resistance holds (safe)
                border_color = "#2E7D32"
                status = "SAFE 🟢"
                text_color = "#fff"
                ratio_color = "#e0f5e0"
            else:
                bg_color = "#FF4D4D"        # red — thrust exceeds resistance (unsafe)
                border_color = "#CC0000"
                status = "UNSAFE 🔴"
                text_color = "#fff"
                ratio_color = "#ffe0e0"


            # Compute utilisation ratio (thrust / resistance)
            ratio = (shot / goal * 100) if goal > 0 else 0

            cards_html += f"""
            <div class="card" style="background-color:{bg_color}; border: 2px solid {border_color}; color:{text_color};">
                <div class="card-name">{title}</div>
                <div class="card-status">{status}</div>
                <div class="card-divider"></div>
                <div class="card-row">
                    <div class="card-label">{shot_title}</div>
                    <div class="card-value">{shot:.1f} {unit}</div>
                </div>
                <div class="card-row">
                    <div class="card-label">{goal_title}</div>
                    <div class="card-value">{goal:.1f} {unit}</div>
                </div>
                <div class="card-ratio" style="background-color:{ratio_color}; color:#333;">
                    Utilisation: {ratio:.1f}%
                </div>
            </div>
            """

        html = f"""
        <!DOCTYPE html>
        <html>
        <head>
            <meta charset="UTF-8">
            <title>Thrust Force Checker</title>
            <style>
                * {{ box-sizing: border-box; margin: 0; padding: 0; }}

                body {{
                    font-family: 'Segoe UI', sans-serif;
                    background: #f4f6f9;
                    padding: 32px;
                }}

                h1 {{
                    font-size: 22px;
                    color: #2c3e50;
                    margin-bottom: 6px;
                }}

                .meta {{
                    font-size: 14px;
                    color: #666;
                    margin-bottom: 28px;
                }}

                .meta span {{
                    font-weight: 600;
                    color: #333;
                }}

                .legend {{
                    display: flex;
                    gap: 20px;
                    margin-bottom: 28px;
                    flex-wrap: wrap;
                }}

                .legend-item {{
                    display: flex;
                    align-items: center;
                    gap: 8px;
                    font-size: 13px;
                    color: #444;
                }}

                .legend-dot {{
                    width: 14px;
                    height: 14px;
                    border-radius: 50%;
                    flex-shrink: 0;
                }}

                .grid {{
                    display: grid;
                    grid-template-columns: repeat(auto-fill, minmax(320px, 1fr));
                    gap: 20px;
                }}

                .card {{
                    border-radius: 12px;
                    padding: 20px 16px;
                    text-align: center;
                    box-shadow: 0 4px 12px rgba(0,0,0,0.12);
                    transition: transform 0.15s ease;
                    display: flex;
                    flex-direction: column;
                    gap: 8px;
                }}

                .card:hover {{
                    transform: translateY(-3px);
                }}

                .card-name {{
                    font-size: 15px;
                    font-weight: 700;
                    letter-spacing: 0.3px;
                }}

                .card-status {{
                    font-size: 13px;
                    font-weight: 600;
                    opacity: 0.95;
                    text-transform: uppercase;
                    letter-spacing: 0.5px;
                }}

                .card-divider {{
                    height: 1px;
                    background: rgba(255,255,255,0.35);
                    margin: 4px 0;
                }}

                .card-row {{
                    display: flex;
                    justify-content: space-between;
                    align-items: center;
                    font-size: 13px;
                    padding: 2px 0;
                }}

                .card-label {{
                    opacity: 0.85;
                    font-weight: 400;
                }}

                .card-value {{
                    font-weight: 700;
                    font-size: 14px;
                }}

                .card-ratio {{
                    margin-top: 6px;
                    border-radius: 8px;
                    padding: 6px 10px;
                    font-size: 13px;
                    font-weight: 600;
                }}

                .empty {{
                    color: #999;
                    font-size: 15px;
                    margin-top: 40px;
                }}
            </style>
        </head>
        <body>
            <h1>⚡ Safety Checks</h1>
            <div class="meta">
                Condition: <span>Criterion &gt; value → Unsafe</span>
            </div>

            <div class="legend">
                <div class="legend-item">
                    <div class="legend-dot" style="background:#4CAF50;"></div> Safe (Value > Criterion)
                </div>
                <div class="legend-item">
                    <div class="legend-dot" style="background:#FF4D4D;"></div> Unsafe (Criterion &gt; Value)
                </div>
            </div>

            <div class="grid">
                {cards_html if cards_html.strip() else '<p class="empty">No blocks defined yet. Add rows in the panel.</p>'}
            </div>
        </body>
        </html>
        """
        return vkt.WebResult(html=html)
    
    @vkt.WebView("Thrust Restraint Calculation")
    def analyze_tb(self, params, **kwargs):
        """Generates a thrust stability check HTML report."""

        image_path = Path(__file__).parent.parent / "assets" / "Arcadis_logo.png"
        with open(image_path, "rb") as img_file:
            img_base64 = base64.b64encode(img_file.read()).decode()

        html = f"""
        <!DOCTYPE html>
        <html lang="en">
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
        height = params.block_section.height
        length = params.block_section.length
        width = params.block_section.width
        
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