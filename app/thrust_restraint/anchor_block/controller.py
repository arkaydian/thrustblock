import viktor as vkt
from app.civeng1.hydraulics import pipes
from app.civeng1.calculations.thrust_block_calculation import build_metallic_flange
from app.civeng1.soils.soil_mechanics import SoilType, SoilConsistency, SoilCategory, EmbedmentClass, SOIL_PROPERTIES
import base64
from pathlib import Path
from openpyxl import load_workbook

#--- utils ---
pipe_material_list: list = [pm.value for pm in pipes.PipeMaterial]
coarse_embedment_list: list = [ec.label_capitalized for ec in EmbedmentClass]
soil_list: list = [st.label for st in SoilType]
coarse_consistency: list = [cc.label for cc in SoilConsistency if cc.category ==  SoilCategory.COARSE]
fine_consistency: list = [fc.label for fc in SoilConsistency if fc.category ==  SoilCategory.FINE]

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
    
def max_backfill_soil_params(params, **kwargs):
    section = params.backfill_section
    property_name = "friction_angle" if get_soil_category_by_label(section.soil_type) == SoilCategory.COARSE else "undrained_shear_strength"
    return _get_section_soil_property_limit(section, property_name, 1)
    
def min_backfill_soil_params(params, **kwargs):
    section = params.backfill_section
    property_name = "friction_angle" if get_soil_category_by_label(section.soil_type) == SoilCategory.COARSE else "undrained_shear_strength"
    return _get_section_soil_property_limit(section, property_name, 0)


def max_passive_backfill_soil_displacement_factor(params, **kwargs):
    return _get_section_soil_property_limit(params.backfill_section, "soil_passive_resistance_factor", 1)
    
def min_passive_backfill_soil_displacement_factor(params, **kwargs):
    return _get_section_soil_property_limit(params.backfill_section, "soil_passive_resistance_factor", 0)
    
def max_active_backfill_soil_displacement_factor(params, **kwargs):
    return _get_section_soil_property_limit(params.backfill_section, "soil_sliding_resistance_factor", 1)
    
def min_active_backfill_soil_displacement_factor(params, **kwargs):
    return _get_section_soil_property_limit(params.backfill_section, "soil_sliding_resistance_factor", 0)
    
#--- end refactor ---
    
#--- visibility conditions ---

def _is_equal_any(lookup_path: str, *values: str):
    return vkt.Or(*[vkt.IsEqual(vkt.Lookup(lookup_path), value) for value in values])

s_one_compaction = vkt.IsEqual(vkt.Lookup("embedment_section.embedment_class"), "S1")

coarse_compaction = _is_equal_any("embedment_section.embedment_class", "S2", "S3", "S4")

clay_compaction = vkt.IsEqual(vkt.Lookup("embedment_section.embedment_class"), "S5")

adhesion = vkt.IsEqual(vkt.Lookup("embedment_section.embedment_class"), "S5")

# --- Backfill visibility conditions

coarse_backfill_soil_consistency = _is_equal_any("backfill_section.soil_type", "Gravel", "Sand")

fine_backfill_soil_consistency = _is_equal_any("backfill_section.soil_type", "Silt", "Clay")

backfill_undrained_shear_strength = fine_backfill_soil_consistency

backfill_friction_angle = coarse_backfill_soil_consistency

backfill_ground_water_level = vkt.IsEqual(vkt.Lookup("backfill_section.ground_condition"), "Below Water")

# --- Native soil visibility

coarse_soil_consistency = _is_equal_any("soil_section.soil_type", "Gravel", "Sand")

fine_soil_consistency = _is_equal_any("soil_section.soil_type", "Silt", "Clay")

undrained_shear_strength = fine_soil_consistency

friction_angle = coarse_soil_consistency

ground_water_level = vkt.IsEqual(vkt.Lookup("soil_section.ground_condition"), "Below Water")


#--- ui logic ---

class Parametrization(vkt.Parametrization):
    # fitting logic
    pipe_section = vkt.Section('Welded Pipe Parameters', initially_expanded=True)
    pipe_section.pipe_material = vkt.OptionField("Pipe Material", flex=20, options=pipe_material_list, default="PE Pipe")
    pipe_section.outside_diameter = vkt.NumberField("Pipe outside diameter (m)", flex=30, default=0.71)
    pipe_section.crown_depth = vkt.NumberField('Depth to Pipe Crown (m)', flex=30, default=1)
    pipe_section.maximum_design_pressure = vkt.NumberField('Maximum Design Pressure (kPa)', flex=35, default=1200)
    pipe_section.length = vkt.NumberField('Length (m)', flex=25, default=200)
    pipe_section.standard_dimension_ratio = vkt.NumberField('Standard dimension ratio', flex=30, default=17)
    pipe_section.poisson_ratio = vkt.NumberField('Poisson’s ratio (ν)', flex=25, default=0.38)
    pipe_section.thermal_coefficient = vkt.NumberField('Thermal Coefficient', flex=20, default=0.00013)
    pipe_section.temperature_reduction = vkt.NumberField('Temperature reduction of pipe material (ᶿC)', flex=42, default=10)
    pipe_section.elastic_modulus= vkt.NumberField('Elastic modulus (MPa)', flex=25, default=712)
    pipe_section.allowable_contraction_movement = vkt.NumberField('Allowable contraction movement (m)', flex=40, default=0.005)
    pipe_section.chainage = vkt.NumberField("Chainage", flex=20)

    # embedment params
    embedment_section = vkt.Section("Embedment Material Parameters", initially_expanded=True)
    embedment_section.embedment_class = vkt.OptionField("Embedment Class", flex=25, options=coarse_embedment_list, default="S3", description="Refer to `Ciria816, Table 3.3` for `Embedment Class` descriptions") 
    embedment_section.ground_water_level = vkt.NumberField("Ground Water Level (m)", flex=25, default=0.8)
    embedment_section.coarse_compaction_class = vkt.OptionField("Compaction Class", flex=30, options=["Compacted sands and gravels (85%)", "Compacted sands and gravels (90%)"], default="Compacted sands and gravels (85%)", visible = coarse_compaction, description="Refer to `Ciria816, Table 3.3` for `Compaction Class` descriptions")
    embedment_section.s_one_compaction_class = vkt.OptionField("Compaction Class", flex=30, options=["Uncompacted processed gravels"], default="Uncompacted processed gravels", visible = s_one_compaction, description="Refer to `Ciria816, Table 3.3` for `Compaction Class` descriptions")
    embedment_section.adhesion =  vkt.OptionField("Adhesion", flex=25, options=["Soft Clay", "Firm or Stiff Clay"], default="Firm or Stiff Clay", visible=adhesion) 
    embedment_section.fine_compaction_class = vkt.OptionField("Compaction Class", flex=25, options=["Compacted clays (85%)", "Compacted clays (90%)"], default="Compacted clays (85%)", visible=clay_compaction) 
    
    # backfill soil params
    backfill_section = vkt.Section("Backfill Parameters", initially_expanded=True)
    backfill_section.soil_type = vkt.OptionField("Soil Type", flex=18, options=soil_list, default="Gravel")
    backfill_section.coarse_soil_consistency = vkt.OptionField("Soil Consistency", flex=25, options=coarse_consistency, visible=coarse_backfill_soil_consistency, default="Medium Dense", description="Refer to `Ciria816, Table 3.2` for `Soil Consistency`")
    backfill_section.fine_soil_consistency = vkt.OptionField("Soil Consistency", flex=25, options=fine_consistency, visible=fine_backfill_soil_consistency, default="Firm", description="Refer to `Ciria816, Table 3.2` for `Soil Consistency`")
    backfill_section.friction_angle = vkt.NumberField("Friction Angle", flex=25, visible=backfill_friction_angle, default=33, step=0.1, max=max_backfill_soil_params, min=min_backfill_soil_params, description="Refer to `Ciria816, Table 3.2` for `Friction Angle` values")
    backfill_section.undrained_shear_strength = vkt.NumberField("Undrained Shear Strength", flex=25, visible=backfill_undrained_shear_strength, default=50, step=0.1, max=max_backfill_soil_params, min=min_backfill_soil_params, description="Refer to `Ciria816, Table 3.2` for `Undrained Shear Strength`")
    backfill_section.lb = vkt.LineBreak()
    backfill_section.soil_passive_factor = vkt.NumberField("DFp", flex=10, default=3, max=max_passive_backfill_soil_displacement_factor, min=min_passive_backfill_soil_displacement_factor, description="Passive resistance displacement limitation factor - Table 3.6")
    backfill_section.soil_sliding_factor = vkt.NumberField("DFs", flex=10, default=2.25, max=max_active_backfill_soil_displacement_factor, min=min_active_backfill_soil_displacement_factor, description="Sliding resistance displacement limitation factor - Table 3.6")
    # soil params 2
    backfill_section.lb_2 = vkt.LineBreak()
    backfill_section.ground_condition = vkt.OptionField("Ground Condition", flex=18, options=["Above Water", "Below Water"], default="Below Water")
    backfill_section.groundwater_level = vkt.NumberField("Ground level depth (m)", flex=25, visible=backfill_ground_water_level, default=0.8)

    # soil params 1
    soil_section = vkt.Section("Native Soil Parameters", initially_expanded=True)
    soil_section.soil_type = vkt.OptionField("Soil Type", flex=18, options=soil_list, default="Gravel")
    soil_section.coarse_soil_consistency = vkt.OptionField("Soil Consistency", flex=25, options=coarse_consistency, visible=coarse_soil_consistency, default="Medium Dense", description="Refer to `Ciria816, Table 3.2` for `Soil Consistency`")
    soil_section.fine_soil_consistency = vkt.OptionField("Soil Consistency", flex=25, options=fine_consistency, visible=fine_soil_consistency, default="Firm", description="Refer to `Ciria816, Table 3.2` for `Soil Consistency`")
    soil_section.friction_angle = vkt.NumberField("Friction Angle (θ)", flex=25, visible=friction_angle, default=33, step=0.1, max=max_soil_params, min=min_soil_params, description="Refer to `Ciria816, Table 3.2` for `Friction Angle` values")
    soil_section.undrained_shear_strength = vkt.NumberField("Undrained Shear Strength (C_u)", flex=25, visible=undrained_shear_strength, default=50, step=0.1, max=max_soil_params, min=min_soil_params, description="Refer to `Ciria816, Table 3.2` for `Undrained Shear Strength`")
    soil_section.lb = vkt.LineBreak()
    soil_section.soil_passive_factor = vkt.NumberField("DF_p", flex=10, default=3, max=max_passive_soil_displacement_factor, min=min_passive_soil_displacement_factor, description="Passive resistance displacement limitation factor - Table 3.6")
    soil_section.soil_sliding_factor = vkt.NumberField("DF_s", flex=10, default=2.25, max=max_active_soil_displacement_factor, min=min_active_soil_displacement_factor, description="Sliding resistance displacement limitation factor - Table 3.6")
    # soil params 2
    soil_section.lb_2 = vkt.LineBreak()
    soil_section.ground_condition = vkt.OptionField("Ground Condition", flex=18, options=["Above Water", "Below Water"], default="Below Water")
    soil_section.groundwater_level = vkt.NumberField("Ground level depth (m)", flex=25, visible=ground_water_level, default=0.8)
    
    # thrust block geometry
    block_section = vkt.Section("Thrust Block Parameters", initially_expanded=True)
    block_section.lb = vkt.LineBreak()
    block_section.height = vkt.NumberField("Thrust Block Height (H)", flex=25, default=2.35, step=0.1)
    block_section.width = vkt.NumberField("Thrust Block Width (W)", flex=25, default=4, step=0.1)
    block_section.length = vkt.NumberField("Thrust Block Length (L)", flex=25, default=3, step=0.1)
    block_section.depth = vkt.NumberField("Thrust Block Depth (Z_b)", flex=25, default=2.85, step=0.1)
    block_section.lb_2 = vkt.LineBreak()
    block_section.download_excel = vkt.DownloadButton("Export to Excel", method="export_to_excel", flex=24)

class AnchorBlockController(vkt.Controller):
    parametrization = Parametrization(width=40)

    def render_workflow_html(self, params):
        fitting_type = build_metallic_flange(params)
        dims=   f"""<div class="label">Pressure fixed by the designer </div>
            <div class="result">P = <b>{params.pipe_section.maximum_design_pressure} kN/m2</b></div>
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
        template_path =  Path(__file__).parent.parent / 'arcadis_calculation_sheet_template.xlsx'
        wb = load_workbook(template_path)
        ws = wb["Thrust Block 1"]

        thrust_block = build_metallic_flange(params)

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
            <h2> Anchor Block Design</h2>
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