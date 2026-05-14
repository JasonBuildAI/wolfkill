import { useState } from 'react';
import { useParams, useNavigate } from 'react-router-dom';
import { clsx, type ClassValue } from 'clsx';
import { twMerge } from 'tailwind-merge';
import { useWebSocket } from '@/hooks/useWebSocket';
import { useStartGame } from '@/hooks/useGameAPI';
import { useGameStore } from '@/store/gameStore';
import { Layout } from '@/components/Layout';
import { GameBoard } from '@/components/GameBoard';
import { ChatLog } from '@/components/ChatLog';
import { GameOver } from '@/components/GameOver';
import { Phase, Team, ROLE_INFO, type Player } from '@/types/game';

function cn(...inputs: ClassValue[]) {
  return twMerge(clsx(inputs));
}

export function SpectatePage() {
  const { gameId } = useParams<{ gameId: string }>();
  const navigate = useNavigate();
  
  const [speed, setSpeed] = useState(1.0);

  const { 
    currentGame, 
    logs, 
    connected, 
    error 
  } = useGameStore();

  const { startGame, loading: starting } = useStartGame();

  // WebSocket连接（观战模式，不传playerId）
  const { sendMessage } = useWebSocket({
    gameId: gameId || '',
  });

  // 开始游戏
  const handleStartGame = async () => {
    if (gameId) {
      try {
        await startGame(gameId, true, speed);
      } catch (err) {
        console.error('开始游戏失败:', err);
      }
    }
  };

  // 调整速度
  const handleSpeedChange = (newSpeed: number) => {
    setSpeed(newSpeed);
    sendMessage('set_speed', { speed: newSpeed });
  };

  // 返回首页
  const handleBackToHome = () => {
    navigate('/');
  };

  // 加入游戏
  const handleJoinGame = () => {
    navigate(`/game/${gameId}`);
  };

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

  const isSetup = currentGame.phase === Phase.SETUP;
  const isGameOver = currentGame.phase === Phase.GAME_OVER;

  return (
    <Layout>
      <div className="space-y-6">
        {/* 观战模式标题栏 */}
        <div className="bg-wolf-card rounded-xl border border-wolf-border p-4">
          <div className="flex flex-col md:flex-row md:items-center md:justify-between gap-4">
            <div className="flex items-center space-x-4">
              <div className="w-10 h-10 rounded-full bg-purple-600/20 flex items-center justify-center">
                <span className="text-xl">👁️</span>
              </div>
              <div>
                <h1 className="font-bold text-white">观战模式</h1>
                <p className="text-sm text-gray-500">游戏ID: {gameId?.slice(0, 8)}...</p>
              </div>
            </div>

            <div className="flex items-center space-x-3">
              {/* 速度控制 */}
              <div className="flex items-center space-x-2 bg-wolf-bg rounded-lg p-1">
                <span className="text-xs text-gray-500 px-2">速度</span>
                {[0.5, 1.0, 1.5, 2.0].map((s) => (
                  <button
                    key={s}
                    onClick={() => handleSpeedChange(s)}
                    className={cn(
                      'px-3 py-1 rounded text-sm font-medium transition-colors',
                      speed === s
                        ? 'bg-purple-600 text-white'
                        : 'text-gray-400 hover:text-white'
                    )}
                  >
                    {s}x
                  </button>
                ))}
              </div>

              {/* 开始游戏按钮 */}
              {isSetup && (
                <button
                  onClick={handleStartGame}
                  disabled={starting}
                  className="px-4 py-2 rounded-lg bg-green-600 text-white font-medium hover:bg-green-700 transition-colors disabled:opacity-50"
                >
                  {starting ? '启动中...' : '🚀 开始游戏'}
                </button>
              )}

              {/* 加入游戏按钮 */}
              {isSetup && (
                <button
                  onClick={handleJoinGame}
                  className="px-4 py-2 rounded-lg bg-blue-600 text-white font-medium hover:bg-blue-700 transition-colors"
                >
                  🎮 加入游戏
                </button>
              )}

              <button
                onClick={handleBackToHome}
                className="px-4 py-2 rounded-lg bg-wolf-bg text-gray-400 hover:text-white transition-colors"
              >
                🏠 返回
              </button>
            </div>
          </div>
        </div>

        {/* 阵营统计 */}
        <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
          <StatCard
            label="好人阵营"
            value={currentGame.players.filter(p => p.team === Team.GOOD && p.alive).length}
            total={currentGame.players.filter(p => p.team === Team.GOOD).length}
            color="blue"
            icon="😇"
          />
          <StatCard
            label="狼人阵营"
            value={currentGame.players.filter(p => p.team === Team.EVIL && p.alive).length}
            total={currentGame.players.filter(p => p.team === Team.EVIL).length}
            color="red"
            icon="🐺"
          />
          <StatCard
            label="当前回合"
            value={currentGame.round}
            color="purple"
            icon="🔄"
          />
          <StatCard
            label="存活玩家"
            value={currentGame.alive_players.length}
            total={currentGame.players.length}
            color="green"
            icon="💚"
          />
        </div>

        {/* 游戏主区域 */}
        <div className="grid lg:grid-cols-3 gap-6">
          {/* 左侧：游戏板（显示所有角色） */}
          <div className="lg:col-span-2">
            <GameBoard
              gameState={currentGame}
              showAllRoles={true}
            />
          </div>

          {/* 右侧：日志和玩家列表 */}
          <div className="space-y-6">
            {/* 玩家列表 */}
            <PlayerList players={currentGame.players} />

            {/* 游戏日志 */}
            <ChatLog logs={logs} maxHeight="400px" />
          </div>
        </div>
      </div>

      {/* 游戏结束弹窗 */}
      {isGameOver && (
        <GameOver
          gameState={currentGame}
          onBackToHome={handleBackToHome}
        />
      )}
    </Layout>
  );
}

// 统计卡片
function StatCard({ 
  label, 
  value, 
  total, 
  color, 
  icon 
}: { 
  label: string; 
  value: number; 
  total?: number;
  color: 'blue' | 'red' | 'purple' | 'green';
  icon: string;
}) {
  const colorClasses = {
    blue: 'bg-blue-500/20 text-blue-400 border-blue-500/30',
    red: 'bg-red-500/20 text-red-400 border-red-500/30',
    purple: 'bg-purple-500/20 text-purple-400 border-purple-500/30',
    green: 'bg-green-500/20 text-green-400 border-green-500/30',
  };

  return (
    <div className={cn('rounded-xl border p-4', colorClasses[color])}>
      <div className="flex items-center justify-between">
        <span className="text-2xl">{icon}</span>
        <div className="text-right">
          <div className="text-2xl font-bold">
            {value}
            {total !== undefined && <span className="text-sm font-normal text-gray-500">/{total}</span>}
          </div>
          <div className="text-xs opacity-80">{label}</div>
        </div>
      </div>
    </div>
  );
}

// 玩家列表
function PlayerList({ players }: { players: Player[] }) {
  return (
    <div className="bg-wolf-card rounded-xl border border-wolf-border p-4">
      <h3 className="font-bold text-white mb-4 flex items-center">
        <span className="mr-2">👥</span>
        玩家列表
      </h3>
      <div className="space-y-2 max-h-64 overflow-y-auto">
        {players.map((player) => {
          const roleInfo = ROLE_INFO[player.role];
          return (
            <div
              key={player.id}
              className={cn(
                'flex items-center justify-between p-2 rounded-lg',
                player.alive ? 'bg-wolf-bg' : 'bg-gray-800/50 opacity-50'
              )}
            >
              <div className="flex items-center space-x-2">
                <span>{getRoleEmoji(player.role)}</span>
                <span className={cn(
                  'text-sm',
                  player.alive ? 'text-gray-200' : 'text-gray-500 line-through'
                )}>
                  {player.display_name}
                </span>
              </div>
              <div className="flex items-center space-x-2">
                <span 
                  className="text-xs px-2 py-0.5 rounded"
                  style={{ 
                    backgroundColor: `${roleInfo.color}20`,
                    color: roleInfo.color 
                  }}
                >
                  {roleInfo.name}
                </span>
                {player.is_human && (
                  <span className="text-xs bg-purple-500/20 text-purple-400 px-2 py-0.5 rounded">
                    玩家
                  </span>
                )}
              </div>
            </div>
          );
        })}
      </div>
    </div>
  );
}

function getRoleEmoji(role: string): string {
  const emojiMap: Record<string, string> = {
    WEREWOLF: '🐺',
    SEER: '🔮',
    WITCH: '🧙‍♀️',
    HUNTER: '🔫',
    GUARD: '🛡️',
    VILLAGER: '👨‍🌾',
  };
  return emojiMap[role] || '👤';
}
