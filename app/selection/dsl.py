from __future__ import annotations

from typing import Annotated, Any, Literal

from pydantic import BaseModel, ConfigDict, Field, ValidationError


class TimeRule(BaseModel):
    model_config = ConfigDict(extra="ignore")

    mode: Literal["current", "any", "all"] = "current"
    lookback: int = Field(default=1, ge=1, le=240)


class MetricReference(BaseModel):
    model_config = ConfigDict(extra="ignore")

    source_type: Literal["indicator"] = "indicator"
    metric_key: str
    output_key: str | None = None
    params: dict[str, Any] = Field(default_factory=dict)


class ConstantReference(BaseModel):
    model_config = ConfigDict(extra="ignore")

    source_type: Literal["value"] = "value"
    value: Any


OperandReference = Annotated[MetricReference | ConstantReference, Field(discriminator="source_type")]


class ConditionNode(BaseModel):
    model_config = ConfigDict(extra="ignore")

    node_type: Literal["condition"] = "condition"
    id: str
    label: str | None = None
    left: MetricReference
    operator: str
    right: OperandReference
    time_rule: TimeRule = Field(default_factory=TimeRule)
    weight: float = Field(default=1.0, ge=0)


class GroupNode(BaseModel):
    model_config = ConfigDict(extra="ignore")

    node_type: Literal["group"] = "group"
    id: str
    label: str | None = None
    combinator: Literal["and", "or", "not"] = "and"
    children: list["SelectionNode"] = Field(default_factory=list)


SelectionNode = Annotated[ConditionNode | GroupNode, Field(discriminator="node_type")]
GroupNode.model_rebuild()


class SelectionTemplatePayload(BaseModel):
    model_config = ConfigDict(extra="ignore")

    version: int = 1
    period: Literal["daily", "weekly", "monthly"] = "daily"
    name: str | None = None
    root: GroupNode
    metadata: dict[str, Any] = Field(default_factory=dict)


def validate_selection_template(payload: dict[str, Any]) -> SelectionTemplatePayload:
    return SelectionTemplatePayload.model_validate(payload)


def iter_condition_nodes(node: SelectionNode):
    if isinstance(node, ConditionNode):
        yield node
        return
    for child in node.children:
        yield from iter_condition_nodes(child)


def count_leaf_conditions(node: SelectionNode) -> int:
    return sum(1 for _ in iter_condition_nodes(node))


def try_validate_selection_template(payload: dict[str, Any]) -> tuple[SelectionTemplatePayload | None, ValidationError | None]:
    try:
        return validate_selection_template(payload), None
    except ValidationError as exc:
        return None, exc
