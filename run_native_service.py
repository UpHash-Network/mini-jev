"""Run the resident native MiniJev decision service on localhost."""
from __future__ import annotations

import argparse
import ipaddress
import json
import logging
import math
from pathlib import Path

from service.schema import decode_json
from service.server import serve_engine

ROOT = Path(__file__).resolve().parent
DEFAULT_CONFIG = ROOT / 'native_config.json'
FIELDS = {'model_file', 'native_binary', 'model', 'revision', 'max_input_tokens',
          'temperature', 'temperature_config', 'prompt_style', 'threads', 'device',
          'dtype', 'log_file', 'model_manifest', 'native_manifest'}
PATH_FIELDS = {'model_file', 'native_binary', 'model_manifest', 'native_manifest', 'log_file'}


def load_config(path=DEFAULT_CONFIG, *, temperature_config=None, without_calibration=False,
                model_file=None):
    path = Path(path).expanduser().resolve()
    raw = path.read_bytes()
    if len(raw) > 65536:
        raise ValueError('configuration exceeds 64 KiB')
    config = decode_json(raw)
    if not isinstance(config, dict) or set(config) - FIELDS:
        raise ValueError('configuration contains unknown fields')
    config = dict(config)
    for key in ('model_file', 'native_binary'):
        if key not in config and not (key == 'model_file' and model_file is not None):
            raise ValueError(f'configuration requires {key}')
    for key in PATH_FIELDS | {'temperature_config', 'model', 'revision', 'dtype', 'device', 'prompt_style'}:
        if key in config and config[key] is not None:
            if not isinstance(config[key], str) or not config[key].strip():
                raise ValueError(f'{key} must be a non-empty string')
        elif key in config and key not in {'temperature_config', 'model_manifest', 'native_manifest', 'log_file'}:
            raise ValueError(f'{key} must not be null')
    for key, maximum in (('threads', 32), ('max_input_tokens', 8192)):
        if key in config and (type(config[key]) is not int or not 1 <= config[key] <= maximum):
            raise ValueError(f'{key} must be an integer in [1, {maximum}]')
    if 'temperature' in config:
        try:
            valid = type(config['temperature']) in (int, float) and config['temperature'] > 0 and math.isfinite(config['temperature'])
        except OverflowError:
            valid = False
        if not valid:
            raise ValueError('temperature must be finite and positive')
    if config.get('device', 'metal') not in {'metal', 'cpu'}:
        raise ValueError('device must be metal or cpu')
    if config.get('prompt_style', 'repeat_typed_score') not in {'compact', 'with_keys', 'structured', 'json', 'json_keys', 'json_strict', 'repeat', 'state_last', 'reread', 'repeat_typed_score'}:
        raise ValueError('unsupported prompt_style')
    for key in PATH_FIELDS:
        if config.get(key) is not None:
            p = Path(config[key]).expanduser()
            config[key] = str((p if p.is_absolute() else path.parent / p).resolve())
    if model_file is not None:
        config['model_file'] = str(Path(model_file).expanduser().resolve())
    calibration = config.get('temperature_config')
    if without_calibration:
        calibration = None
    elif temperature_config is not None:
        calibration = str(Path(temperature_config).expanduser().resolve())
    elif calibration is not None:
        p = Path(calibration).expanduser()
        calibration = str((p if p.is_absolute() else path.parent / p).resolve())
    elif 'temperature_config' not in config and (path.parent / 'native_temperature.json').is_file():
        calibration = str(path.parent / 'native_temperature.json')
    if calibration is not None and not Path(calibration).is_file():
        raise ValueError('temperature configuration file does not exist')
    config['temperature_config'] = calibration
    return config


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--config', type=Path, default=DEFAULT_CONFIG)
    parser.add_argument('--model-file', type=Path)
    group = parser.add_mutually_exclusive_group()
    group.add_argument('--temperature-config', type=Path)
    group.add_argument('--without-calibration', action='store_true')
    parser.add_argument('--host', default='127.0.0.1')
    parser.add_argument('--port', type=int, default=8765)
    parser.add_argument('--max-questions', type=int, default=8)
    parser.add_argument('--max-pending', type=int, default=2)
    parser.add_argument('--request-timeout', type=float, default=30.0)
    parser.add_argument('--print-config', action='store_true')
    args = parser.parse_args(argv)
    if not 1 <= args.max_questions <= 16 or not 1 <= args.max_pending <= 16:
        parser.error('question and pending limits must be in [1, 16]')
    if not 0 < args.request_timeout <= 300 or not 0 <= args.port <= 65535:
        parser.error('invalid request timeout or port')
    try:
        address = ipaddress.ip_address('127.0.0.1' if args.host == 'localhost' else args.host)
        if not address.is_loopback or address.version != 4:
            raise ValueError()
    except ValueError:
        parser.error('host must be an IPv4 loopback address')
    try:
        kwargs = load_config(args.config, temperature_config=args.temperature_config,
                             without_calibration=args.without_calibration,
                             model_file=args.model_file)
    except (OSError, ValueError, TypeError) as exc:
        parser.error(str(exc))
    if args.print_config:
        print(json.dumps(kwargs, ensure_ascii=False, indent=2))
        return
    from native_engine import NativeEngine
    logging.basicConfig(level=logging.INFO, format='%(message)s')
    logging.info('Verifying and loading native model; diagnostics are written to the configured log.')
    with NativeEngine(**kwargs) as engine:
        serve_engine(engine, host=args.host, port=args.port, max_questions=args.max_questions,
                     max_pending=args.max_pending, request_timeout=args.request_timeout)


if __name__ == '__main__':
    main()
