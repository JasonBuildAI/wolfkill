import { useEffect, useRef, useCallback } from 'react';
import { useGameStore } from '@/store/gameStore';
import type { GameAction } from '@/types/game';

const WS_URL = import.meta.env.VITE_WS_URL || 'ws://localhost:8000/ws';
const RECONNECT_DELAY = 3000;
const MAX_RECONNECT_ATTEMPTS = 5;

interface UseWebSocketOptions {
  gameId: string;
  playerId?: string;
  onConnect?: () => void;
  onDisconnect?: () => void;
  onError?: (error: Error) => void;
}

export function useWebSocket(options: UseWebSocketOptions) {
  const { gameId, playerId, onConnect, onDisconnect, onError } = options;
  const wsRef = useRef<WebSocket | null>(null);
  const reconnectAttemptsRef = useRef(0);
  const reconnectTimerRef = useRef<NodeJS.Timeout | null>(null);
  
  const { 
    setConnected, 
    updateGameState, 
    addLog, 
    setActionRequest, 
    setError,
    clearLogs 
  } = useGameStore();

  const connect = useCallback(() => {
    // 如果已有连接，先关闭
    if (wsRef.current) {
      wsRef.current.close();
    }

    // 构建WebSocket URL
    let url = `${WS_URL}/${gameId}`;
    if (playerId) {
      url += `?player_id=${playerId}`;
    }

    console.log('Connecting to WebSocket:', url);
    const ws = new WebSocket(url);
    wsRef.current = ws;

    ws.onopen = () => {
      console.log('WebSocket connected successfully');
      reconnectAttemptsRef.current = 0;
      setConnected(true);
      setError(null);
      onConnect?.();
    };

    ws.onmessage = (event) => {
      try {
        const message = JSON.parse(event.data);
        console.log('Received message:', message);

        switch (message.type) {
          case 'game_state':
            updateGameState(message.data);
            break;
          case 'log':
            addLog(message.data);
            break;
          case 'action_request':
            setActionRequest(message.data);
            break;
          case 'error':
            setError(message.data.message);
            onError?.(new Error(message.data.message));
            break;
          case 'connected':
            console.log('Server confirmed connection:', message.data);
            break;
          case 'disconnected':
            console.log('Server notified disconnect');
            break;
          case 'logs_history':
            // 批量接收历史日志
            if (Array.isArray(message.data)) {
              message.data.forEach((log: unknown) => addLog(log as LogEntry));
            }
            break;
        }
      } catch (err) {
        console.error('Failed to parse WebSocket message:', err);
      }
    };

    ws.onclose = (event) => {
      console.log('WebSocket closed:', event.code, event.reason);
      setConnected(false);
      wsRef.current = null;
      onDisconnect?.();

      // 尝试重连
      if (reconnectAttemptsRef.current < MAX_RECONNECT_ATTEMPTS) {
        reconnectAttemptsRef.current++;
        console.log(`Reconnecting... Attempt ${reconnectAttemptsRef.current}/${MAX_RECONNECT_ATTEMPTS}`);
        
        reconnectTimerRef.current = setTimeout(() => {
          connect();
        }, RECONNECT_DELAY);
      } else {
        setError('无法连接到服务器，请刷新页面重试');
      }
    };

    ws.onerror = (error) => {
      console.error('WebSocket error:', error);
      setError('连接错误');
      onError?.(new Error('WebSocket error'));
    };
  }, [gameId, playerId, setConnected, updateGameState, addLog, setActionRequest, setError, onConnect, onDisconnect, onError]);

  const disconnect = useCallback(() => {
    // 清除重连定时器
    if (reconnectTimerRef.current) {
      clearTimeout(reconnectTimerRef.current);
      reconnectTimerRef.current = null;
    }

    if (wsRef.current) {
      wsRef.current.close();
      wsRef.current = null;
    }
    
    reconnectAttemptsRef.current = 0;
    setConnected(false);
  }, [setConnected]);

  const sendAction = useCallback((action: GameAction) => {
    if (wsRef.current && wsRef.current.readyState === WebSocket.OPEN) {
      wsRef.current.send(
        JSON.stringify({
          type: 'action',
          data: action,
        })
      );
      setActionRequest(null);
      return true;
    } else {
      setError('未连接到服务器');
      return false;
    }
  }, [setActionRequest, setError]);

  const sendMessage = useCallback((type: string, data?: unknown) => {
    if (wsRef.current && wsRef.current.readyState === WebSocket.OPEN) {
      wsRef.current.send(
        JSON.stringify({
          type,
          data,
        })
      );
      return true;
    }
    return false;
  }, []);

  // 组件挂载时连接
  useEffect(() => {
    connect();
    
    // 组件卸载时断开连接
    return () => {
      disconnect();
      clearLogs();
    };
  }, [connect, disconnect, clearLogs]);

  return {
    connect,
    disconnect,
    sendAction,
    sendMessage,
    isConnected: !!wsRef.current && wsRef.current.readyState === WebSocket.OPEN,
  };
}

// 导入类型
import type { LogEntry } from '@/types/game';
