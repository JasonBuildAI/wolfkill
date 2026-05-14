import { useState, useCallback } from 'react';
import type {
  CreateGameRequest,
  CreateGameResponse,
  JoinGameResponse,
  GameListItem,
  GameState,
  GameAction,
} from '@/types/game';

const API_URL = import.meta.env.VITE_API_URL || 'http://localhost:8000';

interface UseAPIState<T> {
  data: T | null;
  loading: boolean;
  error: string | null;
}

// 创建游戏
export function useCreateGame() {
  const [state, setState] = useState<UseAPIState<CreateGameResponse>>({
    data: null,
    loading: false,
    error: null,
  });

  const createGame = useCallback(async (request: CreateGameRequest = {}) => {
    setState({ data: null, loading: true, error: null });
    
    try {
      const response = await fetch(`${API_URL}/api/games`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify(request),
      });

      if (!response.ok) {
        const error = await response.json();
        throw new Error(error.detail || '创建游戏失败');
      }

      const data = await response.json();
      setState({ data, loading: false, error: null });
      return data;
    } catch (err) {
      const error = err instanceof Error ? err.message : '未知错误';
      setState({ data: null, loading: false, error });
      throw err;
    }
  }, []);

  return { ...state, createGame };
}

// 获取游戏列表
export function useListGames() {
  const [state, setState] = useState<UseAPIState<GameListItem[]>>({
    data: null,
    loading: false,
    error: null,
  });

  const listGames = useCallback(async () => {
    setState({ data: null, loading: true, error: null });
    
    try {
      const response = await fetch(`${API_URL}/api/games`);

      if (!response.ok) {
        const error = await response.json();
        throw new Error(error.detail || '获取游戏列表失败');
      }

      const data = await response.json();
      setState({ data, loading: false, error: null });
      return data;
    } catch (err) {
      const error = err instanceof Error ? err.message : '未知错误';
      setState({ data: null, loading: false, error });
      throw err;
    }
  }, []);

  return { ...state, listGames };
}

// 获取游戏详情
export function useGetGame() {
  const [state, setState] = useState<UseAPIState<GameState>>({
    data: null,
    loading: false,
    error: null,
  });

  const getGame = useCallback(async (gameId: string) => {
    setState({ data: null, loading: true, error: null });
    
    try {
      const response = await fetch(`${API_URL}/api/games/${gameId}`);

      if (!response.ok) {
        const error = await response.json();
        throw new Error(error.detail || '获取游戏详情失败');
      }

      const data = await response.json();
      setState({ data, loading: false, error: null });
      return data;
    } catch (err) {
      const error = err instanceof Error ? err.message : '未知错误';
      setState({ data: null, loading: false, error });
      throw err;
    }
  }, []);

  return { ...state, getGame };
}

// 加入游戏
export function useJoinGame() {
  const [state, setState] = useState<UseAPIState<JoinGameResponse>>({
    data: null,
    loading: false,
    error: null,
  });

  const joinGame = useCallback(async (gameId: string) => {
    setState({ data: null, loading: true, error: null });
    
    try {
      const response = await fetch(`${API_URL}/api/games/${gameId}/join`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
      });

      if (!response.ok) {
        const error = await response.json();
        throw new Error(error.detail || '加入游戏失败');
      }

      const data = await response.json();
      setState({ data, loading: false, error: null });
      return data;
    } catch (err) {
      const error = err instanceof Error ? err.message : '未知错误';
      setState({ data: null, loading: false, error });
      throw err;
    }
  }, []);

  return { ...state, joinGame };
}

// 开始游戏
export function useStartGame() {
  const [state, setState] = useState<UseAPIState<{ message: string }>>({
    data: null,
    loading: false,
    error: null,
  });

  const startGame = useCallback(async (
    gameId: string,
    autoPlay: boolean = true,
    speed: number = 1.0
  ) => {
    setState({ data: null, loading: true, error: null });
    
    try {
      const response = await fetch(`${API_URL}/api/games/${gameId}/start`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({ auto_play: autoPlay, speed }),
      });

      if (!response.ok) {
        const error = await response.json();
        throw new Error(error.detail || '开始游戏失败');
      }

      const data = await response.json();
      setState({ data, loading: false, error: null });
      return data;
    } catch (err) {
      const error = err instanceof Error ? err.message : '未知错误';
      setState({ data: null, loading: false, error });
      throw err;
    }
  }, []);

  return { ...state, startGame };
}

// 提交动作
export function useSubmitAction() {
  const [state, setState] = useState<UseAPIState<{ success: boolean; message: string }>>({
    data: null,
    loading: false,
    error: null,
  });

  const submitAction = useCallback(async (gameId: string, action: GameAction) => {
    setState({ data: null, loading: true, error: null });
    
    try {
      const response = await fetch(`${API_URL}/api/games/${gameId}/action`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify(action),
      });

      if (!response.ok) {
        const error = await response.json();
        throw new Error(error.detail || '提交动作失败');
      }

      const data = await response.json();
      setState({ data, loading: false, error: null });
      return data;
    } catch (err) {
      const error = err instanceof Error ? err.message : '未知错误';
      setState({ data: null, loading: false, error });
      throw err;
    }
  }, []);

  return { ...state, submitAction };
}

// 获取游戏日志
export function useGetGameLogs() {
  const [state, setState] = useState<UseAPIState<{ logs: unknown[] }>>({
    data: null,
    loading: false,
    error: null,
  });

  const getLogs = useCallback(async (gameId: string) => {
    setState({ data: null, loading: true, error: null });
    
    try {
      const response = await fetch(`${API_URL}/api/games/${gameId}/logs`);

      if (!response.ok) {
        const error = await response.json();
        throw new Error(error.detail || '获取日志失败');
      }

      const data = await response.json();
      setState({ data, loading: false, error: null });
      return data;
    } catch (err) {
      const error = err instanceof Error ? err.message : '未知错误';
      setState({ data: null, loading: false, error });
      throw err;
    }
  }, []);

  return { ...state, getLogs };
}

// 综合游戏API Hook
export function useGameAPI() {
  const createGameAPI = useCreateGame();
  const listGamesAPI = useListGames();
  const getGameAPI = useGetGame();
  const joinGameAPI = useJoinGame();
  const startGameAPI = useStartGame();
  const submitActionAPI = useSubmitAction();
  const getLogsAPI = useGetGameLogs();

  return {
    createGame: createGameAPI.createGame,
    listGames: listGamesAPI.listGames,
    getGame: getGameAPI.getGame,
    joinGame: joinGameAPI.joinGame,
    startGame: startGameAPI.startGame,
    submitAction: submitActionAPI.submitAction,
    getLogs: getLogsAPI.getLogs,
    
    // 状态汇总
    loading: 
      createGameAPI.loading ||
      listGamesAPI.loading ||
      getGameAPI.loading ||
      joinGameAPI.loading ||
      startGameAPI.loading ||
      submitActionAPI.loading ||
      getLogsAPI.loading,
    
    error: 
      createGameAPI.error ||
      listGamesAPI.error ||
      getGameAPI.error ||
      joinGameAPI.error ||
      startGameAPI.error ||
      submitActionAPI.error ||
      getLogsAPI.error,
  };
}
