import { useState, useEffect, useMemo } from 'react';
import { Link } from 'react-router-dom';
import { clsx, type ClassValue } from 'clsx';
import { twMerge } from 'tailwind-merge';
import { useGetLeaderboard } from '@/hooks/useGameAPI';
import { Role, ROLE_INFO, type LeaderboardEntry } from '@/types/game';

function cn(...inputs: ClassValue[]) {
  return twMerge(clsx(inputs));
}

type SortField = 'rank' | 'win_rate' | 'survival_rate' | 'games_played' | 'avg_contribution' | 'total_score';
type SortOrder = 'asc' | 'desc';

const ROLE_TABS = [
  { role: undefined, label: '全部', color: '#9ca3af' },
  { role: Role.WEREWOLF, label: '狼人', color: ROLE_INFO[Role.WEREWOLF].color },
  { role: Role.SEER, label: '预言家', color: ROLE_INFO[Role.SEER].color },
  { role: Role.WITCH, label: '女巫', color: ROLE_INFO[Role.WITCH].color },
  { role: Role.HUNTER, label: '猎人', color: ROLE_INFO[Role.HUNTER].color },
  { role: Role.GUARD, label: '守卫', color: ROLE_INFO[Role.GUARD].color },
  { role: Role.VILLAGER, label: '平民', color: ROLE_INFO[Role.VILLAGER].color },
];

const PAGE_SIZE = 20;

export function LeaderboardPage() {
  const { data: leaderboard, loading, error, getLeaderboard } = useGetLeaderboard();
  const [activeRole, setActiveRole] = useState<Role | undefined>(undefined);
  const [sortField, setSortField] = useState<SortField>('rank');
  const [sortOrder, setSortOrder] = useState<SortOrder>('asc');
  const [page, setPage] = useState(1);

  useEffect(() => {
    getLeaderboard(activeRole);
  }, [activeRole, getLeaderboard]);

  useEffect(() => {
    setPage(1);
  }, [activeRole]);

  const handleSort = (field: SortField) => {
    if (sortField === field) {
      setSortOrder(sortOrder === 'asc' ? 'desc' : 'asc');
    } else {
      setSortField(field);
      setSortOrder('desc');
    }
  };

  const sortedData = useMemo(() => {
    if (!leaderboard) return [];
    const sorted = [...leaderboard];
    sorted.sort((a, b) => {
      const valA: unknown = a[sortField];
      const valB: unknown = b[sortField];
      if (typeof valA === 'string' && typeof valB === 'string') {
        const strA = valA.toLowerCase();
        const strB = valB.toLowerCase();
        if (strA < strB) return sortOrder === 'asc' ? -1 : 1;
        if (strA > strB) return sortOrder === 'asc' ? 1 : -1;
        return 0;
      }
      if (typeof valA === 'number' && typeof valB === 'number') {
        if (valA < valB) return sortOrder === 'asc' ? -1 : 1;
        if (valA > valB) return sortOrder === 'asc' ? 1 : -1;
        return 0;
      }
      return 0;
    });
    return sorted;
  }, [leaderboard, sortField, sortOrder]);

  const paginatedData = useMemo(() => {
    const start = (page - 1) * PAGE_SIZE;
    return sortedData.slice(start, start + PAGE_SIZE);
  }, [sortedData, page]);

  const totalPages = Math.ceil((sortedData.length || 0) / PAGE_SIZE);

  const SortIcon = ({ field }: { field: SortField }) => {
    if (sortField !== field) return <span className="text-gray-600 ml-1">↕</span>;
    return <span className="text-purple-400 ml-1">{sortOrder === 'asc' ? '↑' : '↓'}</span>;
  };

  return (
    <div className="space-y-6">
      {/* 页面标题 */}
      <div className="text-center py-8">
        <h1 className="text-3xl md:text-4xl font-bold text-white mb-2">🏆 排行榜</h1>
        <p className="text-gray-400">查看各角色玩家的排名与表现</p>
      </div>

      {/* 角色筛选标签 */}
      <div className="flex flex-wrap gap-2 justify-center">
        {ROLE_TABS.map((tab) => (
          <button
            key={tab.label}
            onClick={() => setActiveRole(tab.role)}
            className={cn(
              'px-4 py-2 rounded-lg text-sm font-medium transition-all border',
              activeRole === tab.role || (tab.role === undefined && activeRole === undefined)
                ? 'text-white border-transparent'
                : 'text-gray-400 border-wolf-border hover:text-gray-200 hover:border-gray-500'
            )}
            style={
              activeRole === tab.role || (tab.role === undefined && activeRole === undefined)
                ? { backgroundColor: tab.color, borderColor: tab.color }
                : {}
            }
          >
            {tab.label}
          </button>
        ))}
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

      {/* Top 3 展示 */}
      {!loading && !error && sortedData.length > 0 && (
        <div className="grid md:grid-cols-3 gap-4 mb-8">
          {sortedData.slice(0, 3).map((entry, idx) => (
            <TopThreeCard key={entry.player_id} entry={entry} rank={idx + 1} />
          ))}
        </div>
      )}

      {/* 排行榜表格 */}
      {!loading && !error && (
        <div className="bg-wolf-card rounded-2xl border border-wolf-border overflow-hidden">
          {sortedData.length === 0 ? (
            <div className="text-center py-16 text-gray-500">
              <span className="text-4xl block mb-4">📊</span>
              <p>暂无数据</p>
            </div>
          ) : (
            <>
              <div className="overflow-x-auto">
                <table className="w-full">
                  <thead>
                    <tr className="bg-wolf-bg/50 border-b border-wolf-border">
                      <th
                        className="px-4 py-3 text-left text-xs font-medium text-gray-400 uppercase tracking-wider cursor-pointer hover:text-white transition-colors"
                        onClick={() => handleSort('rank')}
                      >
                        排名 <SortIcon field="rank" />
                      </th>
                      <th className="px-4 py-3 text-left text-xs font-medium text-gray-400 uppercase tracking-wider">
                        玩家
                      </th>
                      <th className="px-4 py-3 text-left text-xs font-medium text-gray-400 uppercase tracking-wider">
                        角色
                      </th>
                      <th
                        className="px-4 py-3 text-left text-xs font-medium text-gray-400 uppercase tracking-wider cursor-pointer hover:text-white transition-colors"
                        onClick={() => handleSort('win_rate')}
                      >
                        胜率 <SortIcon field="win_rate" />
                      </th>
                      <th
                        className="px-4 py-3 text-left text-xs font-medium text-gray-400 uppercase tracking-wider cursor-pointer hover:text-white transition-colors"
                        onClick={() => handleSort('survival_rate')}
                      >
                        存活率 <SortIcon field="survival_rate" />
                      </th>
                      <th
                        className="px-4 py-3 text-left text-xs font-medium text-gray-400 uppercase tracking-wider cursor-pointer hover:text-white transition-colors"
                        onClick={() => handleSort('games_played')}
                      >
                        场次 <SortIcon field="games_played" />
                      </th>
                      <th
                        className="px-4 py-3 text-left text-xs font-medium text-gray-400 uppercase tracking-wider cursor-pointer hover:text-white transition-colors"
                        onClick={() => handleSort('avg_contribution')}
                      >
                        平均贡献 <SortIcon field="avg_contribution" />
                      </th>
                      <th
                        className="px-4 py-3 text-left text-xs font-medium text-gray-400 uppercase tracking-wider cursor-pointer hover:text-white transition-colors"
                        onClick={() => handleSort('total_score')}
                      >
                        总分 <SortIcon field="total_score" />
                      </th>
                    </tr>
                  </thead>
                  <tbody className="divide-y divide-wolf-border">
                    {paginatedData.map((entry) => (
                      <LeaderboardRow key={entry.player_id} entry={entry} />
                    ))}
                  </tbody>
                </table>
              </div>

              {/* 分页 */}
              {totalPages > 1 && (
                <div className="flex items-center justify-between px-4 py-3 border-t border-wolf-border">
                  <div className="text-sm text-gray-500">
                    共 {sortedData.length} 条记录，第 {page} / {totalPages} 页
                  </div>
                  <div className="flex space-x-2">
                    <button
                      onClick={() => setPage(p => Math.max(1, p - 1))}
                      disabled={page === 1}
                      className="px-3 py-1 rounded-lg bg-wolf-bg text-gray-400 hover:text-white disabled:opacity-30 disabled:cursor-not-allowed text-sm"
                    >
                      上一页
                    </button>
                    {Array.from({ length: Math.min(5, totalPages) }, (_, i) => {
                      let pageNum: number;
                      if (totalPages <= 5) {
                        pageNum = i + 1;
                      } else if (page <= 3) {
                        pageNum = i + 1;
                      } else if (page >= totalPages - 2) {
                        pageNum = totalPages - 4 + i;
                      } else {
                        pageNum = page - 2 + i;
                      }
                      return (
                        <button
                          key={pageNum}
                          onClick={() => setPage(pageNum)}
                          className={cn(
                            'px-3 py-1 rounded-lg text-sm font-medium transition-colors',
                            page === pageNum
                              ? 'bg-purple-600 text-white'
                              : 'bg-wolf-bg text-gray-400 hover:text-white'
                          )}
                        >
                          {pageNum}
                        </button>
                      );
                    })}
                    <button
                      onClick={() => setPage(p => Math.min(totalPages, p + 1))}
                      disabled={page === totalPages}
                      className="px-3 py-1 rounded-lg bg-wolf-bg text-gray-400 hover:text-white disabled:opacity-30 disabled:cursor-not-allowed text-sm"
                    >
                      下一页
                    </button>
                  </div>
                </div>
              )}
            </>
          )}
        </div>
      )}
    </div>
  );
}

function TopThreeCard({ entry, rank }: { entry: LeaderboardEntry; rank: number }) {
  const roleInfo = ROLE_INFO[entry.role];
  const medalColors = [
    { bg: 'from-yellow-500/20 to-amber-600/20', border: 'border-yellow-500/50', text: 'text-yellow-400', icon: '🥇' },
    { bg: 'from-gray-400/20 to-gray-500/20', border: 'border-gray-400/50', text: 'text-gray-300', icon: '🥈' },
    { bg: 'from-orange-600/20 to-amber-700/20', border: 'border-orange-500/50', text: 'text-orange-400', icon: '🥉' },
  ];
  const medal = medalColors[rank - 1];

  return (
    <div className={cn(
      'relative rounded-2xl border p-6 bg-gradient-to-br',
      medal.bg,
      medal.border
    )}>
      <div className="absolute -top-3 -right-3 w-10 h-10 rounded-full bg-wolf-card border border-wolf-border flex items-center justify-center text-xl">
        {medal.icon}
      </div>
      <div className="text-center">
        <div className={cn('text-3xl font-bold mb-2', medal.text)}>
          #{entry.rank}
        </div>
        <Link
          to={`/player/${entry.player_id}`}
          className="text-lg font-bold text-white hover:text-purple-400 transition-colors block mb-1"
        >
          {entry.player_name}
        </Link>
        <span
          className="inline-block text-xs px-2 py-0.5 rounded mb-3"
          style={{ backgroundColor: `${roleInfo.color}20`, color: roleInfo.color }}
        >
          {roleInfo.name}
        </span>
        <div className="grid grid-cols-2 gap-2 text-sm mt-3">
          <div className="bg-wolf-bg/50 rounded-lg p-2">
            <div className="text-gray-400 text-xs">胜率</div>
            <div className="text-white font-bold">{(entry.win_rate * 100).toFixed(1)}%</div>
          </div>
          <div className="bg-wolf-bg/50 rounded-lg p-2">
            <div className="text-gray-400 text-xs">贡献</div>
            <div className="text-white font-bold">{entry.avg_contribution.toFixed(1)}</div>
          </div>
        </div>
      </div>
    </div>
  );
}

function LeaderboardRow({ entry }: { entry: LeaderboardEntry }) {
  const roleInfo = ROLE_INFO[entry.role];

  const getRankStyle = (rank: number) => {
    if (rank === 1) return 'text-yellow-400 font-bold';
    if (rank === 2) return 'text-gray-300 font-bold';
    if (rank === 3) return 'text-orange-400 font-bold';
    return 'text-gray-400';
  };

  return (
    <tr className="hover:bg-white/5 transition-colors">
      <td className="px-4 py-3 whitespace-nowrap">
        <span className={cn('text-sm', getRankStyle(entry.rank))}>#{entry.rank}</span>
      </td>
      <td className="px-4 py-3 whitespace-nowrap">
        <Link
          to={`/player/${entry.player_id}`}
          className="text-sm font-medium text-white hover:text-purple-400 transition-colors"
        >
          {entry.player_name}
        </Link>
      </td>
      <td className="px-4 py-3 whitespace-nowrap">
        <span
          className="inline-flex items-center px-2 py-0.5 rounded text-xs font-medium"
          style={{ backgroundColor: `${roleInfo.color}20`, color: roleInfo.color }}
        >
          {roleInfo.name}
        </span>
      </td>
      <td className="px-4 py-3 whitespace-nowrap">
        <div className="flex items-center space-x-2">
          <div className="w-16 bg-wolf-bg rounded-full h-2 overflow-hidden">
            <div
              className="h-full rounded-full bg-gradient-to-r from-purple-500 to-blue-500"
              style={{ width: `${entry.win_rate * 100}%` }}
            />
          </div>
          <span className="text-sm text-gray-300">{(entry.win_rate * 100).toFixed(1)}%</span>
        </div>
      </td>
      <td className="px-4 py-3 whitespace-nowrap">
        <span className="text-sm text-gray-300">{(entry.survival_rate * 100).toFixed(1)}%</span>
      </td>
      <td className="px-4 py-3 whitespace-nowrap">
        <span className="text-sm text-gray-300">{entry.games_played}</span>
      </td>
      <td className="px-4 py-3 whitespace-nowrap">
        <span className="text-sm text-gray-300">{entry.avg_contribution.toFixed(1)}</span>
      </td>
      <td className="px-4 py-3 whitespace-nowrap">
        <span className="text-sm font-medium text-purple-400">{entry.total_score.toFixed(0)}</span>
      </td>
    </tr>
  );
}
