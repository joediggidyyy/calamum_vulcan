"""Measure Qt-shell build, rebuild, and window-log latency offscreen."""

from __future__ import annotations

import json
import os
from pathlib import Path
import statistics
import sys
import time
from typing import Callable
from typing import Dict
from typing import List
from typing import Tuple


REPO_ROOT = Path(__file__).resolve().parent.parent
if str(REPO_ROOT) not in sys.path:
	sys.path.insert(0, str(REPO_ROOT))

os.environ.setdefault('QT_QPA_PLATFORM', 'offscreen')

from calamum_vulcan.app.demo import build_demo_package_assessment
from calamum_vulcan.app.demo import build_demo_pit_inspection
from calamum_vulcan.app.demo import build_demo_session
from calamum_vulcan.app.qt_shell import GUI_WINDOW_LOG_MAX_LINES
from calamum_vulcan.app.qt_shell import ShellWindow
from calamum_vulcan.app.qt_shell import get_or_create_application
from calamum_vulcan.app.view_models import build_shell_view_model


OUTPUT_ROOT = REPO_ROOT / 'temp' / 'gui_latency_diagnostic'
OUTPUT_JSON = OUTPUT_ROOT / 'gui_latency_diagnostic.json'
OUTPUT_MD = OUTPUT_ROOT / 'gui_latency_diagnostic.md'
SAMPLE_COUNT = 7


def _build_model():
	session = build_demo_session('ready')
	package_assessment = build_demo_package_assessment('ready', session=session)
	pit_inspection = build_demo_pit_inspection(
		'ready',
		session=session,
		package_assessment=package_assessment,
	)
	return build_shell_view_model(
		session,
		scenario_name='GUI latency diagnostic',
		package_assessment=package_assessment,
		pit_inspection=pit_inspection,
		pit_required_for_safe_path=True,
	)


def _measure_samples(sample: Callable[[], float], count: int = SAMPLE_COUNT) -> Dict[str, object]:
	samples = [sample() for _ in range(count)]
	return {
		'samples_ms': [round(value, 3) for value in samples],
		'min_ms': round(min(samples), 3),
		'median_ms': round(statistics.median(samples), 3),
		'max_ms': round(max(samples), 3),
	}


def _process_events() -> None:
	application = get_or_create_application()
	application.processEvents()


def _sample_window_build_ms() -> float:
	application = get_or_create_application()
	start = time.perf_counter()
	window = ShellWindow(_build_model())
	try:
		window.show()
		application.processEvents()
		return (time.perf_counter() - start) * 1000.0
	finally:
		window.close()
		application.processEvents()


def _sample_window_rebuild_ms() -> float:
	application = get_or_create_application()
	window = ShellWindow(_build_model())
	seeded_lines = tuple(
		'[ACTION] bounded window line {index}'.format(index=index)
		for index in range(GUI_WINDOW_LOG_MAX_LINES)
	)
	try:
		window.show()
		application.processEvents()
		window._append_live_log_lines(seeded_lines)
		application.processEvents()
		start = time.perf_counter()
		window._rebuild_ui()
		application.processEvents()
		return (time.perf_counter() - start) * 1000.0
	finally:
		window.close()
		application.processEvents()


def _build_verbose_burst() -> Tuple[str, ...]:
	burst: List[str] = []
	for index in range(140):
		burst.append('[COMPANION-PENDING] adb_devices')
		burst.append('[COMMAND] adb devices --synthetic {index}'.format(index=index))
		burst.append('[TRACE] raw trace line {index}'.format(index=index))
		burst.append(
			'[COMPANION-DEVICE] serial=R58N{index:05d} product=SM-G991U'.format(
				index=index,
			)
		)
		burst.append('[ACTION] visible operator step {index}'.format(index=index))
	return tuple(burst)


def _sample_append_burst_ms() -> float:
	application = get_or_create_application()
	window = ShellWindow(_build_model())
	try:
		window.show()
		application.processEvents()
		start = time.perf_counter()
		window._append_live_log_lines(_build_verbose_burst())
		application.processEvents()
		return (time.perf_counter() - start) * 1000.0
	finally:
		window.close()
		application.processEvents()


def _sample_refresh_live_controls_ms() -> float:
	application = get_or_create_application()
	window = ShellWindow(_build_model())
	iterations = 25
	try:
		window.show()
		application.processEvents()
		start = time.perf_counter()
		for _ in range(iterations):
			window._refresh_live_controls()
		application.processEvents()
		return ((time.perf_counter() - start) * 1000.0) / iterations
	finally:
		window.close()
		application.processEvents()


def _capture_log_policy_snapshot() -> Dict[str, object]:
	application = get_or_create_application()
	window = ShellWindow(_build_model())
	verbose_burst = _build_verbose_burst()
	try:
		window.show()
		application.processEvents()
		window._append_live_log_lines(verbose_burst)
		application.processEvents()
		lines = window.operational_log_lines()
		return {
			'input_line_count': len(verbose_burst),
			'visible_line_count': len(lines),
			'trim_notice_present': any(
				'Older operational log lines were condensed' in line
				for line in lines
			),
			'first_visible_line': lines[0] if lines else '',
			'last_visible_line': lines[-1] if lines else '',
		}
	finally:
		window.close()
		application.processEvents()


def _write_markdown_report(payload: Dict[str, object]) -> None:
	metrics = payload['metrics']
	policy = payload['window_log_policy']
	lines = [
		'# GUI latency diagnostic',
		'',
		'- Qt platform: `{platform}`'.format(platform=payload['qt_platform']),
		'- Window log max lines: `{count}`'.format(
			count=payload['window_log_max_lines'],
		),
		'- Verbose input lines: `{count}`'.format(count=policy['input_line_count']),
		'- Visible retained lines: `{count}`'.format(count=policy['visible_line_count']),
		'- Trim notice present: `{flag}`'.format(flag=policy['trim_notice_present']),
		'',
		'## Metrics',
		'',
		'| metric | min ms | median ms | max ms |',
		'| --- | ---: | ---: | ---: |',
	]
	for label, metric in metrics.items():
		lines.append(
			'| `{label}` | `{min_ms}` | `{median_ms}` | `{max_ms}` |'.format(
				label=label,
				min_ms=metric['min_ms'],
				median_ms=metric['median_ms'],
				max_ms=metric['max_ms'],
			)
		)
	lines.extend(
		(
			'',
			'## Window-log snapshot',
			'',
			'- first visible line: `{line}`'.format(line=policy['first_visible_line']),
			'- last visible line: `{line}`'.format(line=policy['last_visible_line']),
			'',
		)
	)
	OUTPUT_MD.write_text('\n'.join(lines), encoding='utf-8')


def main() -> int:
	OUTPUT_ROOT.mkdir(parents=True, exist_ok=True)
	_process_events()

	payload = {
		'qt_platform': os.getenv('QT_QPA_PLATFORM', 'default'),
		'window_log_max_lines': GUI_WINDOW_LOG_MAX_LINES,
		'metrics': {
			'window_build': _measure_samples(_sample_window_build_ms),
			'window_rebuild_bounded_log': _measure_samples(_sample_window_rebuild_ms),
			'append_verbose_burst': _measure_samples(_sample_append_burst_ms),
			'refresh_live_controls_per_call': _measure_samples(
				_sample_refresh_live_controls_ms
			),
		},
		'window_log_policy': _capture_log_policy_snapshot(),
	}

	OUTPUT_JSON.write_text(json.dumps(payload, indent=2), encoding='utf-8')
	_write_markdown_report(payload)

	print('GUI latency diagnostic written to {path}'.format(path=OUTPUT_JSON))
	print(
		'window_build median={value}ms'.format(
			value=payload['metrics']['window_build']['median_ms'],
		)
	)
	print(
		'append_verbose_burst median={value}ms'.format(
			value=payload['metrics']['append_verbose_burst']['median_ms'],
		)
	)
	print(
		'visible_window_lines={count}'.format(
			count=payload['window_log_policy']['visible_line_count'],
		)
	)
	return 0


if __name__ == '__main__':
	raise SystemExit(main())
