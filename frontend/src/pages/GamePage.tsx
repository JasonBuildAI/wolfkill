import { useEffect, useState } from 'react';
import { useParams, useNavigate } from 'react-router-dom';
import { useWebSocket } from '@/hooks/useWebSocket';
import { useJoinGame } from '@/hooks/useGameAPI';
import { useGameStore } from '@/store/gameStore';
import { Layout } from '@/components/Layout';
import { GameBoard } from '@/components/GameBoard';
import { PhasePanel } from '@/components/PhasePanel';
import { ChatLog } from '@/components/ChatLog';
import { RoleReveal } from '@/components/RoleReveal';
import { GameOver } from '@/components/GameOver';
import { Phase, type GameAction } from '@/types/game';

export function GamePage() {
  const { gameId } = useParams<{ gameId: string }>();
  const navigate = useNavigate();
  
  const [playerId, setPlayerId] = useState<string | null>(null);
  const [playerRole, setPlayerRole] = useState<string | null>(null);
  const [showRoleReveal, setShowRoleReveal] = useState(false);
  const [joined, setJoined] = useState(false);

  const { 
    currentGame, 
    logs, 
    connected, 
    actionRequest,
    error 
  } = useGameStore();

  const { joinGame, loading: joining } = useJoinGame();

  // 加入游戏
  useEffect(() => {
    if (gameId && !joined) {
      const doJoin = async () => {
        try {
          const result = await joinGame(gameId);
          if (result?.player_id) {
            setPlayerId(result.player_id);
            setPlayerRole(result.role);
            setJoined(true);
            setShowRoleReveal(true);
          }
        } catch (err) {
          console.error('加入游戏失败:', err);
          // 可能是游戏已满或已开始，尝试观战模式
          navigate(`/spectate/${gameId}`);
        }
      };
      doJoin();
    }
  }, [gameId, joined, joinGame, navigate]);

  // WebSocket连接
  const { sendAction } = useWebSocket({
    gameId: gameId || '',
    playerId: playerId || undefined,
  });

  // 处理动作
  const handleAction = (action: GameAction) => {
    sendAction(action);
  };

  // 返回首页
  const handleBackToHome = () => {
    navigate('/');
  };

  // 切换到观战模式
  const handleSpectate = () => {
    navigate(`/spectate/${gameId}`);
  };

  if (!joined || joining) {
    return (
      <Layout>
        <div className="flex items-center justify-center min-h-[60vh]">
          <div className="text-center">
            <div className="animate-spin w-12 h-12 border-4 border-purple-600 border-t-transparent rounded-full mx-auto mb-4" />
            <p className="text-gray-400">正在加入游戏...</p>
          </div>
        </div>
      </Layout>
    );
  }

  if (!connected) {
    return (
      <Layout>
        <div className="flex items-center justify-center min-h-[60vh]">
          <div className="text-center">
            <div className="animate-spin w-12 h-12 border-4 border-purple-600 border-t-transparent rounded-full mx-auto mb-4" />
            <p className="text-gray-400">正在连接服务器...</p>
            {error && <p className="text-red-400 mt-2">{error}</p>}
          </div>
        </div>
      </Layout>
    );
  }

  if (!currentGame) {
    return (
      <Layout>
        <div className="flex items-center justify-center min-h-[60vh]">
          <div className="text-center">
            <div className="animate-spin w-12 h-12 border-4 border-purple-600 border-t-transparent rounded-full mx-auto mb-4" />
            <p className="text-gray-400">正在加载游戏...</p>
          </div>
        </div>
      </Layout>
    );
  }

  return (
    <Layout>
      <div className="space-y-6">
        {/* 连接状态 */}
        {error && (
          <div className="bg-red-950/50 border border-red-500/50 rounded-lg p-4 text-red-400">
            {error}
          </div>
        )}

        {/* 游戏主区域 */}
        <div className="grid lg:grid-cols-3 gap-6">
          {/* 左侧：游戏板 */}
          <div className="lg:col-span-2 space-y-6">
            <GameBoard
              gameState={currentGame}
              currentPlayerId={playerId}
              showAllRoles={false}
            />

            {/* 行动面板 */}
            <PhasePanel
              gameState={currentGame}
              actionRequest={actionRequest}
              currentPlayerId={playerId}
              onAction={handleAction}
            />
          </div>

          {/* 右侧：日志和角色信息 */}
          <div className="space-y-6">
            {/* 角色信息卡片 */}
            {playerRole && (
              <RoleInfoCard role={playerRole} />
            )}

            {/* 游戏日志 */}
            <ChatLog logs={logs} maxHeight="500px" />

            {/* 操作按钮 */}
            <div className="flex space-x-3">
              <button
                onClick={handleSpectate}
                className="flex-1 px-4 py-3 rounded-lg bg-wolf-card border border-wolf-border text-gray-300 hover:bg-wolf-border transition-colors"
              >
                👁️ 切换观战视角
              </button>
              <button
                onClick={handleBackToHome}
                className="flex-1 px-4 py-3 rounded-lg bg-wolf-card border border-wolf-border text-gray-300 hover:bg-wolf-border transition-colors"
              >
                🏠 退出游戏
              </button>
            </div>
          </div>
        </div>
      </div>

      {/* 角色揭示弹窗 */}
      {showRoleReveal && playerRole && (
        <RoleReveal
          role={playerRole as any}
          isOpen={showRoleReveal}
          onClose={() => setShowRoleReveal(false)}
        />
      )}

      {/* 游戏结束弹窗 */}
      {currentGame.phase === Phase.GAME_OVER && (
        <GameOver
          gameState={currentGame}
          currentPlayerId={playerId}
          onBackToHome={handleBackToHome}
          onSpectate={handleSpectate}
        />
      )}
    </Layout>
  );
}

// 角色信息卡片
function RoleInfoCard({ role }: { role: string }) {
  const roleInfoMap: Record<string, { name: string; emoji: string; color: string; description: string }> = {
    WEREWOLF: { name: '狼人', emoji: '🐺', color: '#dc2626', description: '夜晚可以杀人' },
    SEER: { name: '预言家', emoji: '🔮', color: '#7c3aed', description: '每晚可以查验身份' },
    WITCH: { name: '女巫', emoji: '🧙‍♀️', color: '#16a34a', description: '拥有解药和毒药' },
    HUNTER: { name: '猎人', emoji: '🔫', color: '#ea580c', description: '死亡时可以开枪' },
    GUARD: { name: '守卫', emoji: '🛡️', color: '#eab308', description: '每晚可以守护一人' },
    VILLAGER: { name: '平民', emoji: '👨‍🌾', color: '#6b7280', description: '通过推理找出狼人' },
  };

  const info = roleInfoMap[role] || roleInfoMap.VILLAGER;

  return (
    <div 
      className="rounded-xl border p-4"
      style={{ 
        backgroundColor: `${info.color}10`,
        borderColor: `${info.color}40`
      }}
    >
      <div className="flex items-center space-x-3">
        <div 
          className="w-12 h-12 rounded-full flex items-center justify-center text-2xl"
          style={{ backgroundColor: `${info.color}30` }}
        >
          {info.emoji}
        </div>
        <div>
          <div className="font-bold text-white">{info.name}</div>
          <div className="text-sm text-gray-400">{info.description}</div>
        </div>
      </div>
    </div>
  );
}
