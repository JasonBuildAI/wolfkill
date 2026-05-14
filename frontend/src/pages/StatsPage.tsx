import { useState, useEffect } from 'react';
import { Link } from 'react-router-dom';
import { clsx, type ClassValue } from 'clsx';
import { twMerge } from 'tailwind-merge';
import { useGetStatsOverview, useGetRoleStats } from '@/hooks/useGameAPI';
import { Team, ROLE_INFO, type RoleStats, type RecentGameSummary } from '@/types/game';

function cn(...inputs: ClassValue[]) {
  return twMerge(clsx(inputs));
}

export function StatsPage() {
  const { data: overview, loading: overviewLoading, error: overviewError, getStatsOverview } = useGetStatsOverview();
  const { data: roleStats, loading: roleStatsLoading, error: roleStatsError, getRoleStats } = useGetRoleStats();
  const [searchQuery, setSearchQuery] = useState('');

  useEffect(() => {
    getStatsOverview();
    getRoleStats();
  }, [getStatsOverview, getRoleStats]);

  const loading = overviewLoading || roleStatsLoading;
  const error = overviewError || roleStatsError;

  const formatDuration = (seconds: number) => {
    const mins = Math.floor(seconds / 60);
    const secs = seconds % 60;
    return `${mins}分${secs}秒`;
  };

  return (
    <div className="space-y-8">
      {/* 页面标题 */}
      <div className="text-center py-8">
        <h1 className="text-3xl md:text-4xl font-bold text-white mb-2">📊 数据统计</h1>
        <p className="text-gray-400">全局游戏数据统计与分析</p>
      </div>

      {/* 错误提示 */}
      {error && (
        <div className="bg-red-950/50 border border-red-500/50 rounded-lg p-4 text-red-400 text-center">
          {error}
        </div>
      )}

      {/* 加载状态 */}
      {loading && (
        <div className="flex items-center justify-center py-16">
          <div className="animate-spin w-12 h-12 border-4 border-purple-600 border-t-transparent rounded-full mb-4" />
          <p className="text-gray-400 ml-4">加载中...</p>
        </div>
      )}

      {!loading && !error && overview && (
        <>
          {/* 全局统计卡片 */}
          <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
            <StatCard
              label="总游戏数"
              value={overview.total_games.toString()}
              icon="🎮"
              color="purple"
            />
            <StatCard
              label="平均时长"
              value={formatDuration(overview.avg_duration_seconds)}
              icon="⏱️"
              color="blue"
            />
            <StatCard
              label="好人胜率"
              value={`${(overview.good_win_rate * 100).toFixed(1)}%`}
              icon="😇"
              color="green"
            />
            <StatCard
              label="狼人胜率"
              value={`${(overview.evil_win_rate * 100).toFixed(1)}%`}
              icon="🐺"
              color="red"
            />
          </div>

          {/* 角色胜率条形图 */}
          <div className="bg-wolf-card rounded-2xl border border-wolf-border p-6">
            <h2 className="text-xl font-bold text-white mb-6 flex items-center">
              <span className="mr-3">📈</span>
              角色胜率统计
            </h2>
            {roleStats && roleStats.length > 0 ? (
              <div className="space-y-4">
                {roleStats.map((stat) => (
                  <RoleBarChart key={stat.role} stat={stat} />
                ))}
              </div>
            ) : (
              <div className="text-center py-8 text-gray-500">
                <span className="text-3xl block mb-3">📊</span>
                <p>暂无角色统计数据</p>
              </div>
            )}
          </div>

          {/* 玩家搜索 */}
          <div className="bg-wolf-card rounded-2xl border border-wolf-border p-6">
            <h2 className="text-xl font-bold text-white mb-4 flex items-center">
              <span className="mr-3">🔍</span>
              查找玩家
            </h2>
            <div className="flex gap-3">
              <input
                type="text"
                value={searchQuery}
                onChange={(e) => setSearchQuery(e.target.value)}
                placeholder="输入玩家ID或名称..."
                className="flex-1 px-4 py-3 rounded-lg bg-wolf-bg border border-wolf-border text-white placeholder-gray-500 focus:outline-none focus:border-purple-500 transition-colors"
                onKeyDown={(e) => {
                  if (e.key === 'Enter' && searchQuery.trim()) {
                    window.location.href = `/player/${encodeURIComponent(searchQuery.trim())}`;
                  }
                }}
              />
              <Link
                to={searchQuery.trim() ? `/player/${encodeURIComponent(searchQuery.trim())}` : '#'}
                className={cn(
                  'px-6 py-3 rounded-lg font-medium transition-all',
                  searchQuery.trim()
                    ? 'bg-purple-600 text-white hover:bg-purple-700'
                    : 'bg-wolf-bg text-gray-500 cursor-not-allowed'
                )}
                onClick={(e) => {
                  if (!searchQuery.trim()) e.preventDefault();
                }}
              >
                搜索
              </Link>
            </div>
          </div>

          {/* 最近游戏列表 */}
          <div className="bg-wolf-card rounded-2xl border border-wolf-border p-6">
            <h2 className="text-xl font-bold text-white mb-6 flex items-center">
              <span className="mr-3">🕐</span>
              最近游戏
            </h2>
            {overview.recent_games && overview.recent_games.length > 0 ? (
              <div className="grid md:grid-cols-2 lg:grid-cols-3 gap-4">
                {overview.recent_games.map((game) => (
                  <RecentGameCard key={game.game_id} game={game} />
                ))}
              </div>
            ) : (
              <div className="text-center py-8 text-gray-500">
                <span className="text-3xl block mb-3">📝</span>
                <p>暂无最近游戏记录</p>
              </div>
            )}
          </div>
        </>
      )}
    </div>
  );
}

function StatCard({ label, value, icon, color }: { label: string; value: string; icon: string; color: 'purple' | 'blue' | 'green' | 'red' }) {
  const colorClasses = {
    purple: 'bg-purple-500/10 border-purple-500/30 text-purple-400',
    blue: 'bg-blue-500/10 border-blue-500/30 text-blue-400',
    green: 'bg-green-500/10 border-green-500/30 text-green-400',
    red: 'bg-red-500/10 border-red-500/30 text-red-400',
  };

  return (
    <div className={cn('rounded-xl border p-5', colorClasses[color])}>
      <div className="flex items-center justify-between">
        <span className="text-3xl">{icon}</span>
        <div className="text-right">
          <div className="text-2xl font-bold text-white">{value}</div>
          <div className="text-xs opacity-80 mt-1">{label}</div>
        </div>
      </div>
    </div>
  );
}

function RoleBarChart({ stat }: { stat: RoleStats }) {
  const roleInfo = ROLE_INFO[stat.role];
  const winRate = stat.win_rate * 100;
  const maxBarWidth = 100;

  return (
    <div className="flex items-center space-x-4">
      <div className="w-20 text-right">
        <span
          className="text-sm font-medium"
          style={{ color: roleInfo.color }}
        >
          {roleInfo.name}
        </span>
      </div>
      <div className="flex-1">
        <div className="flex items-center space-x-3">
          <div className="flex-1 bg-wolf-bg rounded-full h-6 overflow-hidden relative">
            <div
              className="h-full rounded-full transition-all duration-500 ease-out flex items-center justify-end pr-2"
              style={{
                width: `${Math.min(winRate, maxBarWidth)}%`,
                backgroundColor: roleInfo.color,
                opacity: 0.8,
              }}
            >
              {winRate > 15 && (
                <span className="text-xs text-white font-medium">{winRate.toFixed(1)}%</span>
              )}
            </div>
            {winRate <= 15 && (
              <span className="absolute left-2 top-1/2 -translate-y-1/2 text-xs text-gray-400">
                {winRate.toFixed(1)}%
              </span>
            )}
          </div>
        </div>
      </div>
      <div className="w-24 text-right text-xs text-gray-400">
        {stat.games} 场
      </div>
    </div>
  );
}

function RecentGameCard({ game }: { game: RecentGameSummary }) {
  const formatDuration = (seconds: number) => {
    const mins = Math.floor(seconds / 60);
    const secs = seconds % 60;
    return `${mins}分${secs}秒`;
  };

  const formatDate = (dateStr: string) => {
    const date = new Date(dateStr);
    return date.toLocaleDateString('zh-CN', {
      month: 'short',
      day: 'numeric',
      hour: '2-digit',
      minute: '2-digit',
    });
  };

  return (
    <div className="bg-wolf-bg rounded-xl border border-wolf-border p-4 hover:border-purple-500/30 transition-colors">
      <div className="flex items-center justify-between mb-3">
        <span className="text-xs text-gray-500 font-mono">{game.game_id.slice(0, 8)}...</span>
        <span
          className={cn(
            'text-xs px-2 py-0.5 rounded font-medium',
            game.winner === Team.GOOD
              ? 'bg-blue-500/20 text-blue-400'
              : 'bg-red-500/20 text-red-400'
          )}
        >
          {game.winner === Team.GOOD ? '好人胜利' : '狼人胜利'}
        </span>
      </div>
      <div className="grid grid-cols-2 gap-2 text-sm mb-3">
        <div className="text-gray-400">
          <span className="text-gray-500">回合:</span>{' '}
          <span className="text-white">{game.rounds}</span>
        </div>
        <div className="text-gray-400">
          <span className="text-gray-500">时长:</span>{' '}
          <span className="text-white">{formatDuration(game.duration_seconds)}</span>
        </div>
        <div className="text-gray-400">
          <span className="text-gray-500">人数:</span>{' '}
          <span className="text-white">{game.player_count}</span>
        </div>
        <div className="text-gray-400">
          <span className="text-gray-500">时间:</span>{' '}
          <span className="text-white">{formatDate(game.date)}</span>
        </div>
      </div>
      <div className="flex space-x-2">
        <Link
          to={`/replay/${game.game_id}`}
          className="flex-1 px-3 py-2 rounded-lg bg-purple-600/20 text-purple-400 hover:bg-purple-600/30 transition-colors text-sm font-medium text-center"
        >
          📺 回放
        </Link>
        <Link
          to={`/spectate/${game.game_id}`}
          className="flex-1 px-3 py-2 rounded-lg bg-wolf-card text-gray-400 hover:text-white hover:bg-wolf-border transition-colors text-sm font-medium text-center"
        >
          👁️ 观战
        </Link>
      </div>
    </div>
  );
}
