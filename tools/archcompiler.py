#!/usr/bin/env python3
import sys, json, datetime, argparse
from pathlib import Path
import pathlib
from typing import Any, Dict, List, Optional, Tuple

def _strip_null_values(obj: Any) -> Any:
    """
    Recursively remove null/None values from the spec before processing.

    - Dict: removes keys whose value is None; recurses into non-None values
    - List: removes None items; recurses into non-None items
    - Scalar: returned as-is

    Rationale: explicit `null` in YAML (e.g. `rpo_minutes: null`) is
    indistinguishable from "user left this blank while templating". Stripping
    lets the defaults+assumptions machinery treat it identically to an omitted
    field, so the compiled output gets a real default value and tracks it as an
    assumption rather than propagating null through rule evaluation.
    """
    if isinstance(obj, dict):
        return {k: _strip_null_values(v) for k, v in obj.items() if v is not None}
    if isinstance(obj, list):
        return [_strip_null_values(item) for item in obj if item is not None]
    return obj


def _load_spec(path: pathlib.Path) -> Dict[str, Any]:
    suffix = path.suffix.lower()
    if suffix in (".yaml", ".yml"):
        try:
            import yaml  # type: ignore
        except Exception:
            raise SystemExit(
                "Missing dependency 'PyYAML'.\n"
                "Install with:\n"
                "  python3 -m pip install -r tools/requirements.txt\n"
            )
        loaded = yaml.safe_load(path.read_text(encoding="utf-8"))
        if not isinstance(loaded, dict):
            raise SystemExit("YAML spec must be a mapping/object at top-level.")
        return loaded
    raise SystemExit(f"Unsupported spec format: {suffix} (only .yaml/.yml are supported)")

def _validate_spec_schema(spec: Dict[str, Any]) -> None:
    """
    Validate input spec against canonical schema.
    On failure: prints the full annotated input spec (with inline ❌ comments on
    violating fields) to stdout, then a per-error summary, then exits with code 1.
    """
    try:
        import jsonschema
        from jsonschema import Draft7Validator
        import yaml
    except ImportError as e:
        print(f"Warning: Skipping schema validation (missing {e.name})")
        return

    schema_path = pathlib.Path(__file__).parent.parent / "schemas" / "canonical-schema.yaml"
    if not schema_path.exists():
        print("Warning: canonical-schema.yaml not found, skipping validation")
        return

    try:
        schema = yaml.safe_load(schema_path.read_text(encoding="utf-8"))
    except Exception as e:
        print(f"Warning: Could not load schema: {e}")
        return

    # Collect ALL validation errors (not just the first)
    errors = list(Draft7Validator(schema).iter_errors(spec))
    if not errors:
        return

    # Build annotation map: JSON pointer -> "❌ <message>"
    # When multiple errors point to the same path, combine them.
    annotation_map: Dict[str, str] = {}
    for err in errors:
        path_parts = list(err.absolute_path)
        pointer = "/" + "/".join(str(p) for p in path_parts) if path_parts else "/"
        if pointer in annotation_map:
            annotation_map[pointer] += f"; {err.message}"
        else:
            annotation_map[pointer] = f"❌ {err.message}"

    # Print annotated spec (raw input, no assumptions injected yet)
    spec_to_show = {k: v for k, v in spec.items() if k != "assumptions"}
    print("\n".join(_render_annotated_yaml(spec_to_show, annotation_map)))
    print()

    # Print per-error summary (reuses existing _format_validation_error for extra hints)
    count = len(errors)
    label = "Error" if count == 1 else "Errors"
    print(f"❌ Schema Validation {label} ({count}):")
    for err in errors:
        print(_format_validation_error(err, spec))
        print()

    sys.exit(1)


def _format_validation_error(error: Any, spec: Dict[str, Any]) -> str:
    """
    Format jsonschema validation error with helpful suggestions.
    """
    import difflib

    # Get error location path
    path_parts = list(error.absolute_path)
    location = "/" + "/".join(str(p) for p in path_parts) if path_parts else "/root"

    # Build error message
    lines = []
    lines.append(f"   {error.message}")
    lines.append(f"   Location: {location}")

    # If it's an additionalProperties error, suggest correct field name
    if "Additional properties are not allowed" in error.message:
        # Extract the unknown field name
        unknown_fields = []
        if error.validator == "additionalProperties":
            # Find the unknown field in the spec at this location
            node = spec
            for part in path_parts:
                node = node.get(part) if isinstance(node, dict) else node

            if isinstance(node, dict):
                # Get valid properties from schema
                schema_props = error.schema.get("properties", {}).keys()
                for field in node.keys():
                    if field not in schema_props:
                        unknown_fields.append(field)

                        # Suggest similar field names
                        matches = difflib.get_close_matches(field, schema_props, n=1, cutoff=0.6)
                        if matches:
                            lines.append(f"   Did you mean: {matches[0]}?")

                        # Show valid fields
                        lines.append(f"\n   Valid fields for {path_parts[-1] if path_parts else 'root'}:")
                        for prop in sorted(schema_props):
                            lines.append(f"   - {prop}")

    return "\n".join(lines)


def _validate_semantic_consistency(spec: Dict[str, Any]) -> None:
    """
    Validate logical consistency of spec fields (catch contradictions).

    Checks:
    1. tenantCount vs multi_tenancy flag
    2. constraints.saas-providers vs constraints.disallowed-saas-providers overlap

    Note: messaging_delivery_guarantee vs async_messaging is enforced by
    requires_constraints on the three delivery-guarantee consumer patterns
    (queue-consumer-idempotency, exactly-once-transactional-consumer,
    async-fire-and-forget) rather than as a compiler heuristic.

    Raises SystemExit if inconsistencies detected.
    """
    errors = []

    # Check 1: tenantCount vs multi_tenancy flag
    multi_tenancy = spec.get("constraints", {}).get("features", {}).get("multi_tenancy", False)
    tenant_count = spec.get("constraints", {}).get("tenantCount")
    if tenant_count is not None:
        if tenant_count > 1 and not multi_tenancy:
            errors.append(
                f"❌ Logical Contradiction:\n"
                f"   constraints.tenantCount is {tenant_count} (multiple tenants)\n"
                f"   but constraints.features.multi_tenancy is false\n"
                f"\n"
                f"   If you have multiple tenants, multi-tenancy must be enabled.\n"
                f"\n"
                f"   Fix: Set constraints.features.multi_tenancy to true"
            )
        elif tenant_count == 1 and multi_tenancy:
            errors.append(
                f"❌ Logical Contradiction:\n"
                f"   constraints.tenantCount is 1 (single tenant)\n"
                f"   but constraints.features.multi_tenancy is true\n"
                f"\n"
                f"   If you have only one tenant, multi-tenancy should be disabled.\n"
                f"\n"
                f"   Fix: Set constraints.features.multi_tenancy to false,\n"
                f"   or increase constraints.tenantCount if you plan to support multiple tenants"
            )

    # Check 2: saas-providers and disallowed-saas-providers must not overlap
    saas_allowed = set(spec.get("constraints", {}).get("saas-providers", []))
    saas_disallowed = set(spec.get("constraints", {}).get("disallowed-saas-providers", []))
    overlap = saas_allowed & saas_disallowed
    if overlap:
        errors.append(
            f"❌ Logical Contradiction:\n"
            f"   constraints.saas-providers and constraints.disallowed-saas-providers overlap.\n"
            f"\n"
            f"   Conflicting providers: {', '.join(sorted(overlap))}\n"
            f"\n"
            f"   A provider cannot be both allowed and disallowed.\n"
            f"\n"
            f"   Fix: Remove the overlapping provider(s) from one of the two lists."
        )

    if errors:
        raise SystemExit("\n" + "\n\n".join(errors) + "\n")


def _validate_required_spec_rules(
    selected_pattern_ids: List[str],
    patterns: Dict[str, Any],
    spec: Dict[str, Any]
) -> List[Dict[str, Any]]:
    """
    For each selected pattern, validate all requires_nfr and requires_constraints
    rules against the spec. Collects ALL failures (not fail-fast).

    Returns list of violation dicts: {pid, path, op, value, reason}
    Caller is responsible for printing errors and exiting.
    """
    violations = []
    for pid in selected_pattern_ids:
        pattern = patterns[pid]
        all_rules = (
            pattern.get("requires_nfr", []) +
            pattern.get("requires_constraints", [])
        )
        for rule in all_rules:
            if not _evaluate_rule(spec, rule):
                violations.append({
                    "pid": pid,
                    "path": rule["path"],
                    "op": rule["op"],
                    "value": rule["value"],
                    "reason": rule["reason"],
                })
    return violations


def _build_error_annotation_map(
    violations: List[Dict[str, Any]],
    honored_rules: Dict[str, Any],
    canonical_schema: Dict[str, Any],
) -> Dict[str, str]:
    """
    Build path -> inline comment map for annotated error output.

    Two passes:
    1. Violation paths  ->  "❌ pid1, pid2"
    2. Activation gates of violating patterns  ->  "pid1, pid2"
       Uses same rule selection logic as _format_suggestions:
       - == gates from constraints or NFR (explicit activation, e.g. compliance == true)
       - "in" gates from constraints only, when the allowed list is a strict subset
         of the schema enum covering < 70% of options (genuinely restrictive)
       - >=/<= gates from constraints or NFR (threshold activation gates)

    Returns dict mapping JSON pointer path -> comment string (without leading #).
    """
    violation_by_path: Dict[str, List[str]] = {}
    for v in violations:
        violation_by_path.setdefault(v["path"], []).append(v["pid"])

    violating_pids = {v["pid"] for v in violations}

    activation_by_path: Dict[str, List[str]] = {}
    for pid in violating_pids:
        rules_for_pid = honored_rules.get(pid, {})
        for kind in ("constraints", "nfr"):
            for rule in rules_for_pid.get(kind, []):
                op = rule.get("op")
                path = rule["path"]
                if path in violation_by_path:
                    continue
                include = False
                if op == "==":
                    include = True
                elif op == "in" and kind == "constraints":
                    allowed = rule.get("value", [])
                    if allowed not in ([True, False], [False, True]):
                        field_info = _lookup_schema_field_info(canonical_schema, path)
                        schema_opts = {o.strip() for o in field_info.split("|")} if field_info != "unknown" else None
                        pattern_opts = {str(v) for v in allowed}
                        if schema_opts is None or (pattern_opts < schema_opts and len(pattern_opts) / len(schema_opts) < 0.7):
                            include = True
                elif op in (">=", "<="):
                    include = True
                if include:
                    activation_by_path.setdefault(path, []).append(pid)

    result: Dict[str, str] = {}
    for path, pids in violation_by_path.items():
        result[path] = "❌ " + ", ".join(sorted(pids))
    for path, pids in activation_by_path.items():
        result[path] = ", ".join(sorted(pids))
    return result


def _annotated_yaml_scalar(value: Any) -> str:
    """Format a scalar value for YAML output."""
    if isinstance(value, bool):
        return "true" if value else "false"
    if value is None:
        return "null"
    if isinstance(value, (int, float)):
        return str(value)
    s = str(value)
    needs_quotes = (
        ":" in s or "#" in s or s.startswith("-") or s.startswith("*")
        or s in ("true", "false", "null", "yes", "no", "on", "off", "~")
        or s != s.strip()
    )
    if needs_quotes:
        escaped = s.replace("\\", "\\\\").replace('"', '\\"')
        return f'"{escaped}"'
    return s


def _render_annotated_yaml(
    obj: Any,
    annotations: Dict[str, str],
    path: str = "",
    indent: int = 0,
) -> List[str]:
    """
    Recursively render obj as YAML lines with inline comments from annotations.

    annotations: maps JSON pointer (e.g. "/nfr/rpo_minutes") -> comment text
    Returns list of YAML lines (no trailing newline per line).
    """
    lines: List[str] = []
    prefix = "  " * indent

    if isinstance(obj, dict):
        for key, value in obj.items():
            current_path = f"{path}/{key}"
            comment = annotations.get(current_path, "")
            comment_str = f"  # {comment}" if comment else ""

            if value is None:
                lines.append(f"{prefix}{key}: null{comment_str}")
            elif isinstance(value, dict):
                lines.append(f"{prefix}{key}:{comment_str}")
                lines.extend(_render_annotated_yaml(value, annotations, current_path, indent + 1))
            elif isinstance(value, list):
                lines.append(f"{prefix}{key}:{comment_str}")
                lines.extend(_render_annotated_yaml(value, annotations, current_path, indent + 1))
            else:
                scalar = _annotated_yaml_scalar(value)
                lines.append(f"{prefix}{key}: {scalar}{comment_str}")

    elif isinstance(obj, list):
        for i, item in enumerate(obj):
            current_path = f"{path}/{i}"
            comment = annotations.get(current_path, "")
            comment_str = f"  # {comment}" if comment else ""

            if item is None:
                lines.append(f"{prefix}- null{comment_str}")
            elif isinstance(item, dict):
                items_rendered = _render_annotated_yaml(item, annotations, current_path, indent + 1)
                if items_rendered:
                    first = items_rendered[0].lstrip()
                    rest = items_rendered[1:]
                    lines.append(f"{prefix}- {first}{comment_str}")
                    lines.extend(rest)
            else:
                scalar = _annotated_yaml_scalar(item)
                lines.append(f"{prefix}- {scalar}{comment_str}")
    else:
        lines.append(f"{prefix}{_annotated_yaml_scalar(obj)}")

    return lines


def _format_error_summary(violations: List[Dict[str, Any]]) -> str:
    """Format the error summary block printed after the annotated spec."""
    lines = ["❌ Constraints/NFRs trade-off requirements not met:"]
    for v in violations:
        lines.append(f"  [{v['pid']}] {v['path']} {v['op']} {v['value']}")
        lines.append(f"  → {v['reason']}")
    return "\n".join(lines)


def _lookup_schema_field_info(canonical_schema: Dict[str, Any], path: str) -> str:
    """
    Look up a JSON pointer path in the canonical schema and return field type/enum info.

    Traverses schema["properties"][seg0]["properties"][seg1]... following the path.
    Returns pipe-joined enum values, "type (min: X)" for numerics, "boolean", or "unknown".

    Examples:
        "/nfr/security/auth"          → "oauth2_oidc | api_key | jwt | mtls | saml | password | n/a"
        "/nfr/rpo_minutes"            → "integer (min: 0)"
        "/nfr/availability/target"    → "number (0–1)"
        "/nfr/security/audit_logging" → "boolean"
        "/bad/path"                   → "unknown"
    """
    segments = [s for s in path.split("/") if s]
    if not segments:
        return "unknown"

    props = canonical_schema.get("properties", {})
    field_node = None
    for i, seg in enumerate(segments):
        if not isinstance(props, dict) or seg not in props:
            return "unknown"
        field_node = props[seg]
        if i < len(segments) - 1:
            props = field_node.get("properties", {})

    if not isinstance(field_node, dict):
        return "unknown"

    if "enum" in field_node:
        return " | ".join(str(v) for v in field_node["enum"])

    # Handle anyOf (e.g., nullable enum: anyOf: [{type: string, enum: [...]}, {type: null}])
    if "anyOf" in field_node:
        for sub in field_node["anyOf"]:
            if isinstance(sub, dict) and "enum" in sub:
                return " | ".join(str(v) for v in sub["enum"])
        for sub in field_node["anyOf"]:
            if isinstance(sub, dict) and sub.get("type") not in (None, "null"):
                return sub.get("type", "unknown")

    field_type = field_node.get("type", "unknown")
    min_val = field_node.get("minimum")
    max_val = field_node.get("maximum")

    if field_type in ("integer", "number"):
        if min_val is not None and max_val is not None:
            return f"{field_type} ({min_val}\u2013{max_val})"
        if min_val is not None:
            return f"{field_type} (min: {min_val})"
        if max_val is not None:
            return f"{field_type} (max: {max_val})"

    return field_type


def _format_suggestions(
    violations: List[Dict[str, Any]],
    honored_rules: Dict[str, Any],
    canonical_schema: Dict[str, Any],
) -> str:
    """
    Build '💡 Suggestions' block — grouped by violating pattern.

    For each violating pattern, finds op=="==" enum gates and op>=/op<= numeric
    threshold gates in honored_rules (the activation gates that selected it).
    - == gates: show current value + available enum options
    - >= / <= gates (constraints OR nfr): show "field = value (threshold: op N)"

    Returns empty string if no activation gates exist for any violating pattern.
    """
    # Deduplicate pids while preserving first-seen order
    seen: Set[str] = set()
    violating_pids: List[str] = []
    for v in violations:
        if v["pid"] not in seen:
            seen.add(v["pid"])
            violating_pids.append(v["pid"])

    blocks: List[str] = []
    for pid in violating_pids:
        rules_for_pid = honored_rules.get(pid, {})
        gate_rules = []
        for kind in ("constraints", "nfr"):
            for r in rules_for_pid.get(kind, []):
                op = r.get("op")
                if op == "==":
                    # Explicit equality gate from either constraints or NFR (e.g. compliance == true)
                    gate_rules.append(r)
                elif op == "in" and kind == "constraints":
                    # Only show "in" rules from constraints, and only when the allowed list
                    # is a strict subset of the schema enum (i.e. actually excludes options)
                    allowed = r.get("value", [])
                    if allowed not in ([True, False], [False, True]):
                        field_info = _lookup_schema_field_info(canonical_schema, r["path"])
                        schema_opts = {o.strip() for o in field_info.split("|")} if field_info != "unknown" else None
                        pattern_opts = {str(v) for v in allowed}
                        if schema_opts is None or (pattern_opts < schema_opts and len(pattern_opts) / len(schema_opts) < 0.7):
                            gate_rules.append(r)
                elif op in (">=", "<="):
                    # Numeric threshold from constraints or NFR (activation gate)
                    gate_rules.append(r)
        if not gate_rules:
            continue

        lines = [f"  {pid} activated by:"]
        for rule in gate_rules:
            op = rule["op"]
            value = rule["value"]
            value_str = f'"{value}"' if isinstance(value, str) else str(value).lower()
            if op == "==":
                field_info = _lookup_schema_field_info(canonical_schema, rule["path"])
                lines.append(f"    {rule['path']} = {value_str}")
                if field_info not in ("boolean", "unknown"):
                    lines.append(f"    Available: {field_info}")
            elif op == "in":
                # Enum membership gate — show the pattern's restricted list and full schema options
                allowed_str = " | ".join(str(v) for v in value) if isinstance(value, list) else value_str
                field_info = _lookup_schema_field_info(canonical_schema, rule["path"])
                lines.append(f"    {rule['path']} in [{allowed_str}]")
                if field_info not in ("boolean", "unknown"):
                    lines.append(f"    Available: {field_info}")
            else:
                # Numeric threshold gate — show threshold condition, no alternatives
                lines.append(f"    {rule['path']} = {value_str} (threshold: {op} {value_str})")
        blocks.append("\n".join(lines))

    if not blocks:
        return ""

    header = "💡 Suggestions — consider changing these activation fields:"
    return header + "\n" + "\n\n".join(blocks)


def _dump_yaml(obj: Any) -> str:
    try:
        import yaml  # type: ignore
        return yaml.safe_dump(obj, sort_keys=False)
    except Exception:
        # Fallback: JSON if yaml isn't available
        return json.dumps(obj, indent=2)


def _json_pointer_get(doc: Any, path: str) -> Any:
    """Very small JSON Pointer getter for paths like /a/b/c."""
    if not path.startswith("/"):
        return None
    node = doc
    for part in [p for p in path.lstrip("/").split("/") if p != ""]:
        if isinstance(node, dict):
            node = node.get(part)
        elif isinstance(node, list) and part.isdigit():
            idx = int(part)
            node = node[idx] if 0 <= idx < len(node) else None
        else:
            return None
    return node

def _json_pointer_set(doc: Dict[str, Any], path: str, value: Any) -> None:
    """Set value at JSON pointer path; creates dicts as needed."""
    if not path.startswith("/"):
        raise ValueError("path must start with /")
    parts = [p for p in path.lstrip("/").split("/") if p != ""]
    node: Any = doc
    for i, part in enumerate(parts):
        is_last = (i == len(parts) - 1)
        if is_last:
            if isinstance(node, dict):
                node[part] = value
            else:
                raise ValueError(f"Cannot set path {path} on non-dict node")
        else:
            if isinstance(node, dict):
                if part not in node or not isinstance(node[part], dict):
                    node[part] = {}
                node = node[part]
            else:
                raise ValueError(f"Cannot traverse path {path} on non-dict node")

def _dedupe(seq: List[Any]) -> List[Any]:
    seen = set()
    out = []
    for x in seq:
        key = json.dumps(x, sort_keys=True) if isinstance(x, (dict, list)) else str(x)
        if key not in seen:
            seen.add(key)
            out.append(x)
    return out

def _load_question_bank(root: pathlib.Path, qb_rel: str) -> Dict[str, Dict[str, str]]:
    qb_path = (root / qb_rel).resolve()
    if not qb_path.exists():
        return {}
    qb = json.loads(qb_path.read_text(encoding="utf-8"))
    qmap = {}
    for q in (qb.get("questions") or []):
        if isinstance(q, dict) and q.get("id"):
            qmap[q["id"]] = q
    return qmap

def _load_patterns(root: pathlib.Path) -> Dict[str, Dict[str, Any]]:
    patterns: Dict[str, Dict[str, Any]] = {}
    for f in (root / "patterns").glob("*.json"):
        try:
            p = json.loads(f.read_text(encoding="utf-8"))
            if isinstance(p, dict) and p.get("id"):
                patterns[p["id"]] = p
        except Exception:
            pass
    return patterns


def _load_canonical_schema() -> Dict[str, Any]:
    """Load canonical-schema.yaml, return {} on failure (suggestions silently omitted)."""
    schema_path = pathlib.Path(__file__).parent.parent / "schemas" / "canonical-schema.yaml"
    try:
        import yaml  # type: ignore
        return yaml.safe_load(schema_path.read_text(encoding="utf-8"))
    except Exception:
        return {}


def _load_defaults(defaults_path: str = "config/defaults.yaml") -> Dict[str, Any]:
    """
    Load static defaults from config file.

    Returns: Dictionary of default values for all spec fields
    """
    try:
        import yaml  # type: ignore
    except ImportError:
        raise SystemExit(
            "Missing dependency 'PyYAML' for defaults loading.\n"
            "Install with: python3 -m pip install PyYAML"
        )

    defaults_file = pathlib.Path(defaults_path)

    if not defaults_file.exists():
        raise SystemExit(f"Defaults file not found: {defaults_path}")

    with open(defaults_file) as f:
        defaults = yaml.safe_load(f)

    return defaults

def _merge_nfr_with_defaults(spec_nfr: Dict, default_nfr: Dict) -> Dict:
    """
    Merge NFR section recursively, applying defaults AND tracking them.

    CRITICAL: Modifies spec_nfr in-place (applies defaults) AND returns assumptions.
    """
    assumptions = {}

    for key, default_value in default_nfr.items():
        if key not in spec_nfr:
            # Apply default to spec AND track in assumptions
            if isinstance(default_value, dict):
                spec_nfr[key] = dict(default_value)  # Deep copy
            else:
                spec_nfr[key] = default_value
            assumptions[key] = default_value
        elif isinstance(default_value, dict) and isinstance(spec_nfr.get(key), dict):
            # Nested object, recurse
            nested_assumptions = _merge_nfr_with_defaults(spec_nfr[key], default_value)
            if nested_assumptions:
                assumptions[key] = nested_assumptions

    return assumptions

def _merge_cost_with_defaults(spec_cost: Dict, default_cost: Dict) -> Dict:
    """
    Merge cost section recursively, applying defaults AND tracking them.

    CRITICAL: Modifies spec_cost in-place (applies defaults) AND returns assumptions.
    """
    assumptions = {}

    for key, default_value in default_cost.items():
        if key not in spec_cost:
            # Apply default to spec AND track in assumptions
            if isinstance(default_value, dict):
                spec_cost[key] = dict(default_value)  # Deep copy
            else:
                spec_cost[key] = default_value
            assumptions[key] = default_value
        elif isinstance(default_value, dict) and isinstance(spec_cost.get(key), dict):
            nested_assumptions = _merge_cost_with_defaults(spec_cost[key], default_value)
            if nested_assumptions:
                assumptions[key] = nested_assumptions

    return assumptions

def _merge_nfr_with_existing_assumptions(
    spec_nfr: Dict[str, Any],
    default_nfr: Dict[str, Any],
    existing_assumptions_nfr: Dict[str, Any]
) -> Dict[str, Any]:
    """
    Merge missing NFR fields into existing assumptions (recompilation scenario).

    Preserves user-provided assumption values, only merges MISSING fields from defaults.

    Args:
        spec_nfr: Top-level NFR from spec
        default_nfr: Default NFR values
        existing_assumptions_nfr: User's existing assumptions.nfr

    Returns:
        Updated assumptions_nfr with missing fields merged
    """
    import copy
    assumptions = copy.deepcopy(existing_assumptions_nfr)

    def _deep_merge_from_assumptions(target: dict, source: dict) -> None:
        """Recursively copy missing keys from source (assumptions) into target (spec).

        Uses deepcopy when adding new dict values so that target and source never
        share the same mutable objects — preventing _remove_redundant_assumptions
        from accidentally deleting keys from target when it cleans source.
        """
        for key, src_value in source.items():
            if key not in target:
                target[key] = copy.deepcopy(src_value)
            elif isinstance(src_value, dict) and isinstance(target.get(key), dict):
                # Both exist as dicts — recurse to fill missing sub-keys
                _deep_merge_from_assumptions(target[key], src_value)

    # CRITICAL: Copy all assumption values (recursively) to spec if not already there.
    _deep_merge_from_assumptions(spec_nfr, assumptions)

    # Now merge missing fields from defaults
    for key, default_value in default_nfr.items():
        if key not in assumptions:
            # Missing from assumptions → merge it
            if isinstance(default_value, dict):
                # Nested section (e.g., availability, latency)
                spec_section = spec_nfr.setdefault(key, {})
                assumed_section = {}

                for nested_key, nested_default in default_value.items():
                    if nested_key not in spec_section:
                        spec_section[nested_key] = nested_default
                        assumed_section[nested_key] = nested_default

                if assumed_section:
                    assumptions[key] = assumed_section
            else:
                # Top-level field
                if key not in spec_nfr:
                    spec_nfr[key] = default_value
                assumptions[key] = default_value
        elif isinstance(default_value, dict) and key in assumptions:
            # Section exists in assumptions, merge missing nested fields
            assumed_section = assumptions[key]
            spec_section = spec_nfr.setdefault(key, {})

            for nested_key, nested_default in default_value.items():
                if nested_key not in assumed_section:
                    if nested_key not in spec_section:
                        # Neither user-provided nor in existing assumptions — apply default
                        spec_section[nested_key] = nested_default
                        assumed_section[nested_key] = nested_default
                    # else: user provided this key at top-level; do NOT add it to
                    # assumptions (it belongs to the user, not the compiler).

    return assumptions

def _merge_cost_with_existing_assumptions(
    spec_cost: Dict[str, Any],
    default_cost: Dict[str, Any],
    existing_assumptions_cost: Dict[str, Any]
) -> Dict[str, Any]:
    """
    Merge missing cost fields into existing assumptions (recompilation scenario).

    Preserves user-provided assumption values, only merges MISSING fields from defaults.

    Args:
        spec_cost: Top-level cost from spec
        default_cost: Default cost values
        existing_assumptions_cost: User's existing assumptions.cost

    Returns:
        Updated assumptions_cost with missing fields merged
    """
    import copy
    assumptions = copy.deepcopy(existing_assumptions_cost)

    def _deep_merge_cost(target: dict, source: dict) -> None:
        for k, sv in source.items():
            if k not in target:
                target[k] = copy.deepcopy(sv)
            elif isinstance(sv, dict) and isinstance(target.get(k), dict):
                _deep_merge_cost(target[k], sv)

    # CRITICAL: Copy all assumption values (recursively) to spec if not already there.
    _deep_merge_cost(spec_cost, assumptions)

    # Now merge missing fields from defaults
    for key, default_value in default_cost.items():
        if key not in assumptions:
            # Missing from assumptions → merge it
            if isinstance(default_value, dict):
                # Nested section (e.g., intent, ceilings)
                spec_section = spec_cost.setdefault(key, {})
                assumed_section = {}

                for nested_key, nested_default in default_value.items():
                    if nested_key not in spec_section:
                        spec_section[nested_key] = nested_default
                        assumed_section[nested_key] = nested_default

                if assumed_section:
                    assumptions[key] = assumed_section
            else:
                # Top-level field
                if key not in spec_cost:
                    spec_cost[key] = default_value
                assumptions[key] = default_value
        elif isinstance(default_value, dict) and key in assumptions:
            # Section exists in assumptions, merge missing nested fields
            assumed_section = assumptions[key]
            spec_section = spec_cost.setdefault(key, {})

            for nested_key, nested_default in default_value.items():
                if nested_key not in assumed_section:
                    if nested_key not in spec_section:
                        spec_section[nested_key] = nested_default
                    assumed_section[nested_key] = nested_default

    return assumptions

def _validate_user_pattern_configs(spec: Dict[str, Any], patterns: Dict[str, Dict[str, Any]]) -> None:
    """
    Validate user-provided pattern configs are complete.

    Rule: If user provides config for a pattern, they must provide ALL fields
    defined in the pattern's configSchema.properties.

    No partial configs allowed - either provide everything or nothing.

    Raises:
        SystemExit: If validation fails with helpful error message
    """
    user_patterns = spec.get("patterns", {})
    if not user_patterns:
        # No user-provided patterns to validate
        return

    errors = []

    for pattern_id, user_config in user_patterns.items():
        # Check pattern exists in registry
        if pattern_id not in patterns:
            errors.append({
                "pattern": pattern_id,
                "error": "Pattern not found in registry",
                "details": f"Pattern '{pattern_id}' does not exist in the pattern registry"
            })
            continue

        pattern = patterns[pattern_id]
        config_schema = pattern.get("configSchema")

        # If pattern has no configSchema, accept any config (no validation)
        if not config_schema:
            continue

        # Get all required fields from configSchema.properties
        schema_properties = config_schema.get("properties", {})
        if not schema_properties:
            # No properties defined, accept any config
            continue

        required_fields = set(schema_properties.keys())
        provided_fields = set(user_config.keys()) if isinstance(user_config, dict) else set()

        # Check for missing fields
        missing_fields = required_fields - provided_fields

        # Check for extra fields not in schema
        extra_fields = provided_fields - required_fields

        if missing_fields or extra_fields:
            error_detail = {
                "pattern": pattern_id,
                "error": "Incomplete or invalid pattern configuration"
            }

            if missing_fields:
                error_detail["missing_fields"] = sorted(missing_fields)

            if extra_fields:
                error_detail["extra_fields"] = sorted(extra_fields)

            error_detail["required_fields"] = sorted(required_fields)
            errors.append(error_detail)

    # If any errors, format and raise SystemExit
    if errors:
        error_lines = ["❌ Pattern Configuration Validation Failed:\n"]

        for err in errors:
            pattern_name = err["pattern"]

            if err["error"] == "Pattern not found in registry":
                error_lines.append(f"  • Pattern '{pattern_name}': {err['details']}")
            else:
                parts = []
                if "missing_fields" in err:
                    parts.append(f"Missing required fields: {', '.join(err['missing_fields'])}")
                if "extra_fields" in err:
                    parts.append(f"Unknown fields: {', '.join(err['extra_fields'])}")

                error_lines.append(f"  • Pattern '{pattern_name}': {'; '.join(parts)}")

        error_lines.append("\n💡 Tip: Either provide ALL fields from configSchema or omit pattern config entirely.")
        error_lines.append("       Partial configs are not allowed.")

        raise SystemExit("\n".join(error_lines))

def _remove_redundant_assumptions(
    assumptions_section: Dict[str, Any],
    spec_section: Dict[str, Any],
    user_provided_keys: set
) -> None:
    """
    Remove fields from assumptions that are explicitly provided by user in spec.

    When user provides a field at top-level AND it exists in assumptions,
    the assumption is redundant (user likely forgot to clean it up).

    This function removes such redundant fields from assumptions, but only for
    fields that the user explicitly provided (not fields copied from assumptions).

    Args:
        assumptions_section: The assumptions subsection (e.g., assumptions.constraints)
        spec_section: The top-level spec section (e.g., spec.constraints)
        user_provided_keys: Set of keys that user explicitly provided at top-level

    Mutates assumptions_section in-place.
    """
    if not assumptions_section or not spec_section:
        return

    # Find keys that exist in both spec and assumptions AND were explicitly provided by user
    redundant_keys = []
    for key in list(assumptions_section.keys()):
        if key in spec_section and key in user_provided_keys:
            # User explicitly provided this field - it's redundant in assumptions
            # Check if it's a nested dict that needs recursive cleanup
            if isinstance(assumptions_section[key], dict) and isinstance(spec_section[key], dict):
                # Compute which sub-keys were user-provided.  After merging, spec contains
                # both user values and assumption-derived copies; distinguish them by:
                #   (a) sub-key not in assumptions at all → user introduced it, OR
                #   (b) sub-key value in spec DIFFERS from assumption value → user overrode it.
                # Keys whose spec value equals the assumption value were copied in by the
                # deep-merge helper and should NOT be treated as user-provided.
                nested_user_keys = set()
                for sub_key, spec_val in spec_section[key].items():
                    if sub_key not in assumptions_section[key]:
                        nested_user_keys.add(sub_key)
                    elif spec_val != assumptions_section[key][sub_key]:
                        nested_user_keys.add(sub_key)
                _remove_redundant_assumptions(assumptions_section[key], spec_section[key], nested_user_keys)
                # If nested dict is now empty, mark for removal
                if not assumptions_section[key]:
                    redundant_keys.append(key)
            else:
                # Simple field - user provided it, remove from assumptions
                redundant_keys.append(key)

    # Remove redundant keys
    for key in redundant_keys:
        del assumptions_section[key]


def _merge_with_defaults(spec: Dict[str, Any], defaults: Dict[str, Any]) -> Dict[str, Any]:
    """
    Merge spec with defaults, tracking assumptions.

    CRITICAL: Only track defaulted fields in assumptions, NOT all defaults.

    NEW BEHAVIOR (2026-02-24):
    If spec already has assumptions section (recompilation scenario):
    - Preserve existing assumption values (don't overwrite with defaults)
    - Only merge MISSING fields into existing assumptions
    - Add new assumption sections from defaults
    - Remove redundant fields from assumptions (user explicitly provided them)

    If spec has no assumptions (fresh spec):
    - Normal merge behavior
    - Track all defaulted fields as assumptions

    Args:
        spec: User-provided spec (partial or compiled)
        defaults: Static defaults from config/defaults.yaml

    Returns:
        spec with assumptions populated (spec itself unchanged)
    """
    # Detect if this is a recompilation (spec has assumptions already)
    existing_assumptions = spec.get("assumptions", {})
    is_recompilation = bool(existing_assumptions)

    assumptions = spec.setdefault("assumptions", {})

    # Track which fields user explicitly provided at top-level
    # (to distinguish from fields copied from assumptions)
    user_provided_fields = {
        "constraints": set(spec.get("constraints", {}).keys()),
        "nfr": set(spec.get("nfr", {}).keys()),
        "operating_model": set(spec.get("operating_model", {}).keys()),
        "cost": set(spec.get("cost", {}).keys())
    }

    # Merge constraints
    spec_constraints = spec.setdefault("constraints", {})
    default_constraints = defaults.get("constraints", {})

    if is_recompilation and "constraints" in existing_assumptions:
        # RECOMPILATION: User provided assumptions.constraints
        # Preserve existing values, only merge MISSING fields
        assumptions_constraints = existing_assumptions.get("constraints", {}).copy()

        # CRITICAL: Copy all assumption values (recursively) to spec if not already there.
        # Deepcopy prevents spec and assumptions sharing the same mutable dict objects.
        import copy as _copy

        def _deep_merge_constraints(target: dict, source: dict) -> None:
            for k, sv in source.items():
                if k not in target:
                    target[k] = _copy.deepcopy(sv)
                elif isinstance(sv, dict) and isinstance(target.get(k), dict):
                    _deep_merge_constraints(target[k], sv)

        _deep_merge_constraints(spec_constraints, assumptions_constraints)

        # Now merge missing fields from defaults
        for key, default_value in default_constraints.items():
            # Check if field is missing from ASSUMPTIONS (not just top-level)
            if key not in assumptions_constraints:
                # Missing from assumptions → merge it
                if key not in spec_constraints:
                    spec_constraints[key] = default_value
                # Use an independent copy for assumptions so that deepcopy-aliasing
                # in _clean_spec_for_output cannot accidentally empty this dict.
                assumptions_constraints[key] = dict(default_value) if isinstance(default_value, dict) else default_value
            elif key == "features" and isinstance(default_value, dict):
                # Merge missing feature flags
                assumed_features = assumptions_constraints.get("features", {})
                spec_features = spec_constraints.setdefault("features", {})

                for feature_key, feature_default in default_value.items():
                    if feature_key not in assumed_features:
                        if feature_key not in spec_features:
                            # Neither user-provided nor in existing assumptions — apply default
                            spec_features[feature_key] = feature_default
                            assumed_features[feature_key] = feature_default
                        # else: user provided this flag; do NOT add it to assumptions.

        assumptions["constraints"] = assumptions_constraints
    elif is_recompilation:
        # RECOMPILATION: User did NOT provide assumptions.constraints
        # Add this section from defaults
        assumptions_constraints = {}

        for key, default_value in default_constraints.items():
            if key not in spec_constraints:
                spec_constraints[key] = default_value
                # Independent copy prevents deepcopy-aliasing in cleanup
                assumptions_constraints[key] = dict(default_value) if isinstance(default_value, dict) else default_value
            elif key == "features" and isinstance(default_value, dict) and isinstance(spec_constraints[key], dict):
                spec_features = spec_constraints[key]
                defaulted_features = {}

                for feature_key, feature_default in default_value.items():
                    if feature_key not in spec_features:
                        spec_features[feature_key] = feature_default
                        defaulted_features[feature_key] = feature_default

                if defaulted_features:
                    assumptions_constraints["features"] = defaulted_features

        if assumptions_constraints:
            assumptions["constraints"] = assumptions_constraints
    else:
        # FRESH SPEC: Normal merge behavior
        assumptions_constraints = {}

        for key, default_value in default_constraints.items():
            if key not in spec_constraints:
                spec_constraints[key] = default_value
                # Independent copy prevents deepcopy-aliasing in cleanup
                assumptions_constraints[key] = dict(default_value) if isinstance(default_value, dict) else default_value
            elif key == "features" and isinstance(default_value, dict) and isinstance(spec_constraints[key], dict):
                spec_features = spec_constraints[key]
                default_features = default_value
                defaulted_features = {}

                for feature_key, feature_default in default_features.items():
                    if feature_key not in spec_features:
                        spec_features[feature_key] = feature_default
                        defaulted_features[feature_key] = feature_default

                if defaulted_features:
                    assumptions_constraints["features"] = defaulted_features

        if assumptions_constraints:
            assumptions["constraints"] = assumptions_constraints

    # Remove redundant fields from assumptions.constraints
    # (fields that user explicitly provided at top-level)
    # Only for recompilation - fresh specs should track all defaults
    if is_recompilation and "constraints" in assumptions:
        _remove_redundant_assumptions(assumptions["constraints"], spec_constraints, user_provided_fields["constraints"])
        # If section is now empty, remove it
        if not assumptions["constraints"]:
            del assumptions["constraints"]

    # Merge NFR
    spec_nfr = spec.setdefault("nfr", {})
    default_nfr = defaults.get("nfr", {})

    if is_recompilation and "nfr" in existing_assumptions:
        # RECOMPILATION: User provided assumptions.nfr
        # Preserve existing values, only merge MISSING fields
        assumptions_nfr = _merge_nfr_with_existing_assumptions(spec_nfr, default_nfr, existing_assumptions.get("nfr", {}))
        assumptions["nfr"] = assumptions_nfr
    elif is_recompilation:
        # RECOMPILATION: User did NOT provide assumptions.nfr
        # Add this section from defaults
        assumptions_nfr = _merge_nfr_with_defaults(spec_nfr, default_nfr)
        if assumptions_nfr:
            assumptions["nfr"] = assumptions_nfr
    else:
        # FRESH SPEC: Normal merge
        assumptions_nfr = _merge_nfr_with_defaults(spec_nfr, default_nfr)
        if assumptions_nfr:
            assumptions["nfr"] = assumptions_nfr

    # Remove redundant fields from assumptions.nfr
    # (fields that user explicitly provided at top-level)
    # Only for recompilation - fresh specs should track all defaults
    if is_recompilation and "nfr" in assumptions:
        _remove_redundant_assumptions(assumptions["nfr"], spec_nfr, user_provided_fields["nfr"])
        # If section is now empty, remove it
        if not assumptions["nfr"]:
            del assumptions["nfr"]

    # Merge operating_model
    spec_operating = spec.setdefault("operating_model", {})
    default_operating = defaults.get("operating_model", {})

    if is_recompilation and "operating_model" in existing_assumptions:
        # RECOMPILATION: User provided assumptions.operating_model
        # Preserve existing values, only merge MISSING fields
        assumptions_operating = existing_assumptions.get("operating_model", {}).copy()

        # CRITICAL: Copy assumption values to top-level if not already there
        for key, assumed_value in assumptions_operating.items():
            if key not in spec_operating:
                spec_operating[key] = assumed_value

        # Now merge missing fields from defaults
        for key, default_value in default_operating.items():
            if key not in assumptions_operating:
                # Missing from assumptions → merge it
                if key not in spec_operating:
                    spec_operating[key] = default_value
                assumptions_operating[key] = default_value

        assumptions["operating_model"] = assumptions_operating
    elif is_recompilation:
        # RECOMPILATION: User did NOT provide assumptions.operating_model
        # Add this section from defaults
        assumptions_operating = {}

        for key, default_value in default_operating.items():
            if key not in spec_operating:
                spec_operating[key] = default_value
                assumptions_operating[key] = default_value

        if assumptions_operating:
            assumptions["operating_model"] = assumptions_operating
    else:
        # FRESH SPEC: Normal merge
        assumptions_operating = {}

        for key, default_value in default_operating.items():
            if key not in spec_operating:
                spec_operating[key] = default_value
                assumptions_operating[key] = default_value

        if assumptions_operating:
            assumptions["operating_model"] = assumptions_operating

    # Remove redundant fields from assumptions.operating_model
    # (fields that user explicitly provided at top-level)
    # Only for recompilation - fresh specs should track all defaults
    if is_recompilation and "operating_model" in assumptions:
        _remove_redundant_assumptions(assumptions["operating_model"], spec_operating, user_provided_fields["operating_model"])
        # If section is now empty, remove it
        if not assumptions["operating_model"]:
            del assumptions["operating_model"]

    # Merge cost
    spec_cost = spec.setdefault("cost", {})
    default_cost = defaults.get("cost", {})

    if is_recompilation and "cost" in existing_assumptions:
        # RECOMPILATION: User provided assumptions.cost
        # Preserve existing values, only merge MISSING fields
        assumptions_cost = _merge_cost_with_existing_assumptions(spec_cost, default_cost, existing_assumptions.get("cost", {}))
        assumptions["cost"] = assumptions_cost
    elif is_recompilation:
        # RECOMPILATION: User did NOT provide assumptions.cost
        # Add this section from defaults
        assumptions_cost = _merge_cost_with_defaults(spec_cost, default_cost)
        if assumptions_cost:
            assumptions["cost"] = assumptions_cost
    else:
        # FRESH SPEC: Normal merge
        assumptions_cost = _merge_cost_with_defaults(spec_cost, default_cost)
        if assumptions_cost:
            assumptions["cost"] = assumptions_cost

    # Remove redundant fields from assumptions.cost
    # (fields that user explicitly provided at top-level)
    # Only for recompilation - fresh specs should track all defaults
    if is_recompilation and "cost" in assumptions:
        _remove_redundant_assumptions(assumptions["cost"], spec_cost, user_provided_fields["cost"])
        # If section is now empty, remove it
        if not assumptions["cost"]:
            del assumptions["cost"]

    return spec

def _evaluate_rule(spec: Dict[str, Any], rule: Dict[str, Any]) -> bool:
    """
    Evaluate a supports_constraints or supports_nfr rule against spec.

    Rule format: {"path": "/constraints/cloud", "op": "in", "value": ["aws", "gcp"], "reason": "..."}

    Returns: True if rule is satisfied by spec, False otherwise
    """
    path = rule.get("path", "")
    op = rule.get("op")
    expected = rule.get("value")

    # Get actual value from spec
    actual = _json_pointer_get(spec, path)

    # When actual is None/null:
    # - "==" rules: FAIL — null cannot equal a specific value (used as exclusive activation gates)
    # - "in" rules: FAIL — null is not a member of any value list (used for enum enforcement)
    # - "!= null" rules (expected is also None): FAIL — explicit "must be set" check
    # - all other operators: PASS — spec doesn't constrain this dimension, pattern stays eligible
    if actual is None:
        if expected is None and op == "!=":
            return False  # null fails "!= null" — field must be explicitly set
        return op not in ("==", "in")

    # Evaluate operator
    if op == "==":
        return actual == expected
    elif op == "!=":
        return actual != expected
    elif op == "in":
        if isinstance(expected, list):
            return actual in expected
        return False
    elif op == "not-in":
        if isinstance(expected, list):
            return actual not in expected
        return True  # If expected not a list, assume satisfied
    elif op == "contains-any":
        if isinstance(actual, list) and isinstance(expected, list):
            return any(item in actual for item in expected)
        return False
    elif op == ">":
        try:
            return float(actual) > float(expected)
        except (TypeError, ValueError):
            return False
    elif op == "<":
        try:
            return float(actual) < float(expected)
        except (TypeError, ValueError):
            return False
    elif op == ">=":
        try:
            return float(actual) >= float(expected)
        except (TypeError, ValueError):
            return False
    elif op == "<=":
        try:
            return float(actual) <= float(expected)
        except (TypeError, ValueError):
            return False
    else:
        return False  # Unknown operator


def _evaluate_warn_nfr_rules(
    selected_patterns: List[Dict[str, Any]],
    spec: Dict[str, Any]
) -> List[Dict[str, Any]]:
    """
    Evaluate warn_nfr rules for all selected patterns.

    Returns a list of warning dicts (same shape as cost warnings) for each
    rule that fails. Rules with a null/missing spec value are skipped (no warning).

    Each warning dict:
      {
        "code": "warn_nfr",
        "severity": "warning",
        "pattern_id": "<pattern-id>",
        "message": "<human-readable message with {actual} interpolated>",
        "details": {"path": "...", "expected": ..., "actual": ...},
        "suggestions": ["<reason text>"]
      }
    """
    warnings: List[Dict[str, Any]] = []
    for pattern in selected_patterns:
        pid = pattern.get("id", "unknown")
        for rule in pattern.get("warn_nfr", []):
            path = rule.get("path", "")
            op = rule.get("op")
            value = rule.get("value")
            reason = rule.get("reason", "")
            msg_template = rule.get("message", reason)

            # Get actual value from spec directly to check for None before evaluating
            actual = _json_pointer_get(spec, path)

            # Skip if actual is None/missing — can't evaluate, no warning (avoids false positives)
            if actual is None:
                continue

            # Warn when rule PASSES (the sub-optimal condition is present in spec)
            # e.g., op="<" value=10 warns when actual IS < 10 (low QPS)
            rule_dict = {"path": path, "op": op, "value": value, "reason": reason}
            if _evaluate_rule(spec, rule_dict):
                msg = msg_template.replace("{actual}", str(actual))
                warnings.append({
                    "code": "warn_nfr",
                    "severity": "warning",
                    "pattern_id": pid,
                    "message": msg,
                    "details": {
                        "path": path,
                        "expected": f"{op} {value}",
                        "actual": actual
                    },
                    "suggestions": [reason]
                })
    return warnings


def _evaluate_warn_constraints_rules(
    selected_patterns: List[Dict[str, Any]],
    spec: Dict[str, Any]
) -> List[Dict[str, Any]]:
    """
    Evaluate warn_constraints rules for all selected patterns.
    Same semantics as _evaluate_warn_nfr_rules but reads from warn_constraints.
    Null/missing spec values are skipped (no false positives).
    """
    warnings: List[Dict[str, Any]] = []
    for pattern in selected_patterns:
        pid = pattern.get("id", "unknown")
        for rule in pattern.get("warn_constraints", []):
            path = rule["path"]
            op = rule["op"]
            value = rule["value"]
            reason = rule.get("reason", "")
            msg_template = rule.get("message", reason)

            actual = _json_pointer_get(spec, path)

            if actual is None:
                continue

            rule_dict = {"path": path, "op": op, "value": value, "reason": reason}
            if _evaluate_rule(spec, rule_dict):
                msg = msg_template.replace("{actual}", str(actual))
                warnings.append({
                    "code": "warn_constraints",
                    "severity": "warning",
                    "pattern_id": pid,
                    "message": msg,
                    "details": {
                        "path": path,
                        "expected": f"{op} {value}",
                        "actual": actual
                    },
                    "suggestions": [reason]
                })
    return warnings


def _filter_by_supports_constraints(
    patterns: Dict[str, Dict[str, Any]],
    spec: Dict[str, Any]
) -> Tuple[List[str], List[Dict[str, Any]], Dict[str, Dict[str, List[Dict]]]]:
    """
    Phase 3.1: Filter patterns by supports_constraints.

    Empty supports_constraints = neutral (include for all specs).

    Args:
        patterns: Full pattern registry
        spec: User spec (with defaults merged)

    Returns:
        Tuple of (selected_pattern_ids, rejected_patterns, honored_rules)
        honored_rules: Dict mapping pattern_id -> {"constraints": [rules], "nfr": []}
    """
    selected = []
    rejected = []
    honored_rules = {}
    disallowed_saas = set(spec.get("constraints", {}).get("disallowed-saas-providers", []))

    for pid, pattern in patterns.items():
        supports_constraints = pattern.get("supports_constraints", [])

        if not supports_constraints:
            # Empty = neutral (include)
            selected.append(pid)
            # Initialize honored_rules for this pattern (no constraint rules)
            honored_rules[pid] = {"constraints": [], "nfr": []}
            continue

        # Check all rules
        all_satisfied = True
        failed_rules = []
        passed_rules = []

        for rule in supports_constraints:
            if not _evaluate_rule(spec, rule):
                all_satisfied = False
                failed_rules.append(rule)
            else:
                # Rule passed - save it
                passed_rules.append(rule)

        if all_satisfied:
            # Reject pattern if any required SaaS provider is disallowed
            if disallowed_saas:
                rejection_reason = None
                for rule in supports_constraints:
                    if (
                        rule.get("path") == "/constraints/saas-providers"
                        and rule.get("op") == "contains-any"
                    ):
                        required_providers = set(rule.get("value", []))
                        blocked = required_providers & disallowed_saas
                        if blocked:
                            rejection_reason = (
                                f"Provider(s) [{', '.join(sorted(blocked))}] required by this pattern "
                                f"are listed in constraints.disallowed-saas-providers"
                            )
                            break
                if rejection_reason:
                    rejected.append({
                        "id": pid,
                        "reason": rejection_reason,
                        "tier": pattern.get("availability", {}).get("tier", "open"),
                        "phase": "phase_3_1_constraints_disallowed_saas"
                    })
                    continue

            selected.append(pid)
            # Store honored constraint rules
            honored_rules[pid] = {"constraints": passed_rules, "nfr": []}
        else:
            rejected.append({
                "id": pid,
                "reason": f"Failed {len(failed_rules)} constraint rule(s)",
                "failed_rules": failed_rules,
                "tier": pattern.get("availability", {}).get("tier", "open"),
                "phase": "phase_3_1_constraints"
            })

    return selected, rejected, honored_rules

def _filter_by_disallowed_patterns(
    pattern_ids: List[str],
    patterns: Dict[str, Dict[str, Any]],
    spec: Dict[str, Any],
) -> Tuple[List[str], List[Dict[str, Any]]]:
    """
    Phase 2.5: Remove any pattern explicitly listed in disallowed-patterns.

    Runs before Phase 3.1 so disallowed patterns are never evaluated for
    constraint/NFR compatibility — the human's explicit choice takes precedence.

    Returns:
        Tuple of (remaining_pattern_ids, rejected_entries)
    """
    disallowed = set(spec.get("disallowed-patterns", []))
    if not disallowed:
        return pattern_ids, []

    selected = []
    rejected = []
    for pid in pattern_ids:
        if pid in disallowed:
            rejected.append({
                "id": pid,
                "reason": (
                    f"Explicitly excluded by disallowed-patterns. "
                    f"This pattern matched the spec but was removed per human decision."
                ),
                "phase": "phase_2_5_disallowed_patterns",
                "tier": patterns[pid].get("availability", {}).get("tier", "open"),
            })
        else:
            selected.append(pid)
    return selected, rejected


def _filter_by_supports_nfr(
    pattern_ids: List[str],
    patterns: Dict[str, Dict[str, Any]],
    spec: Dict[str, Any],
    honored_rules: Dict[str, Dict[str, List[Dict]]]
) -> Tuple[List[str], List[Dict[str, Any]], Dict[str, Dict[str, List[Dict]]]]:
    """
    Phase 3.2: Filter patterns by supports_nfr.

    Empty supports_nfr = insufficient (exclude) when spec has NFR requirements.

    Args:
        pattern_ids: Pattern IDs from Phase 3.1
        patterns: Full pattern registry
        spec: User spec (with defaults merged)
        honored_rules: Honored rules from Phase 3.1 (constraints only)

    Returns:
        Tuple of (selected_pattern_ids, rejected_patterns, honored_rules)
        honored_rules: Dict mapping pattern_id -> {"constraints": [rules], "nfr": [rules]}
    """
    selected = []
    rejected = []

    spec_nfr = spec.get("nfr", {})
    has_nfr_requirements = bool(spec_nfr)

    for pid in pattern_ids:
        pattern = patterns.get(pid, {})
        supports_nfr = pattern.get("supports_nfr", [])

        if not has_nfr_requirements:
            # No NFR requirements in spec → all patterns pass
            selected.append(pid)
            # No NFR rules to add (keep existing constraints from Phase 3.1)
            continue

        if not supports_nfr:
            # Spec has NFR requirements but pattern has no support → reject
            rejected.append({
                "id": pid,
                "reason": "No NFR support declared (empty supports_nfr) but spec has NFR requirements",
                "tier": pattern.get("availability", {}).get("tier", "open"),
                "phase": "phase_3_2_nfr"
            })
            # Remove from honored_rules since pattern is rejected
            if pid in honored_rules:
                del honored_rules[pid]
            continue

        # Check all NFR rules
        all_satisfied = True
        failed_rules = []
        passed_rules = []

        for rule in supports_nfr:
            if not _evaluate_rule(spec, rule):
                all_satisfied = False
                failed_rules.append(rule)
            else:
                # Rule passed - save it
                passed_rules.append(rule)

        if all_satisfied:
            selected.append(pid)
            # Add NFR rules to honored_rules
            if pid in honored_rules:
                honored_rules[pid]["nfr"] = passed_rules
            else:
                # Should not happen (pattern should have been in Phase 3.1)
                honored_rules[pid] = {"constraints": [], "nfr": passed_rules}
        else:
            rejected.append({
                "id": pid,
                "reason": f"Failed {len(failed_rules)} NFR rule(s)",
                "failed_rules": failed_rules,
                "tier": pattern.get("availability", {}).get("tier", "open"),
                "phase": "phase_3_2_nfr"
            })
            # Remove from honored_rules since pattern is rejected
            if pid in honored_rules:
                del honored_rules[pid]

    return selected, rejected, honored_rules

def _calculate_pattern_cost_by_intent(
    pattern: Dict[str, Any],
    intent: str,
    amortization_months: int
) -> float:
    """
    Calculate pattern cost based on cost.intent.

    Based on COCOMO II, AWS TCO, Google SRE, DORA research.

    Citations:
    - COCOMO II Model (Boehm et al., 2000) - TCO methodology
    - AWS TCO Calculator Methodology (AWS, 2023) - Amortization
    - Google SRE Handbook (Google, 2016) - Operational cost
    - DORA State of DevOps Report (DORA, 2021) - Cost optimization

    Args:
        pattern: Pattern object
        intent: Cost intent (minimize-opex, minimize-capex, optimize-tco)
        amortization_months: Amortization period for TCO (default: 24)

    Returns:
        Cost in USD based on intent
    """
    cost_data = pattern.get("cost", {})

    if intent == "minimize-opex":
        # Monthly operational cost only
        return cost_data.get("estimatedMonthlyRangeUsd", {}).get("min", 0)

    elif intent == "minimize-capex":
        # One-time capital expenditure
        adoption_cost = cost_data.get("adoptionCost", 0)
        license_cost = cost_data.get("licenseCost", 0)
        return adoption_cost + license_cost

    else:  # optimize-tco (default)
        # Total cost of ownership over amortization period
        # TCO = capex + (opex × months)
        capex = cost_data.get("adoptionCost", 0) + cost_data.get("licenseCost", 0)
        opex_monthly = cost_data.get("estimatedMonthlyRangeUsd", {}).get("min", 0)
        return capex + (opex_monthly * amortization_months)

def _calculate_pattern_match_score(
    pattern: Dict[str, Any],
    spec: Dict[str, Any]
) -> int:
    """
    Calculate how many constraint/NFR rules pattern matches.

    Higher score = more specific to spec requirements.

    Args:
        pattern: Pattern object
        spec: User spec

    Returns:
        Total matched rules count
    """
    matched_count = 0

    # Count matched constraint rules
    for rule in pattern.get("supports_constraints", []):
        if _evaluate_rule(spec, rule):
            matched_count += 1

    # Count matched NFR rules
    for rule in pattern.get("supports_nfr", []):
        if _evaluate_rule(spec, rule):
            matched_count += 1

    return matched_count

def _find_conflict_group(
    start_pid: str,
    conflict_graph: Dict[str, set],
    available_pids: set
) -> set:
    """
    Find all patterns in the same conflict group using graph traversal.

    Uses BFS to find all patterns that are transitively conflicting with start_pid.

    Args:
        start_pid: Starting pattern ID
        conflict_graph: Bidirectional conflict graph (pid -> set of conflicting pids)
        available_pids: Set of pattern IDs available for selection

    Returns:
        Set of pattern IDs in the same conflict group
    """
    visited = set()
    queue = [start_pid]
    group = {start_pid}

    while queue:
        current = queue.pop(0)
        if current in visited:
            continue
        visited.add(current)

        # Find all patterns that conflict with current pattern
        for conflict_pid in conflict_graph.get(current, set()):
            if conflict_pid in available_pids and conflict_pid not in visited:
                group.add(conflict_pid)
                queue.append(conflict_pid)

    return group

def _resolve_conflicts_with_match_scoring(
    pattern_ids: List[str],
    patterns: Dict[str, Dict[str, Any]],
    spec: Dict[str, Any]
) -> Tuple[List[str], List[Dict[str, Any]], Dict[str, int]]:
    """
    Phase 3.3: For conflicting patterns, choose ones with higher match scores.

    Uses greedy maximum independent set within each conflict group so that
    compatible patterns (e.g. two specific-provider variants) can coexist even
    when both are connected to a common hub (e.g. a generic fallback pattern).

    Algorithm:
    1. Calculate match score for each pattern (constraint + NFR rules matched)
    2. Build bidirectional conflict graph
    3. Find conflict groups via BFS
    4. Within each group, apply greedy independent set:
       - Sort by score (desc), cost (asc), name (asc)
       - Greedily select: if a pattern has not been eliminated, select it and
         mark all its direct conflict-neighbors as eliminated
       - This allows non-conflicting patterns within the same connected component
         to both be selected (e.g. supabase + render when both are requested)

    Args:
        pattern_ids: Pattern IDs from Phase 3.2
        patterns: Full pattern registry
        spec: User spec

    Returns:
        Tuple of (selected_pattern_ids, rejected_patterns, match_scores)
        match_scores: Dict mapping pattern_id -> count of matched rules
    """
    selected = []
    rejected = []

    # Get cost intent and amortization
    intent = spec.get("cost", {}).get("intent", {}).get("priority", "optimize-tco")
    amortization_months = spec.get("operating_model", {}).get("amortization_months", 24)

    # Calculate match scores for all patterns
    pattern_scores = {}
    for pid in pattern_ids:
        pattern_scores[pid] = _calculate_pattern_match_score(patterns[pid], spec)

    # Build bidirectional conflict graph
    # If pattern A declares B as incompatible, both A and B should know about each other
    conflict_graph = {}  # pid -> set of conflicting pids
    available_pids_set = set(pattern_ids)

    for pid in pattern_ids:
        conflicts = patterns[pid].get("conflicts", {}).get("incompatibleWithDesignPatterns", [])
        # Only include conflicts that are in our available patterns
        conflict_graph[pid] = set(c for c in conflicts if c in available_pids_set)

    # Add reverse relationships (bidirectional)
    # If A declares B incompatible, B should also know about A
    for pid, conflicts in list(conflict_graph.items()):
        for conflict_pid in conflicts:
            if conflict_pid in conflict_graph:
                conflict_graph[conflict_pid].add(pid)

    # Find conflict groups using graph traversal
    visited = set()
    conflict_groups = []  # List of sets of conflicting pattern IDs

    for pid in pattern_ids:
        if pid in visited:
            continue

        # Find all patterns in this conflict group
        group = _find_conflict_group(pid, conflict_graph, available_pids_set)

        if len(group) == 1:
            # No conflicts for this pattern
            selected.append(pid)
            visited.add(pid)
        else:
            # Conflict group found
            conflict_groups.append(group)
            visited.update(group)

    # Resolve each conflict group using greedy maximum independent set.
    # Patterns that do not conflict with each other directly can both be selected
    # even if they share a common conflicting neighbour (the "hub" pattern).
    for group in conflict_groups:
        # Build sorted list: score desc, cost asc, name asc
        group_patterns = []
        for pid in group:
            cost = _calculate_pattern_cost_by_intent(patterns[pid], intent, amortization_months)
            group_patterns.append((pid, pattern_scores[pid], cost))
        group_patterns.sort(key=lambda x: (-x[1], x[2], x[0]))

        cost_by_pid = {pid: cost for pid, _, cost in group_patterns}

        # eliminated[pid] = (winner_pid, winner_score, winner_cost) of the first
        # selected pattern that has a direct conflict edge to pid
        eliminated = {}

        for pid, score, cost in group_patterns:
            if pid in eliminated:
                winner_pid, winner_score, winner_cost = eliminated[pid]
                if score == winner_score:
                    reason = (
                        f"Incompatible with '{winner_pid}' "
                        f"(tied score {score}, but higher cost: "
                        f"${cost:.0f} vs ${winner_cost:.0f})"
                    )
                else:
                    reason = (
                        f"Incompatible with '{winner_pid}' "
                        f"(score: {winner_score} vs {score})"
                    )
                rejected.append({
                    "id": pid,
                    "reason": reason,
                    "tier": patterns[pid].get("availability", {}).get("tier", "open"),
                    "phase": "phase_3_3_conflict",
                    "winner": winner_pid,
                    "winner_score": winner_score,
                    "loser_score": score,
                    "winner_cost": winner_cost,
                    "loser_cost": cost,
                    "cost_intent": intent
                })
            else:
                # Select this pattern; mark all its direct neighbours as eliminated
                selected.append(pid)
                for neighbor in conflict_graph.get(pid, set()):
                    if neighbor in group and neighbor not in eliminated:
                        eliminated[neighbor] = (pid, score, cost)

    # Return match scores for all selected patterns
    selected_match_scores = {pid: pattern_scores[pid] for pid in selected}

    return selected, rejected, selected_match_scores

def _merge_pattern_default_configs(
    selected_pattern_ids: List[str],
    patterns: Dict[str, Dict[str, Any]],
    spec: Dict[str, Any],
    match_scores: Dict[str, int]
) -> None:
    """
    Phase 3.4: Merge pattern defaultConfig into assumptions.patterns.

    Only merge if user didn't provide explicit config in spec.patterns[pattern_id].

    Modifies spec in-place.

    Args:
        selected_pattern_ids: Pattern IDs from Phase 3.3
        patterns: Full pattern registry
        spec: User spec
        match_scores: Dict mapping pattern_id -> count of matched rules
    """
    user_patterns = spec.get("patterns", {})

    # Validate user-specified patterns (top-level spec.patterns)
    # If incompatible patterns exist in user input → ERROR
    if user_patterns:
        invalid_user_patterns = [pid for pid in user_patterns.keys() if pid not in selected_pattern_ids]
        if invalid_user_patterns:
            print("❌ Pattern Configuration Error:")
            print("   The following patterns in 'patterns:' are incompatible with the spec constraints/NFR:")
            for pid in invalid_user_patterns:
                print(f"     • {pid}")
            print()
            print(f"   Compatible patterns: {', '.join(sorted(selected_pattern_ids))}")
            sys.exit(1)

    # Clear and rebuild assumptions.patterns with only selected patterns
    # (removes any incompatible patterns from input spec.assumptions.patterns)
    spec.setdefault("assumptions", {})["patterns"] = {}
    assumptions_patterns = spec["assumptions"]["patterns"]

    # Collect patterns to add to assumptions (unsorted)
    patterns_to_add = {}
    for pid in selected_pattern_ids:
        pattern = patterns[pid]
        default_config = pattern.get("defaultConfig", {})

        if pid in user_patterns:
            # User provided explicit config → don't add to assumptions
            # (but we could track partial defaults if needed in future)
            continue
        else:
            # User didn't provide config → add to assumptions
            if default_config:
                patterns_to_add[pid] = default_config
            else:
                patterns_to_add[pid] = {}

    # Sort patterns by match score (highest first) and populate assumptions_patterns
    sorted_pids = sorted(patterns_to_add.keys(), key=lambda pid: match_scores.get(pid, 0), reverse=True)
    for pid in sorted_pids:
        assumptions_patterns[pid] = patterns_to_add[pid]

def _calculate_ops_team_cost(operating_model: Dict[str, Any]) -> float:
    """
    Calculate TOTAL monthly ops team cost (not per-pattern).

    NEW PARAMETERS (2026-02-19 feedback):
    - ops_team_size: Number of operations engineers (default: 0 = no dedicated ops)
    - single_resource_monthly_ops_usd: Monthly cost per engineer (default: $10,000)

    Formula:
        base_monthly_team_cost = ops_team_size × single_resource_monthly_ops_usd
        adjusted = base × on_call_multiplier × deploy_multiplier

    Based on:
    - COCOMO II Model (Boehm et al., 2000) - Effort multipliers
    - Google SRE Handbook (Google, 2016) - On-call burden (25-50% FTE overhead)
    - DORA State of DevOps Report (DORA, 2021) - Deployment frequency impact

    Citations:
    1. COCOMO II Model:
       - Boehm, B. et al. (2000). "Software Cost Estimation with COCOMO II"
       - Effort multipliers for team size and deployment frequency

    2. Google SRE Handbook:
       - Google SRE Handbook. (2016). "Measuring Toil"
       - On-call burden = 25-50% FTE overhead
       - Formula: On-call_cost = Team_size × Base_cost × On_call_multiplier

    3. DORA State of DevOps:
       - DORA. (2021). "State of DevOps Report"
       - High performers (on-demand deploys): 50% less ops overhead

    Args:
        operating_model: Operating model section from spec

    Returns:
        Monthly ops team cost (USD/month)
    """
    ops_team_size = operating_model.get("ops_team_size", 0)  # Default: 0
    single_resource_monthly_ops_usd = operating_model.get("single_resource_monthly_ops_usd", 10000)  # Default: $10k

    base_monthly_team_cost = ops_team_size * single_resource_monthly_ops_usd

    # On-call multiplier (Google SRE Handbook)
    on_call = operating_model.get("on_call", False)
    on_call_multiplier = 1.5 if on_call else 1.0

    # Deployment frequency multiplier (DORA State of DevOps)
    deploy_freq = operating_model.get("deploy_freq", "weekly")
    deploy_freq_multipliers = {
        "on-demand": 0.5,    # High automation, low overhead
        "daily": 0.6,
        "weekly": 0.8,
        "biweekly": 0.9,
        "monthly": 1.0,      # Manual processes, high overhead
        "quarterly": 1.1,
        "n/a": 1.0
    }
    deploy_multiplier = deploy_freq_multipliers.get(deploy_freq, 0.8)

    # Return FULL team cost (not per-pattern allocation)
    adjusted_team_cost = base_monthly_team_cost * on_call_multiplier * deploy_multiplier

    return adjusted_team_cost

def _check_cost_feasibility(
    selected_pattern_ids: List[str],
    patterns: Dict[str, Dict[str, Any]],
    spec: Dict[str, Any],
    ops_team_cost: float,
    match_scores: Dict[str, float],
    verbose: bool = False
) -> Tuple[List[Dict[str, Any]], Dict[str, Any]]:
    """
    Phase 4: Check cost feasibility against ceilings.

    CRITICAL: Generate warnings, DO NOT reject patterns.
    CRITICAL: Use cost.intent to determine which ceiling to check (user feedback 38ac44d6).

    Args:
        selected_pattern_ids: Pattern IDs from Phase 3
        patterns: Full pattern registry
        spec: User spec
        ops_team_cost: Monthly ops team cost
        match_scores: Dict of pattern_id -> match_score (for sorting display)
        verbose: Unused parameter (kept for backward compatibility)

    Returns:
        Tuple of (warnings list, cost_details dict with detailed calculations)
    """
    warnings = []

    # Get intent and ceilings
    intent = spec.get("cost", {}).get("intent", {}).get("priority", "optimize-tco")
    ceiling_opex = spec.get("cost", {}).get("ceilings", {}).get("monthly_operational_usd")
    ceiling_capex = spec.get("cost", {}).get("ceilings", {}).get("one_time_setup_usd")
    amortization_months = spec.get("operating_model", {}).get("amortization_months", 24)
    ops_team_size = spec.get("operating_model", {}).get("ops_team_size", 0)

    # Calculate total costs
    total_pattern_opex = sum(
        patterns[pid].get("cost", {}).get("estimatedMonthlyRangeUsd", {}).get("min", 0)
        for pid in selected_pattern_ids
    )

    total_pattern_capex = sum(
        patterns[pid].get("cost", {}).get("adoptionCost", 0) +
        patterns[pid].get("cost", {}).get("licenseCost", 0)
        for pid in selected_pattern_ids
    )

    total_opex_with_ops = total_pattern_opex + ops_team_cost

    # Collect cost details (always shown, not just in verbose mode)
    single_resource_monthly_ops_usd = spec.get("operating_model", {}).get("single_resource_monthly_ops_usd", 10000)

    # Sort patterns by match_score (descending) for display
    sorted_pattern_ids = sorted(
        selected_pattern_ids,
        key=lambda pid: match_scores.get(pid, 0),
        reverse=True
    )

    # Collect per-pattern costs
    pattern_costs = []
    for idx, pid in enumerate(sorted_pattern_ids, 1):
        pattern = patterns[pid]
        cost_info = pattern.get("cost", {})

        adoption_cost = cost_info.get("adoptionCost", 0)
        license_cost = cost_info.get("licenseCost", 0)
        total_capex = adoption_cost + license_cost

        monthly_range = cost_info.get("estimatedMonthlyRangeUsd", {})
        monthly_min = monthly_range.get("min", 0)
        monthly_expected = monthly_range.get("expected", monthly_min)

        # Check if pattern requires self-hosting (has ops burden)
        hosting = pattern.get("hosting", {})
        self_hosted = hosting.get("self_hosted", False)
        managed_service = hosting.get("managed_service", False)

        # Ops cost explanation
        if self_hosted and not managed_service:
            ops_explanation = f"${ops_team_cost:,.0f} (self-hosted)"
        elif managed_service:
            ops_explanation = "$0 (managed service)"
        else:
            ops_explanation = "$0 (no infrastructure)"

        # Calculate TCO for this pattern
        pattern_tco = total_capex + (monthly_expected * amortization_months)

        pattern_costs.append({
            "index": idx,
            "id": pid,
            "adoption_cost": total_capex,
            "monthly_min": monthly_min,
            "monthly_expected": monthly_expected,
            "ops_explanation": ops_explanation,
            "tco": pattern_tco,
            "match_score": match_scores.get(pid, 0)
        })

    # Total TCO
    total_tco = total_pattern_capex + (total_opex_with_ops * amortization_months)

    # Calculate ops cost breakdown for display
    operating_model = spec.get("operating_model", {})
    ops_base_cost = ops_team_size * single_resource_monthly_ops_usd

    on_call = operating_model.get("on_call", False)
    on_call_multiplier = 1.5 if on_call else 1.0
    on_call_explanation = "on-call burden" if on_call else "no on-call"

    deploy_freq = operating_model.get("deploy_freq", "weekly")
    deploy_freq_multipliers = {
        "on-demand": 0.5,
        "daily": 0.6,
        "weekly": 0.8,
        "biweekly": 0.9,
        "monthly": 1.0,
        "quarterly": 1.1,
        "n/a": 1.0
    }
    deploy_multiplier = deploy_freq_multipliers.get(deploy_freq, 0.8)
    deploy_explanations = {
        "on-demand": "high automation",
        "daily": "high automation",
        "weekly": "moderate automation",
        "biweekly": "moderate automation",
        "monthly": "manual processes",
        "quarterly": "manual processes",
        "n/a": "no deployment"
    }
    deploy_explanation = deploy_explanations.get(deploy_freq, "moderate automation")

    cost_details = {
        "intent": intent,
        "amortization_months": amortization_months,
        "ops_team_size": ops_team_size,
        "single_resource_monthly_ops_usd": single_resource_monthly_ops_usd,
        "pattern_costs": pattern_costs,
        "total_tco": total_tco,
        "total_opex_with_ops": total_opex_with_ops,
        "total_pattern_capex": total_pattern_capex,
        "ceiling_opex": ceiling_opex,
        "ceiling_capex": ceiling_capex,
        # Ops cost breakdown
        "ops_team_cost": ops_team_cost,
        "ops_base_cost": ops_base_cost,
        "ops_on_call_multiplier": on_call_multiplier,
        "ops_on_call_explanation": on_call_explanation,
        "ops_deploy_multiplier": deploy_multiplier,
        "ops_deploy_explanation": deploy_explanation,
        "ops_deploy_freq": deploy_freq
    }

    # Intent-based cost checking (user feedback: commit 38ac44d6)
    if intent == "minimize-opex":
        # Check total_opex_with_ops against monthly_operational_usd ceiling
        if ceiling_opex is not None and total_opex_with_ops > ceiling_opex:
            overage = total_opex_with_ops - ceiling_opex
            high_cost_patterns = sorted(
                [(pid, patterns[pid].get("cost", {}).get("estimatedMonthlyRangeUsd", {}).get("min", 0))
                 for pid in selected_pattern_ids],
                key=lambda x: -x[1]
            )[:3]  # Top 3 expensive

            warnings.append({
                "code": "cost_opex_exceeds_ceiling",
                "message": f"Total monthly operational cost (${total_opex_with_ops:.0f}) exceeds ceiling (${ceiling_opex:.0f}) by ${overage:.0f} (intent: minimize-opex)",
                "details": {
                    "intent": intent,
                    "pattern_opex": total_pattern_opex,
                    "ops_team_cost": ops_team_cost,
                    "total": total_opex_with_ops,
                    "ceiling": ceiling_opex,
                    "overage": overage
                },
                "suggestions": [
                    f"Increase monthly ceiling to ${total_opex_with_ops:.0f} or more",
                    f"Remove high-cost patterns: {', '.join(p[0] for p in high_cost_patterns)}",
                    f"Reduce ops_team_size from {spec.get('operating_model', {}).get('ops_team_size', 0)}"
                ],
                "severity": "high"
            })

    elif intent == "minimize-capex":
        # Check total_pattern_capex against one_time_setup_usd ceiling
        if ceiling_capex is not None and total_pattern_capex > ceiling_capex:
            overage = total_pattern_capex - ceiling_capex
            high_cost_patterns = sorted(
                [(pid, patterns[pid].get("cost", {}).get("adoptionCost", 0) + patterns[pid].get("cost", {}).get("licenseCost", 0))
                 for pid in selected_pattern_ids],
                key=lambda x: -x[1]
            )[:3]

            warnings.append({
                "code": "cost_capex_exceeds_ceiling",
                "message": f"Total capital expenditure (${total_pattern_capex:.0f}) exceeds ceiling (${ceiling_capex:.0f}) by ${overage:.0f} (intent: minimize-capex)",
                "details": {
                    "intent": intent,
                    "total_capex": total_pattern_capex,
                    "ceiling": ceiling_capex,
                    "overage": overage
                },
                "suggestions": [
                    f"Increase capex ceiling to ${total_pattern_capex:.0f} or more",
                    f"Remove high-capex patterns: {', '.join(p[0] for p in high_cost_patterns)}"
                ],
                "severity": "high"
            })

    else:  # optimize-tco (default)
        # Check TCO against combined ceiling
        # tco = total_pattern_capex + (total_opex_with_ops * amortization_months)
        # ceiling_tco = one_time_setup_usd + (monthly_operational_usd * amortization_months)
        tco = total_pattern_capex + (total_opex_with_ops * amortization_months)

        if ceiling_opex is not None and ceiling_capex is not None:
            ceiling_tco = ceiling_capex + (ceiling_opex * amortization_months)

            if tco > ceiling_tco:
                overage = tco - ceiling_tco
                high_cost_patterns = sorted(
                    [(pid,
                      patterns[pid].get("cost", {}).get("adoptionCost", 0) +
                      patterns[pid].get("cost", {}).get("licenseCost", 0) +
                      (patterns[pid].get("cost", {}).get("estimatedMonthlyRangeUsd", {}).get("min", 0) * amortization_months))
                     for pid in selected_pattern_ids],
                    key=lambda x: -x[1]
                )[:3]

                warnings.append({
                    "code": "cost_tco_exceeds_ceiling",
                    "message": f"Total cost of ownership over {amortization_months} months (${tco:.0f}) exceeds ceiling (${ceiling_tco:.0f}) by ${overage:.0f} (intent: optimize-tco)",
                    "details": {
                        "intent": intent,
                        "total_capex": total_pattern_capex,
                        "pattern_opex_monthly": total_pattern_opex,
                        "ops_team_cost_monthly": ops_team_cost,
                        "total_opex_monthly": total_opex_with_ops,
                        "amortization_months": amortization_months,
                        "tco": tco,
                        "ceiling_tco": ceiling_tco,
                        "overage": overage
                    },
                    "suggestions": [
                        f"Increase ceilings (capex: ${ceiling_capex:.0f}, opex: ${ceiling_opex:.0f})",
                        f"Remove high-TCO patterns: {', '.join(p[0] for p in high_cost_patterns)}",
                        f"Reduce amortization period from {amortization_months} months"
                    ],
                    "severity": "high"
                })

    return warnings, cost_details

def _print_cost_details(cost_details: Dict[str, Any]) -> None:
    """
    Print detailed cost calculations in verbose mode (Task 8).
    Output is formatted as comments to match compiled-spec.yaml format.

    Args:
        cost_details: Cost calculation details from _check_cost_feasibility
    """
    intent = cost_details["intent"]
    amortization_months = cost_details["amortization_months"]
    ops_team_size = cost_details["ops_team_size"]
    single_resource_monthly_ops_usd = cost_details["single_resource_monthly_ops_usd"]
    pattern_costs = cost_details["pattern_costs"]
    total_tco = cost_details["total_tco"]
    total_opex_with_ops = cost_details["total_opex_with_ops"]
    total_pattern_capex = cost_details["total_pattern_capex"]
    ceiling_opex = cost_details["ceiling_opex"]
    ceiling_capex = cost_details["ceiling_capex"]

    print("\n# Cost Feasibility Check")
    print("# " + "=" * 60)

    # Intent description
    if intent == "optimize-tco":
        intent_desc = f"optimize-tco (minimize TCO over {amortization_months} months)"
    elif intent == "minimize-opex":
        intent_desc = "minimize-opex"
    elif intent == "minimize-capex":
        intent_desc = "minimize-capex"
    else:
        intent_desc = intent

    print(f"# Intent: {intent_desc}")
    print(f"# Amortization: {amortization_months} months")

    # Show ops team cost breakdown
    if ops_team_size > 0:
        print(f"#")
        print(f"# Ops Team Cost Breakdown:")
        print(f"#   Base: {ops_team_size} engineers × ${single_resource_monthly_ops_usd:,}/month = ${cost_details['ops_base_cost']:,.0f}")
        print(f"#   On-call multiplier: {cost_details['ops_on_call_multiplier']}x ({cost_details['ops_on_call_explanation']})")

        # Show deploy frequency with current value
        deploy_freq_current = cost_details.get('ops_deploy_freq', 'weekly')
        print(f"#   Deploy frequency multiplier: {cost_details['ops_deploy_multiplier']}x (deploy_freq: {deploy_freq_current}, {cost_details['ops_deploy_explanation']})")

        print(f"#   Adjusted ops cost: ${cost_details['ops_base_cost']:,.0f} × {cost_details['ops_on_call_multiplier']} × {cost_details['ops_deploy_multiplier']} = ${cost_details['ops_team_cost']:,.0f}/month")

        # Show deploy frequency table for user reference
        print(f"#")
        print(f"#   Deploy Frequency Options (DORA State of DevOps):")
        print(f"#     on-demand: 0.5x  (very high automation)")
        print(f"#     daily:     0.6x  (high automation)")
        print(f"#     weekly:    0.8x  (moderate automation)")
        print(f"#     biweekly:  0.9x  (manual processes)")
        print(f"#     monthly:   1.0x  (very manual)")
        print(f"#     quarterly: 1.1x  (extremely manual)")

    else:
        print(f"#")
        print(f"# Ops team size: 0 engineers (no ops cost)")

    # Always show algorithm citations as reference (even when not used)
    print(f"#")
    print(f"# Ops Team Cost Algorithm (for reference):")
    print(f"#   Formula: ops_team_size × single_resource_monthly_ops_usd × on_call_multiplier × deploy_freq_multiplier")
    print(f"#   Based on:")
    print(f"#     - Google SRE Handbook (2016): On-call burden = 25-50% FTE overhead")
    print(f"#     - DORA State of DevOps (2021): Deploy frequency impact on ops overhead")

    print(f"#")
    print(f"# Calculating costs for {len(pattern_costs)} selected patterns:")
    print(f"#")

    # Display per-pattern costs
    for pc in pattern_costs:
        # Show match score in verbose output
        match_score_display = f" (match score: {pc['match_score']:.2f})" if pc.get('match_score') is not None else ""
        print(f"#   {pc['index']}. {pc['id']}{match_score_display}")
        print(f"#      Adoption: ${pc['adoption_cost']:,}")
        print(f"#      Monthly (min): ${pc['monthly_min']:,}")
        print(f"#      Monthly (expected): ${pc['monthly_expected']:,}")
        print(f"#      Ops cost: {pc['ops_explanation']}")
        print(f"#      {'─' * 38}")

        # Show relevant metric based on intent
        if intent == "minimize-opex":
            print(f"#      Monthly OpEx: ${pc['monthly_expected']:,}")
        elif intent == "minimize-capex":
            print(f"#      CapEx (one-time): ${pc['adoption_cost']:,}")
        else:  # optimize-tco
            print(f"#      TCO ({amortization_months}mo): ${pc['adoption_cost']:,} + (${pc['monthly_expected']:,} × {amortization_months}) = ${pc['tco']:,}")
        print("#")

    # Show total cost based on intent
    if intent == "minimize-opex":
        print(f"# Total Monthly OpEx: ${total_opex_with_ops:,}")
    elif intent == "minimize-capex":
        print(f"# Total CapEx (one-time): ${total_pattern_capex:,}")
    else:  # optimize-tco
        print(f"# Total TCO ({amortization_months}mo): ${total_tco:,}")

    # Budget check results
    if intent == "minimize-opex":
        if ceiling_opex is not None:
            status = "✓ PASS" if total_opex_with_ops <= ceiling_opex else "✗ FAIL"
            print(f"# Monthly operational ceiling: ${ceiling_opex:,} {status}")
        else:
            print("# Monthly operational ceiling: Not specified")
    elif intent == "minimize-capex":
        if ceiling_capex is not None:
            status = "✓ PASS" if total_pattern_capex <= ceiling_capex else "✗ FAIL"
            print(f"# One-time setup ceiling: ${ceiling_capex:,} {status}")
        else:
            print("# One-time setup ceiling: Not specified")
    else:  # optimize-tco
        if ceiling_opex is not None:
            status = "✓ PASS" if total_opex_with_ops <= ceiling_opex else "✗ FAIL"
            print(f"# Monthly operational ceiling: ${ceiling_opex:,} {status}")
        if ceiling_capex is not None:
            status = "✓ PASS" if total_pattern_capex <= ceiling_capex else "✗ FAIL"
            print(f"# One-time setup ceiling: ${ceiling_capex:,} {status}")
        if ceiling_opex is None and ceiling_capex is None:
            print("# No budget ceilings specified")

    print("# " + "=" * 60)

def _write_cost_summary_section(f, cost_details: Dict[str, Any], warnings: List[Dict[str, Any]]) -> None:
    """
    Write the Cost Feasibility Analysis (Summary) block as YAML comments.
    Called for both verbose and non-verbose compiled-spec.yaml output.

    Args:
        f: Open file handle (write mode)
        cost_details: Cost calculation details from _check_cost_feasibility
        warnings: List of warning dicts from cost feasibility checks
    """
    f.write("\n")
    f.write("# ============================================================\n")
    f.write("# Cost Feasibility Analysis (Summary)\n")
    f.write("# ============================================================\n")
    f.write("#\n")
    f.write(f"# Intent: {cost_details['intent']}\n")
    f.write(f"# Amortization: {cost_details['amortization_months']} months\n")
    f.write(f"# Total Patterns Selected: {len(cost_details['pattern_costs'])}\n")
    f.write("#\n")
    f.write("# COST BREAKDOWN:\n")
    f.write("# ────────────────────────────────────────────────────────────\n")
    f.write(f"# Total CapEx (one-time):     ${cost_details['total_pattern_capex']:>12,.0f}\n")
    pattern_opex = cost_details['total_opex_with_ops'] - cost_details['ops_team_cost']
    f.write(f"# Pattern OpEx (monthly):     ${pattern_opex:>12,.0f}\n")
    f.write(f"# Ops Team Cost (monthly):    ${cost_details['ops_team_cost']:>12,.0f}")
    if cost_details['ops_team_size'] > 0:
        f.write(f"  ({cost_details['ops_team_size']} × ${cost_details['single_resource_monthly_ops_usd']:,.0f})\n")
    else:
        f.write("\n")
    f.write(f"# Total OpEx (monthly):       ${cost_details['total_opex_with_ops']:>12,.0f}\n")
    f.write(f"# Total TCO ({cost_details['amortization_months']}mo):         ${cost_details['total_tco']:>12,.0f}\n")
    f.write("#\n")

    if cost_details["ceiling_opex"] is not None or cost_details["ceiling_capex"] is not None:
        f.write("# COST CEILINGS:\n")
        f.write("# ────────────────────────────────────────────────────────────\n")
        if cost_details["ceiling_capex"] is not None:
            capex_status = "✓ PASS" if cost_details['total_pattern_capex'] <= cost_details['ceiling_capex'] else "✗ FAIL"
            f.write(f"# CapEx Ceiling:              ${cost_details['ceiling_capex']:>12,.0f} {capex_status}\n")
        if cost_details["ceiling_opex"] is not None:
            opex_status = "✓ PASS" if cost_details['total_opex_with_ops'] <= cost_details['ceiling_opex'] else "✗ FAIL"
            f.write(f"# OpEx Ceiling (monthly):     ${cost_details['ceiling_opex']:>12,.0f} {opex_status}\n")
        f.write("#\n")

    if warnings:
        f.write("# ⚠️  WARNINGS:\n")
        f.write("# ────────────────────────────────────────────────────────────\n")
        for w in warnings:
            f.write(f"# [{w['severity']}] {w['code']}:\n")
            f.write(f"#   {w['message']}\n")
            if 'suggestions' in w and w['suggestions']:
                f.write("#\n")
                f.write("#   Suggestions:\n")
                for suggestion in w['suggestions']:
                    f.write(f"#   - {suggestion}\n")
            f.write("#\n")

    f.write("# ============================================================\n")
    f.write("\n")


def _write_advisory_warnings_section(f, advisory_warnings: List[Dict[str, Any]]) -> None:
    """
    Write warn_nfr and warn_constraints advisories as a separate YAML comment block.
    Always called when advisory_warnings is non-empty, independent of cost analysis.
    Patterns are still SELECTED — these are advisory notices only.
    """
    f.write("\n")
    f.write("# ============================================================\n")
    f.write("# ⚠️  Pattern Advisory Warnings\n")
    f.write("# (Patterns are still SELECTED — review these before finalizing)\n")
    f.write("# ============================================================\n")
    f.write("#\n")
    for w in advisory_warnings:
        f.write(f"# [{w['severity']}] {w['code']}:\n")
        f.write(f"#   {w['message']}\n")
        if w.get("suggestions"):
            f.write("#\n")
            f.write("#   Suggestions:\n")
            for s in w["suggestions"]:
                f.write(f"#   - {s}\n")
        f.write("#\n")
    f.write("# ============================================================\n")
    f.write("\n")


def _write_cost_details_section(f, cost_details: Dict[str, Any]) -> None:
    """
    Write the Cost Feasibility Analysis (Details) block as YAML comments.
    Only called in verbose mode. Contains rich ops breakdown with citations
    and per-pattern cost breakdown.

    Args:
        f: Open file handle (text write mode, UTF-8 encoded)
        cost_details: Cost calculation details from _check_cost_feasibility
    """
    intent = cost_details['intent']
    amortization_months = cost_details['amortization_months']
    ops_team_size = cost_details['ops_team_size']
    single_resource_monthly_ops_usd = cost_details['single_resource_monthly_ops_usd']

    f.write("# ============================================================\n")
    f.write("# Cost Feasibility Analysis (Details)\n")
    f.write("# ============================================================\n")
    f.write("#\n")
    f.write(f"# Intent: {intent}\n")
    f.write(f"# Amortization: {amortization_months} months\n")
    f.write("#\n")

    # Ops Team Cost Breakdown
    if ops_team_size > 0:
        f.write("# Ops Team Cost Breakdown:\n")
        f.write(f"#   Base: {ops_team_size} engineers × ${single_resource_monthly_ops_usd:,}/month = ${cost_details['ops_base_cost']:,.0f}\n")
        f.write(f"#   On-call multiplier: {cost_details['ops_on_call_multiplier']}x ({cost_details['ops_on_call_explanation']})\n")
        deploy_freq = cost_details.get('ops_deploy_freq', 'weekly')
        f.write(f"#   Deploy frequency multiplier: {cost_details['ops_deploy_multiplier']}x (deploy_freq: {deploy_freq}, {cost_details['ops_deploy_explanation']})\n")
        f.write(f"#   Adjusted ops cost: ${cost_details['ops_base_cost']:,.0f} × {cost_details['ops_on_call_multiplier']} × {cost_details['ops_deploy_multiplier']} = ${cost_details['ops_team_cost']:,.0f}/month\n")
        f.write("#\n")
        f.write("#   Deploy Frequency Options (DORA State of DevOps):\n")
        f.write("#     on-demand: 0.5x  (very high automation)\n")
        f.write("#     daily:     0.6x  (high automation)\n")
        f.write("#     weekly:    0.8x  (moderate automation)\n")
        f.write("#     biweekly:  0.9x  (manual processes)\n")
        f.write("#     monthly:   1.0x  (very manual)\n")
        f.write("#     quarterly: 1.1x  (extremely manual)\n")
        f.write("#\n")
    else:
        f.write("# Ops team size: 0 engineers (no ops cost)\n")

    f.write("#\n")
    f.write("# Ops Team Cost Algorithm (for reference):\n")
    f.write("#   Formula: ops_team_size × single_resource_monthly_ops_usd × on_call_multiplier × deploy_freq_multiplier\n")
    f.write("#   Based on:\n")
    f.write("#     - Google SRE Handbook (2016): On-call burden = 25-50% FTE overhead\n")
    f.write("#     - DORA State of DevOps (2021): Deploy frequency impact on ops overhead\n")
    f.write("#\n")
    f.write(f"# Calculating costs for {len(cost_details['pattern_costs'])} selected patterns:\n")
    f.write("#\n")

    # PER-PATTERN COSTS
    f.write("# PER-PATTERN COSTS:\n")
    f.write("# ────────────────────────────────────────────────────────────\n")

    for pc in cost_details['pattern_costs']:
        f.write("#\n")
        f.write(f"#  {pc['index']}. {pc['id']} (match score: {pc['match_score']:.2f})\n")
        f.write(f"#     Adoption: ${pc['adoption_cost']:,.1f}\n")
        f.write(f"#     Monthly (min): ${pc['monthly_min']:,.1f}\n")
        f.write(f"#     Monthly (expected): ${pc['monthly_expected']:,.1f}\n")
        f.write(f"#     Ops cost: {pc['ops_explanation']}\n")
        f.write(f"#     ──────────────────────────────────────\n")
        if intent == "minimize-capex":
            f.write(f"#     CapEx (one-time): ${pc['adoption_cost']:,.1f}\n")
        elif intent == "optimize-tco":
            f.write(f"#     TCO ({amortization_months}mo): ${pc['adoption_cost']:,.1f} + (${pc['monthly_expected']:,.1f} × {amortization_months}) = ${pc['tco']:,.1f}\n")
        else:  # minimize-opex (default)
            f.write(f"#     Monthly OpEx: ${pc['monthly_expected']:,.1f}\n")

    f.write("#\n")
    if intent == "minimize-opex":
        f.write(f"# Total Monthly OpEx: ${cost_details['total_opex_with_ops']:,.1f}\n")
        if cost_details['ceiling_opex'] is not None:
            status = "✓ PASS" if cost_details['total_opex_with_ops'] <= cost_details['ceiling_opex'] else "✗ FAIL"
            f.write(f"# Monthly operational ceiling: ${cost_details['ceiling_opex']:,.0f} {status}\n")
    elif intent == "minimize-capex":
        f.write(f"# Total CapEx (one-time): ${cost_details['total_pattern_capex']:,.1f}\n")
        if cost_details['ceiling_capex'] is not None:
            status = "✓ PASS" if cost_details['total_pattern_capex'] <= cost_details['ceiling_capex'] else "✗ FAIL"
            f.write(f"# One-time setup ceiling: ${cost_details['ceiling_capex']:,.0f} {status}\n")
    else:  # optimize-tco
        f.write(f"# Total TCO ({cost_details['amortization_months']}mo): ${cost_details['total_tco']:,.1f}\n")
        if cost_details['ceiling_opex'] is not None:
            status = "✓ PASS" if cost_details['total_opex_with_ops'] <= cost_details['ceiling_opex'] else "✗ FAIL"
            f.write(f"# Monthly operational ceiling: ${cost_details['ceiling_opex']:,.0f} {status}\n")
        if cost_details['ceiling_capex'] is not None:
            status = "✓ PASS" if cost_details['total_pattern_capex'] <= cost_details['ceiling_capex'] else "✗ FAIL"
            f.write(f"# One-time setup ceiling: ${cost_details['ceiling_capex']:,.0f} {status}\n")

    f.write("# ============================================================\n")


def _format_cargo_warning(warning: Dict[str, Any]) -> str:
    """
    Format warning in Cargo-style diagnostic format.

    Example:
    warning[cost_total_opex_exceeds_ceiling]: Total monthly cost exceeds ceiling
      |
      | Pattern opex: $1,200
      | Ops team cost: $20,000
      | Total: $21,200
      | Ceiling: $15,000
      | Overage: $6,200
      |
      = help: Try one of:
         - Increase monthly ceiling to $21,200 or more
         - Remove high-cost patterns: db-read-replicas, cache-aside
         - Reduce ops_team_size from 2
    """
    code = warning.get("code", "unknown")
    message = warning.get("message", "")
    details = warning.get("details", {})
    suggestions = warning.get("suggestions", [])
    severity = warning.get("severity", "medium")

    output = []
    output.append(f"{severity}[{code}]: {message}")

    if details:
        output.append("  |")
        for key, value in details.items():
            if isinstance(value, (int, float)):
                output.append(f"  | {key}: ${value:,.0f}")
            else:
                output.append(f"  | {key}: {value}")
        output.append("  |")

    if suggestions:
        output.append("  = help: Try one of:")
        for suggestion in suggestions:
            output.append(f"     - {suggestion}")

    return "\n".join(output)

def _clean_spec_for_output(spec: Dict[str, Any]) -> Dict[str, Any]:
    """
    Remove defaulted values from top-level sections before output.

    Keep only user-provided values at top level.
    All defaults remain in assumptions section.

    Args:
        spec: Compiled spec with defaults merged at top level

    Returns:
        Cleaned spec with only user values at top level
    """
    import copy
    cleaned = copy.deepcopy(spec)
    assumptions = cleaned.get("assumptions", {})

    # Remove defaulted constraints from top level
    if "constraints" in assumptions:
        spec_constraints = cleaned.get("constraints", {})
        for key in assumptions["constraints"].keys():
            if key in spec_constraints:
                # Check if entire value matches (it was defaulted)
                if key == "features" and isinstance(spec_constraints[key], dict):
                    # For features dict, remove all defaulted feature flags
                    assumed_features = assumptions["constraints"].get("features", {})
                    for feature_key in list(assumed_features.keys()):
                        spec_constraints[key].pop(feature_key, None)
                    # If features dict is now empty, remove it
                    if not spec_constraints[key]:
                        spec_constraints.pop(key, None)
                else:
                    spec_constraints.pop(key, None)

    # Remove defaulted NFR from top level
    if "nfr" in assumptions:
        spec_nfr = cleaned.get("nfr", {})
        for key in list(assumptions["nfr"].keys()):
            if key in spec_nfr:
                # Check if it's a nested dict
                if isinstance(assumptions["nfr"][key], dict) and isinstance(spec_nfr[key], dict):
                    # Remove nested defaulted fields — recurse one more level so that
                    # user-provided sub-keys (e.g. compliance.sox) are preserved when
                    # the sibling assumed sub-keys (gdpr, ccpa, …) are cleaned out.
                    for nested_key in list(assumptions["nfr"][key].keys()):
                        assumed_nested = assumptions["nfr"][key][nested_key]
                        spec_nested = spec_nfr[key].get(nested_key)
                        if isinstance(assumed_nested, dict) and isinstance(spec_nested, dict):
                            # Rebuild spec_nested keeping only user-provided sub-keys.
                            # Do NOT mutate spec_nested in-place: deepcopy preserves
                            # internal aliases, so spec_nested may be the same object
                            # as assumed_nested (created by _merge_nfr_with_defaults).
                            user_sub_keys = set(spec_nested.keys()) - set(assumed_nested.keys())
                            if user_sub_keys:
                                spec_nfr[key][nested_key] = {k: spec_nested[k] for k in user_sub_keys}
                            else:
                                spec_nfr[key].pop(nested_key, None)
                        else:
                            spec_nfr[key].pop(nested_key, None)
                    # If nested dict is now empty, remove parent key
                    if not spec_nfr[key]:
                        spec_nfr.pop(key, None)
                else:
                    spec_nfr.pop(key, None)

    # Remove defaulted operating_model from top level
    if "operating_model" in assumptions:
        spec_operating = cleaned.get("operating_model", {})
        for key in assumptions["operating_model"].keys():
            spec_operating.pop(key, None)
        # If operating_model is now empty, remove it
        if not spec_operating:
            cleaned.pop("operating_model", None)

    # Remove defaulted cost from top level (if entire cost section was defaulted)
    if "cost" in assumptions and "cost" not in spec:
        # Cost was entirely defaulted, don't add it to top level
        pass
    elif "cost" in assumptions:
        spec_cost = cleaned.get("cost", {})
        for key in list(assumptions["cost"].keys()):
            if key in spec_cost:
                if isinstance(assumptions["cost"][key], dict) and isinstance(spec_cost[key], dict):
                    # Remove nested defaulted fields
                    for nested_key in assumptions["cost"][key].keys():
                        spec_cost[key].pop(nested_key, None)
                    # If nested dict is now empty, remove parent key
                    if not spec_cost[key]:
                        spec_cost.pop(key, None)
                else:
                    spec_cost.pop(key, None)
        # If cost is now empty, remove it
        if not spec_cost:
            cleaned.pop("cost", None)

    # Remove empty top-level sections (user didn't provide any values)
    # These sections should only exist if user provided explicit values
    for section in ["constraints", "nfr", "operating_model", "cost"]:
        if section in cleaned:
            section_data = cleaned[section]
            # Check if section is empty or contains only empty dicts/lists
            if not section_data or (isinstance(section_data, dict) and not any(section_data.values())):
                cleaned.pop(section, None)

    return cleaned

def _calculate_partial_match_score(
    rejected_pattern: Dict[str, Any],
    patterns: Dict[str, Dict[str, Any]],
    spec: Dict[str, Any]
) -> int:
    """
    Calculate partial match score for a rejected pattern.

    Partial match score = total rules - failed rules
    Higher score = pattern was closer to being selected

    Args:
        rejected_pattern: Rejected pattern entry with id and failed_rules
        patterns: Full pattern registry
        spec: User spec

    Returns:
        Partial match score (count of rules that DID match)
    """
    pid = rejected_pattern.get("id")
    pattern = patterns.get(pid, {})

    # Get total rules count
    total_rules = 0
    total_rules += len(pattern.get("supports_constraints", []))
    total_rules += len(pattern.get("supports_nfr", []))

    # Get failed rules count
    failed_rules = rejected_pattern.get("failed_rules", [])
    failed_count = len(failed_rules)

    # Partial match score = rules that DID match
    partial_score = total_rules - failed_count

    return partial_score

def _sort_rejected_patterns_by_relevance(
    rejected_patterns: List[Dict[str, Any]],
    patterns: Dict[str, Dict[str, Any]],
    spec: Dict[str, Any]
) -> List[Dict[str, Any]]:
    """
    Sort rejected patterns by partial match score (descending).

    Patterns that "almost made it" appear first.
    Secondary sort: alphabetically by id (if scores tied)

    Adds partial_match_score field to each rejected pattern.

    Args:
        rejected_patterns: List of rejected pattern entries
        patterns: Full pattern registry
        spec: User spec

    Returns:
        Sorted list of rejected patterns with partial_match_score added
    """
    # Calculate partial match scores and add to entries
    for rejected in rejected_patterns:
        rejected["partial_match_score"] = _calculate_partial_match_score(rejected, patterns, spec)

    # Sort by:
    # 1. partial_match_score descending (highest first)
    # 2. id alphabetically (if tied)
    rejected_patterns.sort(key=lambda x: (-x.get("partial_match_score", 0), x.get("id", "")))

    return rejected_patterns

def _build_requirements_to_patterns_index(
    honored_rules: Dict[str, Dict[str, List[Dict]]],
    match_scores: Dict[str, float]
) -> Dict[str, List[str]]:
    """
    Build inverse index: spec path -> list of pattern IDs (sorted by match_score).

    Args:
        honored_rules: {pattern_id: {constraints: [rules], nfr: [rules]}}
        match_scores: {pattern_id: float}

    Returns:
        Dict mapping spec path -> [pattern_id1, pattern_id2, ...] (sorted by score)

    Example:
        {
            "/constraints/cloud": ["arch-serverless--aws", "cost-serverless-pay-per-use"],
            "/constraints/features/caching": ["api-graphql-schema-first", "arch-serverless--aws"],
            "/nfr/availability/target": ["arch-serverless--aws"]
        }
    """
    index = {}

    for pattern_id, rules_by_type in honored_rules.items():
        # Process constraint rules
        for rule in rules_by_type.get("constraints", []):
            path = rule.get("path", "")
            if path:
                if path not in index:
                    index[path] = []
                index[path].append(pattern_id)

        # Process NFR rules
        for rule in rules_by_type.get("nfr", []):
            path = rule.get("path", "")
            if path:
                if path not in index:
                    index[path] = []
                index[path].append(pattern_id)

    # Sort each pattern list by match_score (descending - highest first)
    for path in index:
        index[path] = sorted(index[path], key=lambda pid: match_scores.get(pid, 0), reverse=True)

    return index

def _format_pattern_list(pattern_ids: List[str], max_display: int = 3) -> str:
    """
    Format pattern list for inline comments.

    Args:
        pattern_ids: List of pattern IDs (already sorted by match_score)
        max_display: Maximum patterns to show before "... (N more)"

    Returns:
        Formatted string like "pattern1, pattern2, pattern3, ... (2 more)"

    Examples:
        ["p1"] -> "p1"
        ["p1", "p2", "p3"] -> "p1, p2, p3"
        ["p1", "p2", "p3", "p4", "p5"] -> "p1, p2, p3, ... (2 more)"
    """
    if not pattern_ids:
        return ""

    if len(pattern_ids) <= max_display:
        return ", ".join(pattern_ids)

    # Show first max_display, then summarize rest
    displayed = ", ".join(pattern_ids[:max_display])
    remaining = len(pattern_ids) - max_display
    return f"{displayed}, ... ({remaining} more)"

def _should_skip_comment_for_path(key_path: str) -> bool:
    """
    Determine if a path should skip comment injection (patterns don't contribute).

    Args:
        key_path: JSON pointer path (e.g., "/cost/intent/priority" or "/assumptions/cost/intent/priority")

    Returns:
        True if path should skip comment, False otherwise

    Skip comments for:
    - /cost/intent/* (patterns don't choose intent)
    - /cost/ceilings/* (patterns don't set budgets)

    Note: /cost/preferences/* is NOT skipped - handled by metadata-based comments
    Note: /operating_model/* is NOT skipped - patterns CAN match on ops_team_size
    Note: Works for both user input paths (/cost/...) and assumptions paths (/assumptions/cost/...)
    """
    # Normalize path: strip /assumptions prefix for consistent checking
    normalized_path = key_path
    if key_path.startswith("/assumptions/"):
        normalized_path = key_path.replace("/assumptions/", "/", 1)

    if normalized_path.startswith("/cost/intent/"):
        return True
    if normalized_path.startswith("/cost/ceilings/"):
        return True
    return False

def _inject_comments_recursive(
    data: Any,
    current_path: str,
    requirements_index: Dict[str, List[str]],
    yaml_obj: Any
) -> None:
    """
    Recursively inject comments into ruamel.yaml object based on requirements index.

    Args:
        data: Current data node (dict, list, or scalar)
        current_path: Current JSON pointer path (e.g., "/constraints/cloud")
        requirements_index: Path -> [pattern_ids] mapping
        yaml_obj: ruamel.yaml object (with comment support)

    Side effects:
        Modifies yaml_obj in-place to add comments
    """
    from ruamel.yaml.comments import CommentedMap

    if isinstance(data, dict):
        for key, value in data.items():
            # Build path for this key
            key_path = f"{current_path}/{key}"

            # Skip comment for paths where patterns don't contribute
            if _should_skip_comment_for_path(key_path):
                # Recurse into nested structures but don't add comments
                if isinstance(value, (dict, list)):
                    _inject_comments_recursive(value, key_path, requirements_index, yaml_obj)
                continue

            # Skip comment for null values
            if value is None:
                continue

            # Normalize path for index lookup: strip /assumptions prefix
            # This allows both user input paths (/constraints/cloud) and
            # assumptions paths (/assumptions/constraints/cloud) to match the same index keys
            lookup_path = key_path
            if key_path.startswith("/assumptions/"):
                lookup_path = key_path.replace("/assumptions/", "/", 1)

            # Check if this path should get a comment
            if lookup_path in requirements_index:
                patterns = requirements_index[lookup_path]
                comment_text = _format_pattern_list(patterns)

                # Inject comment using ruamel.yaml API
                if isinstance(data, CommentedMap) and comment_text:
                    data.yaml_add_eol_comment(comment_text, key)

            # Recurse into nested structures
            if isinstance(value, (dict, list)):
                _inject_comments_recursive(value, key_path, requirements_index, yaml_obj)

def _build_metadata_comments_index(
    selected_pattern_ids: List[str],
    patterns: Dict[str, Dict[str, Any]],
    match_scores: Dict[str, float],
    spec: Dict[str, Any]
) -> Dict[str, List[str]]:
    """
    Build index for metadata-based comments (not rule-based).

    Currently handles:
    - /cost/preferences/prefer_free_tier_if_possible: patterns with freeTierEligible==true

    Args:
        selected_pattern_ids: List of selected pattern IDs
        patterns: Full pattern registry
        match_scores: Pattern match scores
        spec: Compiled spec

    Returns:
        Dict mapping spec path -> [pattern_ids] (sorted by match_score)
    """
    index = {}

    # Check prefer_free_tier_if_possible
    prefer_free = _json_pointer_get(spec, "/cost/preferences/prefer_free_tier_if_possible")
    if prefer_free is True:
        # Find patterns with freeTierEligible==true
        free_tier_patterns = []
        for pid in selected_pattern_ids:
            pattern = patterns.get(pid, {})
            cost_info = pattern.get("cost", {})
            if cost_info.get("freeTierEligible") is True:
                free_tier_patterns.append(pid)

        # Sort by match_score
        free_tier_patterns = sorted(
            free_tier_patterns,
            key=lambda pid: match_scores.get(pid, 0),
            reverse=True
        )

        if free_tier_patterns:
            index["/cost/preferences/prefer_free_tier_if_possible"] = free_tier_patterns

    # Future: Add other metadata-based comments here
    # e.g., prefer_saas_first, etc.

    return index

def _extract_config_options_comment(field_schema: Dict[str, Any]) -> Optional[str]:
    """
    Extract available options for a config field from its schema definition.

    Returns comment string showing valid values:
    - "Options: a, b, c" for enum fields
    - "Range: 0-100" for numeric fields with min/max
    - "Boolean" for boolean fields
    - None if no useful metadata

    Args:
        field_schema: Schema definition for a single config field

    Returns:
        Comment string or None
    """
    if not field_schema:
        return None

    # Enum values (most specific)
    if "enum" in field_schema:
        enum_values = field_schema["enum"]
        if len(enum_values) <= 10:  # Only show if reasonable number of options
            # Format values nicely
            formatted_values = [str(v) for v in enum_values]
            return f"Options: {', '.join(formatted_values)}"
        else:
            return f"Options: {len(enum_values)} choices"

    # Numeric range
    field_type = field_schema.get("type")
    if field_type in ["number", "integer"]:
        min_val = field_schema.get("minimum")
        max_val = field_schema.get("maximum")
        if min_val is not None and max_val is not None:
            return f"Range: {min_val}-{max_val}"
        elif min_val is not None:
            return f"Min: {min_val}"
        elif max_val is not None:
            return f"Max: {max_val}"

    # Boolean
    if field_type == "boolean":
        return "Boolean"

    return None

def _write_compiled_spec_with_comments(
    spec: Dict[str, Any],
    output_file: Path,
    requirements_index: Dict[str, List[str]],
    metadata_index: Dict[str, List[str]],
    patterns: Dict[str, Dict[str, Any]] = None,
    cost_details: Dict[str, Any] = None,
    cost_warnings: List[Dict[str, Any]] = None,
    advisory_warnings: List[Dict[str, Any]] = None,
    verbose: bool = False
) -> None:
    """
    Write compiled-spec.yaml with inline comments showing pattern contributions.

    Args:
        spec: Compiled spec with assumptions
        output_file: Output file path
        requirements_index: Path -> [pattern_ids] mapping from _build_requirements_to_patterns_index
        metadata_index: Path -> [pattern_ids] mapping from _build_metadata_comments_index
        patterns: Full pattern registry (used to inject description comments on pattern keys)
        cost_details: Cost feasibility check details (optional, appended at bottom)
        cost_warnings: Cost-related warnings (code starts with "cost_"), shown inside cost section
        advisory_warnings: warn_nfr/warn_constraints advisories, shown in separate section after cost
        verbose: When True, also appends the Details section (ops breakdown, DORA
                 table, algorithm citations, per-pattern costs) after the Summary.
                 Defaults to False (Summary only).
    """
    from ruamel.yaml import YAML
    from ruamel.yaml.comments import CommentedMap

    # Merge indexes (metadata takes precedence for same paths)
    combined_index = {**requirements_index, **metadata_index}

    # Create ruamel.yaml instance (preserves comments and formatting)
    yaml = YAML()
    yaml.default_flow_style = False
    yaml.preserve_quotes = True
    yaml.width = 4096  # Prevent line wrapping

    # Convert spec dict to CommentedMap (ruamel.yaml's comment-aware dict)
    import io
    stream = io.StringIO()
    yaml.dump(spec, stream)
    stream.seek(0)
    commented_spec = yaml.load(stream)

    # Inject comments recursively
    _inject_comments_recursive(commented_spec, "", combined_index, yaml)

    # Inject description comments on pattern keys in both:
    #   - top-level patterns.{pid} (user-provided config overrides)
    #   - assumptions.patterns.{pid} (compiler-generated defaults)
    # Also inject config option comments on each config field
    if patterns:
        for section in [
            commented_spec.get("patterns"),
            (commented_spec.get("assumptions") or {}).get("patterns"),
        ]:
            if section and isinstance(section, CommentedMap):
                for pid in section:
                    # Add description comment on pattern ID
                    desc = (patterns.get(pid) or {}).get("description", "")
                    if desc:
                        section.yaml_add_eol_comment(desc, pid)

                    # Add config option comments on each config field
                    pattern_config = section[pid]
                    if isinstance(pattern_config, CommentedMap):
                        config_schema = (patterns.get(pid) or {}).get("configSchema", {})
                        properties = config_schema.get("properties", {})

                        for config_key in pattern_config:
                            field_schema = properties.get(config_key)
                            option_comment = _extract_config_options_comment(field_schema)
                            if option_comment:
                                pattern_config.yaml_add_eol_comment(option_comment, config_key)

    # Write to file with cost feasibility analysis as comments at bottom
    with open(output_file, "w", encoding="utf-8") as f:
        yaml.dump(commented_spec, f)

        # Append cost feasibility check as comments (human-readable, not parseable YAML)
        if cost_details:
            _write_cost_summary_section(f, cost_details, cost_warnings or [])
            if verbose:
                _write_cost_details_section(f, cost_details)
        # Advisory warnings (warn_nfr/warn_constraints) always shown after cost section
        if advisory_warnings:
            _write_advisory_warnings_section(f, advisory_warnings)

def _generate_output_files(
    spec: Dict[str, Any],
    selected_patterns: List[str],
    rejected_patterns: List[Dict[str, Any]],
    warnings: List[Dict[str, Any]],
    patterns: Dict[str, Dict[str, Any]],
    output_dir: str,
    verbose: bool,
    timestamp: bool,
    match_scores: Dict[str, int],
    honored_rules: Dict[str, Dict[str, List[Dict]]],
    cost_details: Dict[str, Any] = None
) -> List[Tuple[str, str]]:
    """
    Phase 5: Generate output files.

    Files (always):
    - compiled-spec.yaml (spec with assumptions)
    - selected-patterns.yaml

    Files (verbose only):
    - rejected-patterns.yaml
    - warnings.yaml

    Args:
        spec: Compiled spec with assumptions
        selected_patterns: Selected pattern IDs
        rejected_patterns: Rejected pattern objects with reasons
        warnings: Warning objects from Phase 4
        patterns: Full pattern registry
        output_dir: Output directory path
        verbose: Verbose flag
        timestamp: Timestamp flag
        match_scores: Dict mapping pattern_id -> count of matched rules
        honored_rules: Dict mapping pattern_id -> {"constraints": [rules], "nfr": [rules]}

    Returns:
        List of (file_path, annotation) tuples for files written
    """
    import os
    from pathlib import Path
    from datetime import datetime, timezone
    import yaml

    output_path = Path(output_dir)
    output_path.mkdir(parents=True, exist_ok=True)

    # Generate timestamp suffix if requested
    ts_suffix = ""
    if timestamp:
        ts_suffix = f"-{datetime.now(timezone.utc).strftime('%Y-%m-%dT%H:%M:%SZ')}"

    # Track written files with annotations
    written_files = []

    # Always: compiled-spec.yaml
    # Clean spec: remove defaulted values from top level, keep only in assumptions
    # Strip nulls from output so compiled-spec.yaml fed back as input is idempotent
    cleaned_spec = _strip_null_values(_clean_spec_for_output(spec))
    compiled_spec_file = output_path / f"compiled-spec{ts_suffix}.yaml"

    # Split warnings: cost warnings stay in cost section; advisory warnings get their own section
    cost_warnings = [w for w in (warnings or []) if w.get("code", "").startswith("cost_")]
    advisory_warnings = sorted(
        [w for w in (warnings or []) if w.get("code", "") in ("warn_nfr", "warn_constraints")],
        key=lambda w: match_scores.get(w.get("pattern_id", ""), 0),
        reverse=True
    )

    if verbose:
        # Verbose mode: write with inline comments showing pattern contributions
        requirements_index = _build_requirements_to_patterns_index(honored_rules, match_scores)
        metadata_index = _build_metadata_comments_index(selected_patterns, patterns, match_scores, spec)
        _write_compiled_spec_with_comments(cleaned_spec, compiled_spec_file, requirements_index, metadata_index, patterns, cost_details, cost_warnings, advisory_warnings, verbose=verbose)
    else:
        # Normal mode: write plain YAML + cost summary as comments
        with open(compiled_spec_file, "w", encoding="utf-8") as f:
            yaml.dump(cleaned_spec, f, default_flow_style=False, sort_keys=False)
            if cost_details:
                _write_cost_summary_section(f, cost_details, cost_warnings)
            if advisory_warnings:
                _write_advisory_warnings_section(f, advisory_warnings)

    written_files.append((str(compiled_spec_file), "(above output)"))

    # Always: selected-patterns.yaml
    # Sort selected patterns by match_score (descending - highest first)
    sorted_patterns = sorted(selected_patterns, key=lambda pid: match_scores.get(pid, 0), reverse=True)

    selected_output = []
    for pid in sorted_patterns:
        pattern = patterns[pid]

        # Build output entry with required fields
        entry = {
            "id": pid,
            "title": pattern.get("title", "")
        }

        # Add verbose-only fields if requested
        if verbose:
            # description (verbose only)
            description = pattern.get("description", "")
            if description:
                entry["description"] = description

        # honored_rules (always included) - keep only path and reason per rule
        raw_rules = honored_rules.get(pid, {"constraints": [], "nfr": []})
        entry["honored_rules"] = {
            section: [{"path": r["path"], "reason": r.get("reason", "")} for r in rules]
            for section, rules in raw_rules.items()
        }

        if verbose:
            # provides (verbose only)
            provides_caps = [
                {"capability": p["capability"], "reasoning": p["reasoning"]}
                for p in pattern.get("provides", [])
                if p.get("capability") and p.get("reasoning")
            ]
            if provides_caps:
                entry["provides"] = provides_caps

            # requires (verbose only)
            requires_caps = [
                {"capability": r["capability"], "reasoning": r["reasoning"]}
                for r in pattern.get("requires", [])
                if r.get("capability") and r.get("reasoning")
            ]
            if requires_caps:
                entry["requires"] = requires_caps

            # cost (for reference only) (verbose only)
            cost_data = pattern.get("cost", {})
            if cost_data:
                monthly_range = cost_data.get("estimatedMonthlyRangeUsd", {})
                min_monthly = monthly_range.get("min", 0)
                max_monthly = monthly_range.get("max", 0)

                cost_entry = {
                    "adoption_usd": cost_data.get("adoptionCost", 0),
                    "monthly_min_usd": min_monthly,
                    "monthly_max_usd": max_monthly,
                    "monthly_expected_usd": (min_monthly + max_monthly) / 2 if min_monthly or max_monthly else 0,
                    "license_cost": cost_data.get("licenseCost", "Free (no license)")
                }
                entry["cost (for reference only)"] = cost_entry

            # conflicts (verbose only)
            conflicts = pattern.get("conflicts", {})
            incompatible = conflicts.get("incompatibleWithDesignPatterns", [])
            if incompatible:
                entry["conflicts"] = {
                    "incompatibleWithDesignPatterns": incompatible
                }

        selected_output.append(entry)

    selected_file = output_path / f"selected-patterns{ts_suffix}.yaml"
    with open(selected_file, "w", encoding="utf-8") as f:
        yaml.dump(selected_output, f, default_flow_style=False, sort_keys=False)
    written_files.append((str(selected_file), "(further details of selected patterns)"))

    # Verbose only: rejected-patterns.yaml
    if verbose and rejected_patterns:
        sorted_rejected = _sort_rejected_patterns_by_relevance(rejected_patterns, patterns, spec)
        # Sort alphabetically by pattern id (a → z)
        sorted_rejected.sort(key=lambda e: e.get("id", ""))

        rejected_file = output_path / f"rejected-patterns{ts_suffix}.yaml"
        with open(rejected_file, "w", encoding="utf-8") as f:
            yaml.dump(sorted_rejected, f, default_flow_style=False, sort_keys=False)
        written_files.append((str(rejected_file), "(why these patterns were rejected)"))

    return written_files

def _matches_excluded_if(spec: Dict[str, Any], ex: Dict[str, Any]) -> bool:
    path = ex.get("path", "")
    op = ex.get("op")
    value = ex.get("value")
    actual = _json_pointer_get(spec, path)
    if op == "==":
        return actual == value
    if op == "!=":
        return actual != value
    if op == "in":
        # Check if actual is in the value list
        if isinstance(value, list):
            return actual in value
        return False
    if op == "not-in":
        # Check if actual is NOT in the value list
        if isinstance(value, list):
            return actual not in value
        return False
    if op in (">", "<", ">=", "<="):
        # Numeric comparison operators
        try:
            if op == ">":
                return float(actual) > float(value)
            if op == "<":
                return float(actual) < float(value)
            if op == ">=":
                return float(actual) >= float(value)
            if op == "<=":
                return float(actual) <= float(value)
        except (TypeError, ValueError):
            return False
    # Unknown operator
    return False

def _detect_and_reject_conflicts(
    selected: List[Dict[str, Any]],
    patterns: Dict[str, Dict[str, Any]]
) -> Tuple[List[Dict[str, Any]], List[Dict[str, Any]]]:
    """
    Process selected patterns sequentially; reject patterns that conflict
    with already-accepted patterns.

    Algorithm: First-selected pattern wins. If pattern B conflicts with
    already-accepted pattern A, reject B.

    Args:
        selected: List of pattern dicts with 'id', 'reason', 'tier'
        patterns: Full pattern registry (id -> pattern object)

    Returns:
        Tuple of (accepted_patterns, conflict_rejected_patterns)
    """
    accepted = []
    conflict_rejected = []
    accepted_ids = set()

    for candidate in selected:
        pid = candidate["id"]
        pattern = patterns.get(pid, {})
        conflicts = pattern.get("conflicts", {}).get("incompatibleWithDesignPatterns", [])

        # Check if this pattern conflicts with any already-accepted pattern
        conflicting_with = [c for c in conflicts if c in accepted_ids]

        if conflicting_with:
            # Reject this pattern due to conflict
            reason = f"Incompatible with already-selected pattern(s): {', '.join(conflicting_with)}"
            conflict_rejected.append({
                "id": pid,
                "reason": reason,
                "tier": candidate.get("tier", "open"),
                "conflictsWith": conflicting_with
            })
        else:
            # Accept this pattern
            accepted.append(candidate)
            accepted_ids.add(pid)

    return accepted, conflict_rejected

def _filter_coding_patterns_post_selection(selected_ids, patterns, include_coding_patterns):
    """
    Phase 3.5: Post-process filter to remove coding patterns unless flag is enabled.

    This runs AFTER all selection logic (constraints/NFR/conflicts) and BEFORE cost check.
    A pattern is considered "coding-level" if "coding" appears in its types array.

    Args:
        selected_ids: List of selected pattern IDs
        patterns: Full pattern registry (dict mapping id -> pattern object)
        include_coding_patterns: Boolean flag from CLI

    Returns:
        Tuple of (final_selected_ids, coding_filtered_patterns)
    """
    if include_coding_patterns:
        # Flag enabled: include all patterns (no filtering)
        return selected_ids, []

    final_selected = []
    coding_filtered = []

    for pattern_id in selected_ids:
        pattern = patterns[pattern_id]
        types = pattern.get('types', [])
        if 'coding' in types:
            # Exclude: pattern has "coding" type
            coding_filtered.append({
                'id': pattern_id,
                'reason': 'Coding-level pattern excluded (use --include-coding-patterns to include)',
                'tier': pattern.get('availability', {}).get('tier', 'open')
            })
        else:
            # Include: no "coding" type
            final_selected.append(pattern_id)

    return final_selected, coding_filtered

def _select_patterns(spec: Dict[str, Any], patterns: Dict[str, Dict[str, Any]], include_coding_patterns: bool = False) -> Tuple[List[Dict[str, Any]], List[Dict[str, Any]]]:
    """
    Select applicable patterns based on spec constraints.

    Filtering steps (in order):
    1. Apply excludedIf rules (pattern-level exclusion logic)
    2. Check cloud and language compatibility
    3. Detect and reject incompatible patterns (first-selected wins)
    4. Filter generic vs specific variants

    Returns:
        Tuple of (selected_patterns, rejected_patterns)
        Each is a list of dicts with 'id', 'reason', 'tier' keys.
        Rejected patterns with conflicts include 'conflictsWith' field.
    """
    selected: List[Dict[str, Any]] = []
    rejected: List[Dict[str, Any]] = []

    cloud = _json_pointer_get(spec, "/constraints/cloud")
    lang = _json_pointer_get(spec, "/constraints/language")
    pii = bool(_json_pointer_get(spec, "/nfr/data/pii") or False)

    for pid, p in patterns.items():
        tier = (p.get("availability", {}) or {}).get("tier", "open")

        # Determine if excluded
        excluded = False
        excluded_reason = None
        for ex in (p.get("conflicts", {}) or {}).get("excludedIf", []) or []:
            if isinstance(ex, dict) and _matches_excluded_if(spec, ex):
                excluded = True
                excluded_reason = ex.get("reason") or "Excluded by rule"
                break
        if excluded:
            rejected.append({"id": pid, "reason": excluded_reason, "tier": tier})
            continue

        # Light compatibility check
        compat = p.get("compatibility", {}) or {}
        pattern_clouds = compat.get("cloud") or ["agnostic"]  # Now singular
        pattern_langs = compat.get("language") or ["agnostic"]  # Now singular
        pattern_platforms = compat.get("platform") or ["agnostic"]  # New field

        cloud_ok = ("agnostic" in pattern_clouds) or (cloud in pattern_clouds)
        lang_ok = ("agnostic" in pattern_langs) or (lang in pattern_langs)

        # NEW: Platform compatibility check
        spec_platform = _json_pointer_get(spec, "/constraints/platform")
        if spec_platform:
            platform_ok = ("agnostic" in pattern_platforms) or (spec_platform in pattern_platforms)
        else:
            platform_ok = True  # No platform constraint = all platforms OK

        # Example: free-tier patterns are typically unsuitable for PII
        if pid.startswith("cost-") and "free" in pid and pii:
            rejected.append({"id": pid, "reason": "PII present; free-tier patterns typically disallowed/inadvisable", "tier": tier})
            continue

        if cloud_ok and lang_ok and platform_ok:
            selected.append({"id": pid, "reason": "Compatible", "tier": tier})
        else:
            reason_parts = []
            if not cloud_ok:
                reason_parts.append("cloud")
            if not lang_ok:
                reason_parts.append("language")
            if not platform_ok:
                reason_parts.append("platform")
            reason = f"Compatibility mismatch: {', '.join(reason_parts)}"
            rejected.append({"id": pid, "reason": reason, "tier": tier})

    # Detect and reject conflicting patterns
    # Algorithm: First-selected pattern wins. If pattern B declares pattern A
    # as incompatible, and A is already accepted, reject B.
    # This ensures no two conflicting patterns are selected.
    accepted, conflict_rejected = _detect_and_reject_conflicts(selected, patterns)
    selected = accepted
    rejected.extend(conflict_rejected)

    # Generic vs specific filtering: if specific variants are selected, exclude generic base
    # Pattern naming convention: generic pattern "foo", specific variants "foo--bar", "foo--baz"
    generic_to_exclude = set()
    specific_selected = set()

    for s in selected:
        pid = s["id"]
        if "--" in pid:
            # This is a specific variant
            base = pid.split("--")[0]
            specific_selected.add(base)

    # Mark generic patterns for exclusion if their specific variants are selected
    for s in selected:
        pid = s["id"]
        if "--" not in pid and pid in specific_selected:
            # This is a generic pattern and we have specific variants selected
            generic_to_exclude.add(pid)

    # Filter out generic patterns that should be excluded
    final_selected = []
    for s in selected:
        if s["id"] in generic_to_exclude:
            rejected.append({"id": s["id"], "reason": "Generic pattern excluded because specific variant(s) selected", "tier": s.get("tier", "open")})
        else:
            final_selected.append(s)

    return final_selected, rejected

def _build_decisions(selected: List[Dict[str, Any]], patterns: Dict[str, Dict[str, Any]]) -> List[Dict[str, Any]]:
    """Create skimmable decisions without changing the schema: array of {id,title,choice,...}."""
    decisions: List[Dict[str, Any]] = []
    for s in selected:
        pid = s["id"]
        pat = patterns.get(pid, {})
        # auto decision per selected pattern (simple Phase 1)
        decisions.append({
            "id": f"auto-{pid}",
            "title": pat.get("title") or f"Select {pid}",
            "choice": "selected",
            "rationale": [s.get("reason", "Selected")],
            "implications": (pat.get("tags") or [])[:8]
        })
    return decisions

def _build_assumptions(spec: Dict[str, Any], selected: List[Dict[str, Any]], patterns: Dict[str, Dict[str, Any]]) -> List[str]:
    """Deterministic, minimal assumptions. Prefer pattern hints if available."""
    out: List[str] = []

    # Prefer pattern-provided hints (if present, no schema change required; just optional field usage)
    for s in selected:
        pid = s["id"]
        pat = patterns.get(pid, {})
        hints = pat.get("assumptionHints")
        if isinstance(hints, list):
            for h in hints:
                if isinstance(h, str) and h.strip():
                    out.append(h.strip())

    # Add a few safe, non-LLM heuristics derived from inputs
    cloud = _json_pointer_get(spec, "/constraints/cloud")
    if cloud == "on-prem":
        out.append("Deployment environment may be air-gapped or have restricted outbound internet access.")
        out.append("Artifact distribution and dependency management must support offline installs (mirrors/registries).")

    # de-dupe
    return _dedupe([a for a in out if isinstance(a, str) and a.strip()])

def _build_open_questions(selected: List[Dict[str, Any]], patterns: Dict[str, Dict[str, Any]], qmap: Dict[str, Dict[str, str]]) -> List[str]:
    """Uses pattern openQuestions IDs + question bank; outputs list of strings per canonical schema."""
    required_qids: List[str] = []
    optional_qids: List[str] = []

    for s in selected:
        pat = patterns.get(s["id"], {})
        oq = pat.get("openQuestions") or {}
        if isinstance(oq, dict):
            required_qids += (oq.get("required") or [])
            optional_qids += (oq.get("optional") or [])

    def dedupe_str(lst: List[Any]) -> List[str]:
        seen=set(); out=[]
        for x in lst:
            if isinstance(x, str) and x and x not in seen:
                seen.add(x); out.append(x)
        return out

    required_qids = dedupe_str(required_qids)
    optional_qids = [x for x in dedupe_str(optional_qids) if x not in required_qids]

    # Render to simple strings (canonical schema expects array of strings)
    lines: List[str] = []
    for qid in required_qids:
        q = qmap.get(qid)
        if q:
            lines.append(f"[REQUIRED] {q.get('text','').strip()}")
        else:
            lines.append(f"[REQUIRED] {qid} (missing from question bank)")
    for qid in optional_qids:
        q = qmap.get(qid)
        if q:
            lines.append(f"[OPTIONAL] {q.get('text','').strip()}")
        else:
            lines.append(f"[OPTIONAL] {qid} (missing from question bank)")
    return lines

def _populate_cost_outputs(spec: Dict[str, Any]) -> Dict[str, Any]:
    """
    Phase 1: Populate cost.preferences and cost.tradeoff_priorities if missing.
    Keep conservative defaults, derived from intent/ceilings.
    """
    cost = spec.get("cost") if isinstance(spec.get("cost"), dict) else {}
    intent = cost.get("intent") if isinstance(cost.get("intent"), dict) else {}
    ceilings = cost.get("ceilings") if isinstance(cost.get("ceilings"), dict) else {}
    preferences = cost.get("preferences") if isinstance(cost.get("preferences"), dict) else {}
    tradeoffs = cost.get("tradeoff_priorities") if isinstance(cost.get("tradeoff_priorities"), dict) else {}

    priority = intent.get("priority")
    monthly = ceilings.get("monthly_operational_usd")

    # conservative defaults only if not set
    if "prefer_free_tier_if_possible" not in preferences:
        preferences["prefer_free_tier_if_possible"] = bool(monthly == 0)
    if "prefer_saas_first" not in preferences:
        # SaaS-first tends to reduce ops cost, but can conflict with on-prem
        cloud = _json_pointer_get(spec, "/constraints/cloud")
        preferences["prefer_saas_first"] = (cloud != "on-prem")
    # tradeoff priorities default weights based on intent
    if tradeoffs == {}:
        if priority == "minimize-opex":
            tradeoffs = {"availability": 0.3, "cost": 0.6, "time_to_market": 0.4}
        elif priority == "optimize-tco":
            tradeoffs = {"availability": 0.4, "cost": 0.5, "time_to_market": 0.3}
        elif priority == "no-limit":
            tradeoffs = {"availability": 0.7, "cost": 0.1, "time_to_market": 0.5}
        else:
            tradeoffs = {"availability": 0.4, "cost": 0.4, "time_to_market": 0.4}

    cost["preferences"] = preferences
    cost["tradeoff_priorities"] = tradeoffs
    return cost

def main():
    """
    Main compiler entry point - 5-phase progressive refinement architecture.

    Phase 1: Parse & Validate
    Phase 2: Merge with Defaults
    Phase 3: Filter Patterns (3.1-3.4)
    Phase 4: Cost Feasibility Check
    Phase 5: Cargo-Style Output
    """
    parser = argparse.ArgumentParser(
        description="ArchCompiler compiles architecture from constraints into explicit, reviewable decisions with clear trade-offs and cost impact",
        formatter_class=argparse.RawDescriptionHelpFormatter
    )
    parser.add_argument("spec_file", help="Path to YAML spec file")
    parser.add_argument(
        "-o", "--output",
        default=None,
        help="Output directory (if omitted, only compiled yaml is printed to stdout only; no compiled spec/selected/rejected patterns files are written)"
    )
    parser.add_argument(
        "-v", "--verbose",
        action="store_true",
        help="Verbose output for compiled spec"
    )
    parser.add_argument(
        "-t", "--timestamp",
        action="store_true",
        help="Add UTC timestamp to output filenames (requires --output/-o to be specified)"
    )
    parser.add_argument(
        '--include-coding-patterns',
        action='store_true',
        default=False,
        help='Include coding-level patterns (GoF, DI, test strategies, dev workflows). '
             'Default: excluded (AI can implement these). '
             'Affected patterns: gof-*, code-di-pure, build-hermetic-builds, dev-*, test-*'
    )
    # Legacy flags for backward compatibility
    parser.add_argument("--spec", help=argparse.SUPPRESS)
    parser.add_argument("--outdir", help=argparse.SUPPRESS)

    args = parser.parse_args()

    # Handle legacy flags
    if args.spec and not hasattr(args, 'spec_file'):
        args.spec_file = args.spec
    if args.outdir:
        args.output = args.outdir

    # --timestamp requires --output (no files are written without it)
    if args.timestamp and args.output is None:
        parser.error("--timestamp requires --output (-o) to be specified")

    # Phase 1: Parse & Validate
    canonical_schema = _load_canonical_schema()
    spec = _load_spec(pathlib.Path(args.spec_file))
    spec = _strip_null_values(spec)
    _validate_spec_schema(spec)
    _validate_semantic_consistency(spec)

    # Load patterns for validation
    patterns = _load_patterns(pathlib.Path.cwd())

    # Reject unknown pattern IDs in disallowed-patterns (typo protection)
    disallowed_ids = spec.get("disallowed-patterns", [])
    if disallowed_ids:
        unknown_disallowed = [pid for pid in disallowed_ids if pid not in patterns]
        if unknown_disallowed:
            for uid in unknown_disallowed:
                print(
                    f"❌ Error: disallowed-patterns contains '{uid}' "
                    f"which was not found in registry. Check for typos.",
                    file=sys.stderr,
                )
            sys.exit(1)

    # NEW: Validate user pattern configs
    _validate_user_pattern_configs(spec, patterns)

    # Phase 2: Merge with defaults
    defaults = _load_defaults()
    _merge_with_defaults(spec, defaults)

    # Phase 2.5 / Phase 3: Pattern filtering
    # Phase 2.5 (disallowed) runs first, then Phase 3.1-3.5 apply rules-based filtering.

    # Phase 2.5: Disallowed patterns filter
    # Runs before Phase 3.1 so disallowed patterns never reach constraint/NFR evaluation.
    # Only Phase 3.1 needs the filtered dict (it iterates patterns.keys() to build candidates).
    # Phases 3.2-3.5 operate on selected_ids, so they naturally skip disallowed patterns
    # without needing patterns_filtered — leave their calls unchanged.
    candidate_ids, rejected_disallowed = _filter_by_disallowed_patterns(
        list(patterns.keys()), patterns, spec
    )
    patterns_filtered = {pid: patterns[pid] for pid in candidate_ids}

    # Phase 3.1: supports_constraints  (uses patterns_filtered, not patterns)
    selected_ids, rejected_constraints, honored_rules = _filter_by_supports_constraints(patterns_filtered, spec)

    # Phase 3.2: supports_nfr  (uses original patterns for metadata lookup — safe because
    # selected_ids cannot contain any disallowed pattern at this point)
    selected_ids, rejected_nfr, honored_rules = _filter_by_supports_nfr(selected_ids, patterns, spec, honored_rules)
    rejected_patterns = rejected_disallowed + rejected_constraints + rejected_nfr

    # Phase 3.3: Conflict resolution
    selected_ids, rejected_conflicts, match_scores = _resolve_conflicts_with_match_scoring(selected_ids, patterns, spec)
    rejected_patterns.extend(rejected_conflicts)

    # Phase 3.3.1: Clean up honored_rules to remove rejected patterns from Phase 3.3
    # BUG FIX: honored_rules still contained entries for patterns rejected in conflict resolution
    # This caused verbose mode to show rejected patterns in requirement comments
    selected_ids_set = set(selected_ids)
    honored_rules = {pid: rules for pid, rules in honored_rules.items() if pid in selected_ids_set}

    # Phase 3.3.5: Validate requires_nfr and requires_constraints for selected patterns
    violations = _validate_required_spec_rules(selected_ids, patterns, spec)

    # Phase 3.4: Merge defaultConfig
    _merge_pattern_default_configs(selected_ids, patterns, spec, match_scores)

    # Phase 3.5: Coding pattern filter (post-selection)
    # Remove patterns with "coding" type unless --include-coding-patterns flag set
    # This runs after all selection logic to avoid touching existing phases
    # Cost calculation (Phase 4) uses post-filter results for accuracy
    selected_ids, coding_rejected = _filter_coding_patterns_post_selection(
        selected_ids,
        patterns,
        args.include_coding_patterns
    )
    rejected_patterns.extend(coding_rejected)

    # Phase 3.5.1: Clean up spec.assumptions.patterns to remove filtered coding patterns
    # BUG FIX: Phase 3.4 merged patterns into spec, but Phase 3.5 filtered selected_ids.
    # Must remove filtered patterns from spec to prevent them appearing in compiled-spec.yaml
    if 'assumptions' in spec and 'patterns' in spec['assumptions']:
        selected_ids_set = set(selected_ids)
        spec['assumptions']['patterns'] = {
            pid: config for pid, config in spec['assumptions']['patterns'].items()
            if pid in selected_ids_set
        }

    # Also clean up honored_rules again to remove coding patterns
    selected_ids_set = set(selected_ids)
    honored_rules = {pid: rules for pid, rules in honored_rules.items() if pid in selected_ids_set}

    # Phase 4: Cost feasibility check
    ops_team_cost = _calculate_ops_team_cost(spec.get("operating_model", {}))
    warnings, cost_details = _check_cost_feasibility(selected_ids, patterns, spec, ops_team_cost, match_scores, args.verbose)

    # Phase 3.5 (advisory): Evaluate warn_nfr and warn_constraints rules
    selected_list = [patterns[pid] for pid in selected_ids if pid in patterns]
    nfr_warnings = _evaluate_warn_nfr_rules(selected_list, spec)
    constraint_warnings = _evaluate_warn_constraints_rules(selected_list, spec)
    warnings = (warnings or []) + nfr_warnings + constraint_warnings

    # Phase 5: Output
    if violations:
        # Error case: print annotated compiled-spec to stdout + error summary, no file output
        cleaned = _clean_spec_for_output(spec)
        annotation_map = _build_error_annotation_map(violations, honored_rules, canonical_schema)
        # Some annotated fields move to assumptions section after cleaning (e.g. defaulted auth).
        # Extend the map with /assumptions/... paths so those fields still get annotated.
        extended_map = {**annotation_map}
        for path, comment in annotation_map.items():
            extended_map["/assumptions" + path] = comment
        yaml_lines = _render_annotated_yaml(cleaned, extended_map)
        print("\n".join(yaml_lines))
        print()
        print(_format_error_summary(violations))
        suggestions = _format_suggestions(violations, honored_rules, canonical_schema)
        if suggestions:
            print()
            print(suggestions)
        sys.exit(1)

    # No violations — normal file output
    import tempfile, shutil
    output_dir = args.output
    use_temp = output_dir is None
    if use_temp:
        output_dir = tempfile.mkdtemp(prefix="compiler_")

    try:
        written_files = _generate_output_files(
            spec, selected_ids, rejected_patterns, warnings, patterns,
            output_dir, args.verbose, args.timestamp, match_scores, honored_rules,
            cost_details
        )

        # Always: print compiled-spec.yaml content to stdout
        compiled_spec_path = written_files[0][0]  # First file is always compiled-spec.yaml
        with open(compiled_spec_path, "r", encoding="utf-8") as f:
            compiled_spec_content = f.read()
        print(compiled_spec_content)

        # Only when -o is specified: print file list with UTC timestamp
        if not use_temp:
            from datetime import datetime, timezone
            utc_timestamp = datetime.now(timezone.utc).strftime('%Y-%m-%dT%H:%M:%SZ')
            print(f"\nOutput Files ({utc_timestamp}):")
            for file_path, annotation in written_files:
                print(f"  - {file_path} {annotation}")
    finally:
        if use_temp:
            shutil.rmtree(output_dir, ignore_errors=True)

if __name__ == "__main__":
    main()
