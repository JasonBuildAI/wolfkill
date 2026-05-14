import { useMemo } from 'react';
import { clsx, type ClassValue } from 'clsx';
import { twMerge } from 'tailwind-merge';
import { PlayerCard } from './PlayerCard';
import { Phase, PHASE_INFO, Team, type Player, type GameState } from '@/types/game';

function cn(...inputs: ClassValue[]) {
  return twMerge(clsx(inputs));
}

interface GameBoardProps {
  gameState: GameState;
  currentPlayerId?: string | null;
  showAllRoles?: boolean;
  selectedPlayerId?: string | null;
  onPlayerClick?: (playerId: string) => void;
  selectablePlayerIds?: string[];
}

export function GameBoard({
  gameState,
  currentPlayerId,
  showAllRoles = false,
  selectedPlayerId,
  onPlayerClick,
  selectablePlayerIds,
}: GameBoardProps) {
  const { players, phase, round, current_speaker, votes, alive_players } = gameState;
  const phaseInfo = PHASE_INFO[phase];

  // 计算投票映射（被投票的玩家 -> 投票者列表）
  const voteMap = useMemo(() => {
    const map: Record<string, string[]> = {};
    Object.entries(votes || {}).forEach(([voterId, targetId]) => {
      if (!map[targetId]) {
        map[targetId] = [];
      }
      map[targetId].push(voterId);
    });
    return map;
  }, [votes]);

  // 将玩家分成两排显示（半圆形布局）
  const topRow = players.slice(0, 6);
  const bottomRow = players.slice(6, 12);

  // 判断是否为夜晚阶段
  const isNight = phaseInfo.is_night;

  return (
    <div
      className={cn(
        'relative rounded-2xl p-6 transition-all duration-1000',
        isNight
          ? 'bg-gradient-to-b from-indigo-950/50 to-purple-950/30'
          : 'bg-gradient-to-b from-amber-950/20 to-orange-950/10'
      )}
    >
      {/* 背景效果 */}
      <div className="absolute inset-0 overflow-hidden rounded-2xl">
        {isNight ? (
          <>
            <div className="absolute top-10 left-10 w-32 h-32 bg-purple-600/10 rounded-full blur-3xl" />
            <div className="absolute bottom-10 right-10 w-40 h-40 bg-indigo-600/10 rounded-full blur-3xl" />
            <div className="absolute top-1/2 left-1/2 -translate-x-1/2 -translate-y-1/2 w-96 h-96 bg-blue-900/5 rounded-full blur-3xl" />
          </>
        ) : (
          <>
            <div className="absolute top-0 left-1/4 w-64 h-64 bg-amber-600/5 rounded-full blur-3xl" />
            <div className="absolute top-0 right-1/4 w-48 h-48 bg-orange-600/5 rounded-full blur-3xl" />
          </>
        )}
      </div>

      {/* 游戏信息栏 */}
      <div className="relative flex items-center justify-between mb-8">
        <div className="flex items-center space-x-4">
          {/* 回合数 */}
          <div className="flex items-center space-x-2 bg-wolf-card/80 px-4 py-2 rounded-lg border border-wolf-border">
            <span className="text-gray-400">回合</span>
            <span className="text-2xl font-bold text-purple-400">{round}</span>
          </div>

          {/* 阶段信息 */}
          <div
            className={cn(
              'flex items-center space-x-2 px-4 py-2 rounded-lg border',
              isNight
                ? 'bg-indigo-950/50 border-indigo-500/30'
                : 'bg-amber-950/30 border-amber-500/30'
            )}
          >
            <span className="text-xl">{isNight ? '🌙' : '☀️'}</span>
            <div>
              <div className={cn('font-medium', isNight ? 'text-indigo-300' : 'text-amber-300')}>
                {phaseInfo.name}
              </div>
              <div className="text-xs text-gray-500">{phaseInfo.description}</div>
            </div>
          </div>
        </div>

        {/* 存活统计 */}
        <div className="flex items-center space-x-4">
          <div className="flex items-center space-x-2 bg-wolf-card/80 px-3 py-2 rounded-lg">
            <span className="text-green-400">好人</span>
            <span className="font-bold">
              {players.filter((p) => p.team === Team.GOOD && p.alive).length}
            </span>
          </div>
          <div className="flex items-center space-x-2 bg-wolf-card/80 px-3 py-2 rounded-lg">
            <span className="text-red-400">狼人</span>
            <span className="font-bold">
              {players.filter((p) => p.team === Team.EVIL && p.alive).length}
            </span>
          </div>
          <div className="flex items-center space-x-2 bg-wolf-card/80 px-3 py-2 rounded-lg">
            <span className="text-gray-400">存活</span>
            <span className="font-bold text-white">{alive_players.length}</span>
            <span className="text-gray-600">/</span>
            <span className="text-gray-500">{players.length}</span>
          </div>
        </div>
      </div>

      {/* 玩家布局 - 半圆形 */}
      <div className="relative">
        {/* 上排玩家 */}
        <div className="flex justify-center items-end space-x-4 mb-8">
          {topRow.map((player, index) => (
            <div
              key={player.id}
              style={{
                transform: `translateY(${Math.abs(index - 2.5) * 8}px)`,
              }}
            >
              <PlayerCard
                player={player}
                isCurrentPlayer={player.id === currentPlayerId}
                isCurrentSpeaker={player.id === current_speaker}
                isSelected={player.id === selectedPlayerId}
                isVotedBy={voteMap[player.id] || []}
                showRole={showAllRoles || player.id === currentPlayerId}
                onClick={() => onPlayerClick?.(player.id)}
                disabled={
                  !player.alive ||
                  (selectablePlayerIds !== undefined &&
                    !selectablePlayerIds.includes(player.id))
                }
                size="md"
              />
            </div>
          ))}
        </div>

        {/* 中央区域 - 可以放置阶段提示或动画 */}
        <div className="flex justify-center items-center py-4">
          {phase === Phase.GAME_OVER && gameState.winner && (
            <div
              className={cn(
                'px-8 py-4 rounded-2xl text-3xl font-bold animate-fade-in',
                gameState.winner === Team.GOOD
                  ? 'bg-blue-600/20 text-blue-400 border-2 border-blue-500/50'
                  : 'bg-red-600/20 text-red-400 border-2 border-red-500/50'
              )}
            >
              {gameState.winner === Team.GOOD ? '🎉 好人阵营获胜！' : '🐺 狼人阵营获胜！'}
            </div>
          )}
        </div>

        {/* 下排玩家 */}
        <div className="flex justify-center items-start space-x-4">
          {bottomRow.map((player, index) => (
            <div
              key={player.id}
              style={{
                transform: `translateY(${Math.abs(index - 2.5) * -8}px)`,
              }}
            >
              <PlayerCard
                player={player}
                isCurrentPlayer={player.id === currentPlayerId}
                isCurrentSpeaker={player.id === current_speaker}
                isSelected={player.id === selectedPlayerId}
                isVotedBy={voteMap[player.id] || []}
                showRole={showAllRoles || player.id === currentPlayerId}
                onClick={() => onPlayerClick?.(player.id)}
                disabled={
                  !player.alive ||
                  (selectablePlayerIds !== undefined &&
                    !selectablePlayerIds.includes(player.id))
                }
                size="md"
              />
            </div>
          ))}
        </div>
      </div>

      {/* 底部状态栏 */}
      <div className="relative mt-8 flex items-center justify-center space-x-6 text-sm text-gray-500">
        <div className="flex items-center space-x-2">
          <div className="w-3 h-3 rounded-full bg-green-500"></div>
          <span>存活</span>
        </div>
        <div className="flex items-center space-x-2">
          <div className="w-3 h-3 rounded-full bg-gray-600"></div>
          <span>死亡</span>
        </div>
        <div className="flex items-center space-x-2">
          <div className="w-3 h-3 rounded-full bg-yellow-500 animate-pulse"></div>
          <span>发言中</span>
        </div>
        {showAllRoles && (
          <>
            <div className="flex items-center space-x-2">
              <div className="w-3 h-3 rounded-full bg-blue-500"></div>
              <span>好人</span>
            </div>
            <div className="flex items-center space-x-2">
              <div className="w-3 h-3 rounded-full bg-red-500"></div>
              <span>狼人</span>
            </div>
          </>
        )}
      </div>
    </div>
  );
}
