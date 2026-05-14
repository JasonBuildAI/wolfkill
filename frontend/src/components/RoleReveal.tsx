import { useState, useEffect } from 'react';
import { clsx, type ClassValue } from 'clsx';
import { twMerge } from 'tailwind-merge';
import { Role, ROLE_INFO, Team } from '@/types/game';

function cn(...inputs: ClassValue[]) {
  return twMerge(clsx(inputs));
}

interface RoleRevealProps {
  role: Role;
  isOpen: boolean;
  onClose: () => void;
}

export function RoleReveal({ role, isOpen, onClose }: RoleRevealProps) {
  const [showRole, setShowRole] = useState(false);
  const [isAnimating, setIsAnimating] = useState(false);
  const roleInfo = ROLE_INFO[role];
  const isWerewolf = roleInfo.team === Team.EVIL;

  useEffect(() => {
    if (isOpen) {
      setShowRole(false);
      setIsAnimating(true);
      // 延迟显示角色，增加悬念
      const timer = setTimeout(() => {
        setShowRole(true);
      }, 1500);
      return () => clearTimeout(timer);
    }
  }, [isOpen]);

  if (!isOpen) return null;

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-black/80 backdrop-blur-sm">
      <div
        className={cn(
          'relative max-w-md w-full rounded-2xl overflow-hidden transition-all duration-700',
          isAnimating ? 'scale-100 opacity-100' : 'scale-95 opacity-0'
        )}
      >
        {/* 背景效果 */}
        <div
          className={cn(
            'absolute inset-0 transition-opacity duration-1000',
            showRole ? 'opacity-100' : 'opacity-0'
          )}
          style={{
            background: `radial-gradient(circle at center, ${roleInfo.color}40 0%, transparent 70%)`,
          }}
        />

        {/* 卡片内容 */}
        <div className="relative bg-wolf-card border border-wolf-border rounded-2xl p-8 text-center">
          {/* 标题 */}
          <h2 className="text-2xl font-bold text-white mb-8">
            {showRole ? '你的身份是' : '身份即将揭晓...'}
          </h2>

          {/* 角色卡片 */}
          <div
            className={cn(
              'relative mx-auto w-48 h-64 rounded-xl transition-all duration-700 transform',
              showRole ? 'rotate-y-0' : 'rotate-y-180'
            )}
            style={{
              transformStyle: 'preserve-3d',
            }}
          >
            {/* 背面（牌面） */}
            <div
              className={cn(
                'absolute inset-0 rounded-xl border-2 flex items-center justify-center backface-hidden transition-opacity duration-500',
                showRole ? 'opacity-0' : 'opacity-100'
              )}
              style={{
                background: 'linear-gradient(135deg, #1a1f2e 0%, #2d3548 100%)',
                borderColor: '#4a5568',
                backfaceVisibility: 'hidden',
              }}
            >
              <div className="text-6xl animate-pulse">🎴</div>
            </div>

            {/* 正面（角色） */}
            <div
              className={cn(
                'absolute inset-0 rounded-xl border-2 flex flex-col items-center justify-center p-4 transition-opacity duration-500',
                showRole ? 'opacity-100' : 'opacity-0'
              )}
              style={{
                background: `linear-gradient(135deg, ${roleInfo.color}20 0%, ${roleInfo.color}05 100%)`,
                borderColor: roleInfo.color,
                backfaceVisibility: 'hidden',
                transform: 'rotateY(180deg)',
              }}
            >
              <div className="text-6xl mb-4">{getRoleEmoji(role)}</div>
              <div
                className="text-2xl font-bold mb-2"
                style={{ color: roleInfo.color }}
              >
                {roleInfo.name}
              </div>
              <div
                className={cn(
                  'px-3 py-1 rounded-full text-sm font-medium',
                  isWerewolf
                    ? 'bg-red-500/20 text-red-400'
                    : 'bg-blue-500/20 text-blue-400'
                )}
              >
                {isWerewolf ? '狼人阵营' : '好人阵营'}
              </div>
            </div>
          </div>

          {/* 角色描述 */}
          {showRole && (
            <div className="mt-8 animate-fade-in">
              <p className="text-gray-400 mb-6">{roleInfo.description}</p>
              <button
                onClick={onClose}
                className={cn(
                  'px-8 py-3 rounded-lg font-medium text-white transition-all hover:scale-105',
                  isWerewolf
                    ? 'bg-gradient-to-r from-red-600 to-red-700 hover:from-red-700 hover:to-red-800'
                    : 'bg-gradient-to-r from-blue-600 to-blue-700 hover:from-blue-700 hover:to-blue-800'
                )}
              >
                开始游戏
              </button>
            </div>
          )}

          {/* 等待提示 */}
          {!showRole && (
            <div className="mt-8">
              <div className="flex items-center justify-center space-x-2">
                <div className="w-3 h-3 bg-purple-500 rounded-full animate-bounce" style={{ animationDelay: '0ms' }} />
                <div className="w-3 h-3 bg-purple-500 rounded-full animate-bounce" style={{ animationDelay: '150ms' }} />
                <div className="w-3 h-3 bg-purple-500 rounded-full animate-bounce" style={{ animationDelay: '300ms' }} />
              </div>
            </div>
          )}
        </div>
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
