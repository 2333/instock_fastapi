from __future__ import annotations

import hashlib
import json
from typing import Any

from app.schemas.selection_schema import SavedScreenerDefinition
from app.services.screener_registry import get_registry_version, get_rule_registry_map

SAVED_SCREENER_SCHEMA_VERSION = 1


def _model_dump(value: Any) -> dict[str, Any]:
    if hasattr(value, "model_dump"):
        return value.model_dump(by_alias=True, exclude_none=True)
    if isinstance(value, dict):
        return dict(value)
    return {}


def _normalize_legacy_filter_payload(params: Any) -> dict[str, Any]:
    payload = _model_dump(params)
    nested_filters = payload.get("filters")
    if isinstance(nested_filters, dict):
        payload = nested_filters
    return {key: value for key, value in payload.items() if value is not None}


def _normalize_predicate_params(rule: dict[str, Any], params: dict[str, Any]) -> dict[str, Any]:
    raw_params = dict(params or {})
    schema = rule.get("param_schema") or {}
    normalized = dict(rule.get("default_params") or {})

    unknown_keys = set(raw_params) - set(schema)
    if unknown_keys:
        raise ValueError(
            f"predicate {rule['rule_key']} received unsupported params: {', '.join(sorted(unknown_keys))}"
        )

    for key, config in schema.items():
        value = raw_params.get(key, normalized.get(key))
        if value is None:
            if config.get("required"):
                raise ValueError(f"predicate {rule['rule_key']} requires params.{key}")
            continue

        expected_type = config.get("type")
        if expected_type == "integer":
            if isinstance(value, bool):
                raise ValueError(f"predicate {rule['rule_key']} requires integer params.{key}")
            try:
                value = int(value)
            except (TypeError, ValueError) as exc:
                raise ValueError(
                    f"predicate {rule['rule_key']} requires integer params.{key}"
                ) from exc
        elif expected_type == "number":
            if isinstance(value, bool):
                raise ValueError(f"predicate {rule['rule_key']} requires numeric params.{key}")
            try:
                value = float(value)
            except (TypeError, ValueError) as exc:
                raise ValueError(
                    f"predicate {rule['rule_key']} requires numeric params.{key}"
                ) from exc
        elif expected_type == "boolean":
            if not isinstance(value, bool):
                raise ValueError(f"predicate {rule['rule_key']} requires boolean params.{key}")
        elif expected_type == "string":
            value = str(value)

        if config.get("enum") and value not in config["enum"]:
            raise ValueError(f"predicate {rule['rule_key']} requires params.{key} in {config['enum']}")
        if config.get("min") is not None and value < config["min"]:
            raise ValueError(f"predicate {rule['rule_key']} requires params.{key} >= {config['min']}")
        if config.get("max") is not None and value > config["max"]:
            raise ValueError(f"predicate {rule['rule_key']} requires params.{key} <= {config['max']}")
        normalized[key] = value

    if rule["rule_key"] in {"macdBullish", "macdBearish"}:
        if normalized["fast_period"] >= normalized["slow_period"]:
            raise ValueError(f"predicate {rule['rule_key']} requires fast_period < slow_period")

    return normalized


def validate_definition(definition: Any) -> SavedScreenerDefinition:
    model = (
        definition
        if isinstance(definition, SavedScreenerDefinition)
        else SavedScreenerDefinition.model_validate(definition)
    )
    if model.registry_version != get_registry_version():
        raise ValueError(
            f"unsupported registry_version: {model.registry_version}"
        )
    registry = get_rule_registry_map()
    seen_filter_keys: dict[str, Any] = {}
    for predicate in model.root.children:
        rule = registry.get(predicate.rule_key)
        if rule is None:
            raise ValueError(f"unsupported rule_key: {predicate.rule_key}")
        if predicate.rule_key == "market":
            raise ValueError("market must be encoded in scope, not as a predicate")
        predicate.params = _normalize_predicate_params(rule, predicate.params)
        filter_key = rule["maps_to_filter_key"]
        if filter_key in seen_filter_keys:
            raise ValueError(f"duplicate predicate for filter_key: {filter_key}")
        seen_filter_keys[filter_key] = predicate.params["value"]
    if model.scope.market is not None and seen_filter_keys.get("market") not in (None, model.scope.market):
        raise ValueError("scope.market conflicts with market predicate")
    return model


def canonicalize_legacy_params(params: Any, scope: Any = None) -> dict[str, Any]:
    filters = _normalize_legacy_filter_payload(params)
    scope_payload = _model_dump(scope)
    if filters.get("market") is not None and scope_payload.get("market") is None:
        scope_payload["market"] = filters["market"]

    predicates: list[dict[str, Any]] = []
    for rule_key, rule in get_rule_registry_map().items():
        filter_key = rule["maps_to_filter_key"]
        if filters.get(filter_key) is None:
            continue
        if rule.get("value_type") == "boolean" and filters.get(filter_key) is False:
            continue
        if rule_key == "market":
            continue
        predicates.append(
            {
                "type": "predicate",
                "rule_key": rule_key,
                "params": {"value": filters[filter_key]},
            }
        )

    definition = {
        "kind": "saved_screener",
        "ast_version": 1,
        "registry_version": get_registry_version(),
        "scope": {key: value for key, value in scope_payload.items() if value is not None},
        "root": {"type": "group", "op": "all", "children": predicates},
    }
    return validate_definition(definition).model_dump(by_alias=True, exclude_none=True)


def definition_to_filters(definition: Any) -> dict[str, Any]:
    model = validate_definition(definition)
    filters: dict[str, Any] = {}
    registry = get_rule_registry_map()

    if model.scope.market is not None:
        filters["market"] = model.scope.market

    for predicate in model.root.children:
        filter_key = registry[predicate.rule_key]["maps_to_filter_key"]
        value = predicate.params.get("value")
        if value is not None:
            filters[filter_key] = value

    return filters


def build_definition_hash(definition: Any) -> str:
    model = validate_definition(definition)
    payload = model.model_dump(by_alias=True, exclude_none=True)
    canonical_json = json.dumps(payload, sort_keys=True, separators=(",", ":"), ensure_ascii=True)
    return hashlib.sha256(canonical_json.encode("utf-8")).hexdigest()


def get_resolved_predicates(definition: Any) -> list[dict[str, Any]]:
    model = validate_definition(definition)
    registry = get_rule_registry_map()
    resolved: list[dict[str, Any]] = []

    for predicate in model.root.children:
        rule = registry[predicate.rule_key]
        params = dict(rule.get("default_params") or {})
        params.update(predicate.params)
        resolved.append(
            {
                "rule_key": predicate.rule_key,
                "params": params,
                "rule": rule,
            }
        )

    return resolved


def normalize_saved_screener_payload(
    *,
    params: Any = None,
    definition: Any = None,
    scope: Any = None,
) -> tuple[dict[str, Any], dict[str, Any], str]:
    if definition is None:
        raw_payload = _model_dump(params)
        if raw_payload.get("kind") == "saved_screener":
            canonical_definition = validate_definition(raw_payload).model_dump(
                by_alias=True, exclude_none=True
            )
        else:
            canonical_definition = canonicalize_legacy_params(params, scope=scope)
    else:
        raw_definition = _model_dump(definition)
        scope_payload = _model_dump(scope)
        raw_scope = dict(raw_definition.get("scope") or {})
        for key, value in scope_payload.items():
            if value is not None and raw_scope.get(key) != value:
                raw_scope[key] = value
        if raw_scope:
            raw_definition["scope"] = raw_scope
        canonical_definition = validate_definition(raw_definition).model_dump(
            by_alias=True, exclude_none=True
        )

    filters = definition_to_filters(canonical_definition)
    definition_hash = build_definition_hash(canonical_definition)
    return canonical_definition, filters, definition_hash


def build_saved_screener_persistence(
    *,
    params: Any = None,
    definition: Any = None,
    scope: Any = None,
    existing_params: Any = None,
    existing_definition_version: int | None = None,
) -> dict[str, Any]:
    canonical_definition, compatible_params, definition_hash = normalize_saved_screener_payload(
        params=params,
        definition=definition,
        scope=scope,
    )

    normalized_existing_definition: dict[str, Any] | None = None
    definition_changed = existing_params is None
    if existing_params is not None:
        normalized_existing_definition, _, _ = normalize_saved_screener_payload(params=existing_params)
        definition_changed = normalized_existing_definition != canonical_definition

    definition_version = max(int(existing_definition_version or 1), 1)
    if existing_params is None:
        definition_version = 1
    elif definition_changed:
        definition_version += 1

    return {
        "definition": canonical_definition,
        "params": compatible_params,
        "schema_version": SAVED_SCREENER_SCHEMA_VERSION,
        "definition_version": definition_version,
        "definition_hash": definition_hash,
        "definition_changed": definition_changed,
    }


def get_saved_screener_schema_version() -> int:
    return SAVED_SCREENER_SCHEMA_VERSION
