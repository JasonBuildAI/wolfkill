import { useState, useRef, useEffect } from 'react';
import { clsx, type ClassValue } from 'clsx';
import { twMerge } from 'tailwind-merge';
import { PHASE_INFO, type LogEntry, type Phase } from '@/types/game';

function cn(...inputs: ClassValue[]) {
  return twMerge(clsx(inputs));
}

interface ChatLogProps {
  logs: LogEntry[];
  maxHeight?: string;
  showFilters?: boolean;
}

export function ChatLog({ logs, maxHeight = '400px', showFilters = true }: ChatLogProps) {
  const [filter, setFilter] = useState<LogEntry['type'] | 'all'>('all');
  const scrollRef = useRef<HTMLDivElement>(null);

  // 自动滚动到底部
  useEffect(() => {
    if (scrollRef.current) {
      scrollRef.current.scrollTop = scrollRef.current.scrollHeight;
    }
  }, [logs]);

  const filteredLogs =
    filter === 'all' ? logs : logs.filter((log) => log.type === filter);

  const filterOptions: { value: LogEntry['type'] | 'all'; label: string; icon: string }[] = [
    { value: 'all', label: '全部', icon: '📋' },
    { value: 'system', label: '系统', icon: '⚙️' },
    { value: 'speech', label: '发言', icon: '🎤' },
    { value: 'action', label: '行动', icon: '⚡' },
    { value: 'death', label: '死亡', icon: '💀' },
    { value: 'vote', label: '投票', icon: '🗳️' },
    { value: 'result', label: '结果', icon: '📊' },
  ];

  const formatTime = (timestamp: string) => {
    const date = new Date(timestamp);
    return date.toLocaleTimeString('zh-CN', {
      hour: '2-digit',
      minute: '2-digit',
      second: '2-digit',
    });
  };

  return (
    <div className="bg-wolf-card rounded-xl border border-wolf-border flex flex-col">
      {/* 标题栏 */}
      <div className="px-4 py-3 border-b border-wolf-border flex items-center justify-between">
        <h3 className="font-medium text-gray-200 flex items-center">
          <span className="mr-2">📜</span>
          游戏日志
        </h3>
        <span className="text-xs text-gray-500">{filteredLogs.length} 条记录</span>
      </div>

      {/* 过滤器 */}
      {showFilters && (
        <div className="px-4 py-2 border-b border-wolf-border">
          <div className="flex flex-wrap gap-2">
            {filterOptions.map((option) => (
              <button
                key={option.value}
                onClick={() => setFilter(option.value)}
                className={cn(
                  'px-2 py-1 rounded text-xs font-medium transition-colors flex items-center space-x-1',
                  filter === option.value
                    ? 'bg-purple-600 text-white'
                    : 'bg-wolf-bg text-gray-400 hover:bg-wolf-border hover:text-gray-200'
                )}
              >
                <span>{option.icon}</span>
                <span>{option.label}</span>
              </button>
            ))}
          </div>
        </div>
      )}

      {/* 日志列表 */}
      <div
        ref={scrollRef}
        className="flex-1 overflow-y-auto p-4 space-y-2"
        style={{ maxHeight }}
      >
        {filteredLogs.length === 0 ? (
          <div className="text-center text-gray-500 py-8">
            <span className="text-3xl block mb-2">📝</span>
            暂无日志记录
          </div>
        ) : (
          filteredLogs.map((log, index) => (
            <LogItem key={index} log={log} formatTime={formatTime} />
          ))
        )}
      </div>
    </div>
  );
}

function LogItem({
  log,
  formatTime,
}: {
  log: LogEntry;
  formatTime: (timestamp: string) => string;
}) {
  const typeStyles: Record<LogEntry['type'], { bg: string; border: string; icon: string }> = {
    system: {
      bg: 'bg-blue-950/30',
      border: 'border-blue-500/30',
      icon: '⚙️',
    },
    speech: {
      bg: 'bg-purple-950/30',
      border: 'border-purple-500/30',
      icon: '🎤',
    },
    action: {
      bg: 'bg-amber-950/30',
      border: 'border-amber-500/30',
      icon: '⚡',
    },
    death: {
      bg: 'bg-red-950/30',
      border: 'border-red-500/30',
      icon: '💀',
    },
    vote: {
      bg: 'bg-green-950/30',
      border: 'border-green-500/30',
      icon: '🗳️',
    },
    result: {
      bg: 'bg-cyan-950/30',
      border: 'border-cyan-500/30',
      icon: '📊',
    },
  };

  const style = typeStyles[log.type];

  return (
    <div
      className={cn(
        'p-3 rounded-lg border text-sm animate-slide-in',
        style.bg,
        style.border
      )}
    >
      <div className="flex items-start space-x-2">
        <span className="text-xs opacity-70">{style.icon}</span>
        <div className="flex-1 min-w-0">
          <div className="flex items-center space-x-2 text-xs text-gray-500 mb-1">
            <span>{formatTime(log.timestamp)}</span>
            {log.round && (
              <span className="px-1.5 py-0.5 bg-wolf-bg rounded text-gray-400">
                第{log.round}回合
              </span>
            )}
            {log.phase && (
              <span className="px-1.5 py-0.5 bg-wolf-bg rounded text-gray-400">
                {PHASE_INFO[log.phase as Phase]?.name || log.phase}
              </span>
            )}
          </div>
          {log.player && (
            <div className="font-medium text-purple-300 mb-1">{log.player}</div>
          )}
          <div className="text-gray-300 break-words">{log.content}</div>
        </div>
      </div>
    </div>
  );
}
