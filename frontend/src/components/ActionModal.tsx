import { useState } from 'react';
import { clsx, type ClassValue } from 'clsx';
import { twMerge } from 'tailwind-merge';
import {
  Role,
  PHASE_INFO,
  type GameState,
  type ActionRequest,
  type GameAction,
} from '@/types/game';

function cn(...inputs: ClassValue[]) {
  return twMerge(clsx(inputs));
}

interface ActionModalProps {
  isOpen: boolean;
  gameState: GameState;
  actionRequest: ActionRequest | null;
  onAction: (action: GameAction) => void;
  onCancel?: () => void;
}

export function ActionModal({
  isOpen,
  gameState,
  actionRequest,
  onAction,
  onCancel,
}: ActionModalProps) {
  const [selectedTarget, setSelectedTarget] = useState<string>('');
  const [speechContent, setSpeechContent] = useState('');
  const [witchChoice, setWitchChoice] = useState({
    useAntidote: false,
    usePoison: false,
    poisonTarget: '',
  });

  if (!isOpen || !actionRequest) return null;

  const { phase, players, witch_status } = gameState;
  const phaseInfo = PHASE_INFO[phase];

  // 获取存活玩家列表
  const alivePlayers = players.filter((p) => p.alive);

  // 处理动作提交
  const handleSubmit = () => {
    switch (phase) {
      case 'NIGHT_GUARD':
        if (selectedTarget) {
          onAction({ type: 'GUARD_PROTECT', target: selectedTarget });
        }
        break;
      case 'NIGHT_WEREWOLF':
        if (selectedTarget) {
          onAction({ type: 'WEREWOLF_KILL', target: selectedTarget });
        }
        break;
      case 'NIGHT_SEER':
        if (selectedTarget) {
          onAction({ type: 'SEER_CHECK', target: selectedTarget });
        }
        break;
      case 'NIGHT_WITCH':
        onAction({
          type: 'WITCH_ACTION',
          use_antidote: witchChoice.useAntidote,
          use_poison: witchChoice.usePoison,
          poison_target: witchChoice.usePoison ? witchChoice.poisonTarget : undefined,
        });
        break;
      case 'DAY_SPEECH':
        if (speechContent.trim()) {
          onAction({ type: 'SPEECH', content: speechContent.trim() });
        }
        break;
      case 'DAY_VOTE':
        if (selectedTarget) {
          onAction({ type: 'VOTE', target: selectedTarget });
        }
        break;
    }
  };

  // 渲染不同的动作表单
  const renderActionForm = () => {
    switch (phase) {
      case 'NIGHT_GUARD':
        return (
          <TargetSelection
            title="选择守护目标"
            description="选择一名玩家进行守护"
            players={alivePlayers}
            selected={selectedTarget}
            onSelect={setSelectedTarget}
          />
        );

      case 'NIGHT_WEREWOLF':
        return (
          <TargetSelection
            title="选择击杀目标"
            description="选择一名玩家进行击杀"
            players={alivePlayers}
            selected={selectedTarget}
            onSelect={setSelectedTarget}
          />
        );

      case 'NIGHT_SEER':
        return (
          <TargetSelection
            title="选择查验目标"
            description="选择一名玩家查验其身份"
            players={alivePlayers}
            selected={selectedTarget}
            onSelect={setSelectedTarget}
          />
        );

      case 'NIGHT_WITCH':
        return (
          <WitchActionForm
            witchStatus={witch_status}
            players={alivePlayers}
            choice={witchChoice}
            onChange={setWitchChoice}
          />
        );

      case 'DAY_SPEECH':
        return (
          <SpeechForm
            content={speechContent}
            onChange={setSpeechContent}
          />
        );

      case 'DAY_VOTE':
        return (
          <TargetSelection
            title="选择投票目标"
            description="选择一名玩家进行放逐投票"
            players={alivePlayers}
            selected={selectedTarget}
            onSelect={setSelectedTarget}
          />
        );

      default:
        return <div className="text-gray-400">当前阶段无需操作</div>;
    }
  };

  // 检查是否可以提交
  const canSubmit = () => {
    switch (phase) {
      case 'NIGHT_GUARD':
      case 'NIGHT_WEREWOLF':
      case 'NIGHT_SEER':
      case 'DAY_VOTE':
        return !!selectedTarget;
      case 'NIGHT_WITCH':
        return (
          witchChoice.useAntidote ||
          (witchChoice.usePoison && witchChoice.poisonTarget) ||
          (!witchChoice.useAntidote && !witchChoice.usePoison)
        );
      case 'DAY_SPEECH':
        return speechContent.trim().length > 0;
      default:
        return false;
    }
  };

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-black/70 backdrop-blur-sm">
      <div className="relative max-w-lg w-full bg-wolf-card rounded-2xl border border-wolf-border shadow-2xl">
        {/* 头部 */}
        <div className="px-6 py-4 border-b border-wolf-border">
          <div className="flex items-center justify-between">
            <div>
              <h3 className="text-xl font-bold text-white">
                {phaseInfo.name}
              </h3>
              <p className="text-sm text-gray-500">{phaseInfo.description}</p>
            </div>
            <div
              className={cn(
                'w-12 h-12 rounded-full flex items-center justify-center text-2xl',
                phaseInfo.is_night ? 'bg-indigo-500/20' : 'bg-amber-500/20'
              )}
            >
              {phaseInfo.is_night ? '🌙' : '☀️'}
            </div>
          </div>
        </div>

        {/* 内容 */}
        <div className="px-6 py-4">{renderActionForm()}</div>

        {/* 底部按钮 */}
        <div className="px-6 py-4 border-t border-wolf-border flex space-x-3">
          {onCancel && (
            <button
              onClick={onCancel}
              className="flex-1 px-4 py-3 rounded-lg font-medium bg-gray-700 text-gray-300 hover:bg-gray-600 transition-colors"
            >
              取消
            </button>
          )}
          <button
            onClick={handleSubmit}
            disabled={!canSubmit()}
            className={cn(
              'flex-1 px-4 py-3 rounded-lg font-medium transition-all',
              canSubmit()
                ? 'bg-purple-600 text-white hover:bg-purple-700'
                : 'bg-gray-700 text-gray-500 cursor-not-allowed'
            )}
          >
            确认
          </button>
        </div>
      </div>
    </div>
  );
}

// 目标选择组件
function TargetSelection({
  title,
  description,
  players,
  selected,
  onSelect,
}: {
  title: string;
  description: string;
  players: { id: string; display_name: string; role: Role }[];
  selected: string;
  onSelect: (id: string) => void;
}) {
  return (
    <div className="space-y-4">
      <div>
        <h4 className="font-medium text-white mb-1">{title}</h4>
        <p className="text-sm text-gray-500">{description}</p>
      </div>
      <div className="grid grid-cols-3 gap-2">
        {players.map((player) => (
          <button
            key={player.id}
            onClick={() => onSelect(player.id)}
            className={cn(
              'p-3 rounded-lg border text-sm font-medium transition-all',
              selected === player.id
                ? 'bg-purple-600 border-purple-500 text-white'
                : 'bg-wolf-bg border-wolf-border text-gray-400 hover:border-purple-500/50 hover:text-gray-200'
            )}
          >
            {player.display_name}
          </button>
        ))}
      </div>
    </div>
  );
}

// 女巫行动表单
function WitchActionForm({
  witchStatus,
  players,
  choice,
  onChange,
}: {
  witchStatus: { antidote_used: boolean; poison_used: boolean };
  players: { id: string; display_name: string }[];
  choice: {
    useAntidote: boolean;
    usePoison: boolean;
    poisonTarget: string;
  };
  onChange: (choice: {
    useAntidote: boolean;
    usePoison: boolean;
    poisonTarget: string;
  }) => void;
}) {
  return (
    <div className="space-y-4">
      <h4 className="font-medium text-white">女巫行动</h4>

      {/* 解药 */}
      {!witchStatus.antidote_used && (
        <label className="flex items-center space-x-3 p-3 rounded-lg bg-wolf-bg cursor-pointer hover:bg-wolf-border transition-colors">
          <input
            type="checkbox"
            checked={choice.useAntidote}
            onChange={(e) =>
              onChange({ ...choice, useAntidote: e.target.checked })
            }
            className="w-5 h-5 rounded border-gray-600 text-green-500 focus:ring-green-500"
          />
          <span className="text-green-400">使用解药救人</span>
        </label>
      )}

      {/* 毒药 */}
      {!witchStatus.poison_used && (
        <div className="space-y-2">
          <label className="flex items-center space-x-3 p-3 rounded-lg bg-wolf-bg cursor-pointer hover:bg-wolf-border transition-colors">
            <input
              type="checkbox"
              checked={choice.usePoison}
              onChange={(e) =>
                onChange({
                  ...choice,
                  usePoison: e.target.checked,
                  poisonTarget: e.target.checked ? choice.poisonTarget : '',
                })
              }
              className="w-5 h-5 rounded border-gray-600 text-red-500 focus:ring-red-500"
            />
            <span className="text-red-400">使用毒药杀人</span>
          </label>

          {choice.usePoison && (
            <div className="grid grid-cols-3 gap-2 pl-8">
              {players.map((player) => (
                <button
                  key={player.id}
                  onClick={() =>
                    onChange({ ...choice, poisonTarget: player.id })
                  }
                  className={cn(
                    'p-2 rounded-lg border text-sm font-medium transition-all',
                    choice.poisonTarget === player.id
                      ? 'bg-red-600 border-red-500 text-white'
                      : 'bg-wolf-bg border-wolf-border text-gray-400 hover:border-red-500/50'
                  )}
                >
                  {player.display_name}
                </button>
              ))}
            </div>
          )}
        </div>
      )}

      {/* 跳过 */}
      <label className="flex items-center space-x-3 p-3 rounded-lg bg-wolf-bg cursor-pointer hover:bg-wolf-border transition-colors">
        <input
          type="checkbox"
          checked={!choice.useAntidote && !choice.usePoison}
          onChange={() =>
            onChange({
              useAntidote: false,
              usePoison: false,
              poisonTarget: '',
            })
          }
          className="w-5 h-5 rounded border-gray-600 text-gray-500 focus:ring-gray-500"
        />
        <span className="text-gray-400">跳过本轮</span>
      </label>
    </div>
  );
}

// 发言表单
function SpeechForm({
  content,
  onChange,
}: {
  content: string;
  onChange: (content: string) => void;
}) {
  return (
    <div className="space-y-4">
      <div>
        <h4 className="font-medium text-white mb-1">发表你的看法</h4>
        <p className="text-sm text-gray-500">分享你的推理和怀疑</p>
      </div>
      <textarea
        value={content}
        onChange={(e) => onChange(e.target.value)}
        placeholder="输入你的发言..."
        rows={4}
        className="w-full px-4 py-3 bg-wolf-bg border border-wolf-border rounded-lg text-gray-200 placeholder-gray-600 focus:outline-none focus:ring-2 focus:ring-purple-500 resize-none"
      />
      <div className="text-right text-xs text-gray-500">
        {content.length} 字符
      </div>
    </div>
  );
}
