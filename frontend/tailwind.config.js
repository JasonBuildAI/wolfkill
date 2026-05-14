/** @type {import('tailwindcss').Config} */
export default {
  content: [
    "./index.html",
    "./src/**/*.{js,ts,jsx,tsx}",
  ],
  theme: {
    extend: {
      colors: {
        // 狼人杀主题色
        wolf: {
          bg: '#0a0e1a',
          card: '#1a1f2e',
          border: '#2d3548',
          accent: '#4a5568',
        },
        // 角色颜色
        role: {
          werewolf: '#dc2626', // 红色 - 狼人
          seer: '#7c3aed',     // 紫色 - 预言家
          witch: '#16a34a',    // 绿色 - 女巫
          hunter: '#ea580c',   // 橙色 - 猎人
          guard: '#eab308',    // 黄色 - 守卫
          villager: '#6b7280', // 灰色 - 平民
        },
        // 阵营颜色
        team: {
          good: '#3b82f6',     // 蓝色 - 好人
          evil: '#dc2626',     // 红色 - 狼人
        },
        // 阶段颜色
        phase: {
          night: '#1e1b4b',    // 深夜蓝
          day: '#fef3c7',      // 白天黄
          dawn: '#c7d2fe',     // 黎明
        }
      },
      fontFamily: {
        sans: ['Inter', 'system-ui', 'sans-serif'],
        display: ['Cinzel', 'serif'],
      },
      animation: {
        'pulse-slow': 'pulse 3s cubic-bezier(0.4, 0, 0.6, 1) infinite',
        'float': 'float 3s ease-in-out infinite',
        'glow': 'glow 2s ease-in-out infinite alternate',
        'slide-in': 'slideIn 0.3s ease-out',
        'fade-in': 'fadeIn 0.5s ease-out',
      },
      keyframes: {
        float: {
          '0%, 100%': { transform: 'translateY(0)' },
          '50%': { transform: 'translateY(-10px)' },
        },
        glow: {
          '0%': { boxShadow: '0 0 5px rgba(124, 58, 237, 0.5)' },
          '100%': { boxShadow: '0 0 20px rgba(124, 58, 237, 0.8), 0 0 40px rgba(124, 58, 237, 0.4)' },
        },
        slideIn: {
          '0%': { transform: 'translateX(-100%)', opacity: '0' },
          '100%': { transform: 'translateX(0)', opacity: '1' },
        },
        fadeIn: {
          '0%': { opacity: '0' },
          '100%': { opacity: '1' },
        },
      },
    },
  },
  plugins: [],
}
