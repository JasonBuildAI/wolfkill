"""
狼人杀角色定义
"""
from enum import Enum


class Role(str, Enum):
    """角色枚举"""
    WEREWOLF = "werewolf"
    SEER = "seer"
    WITCH = "witch"
    HUNTER = "hunter"
    GUARD = "guard"
    VILLAGER = "villager"


class Team(str, Enum):
    """阵营枚举"""
    GOOD = "good"
    EVIL = "evil"


class Phase(str, Enum):
    """游戏阶段枚举"""
    SETUP = "setup"
    NIGHT_GUARD = "night_guard"
    NIGHT_WEREWOLF = "night_werewolf"
    NIGHT_SEER = "night_seer"
    NIGHT_WITCH = "night_witch"
    DAY_ANNOUNCE = "day_announce"
    DAY_SPEECH = "day_speech"
    DAY_VOTE = "day_vote"
    DAY_RESULT = "day_result"
    CHECK_END = "check_end"
    GAME_OVER = "game_over"


# 角色所属阵营映射
ROLE_TEAM: dict[Role, Team] = {
    Role.WEREWOLF: Team.EVIL,
    Role.SEER: Team.GOOD,
    Role.WITCH: Team.GOOD,
    Role.HUNTER: Team.GOOD,
    Role.GUARD: Team.GOOD,
    Role.VILLAGER: Team.GOOD,
}

# 角色中文名
ROLE_NAME_CN: dict[Role, str] = {
    Role.WEREWOLF: "狼人",
    Role.SEER: "预言家",
    Role.WITCH: "女巫",
    Role.HUNTER: "猎人",
    Role.GUARD: "守卫",
    Role.VILLAGER: "村民",
}

# 角色详细描述
ROLE_DESCRIPTION: dict[Role, str] = {
    Role.WEREWOLF: (
        "你是狼人，属于邪恶阵营。每晚你可以与其他狼人一起猎杀一名玩家。"
        "白天你需要伪装成村民，混淆视听，保护你的狼人同伴。"
    ),
    Role.SEER: (
        "你是预言家，属于善良阵营。每晚你可以查验一名玩家的身份，"
        "得知该玩家是否为狼人。你需要巧妙地分享信息，帮助好人阵营找出狼人。"
    ),
    Role.WITCH: (
        "你是女巫，属于善良阵营。你拥有一瓶解药（可救活当晚被杀的玩家）"
        "和一瓶毒药（可毒杀任意一名玩家）。每种药只能使用一次。"
        "你知道每晚谁被狼人杀害。"
    ),
    Role.HUNTER: (
        "你是猎人，属于善良阵营。当你被投票放逐或被狼人杀害时，"
        "你可以开枪带走任意一名玩家（被女巫毒杀时不能开枪）。"
    ),
    Role.GUARD: (
        "你是守卫，属于善良阵营。每晚你可以守护一名玩家，"
        "使其免受狼人杀害。你不能连续两晚守护同一名玩家。"
    ),
    Role.VILLAGER: (
        "你是村民，属于善良阵营。你没有特殊能力，"
        "但你的投票和分析是好人阵营获胜的关键。通过观察发言找出狼人。"
    ),
}

# 12人标准局角色配置
DEFAULT_ROLES: list[Role] = [
    Role.WEREWOLF, Role.WEREWOLF, Role.WEREWOLF, Role.WEREWOLF,
    Role.SEER, Role.WITCH, Role.HUNTER, Role.GUARD,
    Role.VILLAGER, Role.VILLAGER, Role.VILLAGER, Role.VILLAGER,
]