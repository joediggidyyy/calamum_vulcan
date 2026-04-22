"""
Mocks for testing `calamum_vulcan.usb` without relying on physical hardware.
Ensures we adhere to Testing Independence gap (FS5-02).
"""

class MockDevice:
    """Simulates a raw pyusb device return structure"""
    def __init__(self, idVendor, idProduct, bus, address):
        self.idVendor = idVendor
        self.idProduct = idProduct
        self.bus = bus
        self.address = address

class MockBackend:
    """Simulates pyusb backend mapping to bypass OS driver checks."""
    pass

class MockUSBContext:
    """
    Context manager to inject our stub Samsung device (0x04E8:0x685D)
    into the unit test execution pipeline securely.
    """
    def __init__(self, devices):
        self.devices = devices
        self.original_find = None
        
    def __enter__(self):
        import usb.core
        self.original_find = usb.core.find
        
        def mock_find(*args, **kwargs):
            if kwargs.get('find_all') and kwargs.get('idVendor') == 0x04E8 and kwargs.get('idProduct') == 0x685D:
                return self.devices
            return []
            
        usb.core.find = mock_find
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        import usb.core
        usb.core.find = self.original_find
