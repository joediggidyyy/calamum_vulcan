"""Device-registry surfaces for Calamum Vulcan Sprint 0.2.0 work."""

from .registry import DEVICE_REGISTRY_SCHEMA_VERSION
from .registry import DEVICE_PROFILES
from .registry import DeviceCompatibilityResolution
from .registry import DeviceCompatibilityStatus
from .registry import DeviceProfile
from .registry import DeviceRegistryMatchKind
from .registry import DeviceRegistryResolution
from .registry import available_device_profiles
from .registry import normalize_product_code
from .registry import resolve_device_profile
from .registry import resolve_package_compatibility

__all__ = [
	'DEVICE_PROFILES',
	'DEVICE_REGISTRY_SCHEMA_VERSION',
	'DeviceCompatibilityResolution',
	'DeviceCompatibilityStatus',
	'DeviceProfile',
	'DeviceRegistryMatchKind',
	'DeviceRegistryResolution',
	'available_device_profiles',
	'normalize_product_code',
	'resolve_device_profile',
	'resolve_package_compatibility',
]
