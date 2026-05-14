import { useEffect } from 'react';
import { useParams, Link } from 'react-router-dom';
import { clsx, type ClassValue } from 'clsx';
import { twMerge } from 'tailwind-merge';
import { useGetPlayerStats } from '@/hooks/useGameAPI';
import { ROLE_INFO, type RolePerformance, type RecentGameResult, type PlayerComparison } from '@/types/game';

function cn(...inputs: ClassValue[]) {
  return twMerge(clsx(inputs));
}

export function PlayerStatsPage() {
  const { playerId } = useParams<{ playerId: string }>();
  const { data: stats, loading, error, getPlayerStats } = useGetPlayerStats();

  useEffect(() => {
    if (playerId) {
      getPlayerStats(playerId);
    }
  }, [playerId, getPlayerStats]);

  return (
    <div className="space-y-8">
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
          <p className="text-gray-400 ml-4">加载玩家数据...</p>
        </div>
      )}

      {!loading && !error && stats && (
        <>
          {/* 玩家资料卡 */}
          <PlayerProfileCard stats={stats} />

          {/* 核心数据 */}
          <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
            <CoreStatCard label="总场次" value={stats.total_games} icon="🎮" color="purple" />
            <CoreStatCard label="胜利" value={stats.wins} icon="🏆" color="yellow" />
            <CoreStatCard
              label="胜率"
              value={`${(stats.win_rate * 100).toFixed(1)}%`}
              icon="📈"
              color="green"
            />
            <CoreStatCard
              label="存活率"
              value={`${(stats.survival_rate * 100).toFixed(1)}%`}
              icon="💚"
              color="blue"
            />
          </div>

          {/* 角色胜率饼图 + 对比 */}
          <div className="grid md:grid-cols-2 gap-6">
            {/* 角色胜率饼图 */}
            <div className="bg-wolf-card rounded-2xl border border-wolf-border p-6">
              <h2 className="text-lg font-bold text-white mb-6 flex items-center">
                <span className="mr-2">🥧</span>
                各角色胜率
              </h2>
              {stats.role_stats.length > 0 ? (
                <div className="space-y-4">
                  {stats.role_stats.map((roleStat) => (
                    <RolePieChart key={roleStat.role} roleStat={roleStat} />
                  ))}
                </div>
              ) : (
                <div className="text-center py-8 text-gray-500">
                  <p>暂无角色数据</p>
                </div>
              )}
            </div>

            {/* 与平均水平对比 */}
            <div className="bg-wolf-card rounded-2xl border border-wolf-border p-6">
              <h2 className="text-lg font-bold text-white mb-6 flex items-center">
                <span className="mr-2">📊</span>
                与平均水平对比
              </h2>
              <ComparisonBars comparison={stats.comparison} />
            </div>
          </div>

          {/* 优势与劣势 */}
          <div className="grid md:grid-cols-2 gap-6">
            {/* 优势 */}
            <div className="bg-wolf-card rounded-2xl border border-wolf-border p-6">
              <h2 className="text-lg font-bold text-green-400 mb-4 flex items-center">
                <span className="mr-2">💪</span>
                优势
              </h2>
              {stats.strengths.length > 0 ? (
                <ul className="space-y-2">
                  {stats.strengths.map((strength, idx) => (
                    <li key={idx} className="flex items-start text-sm text-gray-300">
                      <span className="text-green-400 mr-2 mt-0.5">✓</span>
                      {strength}
                    </li>
                  ))}
                </ul>
              ) : (
                <p className="text-gray-500 text-sm">暂无分析数据</p>
              )}
            </div>

            {/* 劣势 */}
            <div className="bg-wolf-card rounded-2xl border border-wolf-border p-6">
              <h2 className="text-lg font-bold text-red-400 mb-4 flex items-center">
                <span className="mr-2">⚠️</span>
                劣势
              </h2>
              {stats.weaknesses.length > 0 ? (
                <ul className="space-y-2">
                  {stats.weaknesses.map((weakness, idx) => (
                    <li key={idx} className="flex items-start text-sm text-gray-300">
                      <span className="text-red-400 mr-2 mt-0.5">!</span>
                      {weakness}
                    </li>
                  ))}
                </ul>
              ) : (
                <p className="text-gray-500 text-sm">暂无分析数据</p>
              )}
            </div>
          </div>

          {/* 最近游戏表现 */}
          <div className="bg-wolf-card rounded-2xl border border-wolf-border p-6">
            <h2 className="text-lg font-bold text-white mb-6 flex items-center">
              <span className="mr-2">🕐</span>
              最近游戏表现
            </h2>
            {stats.recent_games.length > 0 ? (
              <div className="space-y-3">
                {stats.recent_games.map((game) => (
                  <RecentGameRow key={game.game_id} game={game} />
                ))}
              </div>
            ) : (
              <div className="text-center py-8 text-gray-500">
                <p>暂无最近游戏记录</p>
              </div>
            )}
          </div>
        </>
      )}
    </div>
  );
}

function PlayerProfileCard({ stats }: { stats: { player_id: string; player_name: string; total_games: number; win_rate: number; avg_contribution: number } }) {
  return (
    <div className="bg-wolf-card rounded-2xl border border-wolf-border p-6">
      <div className="flex flex-col md:flex-row items-center md:items-start gap-6">
        <div className="w-20 h-20 rounded-full bg-gradient-to-br from-purple-600 to-blue-600 flex items-center justify-center text-4xl flex-shrink-0">
          👤
        </div>
        <div className="flex-1 text-center md:text-left">
          <h1 className="text-2xl font-bold text-white">{stats.player_name}</h1>
          <p className="text-gray-500 text-sm mt-1 font-mono">ID: {stats.player_id}</p>
          <div className="flex flex-wrap gap-3 mt-4 justify-center md:justify-start">
            <span className="px-3 py-1 rounded-lg bg-purple-500/10 text-purple-400 text-sm">
              总场次: {stats.total_games}
            </span>
            <span className="px-3 py-1 rounded-lg bg-green-500/10 text-green-400 text-sm">
              胜率: {(stats.win_rate * 100).toFixed(1)}%
            </span>
            <span className="px-3 py-1 rounded-lg bg-blue-500/10 text-blue-400 text-sm">
              平均贡献: {stats.avg_contribution.toFixed(1)}
            </span>
          </div>
        </div>
        <Link
          to="/stats"
          className="px-4 py-2 rounded-lg bg-wolf-bg border border-wolf-border text-gray-400 hover:text-white transition-colors text-sm"
        >
          ← 返回统计
        </Link>
      </div>
    </div>
  );
}

function CoreStatCard({ label, value, icon, color }: { label: string; value: string | number; icon: string; color: 'purple' | 'yellow' | 'green' | 'blue' }) {
  const colorClasses = {
    purple: 'bg-purple-500/10 border-purple-500/30 text-purple-400',
    yellow: 'bg-yellow-500/10 border-yellow-500/30 text-yellow-400',
    green: 'bg-green-500/10 border-green-500/30 text-green-400',
    blue: 'bg-blue-500/10 border-blue-500/30 text-blue-400',
  };

  return (
    <div className={cn('rounded-xl border p-5 text-center', colorClasses[color])}>
      <span className="text-3xl block mb-2">{icon}</span>
      <div className="text-2xl font-bold text-white">{value}</div>
      <div className="text-xs opacity-80 mt-1">{label}</div>
    </div>
  );
}

function RolePieChart({ roleStat }: { roleStat: RolePerformance }) {
  const roleInfo = ROLE_INFO[roleStat.role];
  const winRate = roleStat.win_rate * 100;

  // CSS conic gradient for pie chart
  const pieStyle = {
    background: `conic-gradient(${roleInfo.color} ${winRate * 3.6}deg, #2d3548 0deg)`,
  };

  return (
    <div className="flex items-center space-x-4">
      <div className="relative w-14 h-14 rounded-full flex-shrink-0" style={pieStyle}>
        <div className="absolute inset-1 rounded-full bg-wolf-card flex items-center justify-center">
          <span className="text-xs font-bold text-white">{winRate.toFixed(0)}%</span>
        </div>
      </div>
      <div className="flex-1">
        <div className="flex items-center justify-between">
          <span className="text-sm font-medium text-white">{roleInfo.name}</span>
          <span className="text-xs text-gray-500">{roleStat.games} 场</span>
        </div>
        <div className="flex items-center space-x-3 mt-1 text-xs">
          <span className="text-gray-400">
            胜: <span className="text-green-400">{roleStat.wins}</span>
          </span>
          <span className="text-gray-400">
            负: <span className="text-red-400">{roleStat.games - roleStat.wins}</span>
          </span>
          <span className="text-gray-400">
            贡献: <span className="text-purple-400">{roleStat.avg_contribution.toFixed(1)}</span>
          </span>
        </div>
      </div>
    </div>
  );
}

function ComparisonBars({ comparison }: { comparison: PlayerComparison }) {
  const items = [
    { label: '胜率', value: comparison.win_rate_diff, format: (v: number) => `${(v * 100).toFixed(1)}%`, good: 'positive' },
    { label: '存活率', value: comparison.survival_rate_diff, format: (v: number) => `${(v * 100).toFixed(1)}%`, good: 'positive' },
    { label: '贡献分', value: comparison.contribution_diff, format: (v: number) => `${v.toFixed(1)}`, good: 'positive' },
    { label: '场次', value: comparison.games_played_diff, format: (v: number) => `${v > 0 ? '+' : ''}${v}`, good: 'positive' },
  ];

  return (
    <div className="space-y-5">
      {items.map((item) => {
        const isPositive = item.value > 0;
        const isNeutral = item.value === 0;
        const barWidth = Math.min(Math.abs(item.value) * 100, 100);
        const color = isPositive ? 'bg-green-500' : isNeutral ? 'bg-gray-500' : 'bg-red-500';
        const textColor = isPositive ? 'text-green-400' : isNeutral ? 'text-gray-400' : 'text-red-400';

        return (
          <div key={item.label}>
            <div className="flex items-center justify-between mb-1">
              <span className="text-sm text-gray-400">{item.label}</span>
              <span className={cn('text-sm font-bold', textColor)}>
                {isPositive ? '+' : ''}{item.format(item.value)}
              </span>
            </div>
            <div className="flex items-center">
              <div className="flex-1 bg-wolf-bg rounded-full h-3 overflow-hidden">
                <div
                  className={cn('h-full rounded-full transition-all duration-500', color)}
                  style={{ width: `${Math.max(barWidth, 5)}%` }}
                />
              </div>
              <span className="text-xs text-gray-500 ml-3 w-12 text-right">
                {isPositive ? '高于' : isNeutral ? '持平' : '低于'}平均
              </span>
            </div>
          </div>
        );
      })}
    </div>
  );
}

function RecentGameRow({ game }: { game: RecentGameResult }) {
  const roleInfo = ROLE_INFO[game.role];

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
    <div className="flex items-center justify-between p-3 rounded-lg bg-wolf-bg hover:bg-white/5 transition-colors">
      <div className="flex items-center space-x-3">
        <span
          className={cn(
            'text-lg',
            game.result === 'win' ? 'text-green-400' : 'text-red-400'
          )}
        >
          {game.result === 'win' ? '✓' : '✗'}
        </span>
        <div>
          <div className="flex items-center space-x-2">
            <span
              className="text-xs px-1.5 py-0.5 rounded"
              style={{ backgroundColor: `${roleInfo.color}20`, color: roleInfo.color }}
            >
              {roleInfo.name}
            </span>
            <span className={cn('text-xs font-medium', game.result === 'win' ? 'text-green-400' : 'text-red-400')}>
              {game.result === 'win' ? '胜利' : '失败'}
            </span>
          </div>
          <div className="text-xs text-gray-500 mt-1">
            贡献: {game.contribution.toFixed(1)} · {game.survived ? '存活' : '死亡'}
          </div>
        </div>
      </div>
      <div className="text-right">
        <Link
          to={`/replay/${game.game_id}`}
          className="text-xs text-purple-400 hover:text-purple-300 transition-colors"
        >
          查看回放 →
        </Link>
        <div className="text-xs text-gray-500 mt-1">{formatDate(game.date)}</div>
      </div>
    </div>
  );
}
