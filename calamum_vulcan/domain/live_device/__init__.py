"""Live-device domain contracts for Calamum Vulcan Sprint 0.3.0 work."""

from importlib import import_module

from .model import LIVE_DEVICE_SCHEMA_VERSION
from .model import LIVE_PATH_IDENTITY_SCHEMA_VERSION
from .model import LiveDetectionSession
from .model import LiveDeviceInfoState
from .model import LiveIdentityConfidence
from .model import LiveDetectionState
from .model import LivePathIdentity
from .model import LivePathOwnership
from .model import LiveDeviceSnapshot
from .model import LiveDeviceSource
from .model import LiveDeviceSupportPosture
from .model import LiveFallbackPosture


_LAZY_EXPORTS = {
	'apply_live_device_info_trace': '.builder',
	'build_heimdall_live_detection_session': '.builder',
	'build_live_detection_session': '.builder',
	'build_usb_live_detection_session': '.builder',
}


def __getattr__(name: str):
	"""Lazily resolve builder exports to keep model imports acyclic."""

	module_name = _LAZY_EXPORTS.get(name)
	if module_name is None:
		raise AttributeError(
			"module '{module}' has no attribute '{name}'".format(
				module=__name__,
				name=name,
			)
		)
	module = import_module(module_name, __name__)
	value = getattr(module, name)
	globals()[name] = value
	return value

__all__ = [
	'LIVE_DEVICE_SCHEMA_VERSION',
	'LIVE_PATH_IDENTITY_SCHEMA_VERSION',
	'LiveDetectionSession',
	'LiveDeviceInfoState',
	'LiveIdentityConfidence',
	'LiveDetectionState',
	'LivePathIdentity',
	'LivePathOwnership',
	'LiveDeviceSnapshot',
	'LiveDeviceSource',
	'LiveDeviceSupportPosture',
	'LiveFallbackPosture',
	'apply_live_device_info_trace',
	'build_heimdall_live_detection_session',
	'build_live_detection_session',
	'build_usb_live_detection_session',
]
