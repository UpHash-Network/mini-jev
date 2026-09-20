"""CPU-only checks that integration flags configure both child model launches."""
import contextlib
import io
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

import run_native_service
import validate_native_service as validation


class NativeIntegrationConfigTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.path = self.root / 'config.json'
        self.base = {'model': 'fixture', 'revision': 'fixture-revision',
                     'model_file': 'models/original.gguf',
                     'native_binary': 'runtime/bin/helper',
                     'temperature_config': None}
        self.write()

    def write(self, **overrides):
        self.path.write_text(json.dumps({**self.base, **overrides}))

    def child_config(self, child_args):
        output = io.StringIO()
        with contextlib.redirect_stdout(output):
            run_native_service.main([*child_args, '--print-config'])
        return json.loads(output.getvalue())

    def test_uncalibrated_config_works_and_matches_child(self):
        config, args = validation.resolve_run_settings(self.path)
        self.assertIsNone(config['temperature_config'])
        self.assertEqual(config, self.child_config(args))
        self.assertEqual(args[:2], ['--config', str(self.path.resolve())])

    def test_model_override_is_absolute_and_matches_child(self):
        # All arguments are made absolute before the service changes cwd to ROOT.
        model = self.root / 'selected.gguf'
        config, args = validation.resolve_run_settings(self.path, model_file=model)
        self.assertEqual(config['model_file'], str(model.resolve()))
        self.assertEqual(config, self.child_config(args))
        self.assertIn('--model-file', args)

    def test_calibrated_config_is_preserved_by_default(self):
        calibration = self.root / 'temperature.json'
        calibration.write_text('{}')
        self.write(temperature_config=calibration.name)
        config, args = validation.resolve_run_settings(self.path)
        self.assertEqual(config['temperature_config'], str(calibration.resolve()))
        self.assertEqual(config, self.child_config(args))
        self.assertNotIn('--without-calibration', args)

    def test_without_calibration_overrides_config_in_both_processes(self):
        # Even a missing configured calibration file is ignored by this flag.
        self.write(temperature_config='missing-temperature.json')
        config, args = validation.resolve_run_settings(self.path, without_calibration=True)
        self.assertIsNone(config['temperature_config'])
        self.assertIn('--without-calibration', args)
        self.assertEqual(config, self.child_config(args))

    def test_actual_launch_receives_all_resolved_flags(self):
        output = self.root / 'out'
        output.mkdir()
        model = self.root / 'selected.gguf'
        with patch.object(validation.socket, 'socket') as socket_factory:
            socket_factory.return_value.__enter__.return_value.getsockname.return_value = ('127.0.0.1', 12345)
            with patch.object(validation.subprocess, 'Popen', side_effect=RuntimeError('CPU launch boundary')) as spawn:
                with self.assertRaisesRegex(RuntimeError, 'CPU launch boundary'):
                    validation._run(output, self.path, model_file=model, without_calibration=True)
        command = spawn.call_args.args[0]
        self.assertEqual(command[2:], ['--config', str(self.path.resolve()),
                                      '--model-file', str(model.resolve()),
                                      '--without-calibration', '--port', '12345'])

    def test_cli_flags_are_not_ignored(self):
        output = self.root / 'out'
        model = self.root / 'override.gguf'
        with patch.object(validation, 'run') as run:
            validation.main(['--output-dir', str(output), '--config', str(self.path),
                             '--model-file', str(model), '--without-calibration'])
        run.assert_called_once_with(output, self.path, model_file=model, without_calibration=True)

    def test_run_forwards_config_and_overrides_to_two_launch_runner(self):
        output = self.root / 'out'
        model = self.root / 'override.gguf'
        with patch.object(validation, '_run', return_value='done') as run:
            result = validation.run(output, self.path, model_file=model, without_calibration=True)
        self.assertEqual(result, 'done')
        run.assert_called_once_with(output, self.path, model_file=model, without_calibration=True)


if __name__ == '__main__':
    unittest.main()
