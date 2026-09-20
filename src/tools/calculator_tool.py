"""
src/tools/calculator_tool.py
Deterministic HR Calculator Tool for Precise Mathematical Calculations.
Prevents LLM arithmetic hallucinations for scores, GPAs, weighted averages, and compensation benchmarks.
"""
from typing import Literal, Type
from pydantic import BaseModel, Field

from src.tools.base_tool import BaseHRMSTool


class CalculatorInput(BaseModel):
    operation: Literal["weighted_average", "gpa_normalization", "percentile_rank", "simple_average"] = Field(
        description="Target mathematical calculation operation"
    )
    values: list[float] = Field(min_length=1, description="List of numerical values to compute")
    weights: list[float] = Field(default_factory=list, description="Optional weights for weighted_average")
    scale_max: float = Field(default=4.0, description="Max scale for GPA normalization (e.g. 4.0 or 10.0)")


class CalculatorOutput(BaseModel):
    result: float = Field(description="Deterministic numerical result")
    operation: str = Field(description="Executed operation name")
    formula: str = Field(description="Explanatory mathematical formula applied")


class HRCalculatorTool(BaseHRMSTool):
    name: str = "HRCalculatorTool"
    description: str = "Performs deterministic mathematical calculations for composite interview scores, GPAs, and statistics."
    args_schema: Type[BaseModel] = CalculatorInput
    return_schema: Type[BaseModel] = CalculatorOutput

    def _run(
        self,
        operation: Literal["weighted_average", "gpa_normalization", "percentile_rank", "simple_average"],
        values: list[float],
        weights: list[float] | None = None,
        scale_max: float = 4.0,
    ) -> CalculatorOutput:
        w_list = weights or []

        if operation == "weighted_average":
            if not w_list or len(w_list) != len(values):
                # Default to uniform weights if length mismatch
                w_list = [1.0] * len(values)
            total_weight = sum(w_list)
            if total_weight == 0:
                raise ValueError("Sum of weights cannot be zero.")
            weighted_sum = sum(v * w for v, w in zip(values, w_list))
            res = round(weighted_sum / total_weight, 2)
            formula = f"sum(values * weights) / sum(weights) = {res}"

        elif operation == "gpa_normalization":
            gpa = values[0]
            if scale_max <= 0:
                raise ValueError("scale_max must be greater than zero.")
            res = round(min(100.0, max(0.0, (gpa / scale_max) * 100.0)), 2)
            formula = f"({gpa} / {scale_max}) * 100 = {res}%"

        elif operation == "percentile_rank":
            target = values[0]
            population = values[1:] if len(values) > 1 else [target]
            count_below = sum(1 for x in population if x < target)
            res = round((count_below / max(1, len(population))) * 100.0, 2)
            formula = f"({count_below} candidates below / {len(population)} total) * 100 = {res}%"

        else:  # simple_average
            res = round(sum(values) / len(values), 2)
            formula = f"sum(values) / {len(values)} = {res}"

        return CalculatorOutput(
            result=res,
            operation=operation,
            formula=formula,
        )


hr_calculator_tool = HRCalculatorTool()

