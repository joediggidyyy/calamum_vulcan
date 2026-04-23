#!/usr/bin/env sh
set -eu

VENDOR_ID="04e8"
PRODUCT_ID="685d"

while [ "$#" -gt 0 ]; do
  case "$1" in
    --vendor-id)
      VENDOR_ID=$(printf '%s' "$2" | sed 's/^0x//I' | tr '[:upper:]' '[:lower:]')
      shift 2
      ;;
    --product-id)
      PRODUCT_ID=$(printf '%s' "$2" | sed 's/^0x//I' | tr '[:upper:]' '[:lower:]')
      shift 2
      ;;
    *)
      shift 1
      ;;
  esac
done

if [ "$(id -u)" -ne 0 ]; then
  echo "[USB-REMEDIATION] status=requires_root vendor=${VENDOR_ID} product=${PRODUCT_ID}" >&2
  exit 1
fi

RULE_PATH="/etc/udev/rules.d/70-calamum-vulcan-samsung-download.rules"
TMP_RULE="$(mktemp)"
trap 'rm -f "$TMP_RULE"' EXIT

cat > "$TMP_RULE" <<EOF
# Calamum Vulcan native USB access for Samsung download mode
ACTION=="add", SUBSYSTEM=="usb", ATTR{idVendor}=="${VENDOR_ID}", ATTR{idProduct}=="${PRODUCT_ID}", MODE="0666", TAG+="uaccess", GROUP="plugdev"
EOF

install -m 0644 "$TMP_RULE" "$RULE_PATH"
udevadm control --reload-rules
udevadm trigger --subsystem-match=usb --attr-match=idVendor="$VENDOR_ID" --attr-match=idProduct="$PRODUCT_ID" || true

echo "[USB-REMEDIATION] status=installed rule=$RULE_PATH vendor=${VENDOR_ID} product=${PRODUCT_ID}"
