"""
Calamum Vulcan: Native USB Abstraction Layer (Sprint 0.5.0)
CodeSentinel OS-agnostic hardware mapping. 
"""

import sys
import logging

try:
    import usb.core
    import usb.util
    import usb.backend.libusb1
except ImportError:
    # We trap this, however `pyusb` is a required dependency now.
    logging.warning("pyusb is not installed. CodeSentinel zero-touch packaging violated.")
    usb = None

class VulcanUSBScanner:
    """
    Zero-touch USB scanner. Binds directly to libusb1 backend bundled with the platform,
    handling Samsung hardware detection without requiring user intervention.
    """
    
    def __init__(self, backend_path=None):
        self.logger = logging.getLogger("vulcan.usb")
        self.backend = None
        self._init_backend(backend_path)
    
    def _init_backend(self, backend_path):
        """
        Loads the bundled libusb-1.0 dynamically linked library from `assets/bin/windows`
        to prevent reliance on OS systems and ensure self-resolving installs.
        """
        if not usb:
            return

        if sys.platform == "win32":
            # Attempt to securely load the bundled CodeSentinel zero-touch DLL.
            if backend_path:
                try:
                    import ctypes
                    self.logger.debug(f"Loading custom Windows libusb backend from {backend_path}")
                    ctypes.CDLL(backend_path)
                    self.backend = usb.backend.libusb1.get_backend(find_library=lambda x: backend_path)
                except Exception as e:
                    self.logger.error(f"Failed to load bundled libusb-1.0.dll: {e}")
                    # A true CodeSentinel app would fire the auto-injector/elevation sequence here.
                    self.trigger_elevation_helper()
            else:
                self.backend = usb.backend.libusb1.get_backend()

    def get_samsung_devices(self):
        """
        Scans the USB bus natively for Download Mode devices.
        Returns a list of dicts/namespaces, not pyusb raw objects to preserve the boundary.
        """
        if not usb:
            return []
            
        found = []
        try:
            # Query Samsung devices (0x04E8:0x685D) natively
            devices = usb.core.find(find_all=True, idVendor=0x04E8, idProduct=0x685D, backend=self.backend)
            for d in devices:
                found.append({
                    "vendor_id": d.idVendor,
                    "product_id": d.idProduct,
                    "bus": d.bus,
                    "address": d.address
                })
        except Exception as e:
            # Trap NoBackendError and map to elevation injection
            if "No backend" in str(e) or "access" in str(e).lower():
                self.logger.warning("OS-level backend/permission failure trapped. Requesting Zero-Touch remediation.")
                self.trigger_elevation_helper()
        
        return found
        
    def trigger_elevation_helper(self):
        """
        CodeSentinel rule: If OS-level modifications are needed (driver/udev), we elevate automatically.
        """
        self.logger.info("Executing self-resolving OS elevation for USB access...")
        # To be implemented: Launch `elevation_helper.exe` or `udev_injector.sh`
        pass
