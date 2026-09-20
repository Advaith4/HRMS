"""
src/tools/base_tool.py
Standardized BaseHRMSTool Protocol for Tool Abstraction in TalentForge AI.
Enforces typed Pydantic v2 input and output schemas, automatic request tracing, and latency tracking.
"""
import time
import logging
from typing import Any, Type
from pydantic import BaseModel, ValidationError

from src.core.logging_middleware import log_agent_execution

logger = logging.getLogger(__name__)


class BaseHRMSTool:
    """
    Abstract base class for all TalentForge AI tools.
    Every tool must specify its name, description, input schema, and return schema.
    """
    name: str = "BaseTool"
    description: str = "Base tool description"
    args_schema: Type[BaseModel] = BaseModel
    return_schema: Type[BaseModel] = BaseModel

    def _run(self, *args: Any, **kwargs: Any) -> BaseModel:
        """Subclasses must implement the core tool logic here."""
        raise NotImplementedError("Subclasses must implement _run")

    def run(self, request_id: str = "req-tool", **kwargs: Any) -> BaseModel:
        """
        Public execution wrapper with type validation, latency measurement,
        and structured audit logging.
        """
        start_time = time.perf_counter()
        
        # 1. Validate Input Schema
        try:
            validated_input = self.args_schema(**kwargs)
        except ValidationError as val_err:
            logger.error("Input validation failed for tool '%s': %s", self.name, val_err)
            raise ValueError(f"Invalid input to tool '{self.name}': {val_err}") from val_err

        # 2. Execute Core Tool Logic
        status = "SUCCESS"
        try:
            result = self._run(**validated_input.model_dump())
        except Exception as exc:
            status = "ERROR"
            latency_ms = (time.perf_counter() - start_time) * 1000.0
            log_agent_execution(
                request_id=request_id,
                user_id=None,
                agent="ToolRunner",
                tool=self.name,
                latency_ms=latency_ms,
                status=status,
                details={"error": str(exc)},
            )
            raise exc

        # 3. Validate Output Schema
        latency_ms = (time.perf_counter() - start_time) * 1000.0
        if not isinstance(result, self.return_schema):
            try:
                if isinstance(result, dict):
                    result = self.return_schema(**result)
                else:
                    raise TypeError(f"Tool '{self.name}' returned non-matching output type")
            except Exception as exc:
                logger.error("Output validation failed for tool '%s': %s", self.name, exc)
                raise ValueError(f"Output schema validation error for tool '{self.name}': {exc}") from exc

        log_agent_execution(
            request_id=request_id,
            user_id=None,
            agent="ToolRunner",
            tool=self.name,
            latency_ms=latency_ms,
            status=status,
            details={"output_type": self.return_schema.__name__},
        )

        return result

