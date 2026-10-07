import { QRCodeSVG } from 'qrcode.react';
import { strings } from '../../copy/strings';

/* Real QR rendered from the ticket qr_value (not a placeholder glyph). */
export function QRCodeView({ value, size = 160 }: { value: string; size?: number }) {
  return (
    <span className="qr-real">
      <QRCodeSVG value={value} size={size} marginSize={4} bgColor="#FFFFFF" fgColor="#1B1433" role="img" aria-label={strings.common.qrLabel(value)} />
    </span>
  );
}
