import { clsx, type ClassValue } from 'clsx';
import { twMerge } from 'tailwind-merge';
import { Team, Role, ROLE_INFO, type GameState } from '@/types/game';

function cn(...inputs: ClassValue[]) {
  return twMerge(clsx(inputs));
}

interface GameOverProps {
  gameState: GameState;
  currentPlayerId?: string | null;
  onBackToHome?: () => void;
  onSpectate?: () => void;
}

export function GameOver({
  gameState,
  currentPlayerId,
  onBackToHome,
  onSpectate,
}: GameOverProps) {
  const { winner, players, round } = gameState;
  const isGoodWin = winner === Team.GOOD;
  const currentPlayer = players.find((p) => p.id === currentPlayerId);
  const isWinner = currentPlayer && currentPlayer.team === winner;

  // 统计数据
  const stats = {
    totalRounds: round,
    aliveGood: players.filter((p) => p.team === Team.GOOD && p.alive).length,
    aliveEvil: players.filter((p) => p.team === Team.EVIL && p.alive).length,
    totalDeaths: players.filter((p) => !p.alive).length,
  };

  // 角色分布
  const roleDistribution = {
    werewolves: players.filter((p) => p.role === Role.WEREWOLF),
    specialGood: players.filter(
      (p) => p.team === Team.GOOD && p.role !== Role.VILLAGER
    ),
    villagers: players.filter((p) => p.role === Role.VILLAGER),
  };

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-black/90 backdrop-blur-md">
      <div className="max-w-4xl w-full max-h-[90vh] overflow-y-auto">
        {/* 胜利标题 */}
        <div
          className={cn(
            'text-center mb-8 p-8 rounded-2xl border-2 animate-fade-in',
            isGoodWin
              ? 'bg-blue-950/30 border-blue-500/50'
              : 'bg-red-950/30 border-red-500/50'
          )}
        >
          <div className="text-6xl mb-4">{isGoodWin ? '🎉' : '🐺'}</div>
          <h1
            className={cn(
              'text-4xl md:text-5xl font-bold mb-4',
              isGoodWin ? 'text-blue-400' : 'text-red-400'
            )}
          >
            {isGoodWin ? '好人阵营获胜！' : '狼人阵营获胜！'}
          </h1>
          <p className="text-gray-400 text-lg">
            {isGoodWin
              ? '所有狼人已被找出，村庄恢复了和平'
              : '狼人控制了村庄，黑暗降临'}
          </p>

          {currentPlayer && (
            <div
              className={cn(
                'mt-6 inline-flex items-center space-x-2 px-6 py-3 rounded-full',
                isWinner
                  ? 'bg-green-500/20 text-green-400'
                  : 'bg-gray-700/50 text-gray-400'
              )}
            >
              <span>{isWinner ? '🏆' : '😔'}</span>
              <span className="font-medium">
                {isWinner ? '你获得了胜利！' : '你未能获胜'}
              </span>
            </div>
          )}
        </div>

        {/* 统计卡片 */}
        <div className="grid grid-cols-2 md:grid-cols-4 gap-4 mb-8">
          <StatCard
            label="游戏回合"
            value={stats.totalRounds}
            icon="🔄"
            color="purple"
          />
          <StatCard
            label="存活好人"
            value={stats.aliveGood}
            icon="😇"
            color="blue"
          />
          <StatCard
            label="存活狼人"
            value={stats.aliveEvil}
            icon="🐺"
            color="red"
          />
          <StatCard
            label="死亡人数"
            value={stats.totalDeaths}
            icon="💀"
            color="gray"
          />
        </div>

        {/* 角色分布 */}
        <div className="bg-wolf-card rounded-xl border border-wolf-border p-6 mb-8">
          <h2 className="text-xl font-bold text-white mb-6 flex items-center">
            <span className="mr-2">👥</span>
            角色分布
          </h2>

          <div className="space-y-6">
            {/* 狼人 */}
            <RoleGroup
              title="狼人阵营"
              icon="🐺"
              color="red"
              players={roleDistribution.werewolves}
            />

            {/* 神职 */}
            <RoleGroup
              title="神职人员"
              icon="✨"
              color="purple"
              players={roleDistribution.specialGood}
            />

            {/* 平民 */}
            <RoleGroup
              title="平民"
              icon="👨‍🌾"
              color="gray"
              players={roleDistribution.villagers}
            />
          </div>
        </div>

        {/* 玩家详情 */}
        <div className="bg-wolf-card rounded-xl border border-wolf-border p-6 mb-8">
          <h2 className="text-xl font-bold text-white mb-6 flex items-center">
            <span className="mr-2">📊</span>
            玩家详情
          </h2>

          <div className="grid grid-cols-2 md:grid-cols-3 lg:grid-cols-4 gap-4">
            {players.map((player) => {
              const roleInfo = ROLE_INFO[player.role];
              return (
                <div
                  key={player.id}
                  className={cn(
                    'p-4 rounded-lg border transition-all',
                    player.alive
                      ? 'bg-wolf-bg border-wolf-border'
                      : 'bg-gray-800/50 border-gray-700 opacity-60'
                  )}
                >
                  <div className="flex items-center space-x-3">
                    <div
                      className="w-10 h-10 rounded-full flex items-center justify-center text-lg"
                      style={{
                        background: `linear-gradient(135deg, ${roleInfo.color}30, ${roleInfo.color}10)`,
                      }}
                    >
                      {getRoleEmoji(player.role)}
                    </div>
                    <div className="flex-1 min-w-0">
                      <div className="font-medium text-gray-200 truncate">
                        {player.display_name}
                      </div>
                      <div
                        className="text-xs"
                        style={{ color: roleInfo.color }}
                      >
                        {roleInfo.name}
                      </div>
                    </div>
                  </div>
                  <div className="mt-2 flex items-center justify-between text-xs">
                    <span
                      className={cn(
                        'px-2 py-0.5 rounded',
                        player.team === Team.GOOD
                          ? 'bg-blue-500/20 text-blue-400'
                          : 'bg-red-500/20 text-red-400'
                      )}
                    >
                      {player.team === Team.GOOD ? '好人' : '狼人'}
                    </span>
                    <span
                      className={cn(
                        player.alive ? 'text-green-400' : 'text-gray-500'
                      )}
                    >
                      {player.alive ? '存活' : '死亡'}
                    </span>
                  </div>
                </div>
              );
            })}
          </div>
        </div>

        {/* 操作按钮 */}
        <div className="flex flex-col sm:flex-row gap-4 justify-center">
          {onSpectate && (
            <button
              onClick={onSpectate}
              className="px-8 py-4 rounded-xl font-medium bg-purple-600 text-white hover:bg-purple-700 transition-all flex items-center justify-center space-x-2"
            >
              <span>👁️</span>
              <span>继续观看</span>
            </button>
          )}
          {onBackToHome && (
            <button
              onClick={onBackToHome}
              className="px-8 py-4 rounded-xl font-medium bg-gray-700 text-gray-200 hover:bg-gray-600 transition-all flex items-center justify-center space-x-2"
            >
              <span>🏠</span>
              <span>返回首页</span>
            </button>
          )}
        </div>
      </div>
    </div>
  );
}

// 统计卡片组件
function StatCard({
  label,
  value,
  icon,
  color,
}: {
  label: string;
  value: number;
  icon: string;
  color: 'purple' | 'blue' | 'red' | 'gray';
}) {
  const colorClasses = {
    purple: 'bg-purple-500/20 text-purple-400',
    blue: 'bg-blue-500/20 text-blue-400',
    red: 'bg-red-500/20 text-red-400',
    gray: 'bg-gray-500/20 text-gray-400',
  };

  return (
    <div className="bg-wolf-card rounded-xl border border-wolf-border p-4 text-center">
      <div
        className={cn(
          'w-12 h-12 rounded-full flex items-center justify-center text-2xl mx-auto mb-2',
          colorClasses[color]
        )}
      >
        {icon}
      </div>
      <div className="text-2xl font-bold text-white">{value}</div>
      <div className="text-sm text-gray-500">{label}</div>
    </div>
  );
}

// 角色组组件
function RoleGroup({
  title,
  icon,
  color,
  players,
}: {
  title: string;
  icon: string;
  color: 'red' | 'purple' | 'gray';
  players: { id: string; display_name: string; role: Role; alive: boolean }[];
}) {
  const colorClasses = {
    red: 'border-red-500/30 bg-red-950/10',
    purple: 'border-purple-500/30 bg-purple-950/10',
    gray: 'border-gray-500/30 bg-gray-950/10',
  };

  if (players.length === 0) return null;

  return (
    <div className={cn('p-4 rounded-lg border', colorClasses[color])}>
      <h3 className="font-medium text-gray-300 mb-3 flex items-center">
        <span className="mr-2">{icon}</span>
        {title}
        <span className="ml-2 text-sm text-gray-500">({players.length})</span>
      </h3>
      <div className="flex flex-wrap gap-2">
        {players.map((player) => {
          const roleInfo = ROLE_INFO[player.role];
          return (
            <div
              key={player.id}
              className={cn(
                'flex items-center space-x-2 px-3 py-1.5 rounded-full text-sm',
                player.alive
                  ? 'bg-wolf-bg'
                  : 'bg-gray-800/50 opacity-50 line-through'
              )}
            >
              <span>{getRoleEmoji(player.role)}</span>
              <span className="text-gray-300">{player.display_name}</span>
              <span style={{ color: roleInfo.color }}>{roleInfo.name}</span>
            </div>
          );
        })}
      </div>
    </div>
  );
}

function getRoleEmoji(role: Role): string {
  const emojiMap: Record<Role, string> = {
    [Role.WEREWOLF]: '🐺',
    [Role.SEER]: '🔮',
    [Role.WITCH]: '🧙‍♀️',
    [Role.HUNTER]: '🔫',
    [Role.GUARD]: '🛡️',
    [Role.VILLAGER]: '👨‍🌾',
  };
  return emojiMap[role];
}
