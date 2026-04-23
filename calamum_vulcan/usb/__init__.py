"""USB module namespace for Calamum Vulcan."""

from .scanner import PYUSB_AVAILABLE
from .scanner import USBDeviceDescriptor
from .scanner import USBProbeResult
from .scanner import VulcanUSBScanner

__all__ = [
	'PYUSB_AVAILABLE',
	'USBDeviceDescriptor',
	'USBProbeResult',
	'VulcanUSBScanner',
]
