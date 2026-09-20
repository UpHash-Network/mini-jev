"""Start MiniJev using the reproducible release configuration beside this file."""
from __future__ import annotations

import argparse
import json
import logging
import math
from pathlib import Path

from service.schema import ValidationError, decode_json
from service.server import serve_engine


DEFAULT_CONFIG = Path(__file__).resolve().with_name("release_config.json")
DEFAULTS = {
    "model": "Qwen/Qwen3-4B-Instruct-2507", "device": "auto", "local_files_only": True,
    "max_input_tokens": 2048, "dtype": "float32", "temperature": 1.0,
    "temperature_config": None, "prompt_style": "compact", "revision": None,
    "attention": "eager",
}


def load_config(path=DEFAULT_CONFIG, *, temperature_config=None, without_calibration=False,
                device=None, allow_download=False):
    path = Path(path).expanduser().resolve()
    raw = path.read_bytes()
    if len(raw) > 65536:
        raise ValueError("release configuration exceeds 64 KiB")
    config = decode_json(raw)
    if not isinstance(config, dict) or set(config) - set(DEFAULTS):
        raise ValueError("release configuration must be a flat object of ReleaseEngine keyword arguments")
    kwargs = {**DEFAULTS, **config}
    for name in ("model", "device", "dtype", "prompt_style", "attention"):
        if not isinstance(kwargs[name], str) or not kwargs[name].strip():
            raise ValueError(f"{name} must be a non-empty string")
    if kwargs["device"] not in ("auto", "cpu", "mps", "cuda"):
        raise ValueError("unsupported device")
    if kwargs["dtype"] not in ("float32", "float16", "bfloat16"):
        raise ValueError("unsupported dtype")
    if kwargs["prompt_style"] not in ("compact", "structured", "original"):
        raise ValueError("unsupported prompt_style")
    if kwargs["attention"] not in ("eager", "sdpa"):
        raise ValueError("unsupported attention")
    if type(kwargs["local_files_only"]) is not bool:
        raise ValueError("local_files_only must be boolean")
    if type(kwargs["max_input_tokens"]) is not int or not 1 <= kwargs["max_input_tokens"] <= 8192:
        raise ValueError("max_input_tokens must be an integer between 1 and 8192")
    temperature = kwargs["temperature"]
    try:
        valid_temperature = type(temperature) in (int, float) and temperature > 0 and math.isfinite(temperature)
    except OverflowError:
        valid_temperature = False
    if not valid_temperature:
        raise ValueError("temperature must be finite and positive")
    if kwargs["revision"] is not None and (not isinstance(kwargs["revision"], str) or not kwargs["revision"].strip()):
        raise ValueError("revision must be null or a non-empty string")
    calibration = kwargs["temperature_config"]
    if calibration is not None and (not isinstance(calibration, str) or not calibration.strip()):
        raise ValueError("temperature_config must be null or a non-empty path")
    if without_calibration:
        kwargs["temperature_config"] = None
    else:
        if temperature_config is not None:
            calibration = Path(temperature_config).expanduser().resolve()
        elif calibration is not None:
            calibration = Path(calibration).expanduser()
            if not calibration.is_absolute():
                calibration = path.parent / calibration
        elif "temperature_config" not in config and (path.parent / "temperature.json").is_file():
            calibration = path.parent / "temperature.json"
        if calibration is not None:
            calibration = Path(calibration).resolve()
            if not calibration.is_file():
                raise ValueError("temperature configuration file does not exist")
            kwargs["temperature_config"] = str(calibration)
    if device is not None:
        if device not in ("auto", "cpu", "mps", "cuda"):
            raise ValueError("unsupported device override")
        kwargs["device"] = device
    if allow_download:
        kwargs["local_files_only"] = False
    return kwargs


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--config", type=Path, default=DEFAULT_CONFIG)
    calibration = parser.add_mutually_exclusive_group()
    calibration.add_argument("--temperature-config", type=Path)
    calibration.add_argument("--without-calibration", action="store_true")
    parser.add_argument("--device", choices=("auto", "cpu", "mps", "cuda"))
    parser.add_argument("--allow-download", action="store_true")
    parser.add_argument("--host", default="127.0.0.1")
    parser.add_argument("--port", type=int, default=8765)
    parser.add_argument("--max-questions", type=int, default=8)
    parser.add_argument("--max-pending", type=int, default=2)
    parser.add_argument("--request-timeout", type=float, default=30.0)
    parser.add_argument("--print-config", action="store_true", help="print effective engine arguments without loading a model")
    args = parser.parse_args(argv)
    if not 1 <= args.max_questions <= 16:
        parser.error("--max-questions must be between 1 and 16")
    if args.max_pending < 1:
        parser.error("--max-pending must be positive")
    if not 0 < args.request_timeout <= 300:
        parser.error("--request-timeout must be in (0, 300] seconds")
    if not 0 <= args.port <= 65535:
        parser.error("--port must be between 0 and 65535")
    try:
        kwargs = load_config(args.config, temperature_config=args.temperature_config,
                             without_calibration=args.without_calibration,
                             device=args.device, allow_download=args.allow_download)
    except (OSError, ValueError, ValidationError) as exc:
        parser.error(str(exc))
    if args.print_config:
        print(json.dumps(kwargs, ensure_ascii=False, indent=2))
        return
    logging.basicConfig(level=logging.INFO, format="%(message)s")
    logging.info("Loading release %s (%s / %s / %s)", kwargs["model"],
                 kwargs["dtype"], kwargs["prompt_style"], kwargs["attention"])
    from release_engine import ReleaseEngine
    engine = ReleaseEngine(**kwargs)
    serve_engine(engine, host=args.host, port=args.port, max_questions=args.max_questions,
                 max_pending=args.max_pending, request_timeout=args.request_timeout)


if __name__ == "__main__":
    main()
