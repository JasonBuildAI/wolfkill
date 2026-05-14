import { useState } from 'react';
import { clsx, type ClassValue } from 'clsx';
import { twMerge } from 'tailwind-merge';
import {
  Phase,
  PHASE_INFO,
  Role,
  type GameState,
  type ActionRequest,
  type GameAction,
} from '@/types/game';

function cn(...inputs: ClassValue[]) {
  return twMerge(clsx(inputs));
}

interface PhasePanelProps {
  gameState: GameState;
  actionRequest: ActionRequest | null;
  currentPlayerId?: string | null;
  onAction: (action: GameAction) => void;
}

export function PhasePanel({
  gameState,
  actionRequest,
  currentPlayerId,
  onAction,
}: PhasePanelProps) {
  const { phase, players, witch_status } = gameState;
  const phaseInfo = PHASE_INFO[phase];
  const [selectedTarget, setSelectedTarget] = useState<string | null>(null);
  const [speechContent, setSpeechContent] = useState('');
  const [witchActions, setWitchActions] = useState({
    useAntidote: false,
    usePoison: false,
    poisonTarget: '',
  });

  const currentPlayer = players.find((p) => p.id === currentPlayerId);
  const isPlayerTurn = actionRequest?.player_id === currentPlayerId;

  // 获取可选目标（存活的其他玩家）
  const getAvailableTargets = () => {
    return players.filter(
      (p) => p.alive && p.id !== currentPlayerId
    );
  };

  // 处理守卫守护
  const handleGuardProtect = () => {
    if (selectedTarget) {
      onAction({ type: 'GUARD_PROTECT', target: selectedTarget });
      setSelectedTarget(null);
    }
  };

  // 处理狼人杀人
  const handleWerewolfKill = () => {
    if (selectedTarget) {
      onAction({ type: 'WEREWOLF_KILL', target: selectedTarget });
      setSelectedTarget(null);
    }
  };

  // 处理预言家查验
  const handleSeerCheck = () => {
    if (selectedTarget) {
      onAction({ type: 'SEER_CHECK', target: selectedTarget });
      setSelectedTarget(null);
    }
  };

  // 处理女巫行动
  const handleWitchAction = () => {
    onAction({
      type: 'WITCH_ACTION',
      use_antidote: witchActions.useAntidote,
      use_poison: witchActions.usePoison,
      poison_target: witchActions.usePoison ? witchActions.poisonTarget : undefined,
    });
    setWitchActions({ useAntidote: false, usePoison: false, poisonTarget: '' });
  };

  // 处理发言
  const handleSpeech = () => {
    if (speechContent.trim()) {
      onAction({ type: 'SPEECH', content: speechContent.trim() });
      setSpeechContent('');
    }
  };

  // 处理投票
  const handleVote = () => {
    if (selectedTarget) {
      onAction({ type: 'VOTE', target: selectedTarget });
      setSelectedTarget(null);
    }
  };

  // 处理结束发言
  const handleEndSpeech = () => {
    onAction({ type: 'END_SPEECH' });
  };

  // 如果不是当前玩家的回合，显示等待信息
  if (!isPlayerTurn) {
    return (
      <div className="bg-wolf-card rounded-xl p-6 border border-wolf-border">
        <div className="text-center">
          <div className="text-lg font-medium text-gray-300 mb-2">
            {phaseInfo.name}
          </div>
          <p className="text-gray-500">
            {phase === Phase.SETUP
              ? '等待游戏开始...'
              : phase === Phase.GAME_OVER
              ? '游戏已结束'
              : '等待其他玩家行动...'}
          </p>
          {actionRequest && (
            <div className="mt-4 text-sm text-purple-400">
              当前行动玩家: {players.find((p) => p.id === actionRequest.player_id)?.display_name}
            </div>
          )}
        </div>
      </div>
    );
  }

  // 渲染行动面板
  const renderActionPanel = () => {
    const availableTargets = getAvailableTargets();

    switch (phase) {
      case Phase.NIGHT_GUARD:
        if (currentPlayer?.role !== Role.GUARD) {
          return <WaitingMessage message="等待守卫行动..." />;
        }
        return (
          <ActionContainer
            title="🛡️ 选择守护目标"
            description="选择一名玩家进行守护（不能连续两晚守护同一人）"
          >
            <TargetSelector
              targets={availableTargets}
              selectedId={selectedTarget}
              onSelect={setSelectedTarget}
            />
            <ActionButton
              onClick={handleGuardProtect}
              disabled={!selectedTarget}
              label="确认守护"
            />
          </ActionContainer>
        );

      case Phase.NIGHT_WEREWOLF:
        if (currentPlayer?.role !== Role.WEREWOLF) {
          return <WaitingMessage message="等待狼人行动..." />;
        }
        return (
          <ActionContainer
            title="🐺 选择击杀目标"
            description="选择一名玩家进行击杀"
          >
            <TargetSelector
              targets={availableTargets}
              selectedId={selectedTarget}
              onSelect={setSelectedTarget}
            />
            <ActionButton
              onClick={handleWerewolfKill}
              disabled={!selectedTarget}
              label="确认击杀"
              variant="danger"
            />
          </ActionContainer>
        );

      case Phase.NIGHT_SEER:
        if (currentPlayer?.role !== Role.SEER) {
          return <WaitingMessage message="等待预言家行动..." />;
        }
        return (
          <ActionContainer
            title="🔮 选择查验目标"
            description="选择一名玩家查验其身份"
          >
            <TargetSelector
              targets={availableTargets}
              selectedId={selectedTarget}
              onSelect={setSelectedTarget}
            />
            <ActionButton
              onClick={handleSeerCheck}
              disabled={!selectedTarget}
              label="确认查验"
              variant="info"
            />
          </ActionContainer>
        );

      case Phase.NIGHT_WITCH:
        if (currentPlayer?.role !== Role.WITCH) {
          return <WaitingMessage message="等待女巫行动..." />;
        }
        return (
          <ActionContainer
            title="🧙‍♀️ 女巫行动"
            description="决定是否使用解药或毒药"
          >
            <div className="space-y-4">
              {/* 解药 */}
              {!witch_status.antidote_used && (
                <label className="flex items-center space-x-3 cursor-pointer">
                  <input
                    type="checkbox"
                    checked={witchActions.useAntidote}
                    onChange={(e) =>
                      setWitchActions((prev) => ({
                        ...prev,
                        useAntidote: e.target.checked,
                      }))
                    }
                    className="w-5 h-5 rounded border-gray-600 text-green-500 focus:ring-green-500"
                  />
                  <span className="text-green-400">使用解药救人</span>
                </label>
              )}

              {/* 毒药 */}
              {!witch_status.poison_used && (
                <div className="space-y-2">
                  <label className="flex items-center space-x-3 cursor-pointer">
                    <input
                      type="checkbox"
                      checked={witchActions.usePoison}
                      onChange={(e) =>
                        setWitchActions((prev) => ({
                          ...prev,
                          usePoison: e.target.checked,
                          poisonTarget: e.target.checked ? prev.poisonTarget : '',
                        }))
                      }
                      className="w-5 h-5 rounded border-gray-600 text-red-500 focus:ring-red-500"
                    />
                    <span className="text-red-400">使用毒药杀人</span>
                  </label>
                  {witchActions.usePoison && (
                    <TargetSelector
                      targets={availableTargets}
                      selectedId={witchActions.poisonTarget}
                      onSelect={(id) =>
                        setWitchActions((prev) => ({ ...prev, poisonTarget: id }))
                      }
                      compact
                    />
                  )}
                </div>
              )}
            </div>
            <ActionButton
              onClick={handleWitchAction}
              disabled={
                witchActions.usePoison && !witchActions.poisonTarget
              }
              label="确认行动"
              variant="magic"
            />
          </ActionContainer>
        );

      case Phase.DAY_SPEECH:
        return (
          <ActionContainer
            title="🎤 发言阶段"
            description="发表你的看法和推理"
          >
            <textarea
              value={speechContent}
              onChange={(e) => setSpeechContent(e.target.value)}
              placeholder="输入你的发言..."
              className="w-full h-24 px-4 py-2 bg-wolf-bg border border-wolf-border rounded-lg text-gray-200 placeholder-gray-600 focus:outline-none focus:ring-2 focus:ring-purple-500 resize-none"
            />
            <div className="flex space-x-3">
              <ActionButton
                onClick={handleSpeech}
                disabled={!speechContent.trim()}
                label="发表发言"
              />
              <ActionButton
                onClick={handleEndSpeech}
                label="结束发言"
                variant="secondary"
              />
            </div>
          </ActionContainer>
        );

      case Phase.DAY_VOTE:
        return (
          <ActionContainer
            title="🗳️ 投票阶段"
            description="选择一名玩家进行放逐投票"
          >
            <TargetSelector
              targets={availableTargets}
              selectedId={selectedTarget}
              onSelect={setSelectedTarget}
            />
            <ActionButton
              onClick={handleVote}
              disabled={!selectedTarget}
              label="确认投票"
              variant="warning"
            />
          </ActionContainer>
        );

      default:
        return (
          <div className="text-center text-gray-500">
            当前阶段无需操作
          </div>
        );
    }
  };

  return (
    <div className="bg-wolf-card rounded-xl p-6 border border-wolf-border">
      {renderActionPanel()}
    </div>
  );
}

// 辅助组件

function ActionContainer({
  title,
  description,
  children,
}: {
  title: string;
  description: string;
  children: React.ReactNode;
}) {
  return (
    <div className="space-y-4">
      <div>
        <h3 className="text-lg font-medium text-white">{title}</h3>
        <p className="text-sm text-gray-500">{description}</p>
      </div>
      {children}
    </div>
  );
}

function WaitingMessage({ message }: { message: string }) {
  return (
    <div className="text-center py-4">
      <div className="animate-pulse text-gray-500">{message}</div>
    </div>
  );
}

function TargetSelector({
  targets,
  selectedId,
  onSelect,
  compact = false,
}: {
  targets: { id: string; display_name: string; alive: boolean }[];
  selectedId: string | null;
  onSelect: (id: string) => void;
  compact?: boolean;
}) {
  return (
    <div className={cn('grid gap-2', compact ? 'grid-cols-4' : 'grid-cols-3')}>
      {targets.map((target) => (
        <button
          key={target.id}
          onClick={() => onSelect(target.id)}
          className={cn(
            'px-3 py-2 rounded-lg text-sm font-medium transition-all',
            selectedId === target.id
              ? 'bg-purple-600 text-white'
              : 'bg-wolf-bg text-gray-400 hover:bg-wolf-border hover:text-gray-200'
          )}
        >
          {target.display_name}
        </button>
      ))}
    </div>
  );
}

function ActionButton({
  onClick,
  disabled,
  label,
  variant = 'primary',
}: {
  onClick: () => void;
  disabled?: boolean;
  label: string;
  variant?: 'primary' | 'secondary' | 'danger' | 'info' | 'warning' | 'magic';
}) {
  const variantClasses = {
    primary: 'bg-purple-600 hover:bg-purple-700 text-white',
    secondary: 'bg-gray-600 hover:bg-gray-700 text-white',
    danger: 'bg-red-600 hover:bg-red-700 text-white',
    info: 'bg-blue-600 hover:bg-blue-700 text-white',
    warning: 'bg-amber-600 hover:bg-amber-700 text-white',
    magic: 'bg-gradient-to-r from-purple-600 to-pink-600 hover:from-purple-700 hover:to-pink-700 text-white',
  };

  return (
    <button
      onClick={onClick}
      disabled={disabled}
      className={cn(
        'w-full py-3 rounded-lg font-medium transition-all',
        variantClasses[variant],
        disabled && 'opacity-50 cursor-not-allowed'
      )}
    >
      {label}
    </button>
  );
}
