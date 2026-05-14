import { useState, useEffect } from 'react';
import { useParams, Link } from 'react-router-dom';
import { clsx, type ClassValue } from 'clsx';
import { twMerge } from 'tailwind-merge';
import { useGetGameReplay, useGetGameAttribution, useGetGameSummary } from '@/hooks/useGameAPI';
import { Team, ROLE_INFO, PHASE_INFO, type ReplayEvent, type ReplayPlayer, type TurningPoint } from '@/types/game';

function cn(...inputs: ClassValue[]) {
  return twMerge(clsx(inputs));
}

export function ReplayPage() {
  const { gameId } = useParams<{ gameId: string }>();
  const { data: replay, loading: replayLoading, error: replayError, getGameReplay } = useGetGameReplay();
  const { data: attribution, loading: attrLoading, error: attrError, getGameAttribution } = useGetGameAttribution();
  const { data: summary, loading: summaryLoading, error: summaryError, getGameSummary } = useGetGameSummary();
  const [currentRound, setCurrentRound] = useState(1);

  useEffect(() => {
    if (gameId) {
      getGameReplay(gameId);
      getGameAttribution(gameId);
      getGameSummary(gameId);
    }
  }, [gameId, getGameReplay, getGameAttribution, getGameSummary]);

  const loading = replayLoading || attrLoading || summaryLoading;
  const error = replayError || attrError || summaryError;

  const maxRound = replay?.rounds || 1;

  const currentEvents = replay?.events.filter(e => e.round === currentRound) || [];
  const currentTurningPoints = replay?.key_turning_points.filter(tp => tp.round === currentRound) || [];

  const formatDuration = (seconds: number) => {
    const mins = Math.floor(seconds / 60);
    const secs = seconds % 60;
    return `${mins}分${secs}秒`;
  };

  return (
    <div className="space-y-6">
      {/* 页面标题 */}
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl md:text-3xl font-bold text-white">📺 游戏回放</h1>
          <p className="text-gray-400 text-sm mt-1">游戏ID: {gameId?.slice(0, 12)}...</p>
        </div>
        <Link
          to="/stats"
          className="px-4 py-2 rounded-lg bg-wolf-card border border-wolf-border text-gray-400 hover:text-white transition-colors text-sm"
        >
          ← 返回统计
        </Link>
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
          <p className="text-gray-400 ml-4">加载回放数据...</p>
        </div>
      )}

      {!loading && !error && summary && (
        <>
          {/* 游戏摘要 */}
          <div className="bg-wolf-card rounded-2xl border border-wolf-border p-6">
            <div className="grid md:grid-cols-5 gap-4">
              <SummaryItem
                label="获胜方"
                value={summary.winner === Team.GOOD ? '好人阵营' : '狼人阵营'}
                color={summary.winner === Team.GOOD ? 'text-blue-400' : 'text-red-400'}
              />
              <SummaryItem label="总回合" value={`${summary.rounds} 回合`} />
              <SummaryItem label="时长" value={formatDuration(summary.duration_seconds)} />
              <SummaryItem label="总死亡" value={`${summary.total_deaths} 人`} />
              <SummaryItem label="首杀回合" value={`第 ${summary.first_blood_round} 回合`} />
            </div>
            {summary.mvp_player && (
              <div className="mt-4 pt-4 border-t border-wolf-border flex items-center">
                <span className="text-yellow-400 mr-2">⭐ MVP:</span>
                <Link
                  to={`/player/${summary.mvp_player}`}
                  className="text-white font-medium hover:text-purple-400 transition-colors"
                >
                  {summary.mvp_player}
                </Link>
                {summary.mvp_role && (
                  <span
                    className="ml-2 text-xs px-2 py-0.5 rounded"
                    style={{
                      backgroundColor: `${ROLE_INFO[summary.mvp_role].color}20`,
                      color: ROLE_INFO[summary.mvp_role].color,
                    }}
                  >
                    {ROLE_INFO[summary.mvp_role].name}
                  </span>
                )}
              </div>
            )}
          </div>

          {/* 玩家存活状态 */}
          {replay && replay.players.length > 0 && (
            <div className="bg-wolf-card rounded-2xl border border-wolf-border p-6">
              <h2 className="text-lg font-bold text-white mb-4">👥 玩家状态</h2>
              <div className="grid grid-cols-2 md:grid-cols-3 lg:grid-cols-6 gap-3">
                {replay.players.map((player) => (
                  <PlayerStatusCard key={player.player_id} player={player} currentRound={currentRound} />
                ))}
              </div>
            </div>
          )}

          {/* 回合导航 */}
          <div className="flex items-center justify-between bg-wolf-card rounded-xl border border-wolf-border p-4">
            <button
              onClick={() => setCurrentRound(r => Math.max(1, r - 1))}
              disabled={currentRound === 1}
              className="px-4 py-2 rounded-lg bg-wolf-bg text-gray-400 hover:text-white disabled:opacity-30 disabled:cursor-not-allowed transition-colors"
            >
              ← 上一回合
            </button>
            <div className="text-center">
              <span className="text-lg font-bold text-white">第 {currentRound} 回合</span>
              <span className="text-gray-500 text-sm ml-2">/ 共 {maxRound} 回合</span>
            </div>
            <button
              onClick={() => setCurrentRound(r => Math.min(maxRound, r + 1))}
              disabled={currentRound === maxRound}
              className="px-4 py-2 rounded-lg bg-wolf-bg text-gray-400 hover:text-white disabled:opacity-30 disabled:cursor-not-allowed transition-colors"
            >
              下一回合 →
            </button>
          </div>

          {/* 回合进度条 */}
          <div className="bg-wolf-bg rounded-full h-2 overflow-hidden">
            <div
              className="h-full bg-gradient-to-r from-purple-500 to-blue-500 transition-all duration-300"
              style={{ width: `${(currentRound / maxRound) * 100}%` }}
            />
          </div>

          {/* 关键转折点 */}
          {currentTurningPoints.length > 0 && (
            <div className="bg-wolf-card rounded-2xl border border-wolf-border p-6">
              <h2 className="text-lg font-bold text-white mb-4 flex items-center">
                <span className="mr-2">⚡</span>
                本回合关键事件
              </h2>
              <div className="space-y-3">
                {currentTurningPoints.map((tp, idx) => (
                  <TurningPointCard key={idx} turningPoint={tp} />
                ))}
              </div>
            </div>
          )}

          {/* 事件时间线 */}
          <div className="bg-wolf-card rounded-2xl border border-wolf-border p-6">
            <h2 className="text-lg font-bold text-white mb-4 flex items-center">
              <span className="mr-2">📋</span>
              事件时间线
            </h2>
            {currentEvents.length > 0 ? (
              <div className="space-y-3">
                {currentEvents.map((event) => (
                  <EventCard key={event.id} event={event} />
                ))}
              </div>
            ) : (
              <div className="text-center py-8 text-gray-500">
                <p>本回合暂无事件</p>
              </div>
            )}
          </div>

          {/* 归因分析 */}
          {attribution && attribution.player_attributions.length > 0 && (
            <div className="bg-wolf-card rounded-2xl border border-wolf-border p-6">
              <h2 className="text-lg font-bold text-white mb-4 flex items-center">
                <span className="mr-2">🎯</span>
                归因分析
              </h2>
              <div className="grid md:grid-cols-2 gap-4">
                {attribution.player_attributions.map((attr) => (
                  <AttributionCard key={attr.player_id} attribution={attr} />
                ))}
              </div>
            </div>
          )}
        </>
      )}
    </div>
  );
}

function SummaryItem({ label, value, color }: { label: string; value: string; color?: string }) {
  return (
    <div className="text-center">
      <div className={cn('text-lg font-bold', color || 'text-white')}>{value}</div>
      <div className="text-xs text-gray-500 mt-1">{label}</div>
    </div>
  );
}

function PlayerStatusCard({ player, currentRound }: { player: ReplayPlayer; currentRound: number }) {
  const roleInfo = ROLE_INFO[player.role];
  const isDead = player.died_round !== undefined && currentRound >= (player.died_round || 999);
  const diedThisRound = player.died_round === currentRound;

  return (
    <div
      className={cn(
        'rounded-xl border p-3 text-center transition-all',
        isDead
          ? 'bg-gray-800/30 border-gray-700/30 opacity-50'
          : 'bg-wolf-bg border-wolf-border',
        diedThisRound && 'border-red-500/50 animate-pulse'
      )}
    >
      <div
        className="w-10 h-10 rounded-full flex items-center justify-center text-lg mx-auto mb-2"
        style={{ backgroundColor: `${roleInfo.color}20` }}
      >
        {isDead ? '💀' : '👤'}
      </div>
      <div className="text-sm font-medium text-white truncate">{player.player_name}</div>
      <span
        className="inline-block text-xs px-1.5 py-0.5 rounded mt-1"
        style={{ backgroundColor: `${roleInfo.color}20`, color: roleInfo.color }}
      >
        {roleInfo.name}
      </span>
      {player.died_round && (
        <div className="text-xs text-gray-500 mt-1">
          第{player.died_round}回合 {player.cause_of_death ? `· ${player.cause_of_death}` : ''}
        </div>
      )}
    </div>
  );
}

function TurningPointCard({ turningPoint }: { turningPoint: TurningPoint }) {
  const impactColors = {
    high: 'border-red-500/50 bg-red-500/10',
    medium: 'border-yellow-500/50 bg-yellow-500/10',
    low: 'border-blue-500/50 bg-blue-500/10',
  };

  const impactLabels = {
    high: '高',
    medium: '中',
    low: '低',
  };

  const phaseName = PHASE_INFO[turningPoint.phase]?.name || turningPoint.phase;

  return (
    <div className={cn('rounded-xl border p-4', impactColors[turningPoint.impact])}>
      <div className="flex items-center justify-between mb-2">
        <span className="text-xs text-gray-400">{phaseName}</span>
        <span
          className={cn(
            'text-xs px-2 py-0.5 rounded font-medium',
            turningPoint.impact === 'high' && 'bg-red-500/20 text-red-400',
            turningPoint.impact === 'medium' && 'bg-yellow-500/20 text-yellow-400',
            turningPoint.impact === 'low' && 'bg-blue-500/20 text-blue-400'
          )}
        >
          影响: {impactLabels[turningPoint.impact]}
        </span>
      </div>
      <p className="text-sm text-white">{turningPoint.description}</p>
      {turningPoint.involved_players.length > 0 && (
        <div className="flex flex-wrap gap-1 mt-2">
          {turningPoint.involved_players.map((player, idx) => (
            <span key={idx} className="text-xs bg-wolf-bg px-2 py-0.5 rounded text-gray-400">
              {player}
            </span>
          ))}
        </div>
      )}
    </div>
  );
}

function EventCard({ event }: { event: ReplayEvent }) {
  const typeConfig: Record<string, { icon: string; color: string; label: string }> = {
    kill: { icon: '🗡️', color: '#dc2626', label: '击杀' },
    guard: { icon: '🛡️', color: '#eab308', label: '守护' },
    check: { icon: '🔮', color: '#7c3aed', label: '查验' },
    witch_action: { icon: '🧙‍♀️', color: '#16a34a', label: '女巫' },
    vote: { icon: '🗳️', color: '#3b82f6', label: '投票' },
    death: { icon: '💀', color: '#6b7280', label: '死亡' },
    speech: { icon: '🗣️', color: '#9ca3af', label: '发言' },
    game_end: { icon: '🏁', color: '#f59e0b', label: '结束' },
    hunter_shoot: { icon: '🔫', color: '#ea580c', label: '开枪' },
  };

  const config = typeConfig[event.type] || { icon: '📌', color: '#9ca3af', label: '事件' };
  const phaseName = PHASE_INFO[event.phase]?.name || event.phase;

  return (
    <div className="flex items-start space-x-3 p-3 rounded-lg bg-wolf-bg hover:bg-white/5 transition-colors">
      <div
        className="w-8 h-8 rounded-full flex items-center justify-center text-sm flex-shrink-0"
        style={{ backgroundColor: `${config.color}20` }}
      >
        {config.icon}
      </div>
      <div className="flex-1 min-w-0">
        <div className="flex items-center justify-between">
          <span className="text-xs text-gray-500">{phaseName}</span>
          <span
            className="text-xs px-1.5 py-0.5 rounded"
            style={{ backgroundColor: `${config.color}20`, color: config.color }}
          >
            {config.label}
          </span>
        </div>
        <p className="text-sm text-white mt-1">{event.description}</p>
        {event.player_name && (
          <div className="text-xs text-gray-400 mt-1">
            玩家: <span className="text-gray-300">{event.player_name}</span>
            {event.target_name && (
              <>
                {' → '}
                <span className="text-gray-300">{event.target_name}</span>
              </>
            )}
          </div>
        )}
        {event.result && (
          <div className="text-xs text-gray-500 mt-1">结果: {event.result}</div>
        )}
      </div>
    </div>
  );
}

function AttributionCard({ attribution }: { attribution: { player_id: string; player_name: string; role: string; contribution_score: number; impact_description: string; key_actions: string[] } }) {
  const roleInfo = ROLE_INFO[attribution.role as keyof typeof ROLE_INFO];

  return (
    <div className="bg-wolf-bg rounded-xl border border-wolf-border p-4">
      <div className="flex items-center justify-between mb-3">
        <div className="flex items-center space-x-2">
          <span
            className="w-8 h-8 rounded-full flex items-center justify-center text-sm"
            style={{ backgroundColor: `${roleInfo?.color || '#6b7280'}20` }}
          >
            {roleInfo?.name?.[0] || '?'}
          </span>
          <div>
            <Link
              to={`/player/${attribution.player_id}`}
              className="text-sm font-medium text-white hover:text-purple-400 transition-colors"
            >
              {attribution.player_name}
            </Link>
            <span
              className="text-xs ml-2 px-1.5 py-0.5 rounded"
              style={{
                backgroundColor: `${roleInfo?.color || '#6b7280'}20`,
                color: roleInfo?.color || '#6b7280',
              }}
            >
              {roleInfo?.name || attribution.role}
            </span>
          </div>
        </div>
        <div className="text-right">
          <div className="text-lg font-bold text-purple-400">{attribution.contribution_score.toFixed(1)}</div>
          <div className="text-xs text-gray-500">贡献分</div>
        </div>
      </div>
      <p className="text-sm text-gray-400 mb-2">{attribution.impact_description}</p>
      {attribution.key_actions.length > 0 && (
        <div className="flex flex-wrap gap-1">
          {attribution.key_actions.map((action, idx) => (
            <span key={idx} className="text-xs bg-purple-500/10 text-purple-400 px-2 py-0.5 rounded">
              {action}
            </span>
          ))}
        </div>
      )}
    </div>
  );
}
