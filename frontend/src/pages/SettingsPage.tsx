import { useState, useEffect, useCallback } from 'react';

const API_URL = import.meta.env.VITE_API_URL || 'http://localhost:8000';

interface Provider {
  id: string;
  name: string;
  models: { id: string; name: string }[];
  key_url: string;
}

interface ModelConfig {
  provider: string;
  model: string;
  api_key: string;
  base_url: string;
  temperature: number;
  max_tokens: number;
}

export function SettingsPage() {
  const [providers, setProviders] = useState<Provider[]>([]);
  const [config, setConfig] = useState<ModelConfig>({
    provider: 'openai',
    model: 'gpt-4o-mini',
    api_key: '',
    base_url: '',
    temperature: 0.7,
    max_tokens: 500,
  });
  const [loading, setLoading] = useState(false);
  const [testing, setTesting] = useState(false);
  const [message, setMessage] = useState<{ type: 'success' | 'error'; text: string } | null>(null);
  const [currentProvider, setCurrentProvider] = useState<Provider | null>(null);

  // 获取服务商列表和当前配置
  useEffect(() => {
    fetchProviders();
    fetchCurrentConfig();
  }, []);

  const fetchProviders = async () => {
    try {
      const res = await fetch(`${API_URL}/api/providers`);
      if (!res.ok) {
        throw new Error(`HTTP ${res.status}`);
      }
      const data = await res.json();
      const providerList = data.providers || [];
      setProviders(providerList);
      // 如果获取到数据但当前provider不在列表中，默认选第一个
      if (providerList.length > 0 && !providerList.find((p: Provider) => p.id === config.provider)) {
        setConfig(prev => ({ ...prev, provider: providerList[0].id }));
      }
    } catch (err) {
      console.error('获取服务商列表失败:', err);
      setMessage({ type: 'error', text: '无法连接到后端服务，请确保后端已启动 (python -m uvicorn backend.server:app --host 0.0.0.0 --port 8000)' });
    }
  };

  const fetchCurrentConfig = async () => {
    try {
      const res = await fetch(`${API_URL}/api/model-config`);
      const data = await res.json();
      setConfig(prev => ({
        ...prev,
        provider: data.provider || 'openai',
        model: data.model || 'gpt-4o-mini',
        base_url: data.base_url || '',
        temperature: data.temperature ?? 0.7,
        max_tokens: data.max_tokens ?? 500,
      }));
    } catch (err) {
      console.error('获取当前配置失败:', err);
    }
  };

  // 当选择的服务商变化时更新可用模型
  useEffect(() => {
    const provider = providers.find(p => p.id === config.provider);
    setCurrentProvider(provider || null);
    if (provider && provider.models.length > 0) {
      const modelExists = provider.models.some(m => m.id === config.model);
      if (!modelExists) {
        setConfig(prev => ({ ...prev, model: provider.models[0].id }));
      }
    }
  }, [config.provider, providers]);

  const handleSave = useCallback(async () => {
    setLoading(true);
    setMessage(null);

    try {
      const res = await fetch(`${API_URL}/api/model-config`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(config),
      });

      if (!res.ok) {
        const err = await res.json();
        throw new Error(err.detail || '保存失败');
      }

      setMessage({ type: 'success', text: '配置保存成功！' });
    } catch (err: any) {
      setMessage({ type: 'error', text: err.message || '保存失败' });
    } finally {
      setLoading(false);
    }
  }, [config]);

  const handleTest = useCallback(async () => {
    setTesting(true);
    setMessage(null);

    try {
      const res = await fetch(`${API_URL}/api/model-config/test`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(config),
      });

      if (!res.ok) {
        const err = await res.json();
        throw new Error(err.detail || '测试失败');
      }

      const data = await res.json();
      setMessage({
        type: 'success',
        text: `连接成功！模型响应: "${data.response_preview}"`,
      });
    } catch (err: any) {
      setMessage({ type: 'error', text: err.message || '测试失败' });
    } finally {
      setTesting(false);
    }
  }, [config]);

  return (
    <div className="max-w-4xl mx-auto">
      {/* Header */}
      <div className="mb-8">
        <h1 className="text-3xl font-bold text-white mb-2">模型配置</h1>
        <p className="text-gray-400">选择AI模型服务商并配置API Key</p>
      </div>

      {/* Message */}
      {message && (
        <div
          className={`mb-6 p-4 rounded-lg ${
            message.type === 'success'
              ? 'bg-green-500/10 border border-green-500/30 text-green-400'
              : 'bg-red-500/10 border border-red-500/30 text-red-400'
          }`}
        >
          {message.text}
        </div>
      )}

      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        {/* Main Config */}
        <div className="lg:col-span-2 space-y-6">
          {/* Provider Selection */}
          <div className="bg-wolf-card border border-wolf-border rounded-xl p-6">
            <h2 className="text-lg font-semibold text-white mb-4 flex items-center">
              <span className="w-8 h-8 rounded-lg bg-purple-600/20 flex items-center justify-center mr-3">
                🏢
              </span>
              选择服务商
            </h2>

            <div className="grid grid-cols-2 sm:grid-cols-3 gap-3">
              {providers.map((provider) => (
                <button
                  key={provider.id}
                  onClick={() => setConfig(prev => ({ ...prev, provider: provider.id }))}
                  className={`p-3 rounded-lg border text-left transition-all ${
                    config.provider === provider.id
                      ? 'border-purple-500 bg-purple-500/10 text-white'
                      : 'border-wolf-border bg-white/5 text-gray-300 hover:bg-white/10'
                  }`}
                >
                  <div className="font-medium text-sm">{provider.name}</div>
                  <div className="text-xs text-gray-500 mt-1">
                    {provider.models.length} 个模型
                  </div>
                </button>
              ))}
            </div>
          </div>

          {/* Model Selection */}
          {currentProvider && (
            <div className="bg-wolf-card border border-wolf-border rounded-xl p-6">
              <h2 className="text-lg font-semibold text-white mb-4 flex items-center">
                <span className="w-8 h-8 rounded-lg bg-blue-600/20 flex items-center justify-center mr-3">
                  🤖
                </span>
                选择模型
              </h2>

              <div className="grid grid-cols-1 sm:grid-cols-2 gap-3">
                {currentProvider.models.map((model) => (
                  <button
                    key={model.id}
                    onClick={() => setConfig(prev => ({ ...prev, model: model.id }))}
                    className={`p-3 rounded-lg border text-left transition-all ${
                      config.model === model.id
                        ? 'border-blue-500 bg-blue-500/10 text-white'
                        : 'border-wolf-border bg-white/5 text-gray-300 hover:bg-white/10'
                    }`}
                  >
                    <div className="font-medium text-sm">{model.name}</div>
                    <div className="text-xs text-gray-500 mt-1 font-mono">{model.id}</div>
                  </button>
                ))}
              </div>
            </div>
          )}

          {/* API Key */}
          <div className="bg-wolf-card border border-wolf-border rounded-xl p-6">
            <h2 className="text-lg font-semibold text-white mb-4 flex items-center">
              <span className="w-8 h-8 rounded-lg bg-yellow-600/20 flex items-center justify-center mr-3">
                🔑
              </span>
              API Key
            </h2>

            <div className="space-y-4">
              <div>
                <label className="block text-sm font-medium text-gray-300 mb-2">
                  API Key
                  {currentProvider?.key_url && (
                    <a
                      href={currentProvider.key_url}
                      target="_blank"
                      rel="noopener noreferrer"
                      className="ml-2 text-purple-400 hover:text-purple-300 text-xs"
                    >
                      获取Key →
                    </a>
                  )}
                </label>
                <input
                  type="password"
                  value={config.api_key}
                  onChange={(e) => setConfig(prev => ({ ...prev, api_key: e.target.value }))}
                  placeholder="sk-..."
                  className="w-full px-4 py-3 bg-black/30 border border-wolf-border rounded-lg text-white placeholder-gray-500 focus:outline-none focus:border-purple-500 transition-colors"
                />
                <p className="text-xs text-gray-500 mt-1">
                  您的API Key仅保存在服务器内存中，不会持久化存储
                </p>
              </div>

              {/* Custom Base URL */}
              {(config.provider === 'custom' || config.provider === 'azure') && (
                <div>
                  <label className="block text-sm font-medium text-gray-300 mb-2">
                    Base URL (可选)
                  </label>
                  <input
                    type="text"
                    value={config.base_url}
                    onChange={(e) => setConfig(prev => ({ ...prev, base_url: e.target.value }))}
                    placeholder="https://api.example.com/v1"
                    className="w-full px-4 py-3 bg-black/30 border border-wolf-border rounded-lg text-white placeholder-gray-500 focus:outline-none focus:border-purple-500 transition-colors"
                  />
                </div>
              )}
            </div>
          </div>

          {/* Advanced Settings */}
          <div className="bg-wolf-card border border-wolf-border rounded-xl p-6">
            <h2 className="text-lg font-semibold text-white mb-4 flex items-center">
              <span className="w-8 h-8 rounded-lg bg-gray-600/20 flex items-center justify-center mr-3">
                ⚙️
              </span>
              高级设置
            </h2>

            <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
              <div>
                <label className="block text-sm font-medium text-gray-300 mb-2">
                  Temperature: {config.temperature}
                </label>
                <input
                  type="range"
                  min="0"
                  max="2"
                  step="0.1"
                  value={config.temperature}
                  onChange={(e) => setConfig(prev => ({ ...prev, temperature: parseFloat(e.target.value) }))}
                  className="w-full accent-purple-500"
                />
                <div className="flex justify-between text-xs text-gray-500 mt-1">
                  <span>精确</span>
                  <span>平衡</span>
                  <span>创意</span>
                </div>
              </div>

              <div>
                <label className="block text-sm font-medium text-gray-300 mb-2">
                  Max Tokens: {config.max_tokens >= 10000 ? `${(config.max_tokens / 10000).toFixed(0)}万` : config.max_tokens}
                </label>
                <input
                  type="range"
                  min="100"
                  max="2000000"
                  step="100"
                  value={config.max_tokens <= 10000 ? config.max_tokens : Math.log10(config.max_tokens) * 2500}
                  onChange={(e) => {
                    const val = parseInt(e.target.value);
                    // 使用对数刻度让大范围调节更平滑
                    const tokens = val <= 10000 ? val : Math.round(Math.pow(10, val / 2500));
                    setConfig(prev => ({ ...prev, max_tokens: Math.min(tokens, 2000000) }));
                  }}
                  className="w-full accent-purple-500"
                />
                <div className="flex justify-between text-xs text-gray-500 mt-1">
                  <span>100</span>
                  <span>1万</span>
                  <span>100万</span>
                  <span>200万</span>
                </div>
              </div>
            </div>
          </div>

          {/* Actions */}
          <div className="flex flex-col sm:flex-row gap-3">
            <button
              onClick={handleTest}
              disabled={testing || !config.api_key}
              className="flex-1 px-6 py-3 bg-white/5 border border-wolf-border rounded-lg text-white font-medium hover:bg-white/10 disabled:opacity-50 disabled:cursor-not-allowed transition-colors"
            >
              {testing ? '测试中...' : '测试连接'}
            </button>
            <button
              onClick={handleSave}
              disabled={loading || !config.api_key}
              className="flex-1 px-6 py-3 bg-purple-600 rounded-lg text-white font-medium hover:bg-purple-700 disabled:opacity-50 disabled:cursor-not-allowed transition-colors"
            >
              {loading ? '保存中...' : '保存配置'}
            </button>
          </div>
        </div>

        {/* Sidebar Info */}
        <div className="space-y-6">
          <div className="bg-wolf-card border border-wolf-border rounded-xl p-6">
            <h3 className="font-semibold text-white mb-3">当前配置</h3>
            <div className="space-y-2 text-sm">
              <div className="flex justify-between">
                <span className="text-gray-400">服务商</span>
                <span className="text-white">{currentProvider?.name || config.provider}</span>
              </div>
              <div className="flex justify-between">
                <span className="text-gray-400">模型</span>
                <span className="text-white font-mono text-xs">{config.model}</span>
              </div>
              <div className="flex justify-between">
                <span className="text-gray-400">API Key</span>
                <span className="text-white">
                  {config.api_key ? '✅ 已设置' : '❌ 未设置'}
                </span>
              </div>
            </div>
          </div>

          <div className="bg-wolf-card border border-wolf-border rounded-xl p-6">
            <h3 className="font-semibold text-white mb-3">推荐配置</h3>
            <div className="space-y-3 text-sm">
              <div className="p-3 bg-white/5 rounded-lg">
                <div className="font-medium text-purple-300">快速体验</div>
                <div className="text-gray-400 text-xs mt-1">
                  硅基流动 Qwen2.5-7B (免费) 或 OpenRouter
                </div>
              </div>
              <div className="p-3 bg-white/5 rounded-lg">
                <div className="font-medium text-blue-300">最佳效果</div>
                <div className="text-gray-400 text-xs mt-1">
                  GPT-4o / Claude 3.5 Sonnet / DeepSeek-V3
                </div>
              </div>
              <div className="p-3 bg-white/5 rounded-lg">
                <div className="font-medium text-green-300">性价比</div>
                <div className="text-gray-400 text-xs mt-1">
                  GPT-4o Mini / DeepSeek-V3 / GLM-4-Flash
                </div>
              </div>
            </div>
          </div>

          <div className="bg-wolf-card border border-wolf-border rounded-xl p-6">
            <h3 className="font-semibold text-white mb-3">支持的服务商</h3>
            <div className="space-y-2 text-sm text-gray-400">
              <div>• OpenAI (GPT-4o系列)</div>
              <div>• Anthropic (Claude系列)</div>
              <div>• DeepSeek (V3/R1)</div>
              <div>• OpenRouter (聚合平台)</div>
              <div>• 硅基流动 (SiliconFlow)</div>
              <div>• 智谱AI (GLM系列)</div>
              <div>• Moonshot (月之暗面)</div>
              <div>• 阿里云百炼</div>
              <div>• Azure OpenAI</div>
              <div>• 自定义接口</div>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}
