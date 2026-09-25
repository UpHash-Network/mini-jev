"""Exercise pinned, unmodified ChainForge registration/dispatch HTTP routes.

Uses Flask's in-process HTTP test client, not the browser frontend. This is an
integration check, not a task performance or human usability benchmark.
"""
import argparse
import hashlib
import importlib.metadata
import json
import os
import platform
import tempfile
from dataclasses import asdict
from datetime import datetime, timezone
from pathlib import Path

from service import Client
from service.schema import validate_request, validate_response


def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--api-url", default="http://127.0.0.1:8875")
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    here = Path(__file__).resolve().parent
    plan = json.loads((here / "protocol.json").read_text())
    if importlib.metadata.version("chainforge") != plan["chainforge_version"]:
        raise RuntimeError("ChainForge version differs from frozen protocol")
    os.environ["MINI_JEV_API_URL"] = args.api_url
    import chainforge.flask_app as cf
    # Do not touch the user's ChainForge flows, cache, or API credentials.
    records, failures = [], []
    with tempfile.TemporaryDirectory(prefix="mini-jev-chainforge-") as td:
        cf.FLOWS_DIR = td
        cf.app.config.update(TESTING=True)
        with cf.app.test_client() as transport, Client(args.api_url, timeout=120) as sdk:
            headers = {cf.TOKEN_HEADER: cf.SESSION_TOKEN}
            registered = transport.post("/app/initCustomProvider", headers=headers,
                json={"code": (here / "provider.py").read_text()}).get_json()
            if "error" in registered:
                raise RuntimeError(registered["error"])
            health = sdk.health()
            for case in plan["valid_cases"]:
                payload = case["payload"]
                direct = asdict(sdk.system_one(**payload))
                dispatch = transport.post("/app/callCustomProvider", headers=headers,
                    json={"name": "Mini Jev typed API", "params": {
                        "prompt": json.dumps(payload, ensure_ascii=False)}})
                body = dispatch.get_json()
                if "error" in body:
                    raise RuntimeError(body["error"])
                envelope = json.loads(body["response"])
                actual = envelope["response"]
                ids, cases = validate_request(payload)
                # asdict retains optional None fields; omit absent optional metadata
                # for strict wire schema validation, identically on both routes.
                for result in (actual, direct):
                    for answer in result["answers"].values():
                        for key in list(answer):
                            if answer[key] is None:
                                del answer[key]
                    validate_response(result, ids, cases)
                deltas, same_metadata = [], True
                for key in ids:
                    a, b = direct["answers"][key], actual["answers"][key]
                    deltas.extend(abs(a["probabilities"][k]-b["probabilities"][k])
                                  for k in a["probabilities"])
                    varying = {"probabilities", "confidence", "noul", "score"}
                    same_metadata &= ({k:v for k,v in a.items() if k not in varying}
                                      == {k:v for k,v in b.items() if k not in varying})
                checks = {
                    "http_ok": dispatch.status_code == 200,
                    "request_preserved": envelope["request"] == payload,
                    "schema_valid": True,
                    "same_model": actual["model"] == direct["model"],
                    "same_usage": actual["usage"] == direct["usage"],
                    "same_labels_and_metadata": same_metadata,
                    "probabilities_within_tolerance": max(deltas) <= plan["absolute_tolerance"],
                    "distinct_request_ids": actual["request_id"] != direct["request_id"],
                }
                if not all(checks.values()): failures.append(case["id"])
                records.append({"id": case["id"], "request": payload,
                    "direct_sdk": direct, "chainforge": actual, "checks": checks,
                    "max_probability_abs_difference": max(deltas)})
            negative = []
            for case in plan["invalid_cases"]:
                response = transport.post("/app/callCustomProvider", headers=headers,
                    json={"name":"Mini Jev typed API", "params":case["params"]}).get_json()
                rejected = "error" in response and "response" not in response
                if not rejected: failures.append(case["id"])
                negative.append({"id":case["id"], "rejected":rejected, "result":response})
    result = {
        "created_at_utc":datetime.now(timezone.utc).isoformat(),
        "scope":"Real ChainForge Flask registration/dispatch + native Mini Jev HTTP API; no browser or human study",
        "protocol_sha256":digest(here / "protocol.json"),
        "provider_sha256":digest(here / "provider.py"),
        "runner_sha256":digest(Path(__file__).resolve()),
        "chainforge_version":importlib.metadata.version("chainforge"),
        "chainforge_dispatch_source_sha256":digest(Path(cf.__file__)),
        "python":platform.python_version(), "health":health,
        "valid_request_pairs":len(records),
        "typed_answer_pairs":sum(len(r["request"]["questions"]) for r in records),
        "native_http_requests":2*len(records),
        "native_question_evaluations":2*sum(len(r["request"]["questions"]) for r in records),
        "records":records,"negative_checks":negative,"failures":failures,
        "max_probability_abs_difference":max(r["max_probability_abs_difference"] for r in records),
    }
    args.output.parent.mkdir(parents=True,exist_ok=True)
    args.output.write_text(json.dumps(result,ensure_ascii=False,indent=2)+"\n")
    print(json.dumps({k:v for k,v in result.items() if k not in {"records","health","negative_checks"}},indent=2))
    raise SystemExit(bool(failures))


if __name__ == "__main__":
    main()
