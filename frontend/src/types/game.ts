// 角色枚举
export enum Role {
  WEREWOLF = 'WEREWOLF',
  SEER = 'SEER',
  WITCH = 'WITCH',
  HUNTER = 'HUNTER',
  GUARD = 'GUARD',
  VILLAGER = 'VILLAGER',
}

// 阵营枚举
export enum Team {
  GOOD = 'GOOD',
  EVIL = 'EVIL',
}

// 游戏阶段枚举
export enum Phase {
  SETUP = 'SETUP',
  NIGHT_GUARD = 'NIGHT_GUARD',
  NIGHT_WEREWOLF = 'NIGHT_WEREWOLF',
  NIGHT_SEER = 'NIGHT_SEER',
  NIGHT_WITCH = 'NIGHT_WITCH',
  DAY_ANNOUNCE = 'DAY_ANNOUNCE',
  DAY_SPEECH = 'DAY_SPEECH',
  DAY_VOTE = 'DAY_VOTE',
  DAY_RESULT = 'DAY_RESULT',
  CHECK_END = 'CHECK_END',
  GAME_OVER = 'GAME_OVER',
}

// 玩家接口
export interface Player {
  id: string;
  name: string;
  role: Role;
  team: Team;
  alive: boolean;
  is_human: boolean;
  display_name: string;
}

// 女巫状态
export interface WitchStatus {
  antidote_used: boolean;
  poison_used: boolean;
}

// 游戏状态接口
export interface GameState {
  game_id: string;
  phase: Phase;
  round: number;
  players: Player[];
  alive_players: string[];
  current_speaker: string | null;
  votes: Record<string, string>;
  witch_status: WitchStatus;
  winner: Team | null;
  last_night_deaths: string[];
  guard_target: string | null;
  werewolf_target: string | null;
  auto_play: boolean;
  speed: number;
}

// 日志条目接口
export interface LogEntry {
  timestamp: string;
  type: 'system' | 'speech' | 'action' | 'death' | 'vote' | 'result';
  player?: string;
  content: string;
  round?: number;
  phase?: Phase;
}

// WebSocket消息类型
export type WebSocketMessageType = 
  | 'game_state'
  | 'log'
  | 'action_request'
  | 'action_result'
  | 'error'
  | 'connected'
  | 'disconnected';

// WebSocket消息接口
export interface WebSocketMessage {
  type: WebSocketMessageType;
  data?: GameState | LogEntry | ActionRequest | ActionResult | ErrorData;
}

// 动作请求
export interface ActionRequest {
  player_id: string;
  action_type: string;
  available_targets?: string[];
  message?: string;
}

// 动作结果
export interface ActionResult {
  success: boolean;
  message: string;
  data?: unknown;
}

// 错误数据
export interface ErrorData {
  code: string;
  message: string;
}

// 游戏动作类型
export type GameAction =
  | { type: 'GUARD_PROTECT'; target: string }
  | { type: 'WEREWOLF_KILL'; target: string }
  | { type: 'SEER_CHECK'; target: string }
  | { type: 'WITCH_ACTION'; use_antidote: boolean; use_poison: boolean; poison_target?: string }
  | { type: 'SPEECH'; content: string }
  | { type: 'VOTE'; target: string }
  | { type: 'HUNTER_SHOOT'; target: string }
  | { type: 'START_GAME' }
  | { type: 'END_SPEECH' };

// 创建游戏请求
export interface CreateGameRequest {
  auto_play?: boolean;
  speed?: number;
}

// 创建游戏响应
export interface CreateGameResponse {
  game_id: string;
  message: string;
}

// 加入游戏响应
export interface JoinGameResponse {
  player_id: string;
  player_name: string;
  role: Role;
  message: string;
}

// 游戏列表项
export interface GameListItem {
  game_id: string;
  phase: Phase;
  round: number;
  player_count: number;
  alive_count: number;
  has_winner: boolean;
}

// 角色配置
export interface RoleConfig {
  role: Role;
  name: string;
  description: string;
  team: Team;
  color: string;
  icon: string;
}

// 阶段配置
export interface PhaseConfig {
  phase: Phase;
  name: string;
  description: string;
  is_night: boolean;
}

// 角色信息映射
export const ROLE_INFO: Record<Role, RoleConfig> = {
  [Role.WEREWOLF]: {
    role: Role.WEREWOLF,
    name: '狼人',
    description: '夜晚可以杀人，白天要隐藏身份',
    team: Team.EVIL,
    color: '#dc2626',
    icon: '/roles/werewolf.svg',
  },
  [Role.SEER]: {
    role: Role.SEER,
    name: '预言家',
    description: '每晚可以查验一个人的身份',
    team: Team.GOOD,
    color: '#7c3aed',
    icon: '/roles/seer.svg',
  },
  [Role.WITCH]: {
    role: Role.WITCH,
    name: '女巫',
    description: '拥有解药和毒药，可以救人或毒人',
    team: Team.GOOD,
    color: '#16a34a',
    icon: '/roles/witch.svg',
  },
  [Role.HUNTER]: {
    role: Role.HUNTER,
    name: '猎人',
    description: '死亡时可以开枪带走一个人',
    team: Team.GOOD,
    color: '#ea580c',
    icon: '/roles/hunter.svg',
  },
  [Role.GUARD]: {
    role: Role.GUARD,
    name: '守卫',
    description: '每晚可以守护一个人，使其不被狼人杀死',
    team: Team.GOOD,
    color: '#eab308',
    icon: '/roles/guard.svg',
  },
  [Role.VILLAGER]: {
    role: Role.VILLAGER,
    name: '平民',
    description: '没有特殊技能，通过推理找出狼人',
    team: Team.GOOD,
    color: '#6b7280',
    icon: '/roles/villager.svg',
  },
};

// 阶段信息映射
export const PHASE_INFO: Record<Phase, PhaseConfig> = {
  [Phase.SETUP]: {
    phase: Phase.SETUP,
    name: '准备阶段',
    description: '等待玩家加入或开始游戏',
    is_night: false,
  },
  [Phase.NIGHT_GUARD]: {
    phase: Phase.NIGHT_GUARD,
    name: '守卫阶段',
    description: '守卫选择要守护的目标',
    is_night: true,
  },
  [Phase.NIGHT_WEREWOLF]: {
    phase: Phase.NIGHT_WEREWOLF,
    name: '狼人阶段',
    description: '狼人选择要击杀的目标',
    is_night: true,
  },
  [Phase.NIGHT_SEER]: {
    phase: Phase.NIGHT_SEER,
    name: '预言家阶段',
    description: '预言家选择要查验的目标',
    is_night: true,
  },
  [Phase.NIGHT_WITCH]: {
    phase: Phase.NIGHT_WITCH,
    name: '女巫阶段',
    description: '女巫决定是否使用解药或毒药',
    is_night: true,
  },
  [Phase.DAY_ANNOUNCE]: {
    phase: Phase.DAY_ANNOUNCE,
    name: '公布阶段',
    description: '公布昨晚的死亡信息',
    is_night: false,
  },
  [Phase.DAY_SPEECH]: {
    phase: Phase.DAY_SPEECH,
    name: '发言阶段',
    description: '玩家依次发言',
    is_night: false,
  },
  [Phase.DAY_VOTE]: {
    phase: Phase.DAY_VOTE,
    name: '投票阶段',
    description: '玩家投票选出要放逐的人',
    is_night: false,
  },
  [Phase.DAY_RESULT]: {
    phase: Phase.DAY_RESULT,
    name: '投票结果',
    description: '公布投票结果和放逐信息',
    is_night: false,
  },
  [Phase.CHECK_END]: {
    phase: Phase.CHECK_END,
    name: '结算阶段',
    description: '检查游戏是否结束',
    is_night: false,
  },
  [Phase.GAME_OVER]: {
    phase: Phase.GAME_OVER,
    name: '游戏结束',
    description: '游戏已结束',
    is_night: false,
  },
};
