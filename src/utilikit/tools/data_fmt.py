"""Data-format helpers: JSON pretty/minify/validate/JSONPath, YAML↔JSON, CSV↔JSON."""

from __future__ import annotations

import csv
import io
import json

from fastapi import APIRouter, Body
from pydantic import BaseModel

from ..errors import ToolError
from ..registry import Endpoint, ToolInfo, register

router = APIRouter(prefix="/v1", tags=["data"])


class JsonIn(BaseModel):
    data: str
    indent: int = 2
    sort_keys: bool = False


@router.post("/json/format", summary="Pretty-print, minify or validate JSON")
def json_format(body: JsonIn) -> dict:
    try:
        parsed = json.loads(body.data)
    except json.JSONDecodeError as exc:
        raise ToolError(f"Invalid JSON at line {exc.lineno} col {exc.colno}: {exc.msg}") from exc
    pretty = json.dumps(parsed, indent=body.indent, sort_keys=body.sort_keys, ensure_ascii=False)
    minified = json.dumps(parsed, separators=(",", ":"), sort_keys=body.sort_keys, ensure_ascii=False)
    return {
        "valid": True,
        "pretty": pretty,
        "minified": minified,
        "type": type(parsed).__name__,
        "size_bytes": len(minified.encode()),
    }


@router.post("/json/query", summary="Run a JSONPath expression over JSON")
def json_query(
    data: str = Body(..., embed=True),
    path: str = Body(..., embed=True),
) -> dict:
    from jsonpath_ng.ext import parse as jp_parse

    try:
        doc = json.loads(data)
    except json.JSONDecodeError as exc:
        raise ToolError(f"Invalid JSON: {exc}") from exc
    try:
        expr = jp_parse(path)
    except Exception as exc:  # jsonpath_ng raises bare Exception subclasses
        raise ToolError(f"Invalid JSONPath: {exc}") from exc
    results = [m.value for m in expr.find(doc)]
    return {"path": path, "count": len(results), "results": results}


@router.post("/convert/yaml-json", summary="Convert YAML→JSON or JSON→YAML")
def yaml_json(
    data: str = Body(..., embed=True),
    direction: str = Body("yaml2json", embed=True),
) -> dict:
    import yaml

    if direction == "yaml2json":
        try:
            obj = yaml.safe_load(data)
        except yaml.YAMLError as exc:
            raise ToolError(f"Invalid YAML: {exc}") from exc
        return {"json": json.dumps(obj, indent=2, ensure_ascii=False)}
    if direction == "json2yaml":
        try:
            obj = json.loads(data)
        except json.JSONDecodeError as exc:
            raise ToolError(f"Invalid JSON: {exc}") from exc
        return {"yaml": yaml.safe_dump(obj, sort_keys=False, allow_unicode=True)}
    raise ToolError("direction must be 'yaml2json' or 'json2yaml'.")


@router.post("/convert/csv-json", summary="Convert CSV→JSON (array of objects) or JSON→CSV")
def csv_json(
    data: str = Body(..., embed=True),
    direction: str = Body("csv2json", embed=True),
    delimiter: str = Body(",", embed=True),
) -> dict:
    if direction == "csv2json":
        reader = csv.DictReader(io.StringIO(data), delimiter=delimiter)
        rows = list(reader)
        return {"rows": rows, "count": len(rows), "columns": reader.fieldnames or []}
    if direction == "json2csv":
        try:
            arr = json.loads(data)
        except json.JSONDecodeError as exc:
            raise ToolError(f"Invalid JSON: {exc}") from exc
        if not isinstance(arr, list) or not all(isinstance(x, dict) for x in arr):
            raise ToolError("JSON→CSV needs an array of objects.")
        cols: list[str] = []
        for row in arr:
            for k in row:
                if k not in cols:
                    cols.append(k)
        buf = io.StringIO()
        w = csv.DictWriter(buf, fieldnames=cols, delimiter=delimiter)
        w.writeheader()
        w.writerows(arr)
        return {"csv": buf.getvalue(), "rows": len(arr), "columns": cols}
    raise ToolError("direction must be 'csv2json' or 'json2csv'.")


@router.get("/base/convert", summary="Convert an integer between bases 2-36")
def base_convert(value: str, from_base: int = 10, to_base: int = 16) -> dict:
    if not (2 <= from_base <= 36 and 2 <= to_base <= 36):
        raise ToolError("Bases must be between 2 and 36.")
    try:
        n = int(value.strip().replace(" ", ""), from_base)
    except ValueError as exc:
        raise ToolError(f"{value!r} is not a base-{from_base} integer.") from exc
    digits = "0123456789abcdefghijklmnopqrstuvwxyz"
    if n == 0:
        out = "0"
    else:
        neg, n = n < 0, abs(n)
        chars = []
        while n:
            chars.append(digits[n % to_base])
            n //= to_base
        out = ("-" if neg else "") + "".join(reversed(chars))
    return {"decimal": int(value, from_base), "result": out, "from_base": from_base, "to_base": to_base}


register(
    ToolInfo(
        key="data_fmt",
        title="JSON / YAML / CSV",
        category="Text & data",
        description="JSON pretty/minify/validate, JSONPath queries, YAML↔JSON, CSV↔JSON, integer base conversion.",
        router=router,
        endpoints=[
            Endpoint("POST", "/v1/json/format", "Format JSON", '{"data":"{\\"a\\":1}"}'),
            Endpoint("POST", "/v1/json/query", "JSONPath", '{"data":"{\\"a\\":[1,2]}","path":"$.a[*]"}'),
            Endpoint("POST", "/v1/convert/yaml-json", "YAML↔JSON", '{"data":"a: 1","direction":"yaml2json"}'),
            Endpoint("POST", "/v1/convert/csv-json", "CSV↔JSON", '{"data":"a,b\\n1,2","direction":"csv2json"}'),
            Endpoint("GET", "/v1/base/convert", "Base convert", "?value=255&from_base=10&to_base=16"),
        ],
    )
)
