import { create } from 'zustand';
import type {
  GameState,
  LogEntry,
  ActionRequest,
  GameAction,
} from '@/types/game';

interface GameStore {
  // 状态
  currentGame: GameState | null;
  logs: LogEntry[];
  connected: boolean;
  playerId: string | null;
  ws: WebSocket | null;
  actionRequest: ActionRequest | null;
  error: string | null;

  // 动作
  connect: (gameId: string, playerId?: string) => void;
  disconnect: () => void;
  updateGameState: (gameState: GameState) => void;
  addLog: (log: LogEntry) => void;
  clearLogs: () => void;
  setConnected: (connected: boolean) => void;
  setActionRequest: (request: ActionRequest | null) => void;
  sendAction: (action: GameAction) => void;
  setError: (error: string | null) => void;
}

const WS_URL = import.meta.env.VITE_WS_URL || 'ws://localhost:8000/ws';

export const useGameStore = create<GameStore>((set, get) => ({
  // 初始状态
  currentGame: null,
  logs: [],
  connected: false,
  playerId: null,
  ws: null,
  actionRequest: null,
  error: null,

  // 连接WebSocket
  connect: (gameId: string, playerId?: string) => {
    // 先断开现有连接
    const existingWs = get().ws;
    if (existingWs) {
      existingWs.close();
    }

    // 构建WebSocket URL
    let url = `${WS_URL}/${gameId}`;
    if (playerId) {
      url += `?player_id=${playerId}`;
    }

    const ws = new WebSocket(url);

    ws.onopen = () => {
      console.log('WebSocket connected');
      set({ connected: true, error: null });
    };

    ws.onmessage = (event) => {
      try {
        const message = JSON.parse(event.data);
        console.log('WebSocket message:', message);

        switch (message.type) {
          case 'game_state':
            set({ currentGame: message.data as GameState });
            break;
          case 'log':
            get().addLog(message.data as LogEntry);
            break;
          case 'action_request':
            set({ actionRequest: message.data as ActionRequest });
            break;
          case 'error':
            set({ error: message.data.message });
            break;
          case 'connected':
            console.log('Connected to game:', message.data);
            break;
          case 'disconnected':
            console.log('Disconnected from game');
            break;
        }
      } catch (err) {
        console.error('Failed to parse WebSocket message:', err);
      }
    };

    ws.onclose = () => {
      console.log('WebSocket disconnected');
      set({ connected: false, ws: null });
    };

    ws.onerror = (error) => {
      console.error('WebSocket error:', error);
      set({ error: 'WebSocket connection error', connected: false });
    };

    set({ ws, playerId: playerId || null });
  },

  // 断开WebSocket
  disconnect: () => {
    const ws = get().ws;
    if (ws) {
      ws.close();
    }
    set({ ws: null, connected: false, currentGame: null, actionRequest: null });
  },

  // 更新游戏状态
  updateGameState: (gameState: GameState) => {
    set({ currentGame: gameState });
  },

  // 添加日志
  addLog: (log: LogEntry) => {
    set((state) => ({
      logs: [...state.logs, log],
    }));
  },

  // 清空日志
  clearLogs: () => {
    set({ logs: [] });
  },

  // 设置连接状态
  setConnected: (connected: boolean) => {
    set({ connected });
  },

  // 设置动作请求
  setActionRequest: (request: ActionRequest | null) => {
    set({ actionRequest: request });
  },

  // 发送动作
  sendAction: (action: GameAction) => {
    const ws = get().ws;
    if (ws && ws.readyState === WebSocket.OPEN) {
      ws.send(
        JSON.stringify({
          type: 'action',
          data: action,
        })
      );
      // 清除动作请求
      set({ actionRequest: null });
    } else {
      set({ error: 'WebSocket not connected' });
    }
  },

  // 设置错误
  setError: (error: string | null) => {
    set({ error });
  },
}));
