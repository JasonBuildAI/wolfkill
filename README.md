# AI 狼人杀 - 多智能体协作与博弈系统

基于多 Agent 协作框架构建的狼人杀游戏系统，支持纯 AI 对战和人机混合对战。

## 功能特性

- 12人标准局配置：4狼人、1预言家、1女巫、1猎人、1守卫、4村民
- 完整游戏流程：夜间行动（守卫守护→狼人杀人→预言家查验→女巫用药）→ 白天发言 → 投票放逐
- 严格信息隔离：各角色只能看到应知信息
- AI Agent 智能决策：基于 LLM 的推理、发言、投票
- 实时观战：WebSocket 实时推送游戏状态
- 结构化日志：完整记录每局游戏过程

## 快速开始

### 1. 环境准备

```bash
# 克隆仓库
git clone https://github.com/JasonBuildAI/wolfkill.git
cd wolfkill

# 创建虚拟环境
python -m venv venv
source venv/bin/activate  # Windows: venv\Scripts\activate

# 安装依赖
pip install -r backend/requirements.txt
```

### 2. 配置环境变量

```bash
cp .env.example .env
# 编辑 .env 文件，填入你的 LLM API Key
```

### 3. 启动服务

```bash
python -m backend.main
```

服务将在 http://localhost:8000 启动。

### 4. 创建游戏

```bash
# 创建纯 AI 自动对战
curl -X POST http://localhost:8000/api/games \
  -H "Content-Type: application/json" \
  -d '{"auto_play": true, "speed": 0.5}'

# 启动游戏
curl -X POST "http://localhost:8000/api/games/{game_id}/start?auto_play=true&speed=0.5"
```

### 5. WebSocket 观战

```javascript
const ws = new WebSocket('ws://localhost:8000/ws/{game_id}');
ws.onmessage = (event) => {
  const data = JSON.parse(event.data);
  console.log(data);
};
```

## API 文档

启动服务后访问 http://localhost:8000/docs 查看完整的 API 文档。

### 主要接口

- `POST /api/games` - 创建游戏
- `GET /api/games` - 列出所有游戏
- `GET /api/games/{game_id}` - 获取游戏状态
- `POST /api/games/{game_id}/join` - 加入游戏（作为人类玩家）
- `POST /api/games/{game_id}/start` - 启动游戏
- `POST /api/games/{game_id}/action` - 提交人类操作
- `WebSocket /ws/{game_id}` - 实时游戏状态

## 项目结构

```
backend/
├── game_engine/      # 游戏引擎核心
│   ├── roles.py      # 角色定义
│   ├── state.py      # 游戏状态管理
│   └── engine.py     # 游戏逻辑引擎
├── agents/           # AI Agent 实现
│   ├── llm_client.py # LLM 客户端
│   ├── base.py       # Agent 基类
│   ├── werewolf_agent.py
│   ├── seer_agent.py
│   ├── witch_agent.py
│   ├── guard_agent.py
│   ├── hunter_agent.py
│   └── villager_agent.py
├── server.py         # FastAPI 服务器
├── database.py       # 数据库操作
├── config.py         # 配置管理
└── tests/            # 测试用例
```

## 运行测试

```bash
python -m pytest backend/tests/test_engine.py -v
```

## 配置说明

| 环境变量 | 说明 | 默认值 |
|---------|------|--------|
| LLM_API_KEY | LLM API 密钥 | 必填 |
| LLM_API_BASE | API 基础地址 | https://api.openai.com/v1 |
| LLM_MODEL | 模型名称 | gpt-4o-mini |
| DATABASE_PATH | 数据库路径 | ./werewolf.db |
| HOST | 服务器地址 | 0.0.0.0 |
| PORT | 服务器端口 | 8000 |

## 许可证

MIT
