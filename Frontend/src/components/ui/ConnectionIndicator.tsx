import type { LiveState } from '../../realtime/useOccupancy';
import { strings } from '../../copy/strings';

/* Connection status pill driven by the REAL socket state:
   green pulsing LIVE / yellow Reconnecting… / gray Offline (polling). */
export function ConnectionIndicator({ state }: { state: LiveState }) {
  if (state === 'open') {
    return (
      <span className="conn conn-live">
        <i className="live-dot on pulse" aria-hidden /> {strings.live.connection.open}
      </span>
    );
  }
  if (state === 'reconnecting' || state === 'connecting') {
    return (
      <span className="conn conn-reconnecting">
        <i className="live-dot idle" aria-hidden /> {state === 'connecting' ? strings.live.connection.connecting : strings.live.connection.reconnecting}
      </span>
    );
  }
  if (state === 'polling') {
    return (
      <span className="conn conn-offline">
        <i className="live-dot off" aria-hidden /> {strings.live.connection.polling}
      </span>
    );
  }
  return (
    <span className="conn conn-offline">
      <i className="live-dot off" aria-hidden /> {strings.live.connection.paused}
    </span>
  );
}
