import { clsx, type ClassValue } from 'clsx';
import { twMerge } from 'tailwind-merge';
import { Role, Team, ROLE_INFO, type Player } from '@/types/game';

function cn(...inputs: ClassValue[]) {
  return twMerge(clsx(inputs));
}

interface PlayerCardProps {
  player: Player;
  isCurrentPlayer?: boolean;
  isCurrentSpeaker?: boolean;
  isSelected?: boolean;
  isVotedBy?: string[];
  showRole?: boolean;
  onClick?: () => void;
  disabled?: boolean;
  size?: 'sm' | 'md' | 'lg';
}

export function PlayerCard({
  player,
  isCurrentPlayer = false,
  isCurrentSpeaker = false,
  isSelected = false,
  isVotedBy = [],
  showRole = false,
  onClick,
  disabled = false,
  size = 'md',
}: PlayerCardProps) {
  const roleInfo = ROLE_INFO[player.role];
  const isWerewolf = player.team === Team.EVIL;

  const sizeClasses = {
    sm: 'w-16 h-20',
    md: 'w-24 h-32',
    lg: 'w-32 h-40',
  };

  const avatarSizes = {
    sm: 'w-10 h-10',
    md: 'w-16 h-16',
    lg: 'w-20 h-20',
  };

  const nameSizes = {
    sm: 'text-xs',
    md: 'text-sm',
    lg: 'text-base',
  };

  return (
    <div
      className={cn(
        'relative flex flex-col items-center p-2 rounded-xl transition-all duration-300',
        sizeClasses[size],
        player.alive
          ? 'bg-wolf-card border-2'
          : 'bg-gray-800/50 border-2 border-gray-700 opacity-60',
        isCurrentPlayer && 'ring-2 ring-purple-500 ring-offset-2 ring-offset-wolf-bg',
        isCurrentSpeaker && 'animate-pulse-slow',
        isSelected && 'ring-2 ring-yellow-400',
        onClick && !disabled && 'cursor-pointer hover:scale-105 hover:shadow-lg',
        disabled && 'cursor-not-allowed',
        // 根据阵营设置边框颜色
        player.alive && (
          showRole
            ? isWerewolf
              ? 'border-red-500/50'
              : 'border-blue-500/50'
            : 'border-wolf-border'
        )
      )}
      style={{
        boxShadow: isCurrentSpeaker
          ? `0 0 20px ${roleInfo.color}40`
          : isSelected
          ? '0 0 15px rgba(250, 204, 21, 0.5)'
          : undefined,
      }}
      onClick={!disabled ? onClick : undefined}
    >
      {/* 死亡标记 */}
      {!player.alive && (
        <div className="absolute inset-0 flex items-center justify-center z-10">
          <span className="text-4xl opacity-50">💀</span>
        </div>
      )}

      {/* 发言指示器 */}
      {isCurrentSpeaker && (
        <div className="absolute -top-2 -right-2 w-6 h-6 bg-yellow-500 rounded-full flex items-center justify-center animate-bounce">
          <span className="text-xs">🎤</span>
        </div>
      )}

      {/* 当前玩家标记 */}
      {isCurrentPlayer && (
        <div className="absolute -top-2 -left-2 w-6 h-6 bg-purple-500 rounded-full flex items-center justify-center">
          <span className="text-xs">👤</span>
        </div>
      )}

      {/* 头像 */}
      <div
        className={cn(
          'relative rounded-full flex items-center justify-center mb-2',
          avatarSizes[size],
          player.alive ? 'bg-gradient-to-br' : 'bg-gray-700'
        )}
        style={{
          background: player.alive
            ? `linear-gradient(135deg, ${roleInfo.color}30, ${roleInfo.color}10)`
            : undefined,
        }}
      >
        {/* 角色图标 */}
        <span
          className={cn(
            'text-2xl',
            size === 'lg' && 'text-3xl',
            size === 'sm' && 'text-xl'
          )}
        >
          {getRoleEmoji(player.role)}
        </span>

        {/* 角色显示（仅当showRole为true） */}
        {showRole && player.alive && (
          <div
            className="absolute -bottom-1 -right-1 w-5 h-5 rounded-full flex items-center justify-center text-xs"
            style={{ backgroundColor: roleInfo.color }}
          >
            {getRoleIcon(player.role)}
          </div>
        )}
      </div>

      {/* 玩家名称 */}
      <span
        className={cn(
          'font-medium text-center truncate w-full',
          nameSizes[size],
          player.alive ? 'text-gray-200' : 'text-gray-500'
        )}
      >
        {player.display_name}
      </span>

      {/* 角色名称（仅当showRole为true） */}
      {showRole && (
        <span
          className={cn(
            'text-xs mt-1',
            player.alive ? 'opacity-80' : 'opacity-40'
          )}
          style={{ color: roleInfo.color }}
        >
          {roleInfo.name}
        </span>
      )}

      {/* 投票指示器 */}
      {isVotedBy.length > 0 && (
        <div className="absolute -bottom-3 flex -space-x-1">
          {isVotedBy.slice(0, 3).map((voterId, idx) => (
            <div
              key={voterId}
              className="w-5 h-5 rounded-full bg-red-500 flex items-center justify-center text-xs border border-wolf-bg"
              style={{ zIndex: 10 - idx }}
            >
              🗳️
            </div>
          ))}
          {isVotedBy.length > 3 && (
            <div className="w-5 h-5 rounded-full bg-gray-600 flex items-center justify-center text-xs border border-wolf-bg">
              +{isVotedBy.length - 3}
            </div>
          )}
        </div>
      )}

      {/* 选中标记 */}
      {isSelected && (
        <div className="absolute top-1 right-1 w-5 h-5 bg-yellow-500 rounded-full flex items-center justify-center">
          <svg className="w-3 h-3 text-black" fill="currentColor" viewBox="0 0 20 20">
            <path fillRule="evenodd" d="M16.707 5.293a1 1 0 010 1.414l-8 8a1 1 0 01-1.414 0l-4-4a1 1 0 011.414-1.414L8 12.586l7.293-7.293a1 1 0 011.414 0z" clipRule="evenodd" />
          </svg>
        </div>
      )}
    </div>
  );
}

// 获取角色表情
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

// 获取角色小图标
function getRoleIcon(role: Role): string {
  const iconMap: Record<Role, string> = {
    [Role.WEREWOLF]: '🐺',
    [Role.SEER]: '👁️',
    [Role.WITCH]: '⚗️',
    [Role.HUNTER]: '🔫',
    [Role.GUARD]: '🛡️',
    [Role.VILLAGER]: '🌾',
  };
  return iconMap[role];
}
