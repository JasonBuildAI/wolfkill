import { useState, useEffect } from 'react';
import { useNavigate } from 'react-router-dom';
import { clsx, type ClassValue } from 'clsx';
import { twMerge } from 'tailwind-merge';
import { useGameAPI } from '@/hooks/useGameAPI';
import { useListGames } from '@/hooks/useGameAPI';
import { Phase, type GameListItem } from '@/types/game';

function cn(...inputs: ClassValue[]) {
  return twMerge(clsx(inputs));
}

export function HomePage() {
  const navigate = useNavigate();
  const { createGame, loading: creatingGame } = useGameAPI();
  const { listGames, data: games, loading: loadingGames } = useListGames();
  
  const [autoPlay, setAutoPlay] = useState(true);
  const [speed, setSpeed] = useState(1.0);
  const [showCreateModal, setShowCreateModal] = useState(false);

  // 加载游戏列表
  useEffect(() => {
    listGames();
    // 定时刷新
    const interval = setInterval(listGames, 5000);
    return () => clearInterval(interval);
  }, [listGames]);

  // 创建游戏
  const handleCreateGame = async (withHuman: boolean = false) => {
    try {
      const result = await createGame({
        auto_play: autoPlay,
        speed: speed,
      });
      
      if (result?.game_id) {
        if (withHuman) {
          // 加入游戏
          navigate(`/game/${result.game_id}`);
        } else {
          // 纯AI游戏，进入观战模式
          navigate(`/spectate/${result.game_id}`);
        }
      }
    } catch (error) {
      console.error('创建游戏失败:', error);
      alert('创建游戏失败，请重试');
    }
  };

  //  spectate游戏
  const handleSpectate = (gameId: string) => {
    navigate(`/spectate/${gameId}`);
  };

  // 加入游戏
  const handleJoinGame = (gameId: string) => {
    navigate(`/game/${gameId}`);
  };

  return (
    <div className="space-y-12">
      {/* Hero Section */}
      <section className="text-center py-16 relative overflow-hidden">
        {/* 背景装饰 */}
        <div className="absolute inset-0 overflow-hidden">
          <div className="absolute top-1/4 left-1/4 w-64 h-64 bg-purple-600/10 rounded-full blur-3xl" />
          <div className="absolute bottom-1/4 right-1/4 w-96 h-96 bg-blue-600/10 rounded-full blur-3xl" />
        </div>

        <div className="relative">
          <div className="inline-flex items-center justify-center w-24 h-24 rounded-full bg-gradient-to-br from-purple-600 to-blue-600 mb-8 animate-float">
            <span className="text-5xl">🐺</span>
          </div>
          
          <h1 className="text-5xl md:text-6xl font-bold mb-6 bg-gradient-to-r from-purple-400 via-pink-400 to-blue-400 bg-clip-text text-transparent">
            狼人杀
          </h1>
          
          <p className="text-xl text-gray-400 max-w-2xl mx-auto mb-8">
            AI驱动的多人推理游戏。扮演不同角色，运用智慧和策略，
            在谎言与真相之间找出狼人，或者作为狼人隐藏身份，击败所有好人。
          </p>

          <div className="flex flex-col sm:flex-row gap-4 justify-center">
            <button
              onClick={() => setShowCreateModal(true)}
              disabled={creatingGame}
              className="px-8 py-4 rounded-xl font-medium bg-gradient-to-r from-purple-600 to-blue-600 text-white hover:from-purple-700 hover:to-blue-700 transition-all transform hover:scale-105 disabled:opacity-50 disabled:cursor-not-allowed flex items-center justify-center space-x-2"
            >
              <span>🎮</span>
              <span>{creatingGame ? '创建中...' : '创建游戏'}</span>
            </button>
            
            <button
              onClick={() => document.getElementById('games-section')?.scrollIntoView({ behavior: 'smooth' })}
              className="px-8 py-4 rounded-xl font-medium bg-wolf-card border border-wolf-border text-gray-300 hover:bg-wolf-border hover:text-white transition-all flex items-center justify-center space-x-2"
            >
              <span>👁️</span>
              <span>观战游戏</span>
            </button>
          </div>
        </div>
      </section>

      {/* Features Section */}
      <section className="grid md:grid-cols-3 gap-6">
        <FeatureCard
          icon="🤖"
          title="AI驱动"
          description="智能AI玩家，提供真实的游戏体验，支持纯AI对战或人机对战"
        />
        <FeatureCard
          icon="⚡"
          title="实时对战"
          description="WebSocket实时通信，流畅的游戏体验，支持多人在线观战"
        />
        <FeatureCard
          icon="🎭"
          title="多种角色"
          description="狼人、预言家、女巫、猎人、守卫、平民，经典角色齐全"
        />
      </section>

      {/* Active Games Section */}
      <section id="games-section" className="bg-wolf-card rounded-2xl border border-wolf-border p-6">
        <div className="flex items-center justify-between mb-6">
          <h2 className="text-2xl font-bold text-white flex items-center">
            <span className="mr-3">🎮</span>
            活跃游戏
          </h2>
          <button
            onClick={listGames}
            disabled={loadingGames}
            className="px-4 py-2 rounded-lg bg-wolf-bg text-gray-400 hover:text-white transition-colors text-sm"
          >
            {loadingGames ? '刷新中...' : '🔄 刷新'}
          </button>
        </div>

        {games && games.length > 0 ? (
          <div className="grid md:grid-cols-2 lg:grid-cols-3 gap-4">
            {games.map((game) => (
              <GameCard
                key={game.game_id}
                game={game}
                onSpectate={() => handleSpectate(game.game_id)}
                onJoin={() => handleJoinGame(game.game_id)}
              />
            ))}
          </div>
        ) : (
          <div className="text-center py-12 text-gray-500">
            <span className="text-4xl block mb-4">📝</span>
            <p>暂无活跃游戏</p>
            <p className="text-sm mt-2">创建一个新游戏开始吧！</p>
          </div>
        )}
      </section>

      {/* How to Play Section */}
      <section className="bg-wolf-card rounded-2xl border border-wolf-border p-6">
        <h2 className="text-2xl font-bold text-white mb-6 flex items-center">
          <span className="mr-3">📖</span>
          游戏说明
        </h2>
        
        <div className="grid md:grid-cols-2 gap-8">
          <div>
            <h3 className="text-lg font-medium text-purple-400 mb-4">游戏流程</h3>
            <ol className="space-y-3 text-gray-400">
              <li className="flex items-start">
                <span className="mr-3 text-purple-500">1.</span>
                <span>夜晚阶段：守卫守护、狼人杀人、预言家查验、女巫救人/毒人</span>
              </li>
              <li className="flex items-start">
                <span className="mr-3 text-purple-500">2.</span>
                <span>白天阶段：公布死亡信息、玩家发言、投票放逐</span>
              </li>
              <li className="flex items-start">
                <span className="mr-3 text-purple-500">3.</span>
                <span>重复昼夜交替，直到某一方获胜</span>
              </li>
            </ol>
          </div>
          
          <div>
            <h3 className="text-lg font-medium text-purple-400 mb-4">胜利条件</h3>
            <ul className="space-y-3 text-gray-400">
              <li className="flex items-center">
                <span className="mr-3">🐺</span>
                <span><strong className="text-red-400">狼人阵营</strong>：杀死所有神职或所有平民</span>
              </li>
              <li className="flex items-center">
                <span className="mr-3">😇</span>
                <span><strong className="text-blue-400">好人阵营</strong>：找出并放逐所有狼人</span>
              </li>
            </ul>
          </div>
        </div>
      </section>

      {/* Create Game Modal */}
      {showCreateModal && (
        <CreateGameModal
          autoPlay={autoPlay}
          setAutoPlay={setAutoPlay}
          speed={speed}
          setSpeed={setSpeed}
          onCreateAI={() => {
            setShowCreateModal(false);
            handleCreateGame(false);
          }}
          onCreateHuman={() => {
            setShowCreateModal(false);
            handleCreateGame(true);
          }}
          onClose={() => setShowCreateModal(false)}
          loading={creatingGame}
        />
      )}
    </div>
  );
}

// 特性卡片组件
function FeatureCard({ icon, title, description }: { icon: string; title: string; description: string }) {
  return (
    <div className="bg-wolf-card rounded-xl border border-wolf-border p-6 hover:border-purple-500/30 transition-colors">
      <div className="text-4xl mb-4">{icon}</div>
      <h3 className="text-lg font-bold text-white mb-2">{title}</h3>
      <p className="text-gray-400 text-sm">{description}</p>
    </div>
  );
}

// 游戏卡片组件
function GameCard({
  game,
  onSpectate,
  onJoin,
}: {
  game: GameListItem;
  onSpectate: () => void;
  onJoin: () => void;
}) {
  const getPhaseIcon = (phase: Phase) => {
    if (phase === Phase.GAME_OVER) return '🏁';
    if (phase === Phase.SETUP) return '⏳';
    if (phase.toString().includes('NIGHT')) return '🌙';
    return '☀️';
  };

  const getPhaseColor = (phase: Phase) => {
    if (phase === Phase.GAME_OVER) return 'text-gray-400';
    if (phase === Phase.SETUP) return 'text-yellow-400';
    if (phase.toString().includes('NIGHT')) return 'text-indigo-400';
    return 'text-amber-400';
  };

  return (
    <div className="bg-wolf-bg rounded-xl border border-wolf-border p-4 hover:border-purple-500/30 transition-colors">
      <div className="flex items-center justify-between mb-3">
        <div className="flex items-center space-x-2">
          <span className={cn('text-xl', getPhaseColor(game.phase))}>
            {getPhaseIcon(game.phase)}
          </span>
          <span className="font-medium text-gray-200">{game.game_id.slice(0, 8)}...</span>
        </div>
        <span className="text-xs text-gray-500">第 {game.round} 回合</span>
      </div>
      
      <div className="flex items-center justify-between text-sm text-gray-400 mb-4">
        <span>存活: {game.alive_count}/{game.player_count}</span>
        <span>{game.has_winner ? '已结束' : '进行中'}</span>
      </div>
      
      <div className="flex space-x-2">
        <button
          onClick={onSpectate}
          className="flex-1 px-3 py-2 rounded-lg bg-purple-600/20 text-purple-400 hover:bg-purple-600/30 transition-colors text-sm font-medium"
        >
          👁️ 观战
        </button>
        {!game.has_winner && game.phase === Phase.SETUP && (
          <button
            onClick={onJoin}
            className="flex-1 px-3 py-2 rounded-lg bg-green-600/20 text-green-400 hover:bg-green-600/30 transition-colors text-sm font-medium"
          >
            🎮 加入
          </button>
        )}
      </div>
    </div>
  );
}

// 创建游戏模态框
function CreateGameModal({
  autoPlay,
  setAutoPlay,
  speed,
  setSpeed,
  onCreateAI,
  onCreateHuman,
  onClose,
  loading,
}: {
  autoPlay: boolean;
  setAutoPlay: (value: boolean) => void;
  speed: number;
  setSpeed: (value: number) => void;
  onCreateAI: () => void;
  onCreateHuman: () => void;
  onClose: () => void;
  loading: boolean;
}) {
  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-black/80 backdrop-blur-sm">
      <div className="max-w-md w-full bg-wolf-card rounded-2xl border border-wolf-border p-6">
        <h2 className="text-2xl font-bold text-white mb-6">创建新游戏</h2>
        
        {/* 自动游戏选项 */}
        <div className="mb-6">
          <label className="flex items-center space-x-3 cursor-pointer">
            <input
              type="checkbox"
              checked={autoPlay}
              onChange={(e) => setAutoPlay(e.target.checked)}
              className="w-5 h-5 rounded border-gray-600 text-purple-500 focus:ring-purple-500"
            />
            <span className="text-gray-300">自动进行（AI自动行动）</span>
          </label>
        </div>

        {/* 速度选择 */}
        <div className="mb-8">
          <label className="block text-gray-300 mb-3">游戏速度</label>
          <div className="flex space-x-2">
            {[0.5, 1.0, 1.5, 2.0].map((s) => (
              <button
                key={s}
                onClick={() => setSpeed(s)}
                className={cn(
                  'flex-1 py-2 rounded-lg text-sm font-medium transition-colors',
                  speed === s
                    ? 'bg-purple-600 text-white'
                    : 'bg-wolf-bg text-gray-400 hover:bg-wolf-border'
                )}
              >
                {s}x
              </button>
            ))}
          </div>
        </div>

        {/* 按钮 */}
        <div className="space-y-3">
          <button
            onClick={onCreateAI}
            disabled={loading}
            className="w-full px-4 py-3 rounded-lg bg-gradient-to-r from-purple-600 to-blue-600 text-white font-medium hover:from-purple-700 hover:to-blue-700 transition-all disabled:opacity-50"
          >
            {loading ? '创建中...' : '🤖 创建纯AI游戏'}
          </button>
          <button
            onClick={onCreateHuman}
            disabled={loading}
            className="w-full px-4 py-3 rounded-lg bg-gradient-to-r from-green-600 to-teal-600 text-white font-medium hover:from-green-700 hover:to-teal-700 transition-all disabled:opacity-50"
          >
            {loading ? '创建中...' : '👤 创建人机对战（我加入）'}
          </button>
          <button
            onClick={onClose}
            disabled={loading}
            className="w-full px-4 py-3 rounded-lg bg-gray-700 text-gray-300 font-medium hover:bg-gray-600 transition-all"
          >
            取消
          </button>
        </div>
      </div>
    </div>
  );
}
