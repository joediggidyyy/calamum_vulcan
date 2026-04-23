"""Mocks for testing the native USB seam without physical Samsung hardware."""


class MockUSBError(Exception):
    """Synthetic USB-layer error used by unit tests."""


class MockDevice:
    """Simulate one raw pyusb device object."""

    def __init__(
        self,
        idVendor,
        idProduct,
        bus,
        address,
        serial_number=None,
        manufacturer=None,
        product=None,
    ):
        self.idVendor = idVendor
        self.idProduct = idProduct
        self.bus = bus
        self.address = address
        self.serial_number = serial_number
        self.manufacturer = manufacturer
        self.product = product
        self.iSerialNumber = 1 if serial_number is not None else 0
        self.iManufacturer = 2 if manufacturer is not None else 0
        self.iProduct = 3 if product is not None else 0


class MockBackend:
    """Simulate a resolved libusb backend handle."""


class MockUSBCore:
    """Minimal ``usb.core`` stand-in used by the scanner tests."""

    def __init__(self, devices=(), error=None):
        self._devices = tuple(devices)
        self._error = error
        self.calls = []

    def find(self, *args, **kwargs):
        self.calls.append({'args': args, 'kwargs': kwargs})
        if self._error is not None:
            raise self._error
        return tuple(self._devices)


class MockUSBUtil:
    """Minimal ``usb.util`` stand-in used by the scanner tests."""

    @staticmethod
    def get_string(device, index):
        mapping = {
            getattr(device, 'iSerialNumber', 0): getattr(device, 'serial_number', None),
            getattr(device, 'iManufacturer', 0): getattr(device, 'manufacturer', None),
            getattr(device, 'iProduct', 0): getattr(device, 'product', None),
        }
        return mapping.get(index)
