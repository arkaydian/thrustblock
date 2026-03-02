from typing import Dict, Union, Optional, Any

EngRes = Dict[str, Any]

def eng(
        *,
        label: str,
        output: Union[float, str, bool],
        si_unit: str,
        formula_html: str,
        formula_xls: str,
        reference: str,
        symbol: Optional[str] = None
) -> EngRes:
    row: EngRes = {
        "label": label,
        "output": output,
        "si_unit": si_unit,
        "formula_html": formula_html,
        "formula_xls": formula_xls,
        "reference": reference,
    }
    if symbol is not None:
        row["symbol"] = symbol
    return row