import viktor as vkt
from app.civeng.civeng.hydraulics import fittings
from app.civeng.civeng.soils.soil_mechanics import FINE_SOILS, COARSE_SOILS, SoilType, SoilConsistency, SoilCategory, Soil, create_soil, get_soil_category, get_soil_type, get_soil_consistency, SOIL_PROPERTIES, WaterCondition
from app.civeng.civeng.structures.concrete import create_thrust_block, ThrustBlock

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
    vkt.IsEqual(vkt.Lookup("fitting_section.fitting_type"), "Vertical Bend"),
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
    vkt.IsEqual(vkt.Lookup("fitting_section.fitting_type"), "Vertical Bend"),
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

#--- ui logic ---

class Parametrization(vkt.Parametrization):
    # fitting logic
    fitting_section = vkt.Section('Fitting Type', initially_expanded=True)
    fitting_section.fitting_type = vkt.OptionField('Select fitting type', flex=18, options=fitting_list, default="Taper Thrust") #type: ignore
    fitting_section.crown_depth = vkt.NumberField('Depth to Crown Height (m)', flex=15, default=1) #type: ignore
    fitting_section.maximum_design_pressure = vkt.NumberField('Enter Maximum Design Pressure (kPa)', flex=15, default=1200) #type: ignore
    fitting_section.outside_diameter = vkt.NumberField("Pipe outside diameter (m)", flex=15, visible=pipe_outside_param, default=0.8)
    fitting_section.outside_diameter_large = vkt.NumberField("Pipe outside diameter – larger end (m)", flex=15, visible=pipe_outside_larger_end, default=0.63)
    fitting_section.outside_diameter_small = vkt.NumberField("Pipe outside diameter – smaller end (m)", flex=15, visible=pipe_outside_smaller_end, default=0.43)
    fitting_section.outside_diameter_main = vkt.NumberField("Pipe outside diameter – main (m)", flex=15, visible=pipe_diameter_main, default=0.43)
    fitting_section.outside_diameter_branch = vkt.NumberField("Branch Pipe outside diameter (m)", flex=15, visible=pipe_diameter_branch, default=0.63)
    fitting_section.angle = vkt.NumberField("Bend Radius (°)", flex=15, visible=bend_angle, default=45)
    fitting_section.turn_direction = vkt.OptionField("Turn Direction", options=["upturn", "downturn"], flex=15, visible=bend_direction, default="downturn")

    # soil params 1
    soil_section = vkt.Section("Soil Type", initially_expanded=True)
    soil_section.soil_type = vkt.OptionField("Select Soil Type", flex=18, options=soil_list, default="Gravel") #type: ignore
    soil_section.coarse_soil_consistency = vkt.OptionField("Soil Consistency", flex=15, options=coarse_consistency, visible=coarse_soil_consistency, default="Medium Dense") #type: ignore
    soil_section.fine_soil_consistency = vkt.OptionField("Soil Consistency", flex=15, options=fine_consistency, visible=fine_soil_consistency, default="Firm") #type: ignore
    soil_section.friction_angle = vkt.NumberField("Friction Angle", flex=25, visible=friction_angle, default=33, max=max_soil_params, min=min_soil_params)
    soil_section.undrained_shear_strength = vkt.NumberField("Undrained Shear Strength", flex=25, visible=undrained_shear_strength, default=50, max=max_soil_params, min=min_soil_params)
    soil_section.lb = vkt.LineBreak()
    soil_section.user_soil_passive_factor = vkt.NumberField("Passive resistance displacement limitation factor", flex=15, default=3, max=max_passive_soil_displacement_factor, min=min_passive_soil_displacement_factor)
    soil_section.user_soil_sliding_factor = vkt.NumberField("Sliding resistance displacement limitation factor", flex=15, default=2.25, max=max_active_soil_displacement_factor, min=min_active_soil_displacement_factor)
    # soil params 2
    soil_section.lb_2 = vkt.LineBreak()
    soil_section.ground_condition = vkt.OptionField("Select Ground Condition", flex=18, options=["Above Water", "Below Water"], default="Below Water") #type: ignore
    soil_section.groundwater_level = vkt.NumberField("Enter ground level depth (m)", flex=15, visible=ground_water_level, default=0.8)
    
    # thrust block geometry
    block_section = vkt.Section("Thrust Block Parameters", initially_expanded=True)
    block_section.block_height = vkt.NumberField("Thrust Block Height", flex=18, default=1.8)
    block_section.block_width = vkt.NumberField("Thrust Block Width", flex=18, default=3.5)
    block_section.block_length = vkt.NumberField("Thrust Block Length", flex=18, default=2.5)
    block_section.block_depth = vkt.NumberField("Thrust Block Depth", flex=18, default=2.3)
    block_section.download_pdf = vkt.DownloadButton("Export to PDF (not ready)", method="generate_pdf")

class Controller(vkt.Controller):
    parametrization = Parametrization(width=50)

    def report_fitting_type_html(self, fitting_type: fittings.Fitting) -> str:
        fitting_report = "".join(
            f""" <div class="name">{key}</div>
                <div class="result">{value}</div>
            """ for key, value in fitting_type.report_dimensions()
        )
        return fitting_report
        
    def report_soil_type_html(self, soil_class: Soil):
        soil_report = "".join(
            f""" <div class="name">{key}</div>
                <div class="result">{value}</div>
            """ for key, value in soil_class.report_dimensions()
        )
        return soil_report
    
    def pass_through_checks(self, thrust_block: ThrustBlock):
                pass_through_check = thrust_block.pass_through_resistance_check()
                thrust_force_name = "Thrust Force (horizontal component)" if isinstance(thrust_block.fitting, fittings.VerticalBend) else "Thrust Force"
                thrust_force_unit = f"T<sub>x</sub> = {pass_through_check[1]}"  if isinstance(thrust_block.fitting, fittings.VerticalBend) else f"T = {pass_through_check[1]}"
                return f"""
                <div class ="name"> Buoyancy coefficient </div>
                <div class="result">C<sub>GW</sub> = {thrust_block.buoyancy_coefficient:.2f}</div>
                <div class ="name"> Net passive soil pressure </div>
                <div class="result">σ<sub>pa</sub> = {thrust_block.net_unit_area_soil_pressure:.2f} kN/m<sup>2</sup></div>
                <div class ="name"> Base sliding resistance </div>
                <div class="result"> 𝜏<sub>b</sub> = {thrust_block.sliding_resistance_base:.2f} kN/m<sup>2</sup></div>
                <div class ="name"> Side sliding resistance </div>
                <div class="result"> 𝜏<sub>s</sub> = {thrust_block.sliding_resistance_side:.2f} kN/m<sup>2</sup></div>
                <div class ="name"> Passive face area </div>
                <div class="result"> A<sub>f</sub> = H x W = {thrust_block.area_passive_face:.2f} m<sup>2</sup></div>
                <div class ="name"> Base sliding area </div>
                <div class="result"> A<sub>b</sub> = L x W = {thrust_block.area_base_sliding:.2f} m<sup>2</sup></div>
                <div class ="name"> Sliding area per side </div>
                <div class="result"> A<sub>s</sub> = H x L = {thrust_block.area_side_sliding:.2f} m<sup>2</sup></div>
                <div class ="name"> Disturbed passive area due to pipe trench </div>
                <div class="result"> A<sub>d</sub> = {thrust_block.area_disturbed_passive:.2f} m<sup>2</sup></div>
                <div class ="name"> Block resistance force </div>
                <div class="result"> R<sub>s</sub> = {thrust_block.soil_resistance:.2f} kN</div>
                <div class="name"> {thrust_force_name}</div>
                <div class="result"> {thrust_force_unit} kN</div>
                <div class="name"><b>Horizontal Pass Through Check </b></div>
                <div class="result"><b> {pass_through_check[0]} </b></div>
                """
    def overturning_checks(self, thrust_block: ThrustBlock):
        if isinstance(thrust_block.fitting, fittings.VerticalBend) and thrust_block.fitting.turn_direction == "upturn":
            return """"""
        vertical_reaction_block = f"R<sub>v</sub> = (γ<sub>RC</sub> - (C<sub>GW</sub> x γ<sub>w</sub>)) x H x W x L = {thrust_block.vertical_reaction_block:.2f}" if isinstance(thrust_block.fitting ,fittings.VerticalBend) else \
                f"R<sub>v</sub> = (γ<sub>s</sub> - (C<sub>GW</sub> x γ<sub>w</sub>)) x Z<sub>b</sub> x W x L = {thrust_block.vertical_reaction_block:.2f}"
        net_vertical_reaction_of_block_key = f"Net vertical reaction of block" if isinstance(thrust_block.fitting ,fittings.VerticalBend) and thrust_block.fitting.turn_direction == "downturn" else ""
        net_vertical_reaction_of_block = f"R<sub>v_net</sub> = R<sub>v_net</sub> - T<sub>z</sub> = {thrust_block.net_effective_weight_thrust_block:.2f} kN" if isinstance(thrust_block.fitting ,fittings.VerticalBend) and thrust_block.fitting.turn_direction == "downturn" else \
                f""
        return f"""
                <div class="name"> Overturning moment lever arm </div>
                <div class="result">{thrust_block.overturning_level_arm:.2f}</div>
                <div class="name"> Overturning moment </div>
                <div class="result">{thrust_block.over_turning_moment:.2f}</div>
                <div class="name"> Passive face restoring moment </div>
                <div class="result">{thrust_block.passive_face_restoring_moment:.2f}</div>
                <div class="name"> Net disturbing moment </div>
                <div class="result">{thrust_block.net_disturbing_moment:.2f}</div>
                <div class="name"> Vertical reaction of block </div>
                <div class="result">{vertical_reaction_block}</div>
                <div class="name">{net_vertical_reaction_of_block_key}</div>
                <div class="result">{net_vertical_reaction_of_block}</div>
                <div class="name"> Concrete block restoring moment </div>
                <div class="result">{thrust_block.block_restoring_moment:.2f}</div>
                <div class="name"> Safety factor against overturning </div>
                <div class="result">{thrust_block.safety_factor_against_overturning:.2f}</div>
                <div class="name"><b> Overturning safety check </b></div>
                <div class="result"><b>{thrust_block.overturning_stability_check()}</b></div>
                """
    def tb_workflow(self, thrust_block: ThrustBlock):
        ...

    # Move below to soil_mechanics.py -> simplify the logic, it's too clunky right now
    def create_soil_instance(self, params) -> Soil:
        s = params.soil_section
        if get_soil_type(params.soil_section.soil_type) in COARSE_SOILS:
            return create_soil(
            user_soil_type=s.soil_type,
            user_soil_consistency=s.coarse_soil_consistency,
            water_condition= get_water_condition(s.ground_condition),
            ground_water_level=s.groundwater_level,
            user_soil_passive_factor=s.user_soil_passive_factor,
            user_soil_sliding_factor=s.user_soil_sliding_factor,
            user_friction_angle=s.friction_angle,
            user_undrained_shear_strength=0)
        elif get_soil_type(params.soil_section.soil_type) in FINE_SOILS:
            return create_soil(
            user_soil_type=s.soil_type,
            user_soil_consistency=s.fine_soil_consistency,
            water_condition= get_water_condition(s.ground_condition),
            ground_water_level=s.groundwater_level,
            user_soil_passive_factor=s.user_soil_passive_factor,
            user_soil_sliding_factor=s.user_soil_sliding_factor,
            user_friction_angle=0,
            user_undrained_shear_strength=s.undrained_shear_strength)
        else:
            raise ValueError(f"Unkown soil type: {params.soil_section.soil_type}")
        
    def vertical_bend_checks(self, thrust_block: ThrustBlock):
        if isinstance(thrust_block.fitting, fittings.VerticalBend):
            if thrust_block.fitting.turn_direction == "upturn":
                thrust_force_vertical = thrust_block.fitting.thrust_force_vertical()
                ultimate_ground_bearing_resistance = thrust_block.ultimate_vertical_bearing_capacity
                vertical_block_resistance_force = thrust_block.vertical_block_resistance_force
                return f"""
                <div class="name">Thrust force (vertical component)</div>
                <div class="result">T<sub>z</sub> = P<sub>d</sub> x π /4 x (D<sub>O</sub>)<sup>2</sup> x sin(θ) = <b>{thrust_force_vertical:.2f} kN</b></div>
                <div class="name">Ultimate ground bearing resistance</div>
                <div class="result">q<sub>b</sub> = 6 x C<sub>u</sub> ÷ DF<sub>P</sub> = <b>{ultimate_ground_bearing_resistance:.2f} kN</b></div>
                <div class="name">Vertical block resistance force</div>
                <div class="result">Qb = q<sub>b</sub> x A<sub>b</sub> = <b>{vertical_block_resistance_force:.2f} kN</b></div>
                <div class="name"><b>Vertical Ground Bearing Resistance check</b></div>
                <div class="result"><b>{thrust_block.vertical_bend_check()}</b></div>
                """
            if thrust_block.fitting.turn_direction == "downturn":
                return f"""
                <div class="name">Thrust force (vertical component)</div>
                <div class="result">{thrust_block.fitting.thrust_force_vertical():.2f}</div>
                <div class="name">Effective weight of thrust block</div>
                <div class="result">{thrust_block.effective_weight_thrust_block:.2f}</div>
                <div class="name">Uplift factor of safety</div>
                <div class="result">{thrust_block.uplift_factor_of_safety:.2f}</div>
                <div class="name"><b>Vertical Uplift Check</b></div>
                <div class="result"><b>{thrust_block.uplift_factor_of_safety_check()}</b></div>
                """
        else:
            return f""""""

    @vkt.WebView("Thrust Block Analysis Report")
    def analyze_tb(self, params, **kwargs):
        fitting_type = fittings.fitting_from_params(params=params)
        # --- refactor below to civeng module to include params ---
        soil_instance = self.create_soil_instance(params=params)
        print(soil_instance)
        # print(soil_instance.unit_weight)
        # print(soil_instance.soil_type)
        # print(soil_instance.soil_consistency)
        # print(soil_instance.soil_category)
        # --- end refactor ---
        tb = params.block_section
        thrust_block = create_thrust_block(
            fitting = fitting_type,
            soil = soil_instance,
            user_height= tb.block_height,
            user_width = tb.block_width,
            user_length = tb.block_length,
            user_depth_block= tb.block_depth
        )
        """Generate a simple HTML report."""
        # Simple HTML with just an H1 title
        html = f"""
        <!DOCTYPE html>
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
                
                h1 {{
                    color: #FF6600;
                    font-size: 36px;
                    font-weight: bold;
                    border-bottom: 4px solid #FF6600;
                    padding-bottom: 10px;
                    margin-top: 0;
                }}
                h2 {{
                    color: #FF6600;
                    font-size: 16px;
                    font-weight: bold;
                    border-bottom: 1px solid #FF6600;
                    padding-bottom: 10px;
                    margin-top: 0;
                }}
                .pb-12 {{ padding-bottom: 12px; }} /* adjust value as needed */
                .row {{
                    display: grid;
                    grid-template-columns: auto auto; /* left auto, middle fills, right auto */
                    align-items: baseline;                /* nice alignment for equations/text */
                    gap: 12px;
                    }}
                .name   {{ justify-self: start;  }}
                .result {{ justify-self: end;    text-align: right; }}
            </style>
        </head>
        <body>
            <h1> Thrust block sizing </h1>
            <h2> {params.fitting_section.fitting_type} block </h2>
            <div class="row">
                <div class ="name"> Pressure fixed by the designer </div>
                <div class="result">P = {params.fitting_section.maximum_design_pressure} kN/m2</div>
                <div class ="name"> Height </div>
                <div class="result"> H = {thrust_block.user_height} m</div>
                <div class ="name"> Width </div>
                <div class="result"> W = {thrust_block.user_width} m</div>
                <div class ="name"> Length </div>
                <div class="result"> L = {thrust_block.user_length} m</div>
                <div class ="name"> Depth </div>
                <div class="result"> Z<sub>b</sub> = {thrust_block.user_depth_block} m</div>
            </div>
            <br>
            <div class="row">
                {self.report_fitting_type_html(fitting_type)}
            </div>
            <br>
            <div class="row">
                {self.report_soil_type_html(soil_instance)}
            </div>
            <br>
            <div class="row">
                {self.pass_through_checks(thrust_block=thrust_block)}
                {self.vertical_bend_checks(thrust_block=thrust_block)}
                {self.overturning_checks(thrust_block=thrust_block)}
            </div>
        </body>
        </html>
        """
        
        return vkt.WebResult(html=html)
    
    def generate_pdf(self, params, **kwargs):
        """Generate a professional PDF report using HTML template."""
        # Get the HTML from the reusable helper method
        html_template = self.analyze_tb(params)
        
        # Create a File object from the HTML string
        html_file = vkt.File.from_data(html_template)
        
        # Convert HTML to PDF using VIKTOR's built-in converter
        pdf_file = vkt.convert_svg_to_pdf(html_file.open_binary())
        
        # Return as DownloadResult
        return vkt.DownloadResult(pdf_file, "block_report.pdf")

    @vkt.GeometryView("3D Arrangement", duration_guess=1, x_axis_to_right=True)
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