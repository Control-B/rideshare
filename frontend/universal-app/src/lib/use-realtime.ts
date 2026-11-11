import { useQueryClient } from '@tanstack/react-query';
import React from 'react';

import { realtimeUrl } from '@/lib/api';

export function useRealtimeUpdates(token: string, userId: string) {
  const queryClient = useQueryClient();

  React.useEffect(() => {
    let socket: WebSocket | undefined;
    let reconnectTimer: ReturnType<typeof setTimeout> | undefined;
    let closed = false;
    let attempt = 0;

    const connect = () => {
      socket = new WebSocket(realtimeUrl(token));
      socket.onopen = () => {
        attempt = 0;
      };
      socket.onmessage = () => {
        queryClient.invalidateQueries({ queryKey: ['trips', userId] });
        queryClient.invalidateQueries({ queryKey: ['offers'] });
        queryClient.invalidateQueries({ queryKey: ['nearby-vehicles'] });
      };
      socket.onclose = () => {
        if (closed) return;
        const delay = Math.min(1_000 * 2 ** attempt, 15_000);
        attempt += 1;
        reconnectTimer = setTimeout(connect, delay);
      };
    };

    connect();
    return () => {
      closed = true;
      if (reconnectTimer) clearTimeout(reconnectTimer);
      socket?.close();
    };
  }, [queryClient, token, userId]);
}
