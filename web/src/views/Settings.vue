<template>
  <div class="settings-page">
    <div class="page-header">
      <h1>设置</h1>
      <p class="subtitle">配置应用程序首选项</p>
    </div>

    <div class="settings-layout">
      <aside class="settings-nav">
        <button 
          v-for="section in sections" 
          :key="section.id"
          class="nav-item"
          :class="{ active: activeSection === section.id }"
          @click="activeSection = section.id"
        >
          <span class="nav-icon">{{ section.icon }}</span>
          <span>{{ section.label }}</span>
        </button>
      </aside>

      <main class="settings-content">
        <div v-if="activeSection === 'general'" class="settings-section">
          <h2>通用设置</h2>
          
          <div class="setting-item">
            <div class="setting-info">
              <h4>深色模式</h4>
              <p>启用深色主题以获得更好的视觉体验</p>
            </div>
            <label class="toggle">
              <input type="checkbox" v-model="settings.darkMode" checked>
              <span class="toggle-slider"></span>
            </label>
          </div>

          <div class="setting-item">
            <div class="setting-info">
              <h4>语言</h4>
              <p>选择您偏好的语言</p>
            </div>
            <select v-model="settings.language" class="setting-select">
              <option value="zh">中文</option>
              <option value="en">English</option>
            </select>
          </div>

          <div class="setting-item">
            <div class="setting-info">
              <h4>日期格式</h4>
              <p>选择日期显示格式</p>
            </div>
            <select v-model="settings.dateFormat" class="setting-select">
              <option value="YYYY-MM-DD">YYYY-MM-DD</option>
              <option value="MM/DD/YYYY">MM/DD/YYYY</option>
              <option value="DD/MM/YYYY">DD/MM/YYYY</option>
            </select>
          </div>
        </div>

        <div v-if="activeSection === 'data'" class="settings-section">
          <h2>数据设置</h2>
          
          <div class="setting-item">
            <div class="setting-info">
              <h4>自动刷新</h4>
              <p>自动按指定间隔刷新数据</p>
            </div>
            <label class="toggle">
              <input type="checkbox" v-model="settings.autoRefresh">
              <span class="toggle-slider"></span>
            </label>
          </div>

          <div class="setting-item">
            <div class="setting-info">
              <h4>刷新间隔</h4>
              <p>数据刷新间隔（秒）</p>
            </div>
            <select v-model="settings.refreshInterval" class="setting-select">
              <option value="30">30 秒</option>
              <option value="60">1 分钟</option>
              <option value="300">5 分钟</option>
              <option value="600">10 分钟</option>
            </select>
          </div>

          <div class="setting-item">
            <div class="setting-info">
              <h4>数据源</h4>
              <p>市场数据的主要数据源</p>
            </div>
            <select v-model="settings.dataSource" class="setting-select">
              <option value="eastmoney">东方财富</option>
              <option value="tushare">Tushare</option>
              <option value="sina">新浪</option>
            </select>
          </div>
        </div>

        <div v-if="activeSection === 'notifications'" class="settings-section">
          <h2>通知设置</h2>
          
          <div class="setting-item">
            <div class="setting-info">
              <h4>价格提醒</h4>
              <p>当达到目标价格时接收通知</p>
            </div>
            <label class="toggle">
              <input type="checkbox" v-model="settings.priceAlerts">
              <span class="toggle-slider"></span>
            </label>
          </div>

          <div class="setting-item">
            <div class="setting-info">
              <h4>形态通知</h4>
              <p>当检测到形态时获取通知</p>
            </div>
            <label class="toggle">
              <input type="checkbox" v-model="settings.patternNotifications">
              <span class="toggle-slider"></span>
            </label>
          </div>

          <div class="setting-item">
            <div class="setting-info">
              <h4>涨跌停提醒</h4>
              <p>股票涨跌停时的通知</p>
            </div>
            <label class="toggle">
              <input type="checkbox" v-model="settings.limitAlerts">
              <span class="toggle-slider"></span>
            </label>
          </div>
        </div>

        <div v-if="activeSection === 'display'" class="settings-section">
          <h2>显示设置</h2>
          
          <div class="setting-item">
            <div class="setting-info">
              <h4>图表样式</h4>
              <p>默认图表可视化样式</p>
            </div>
            <select v-model="settings.chartStyle" class="setting-select">
              <option value="candlestick">K线图</option>
              <option value="hollow">空心K线</option>
              <option value="heikin">平均K线</option>
            </select>
          </div>

          <div class="setting-item">
            <div class="setting-info">
              <h4>成交量显示</h4>
              <p>在图表上显示成交量</p>
            </div>
            <label class="toggle">
              <input type="checkbox" v-model="settings.showVolume">
              <span class="toggle-slider"></span>
            </label>
          </div>

          <div class="setting-item">
            <div class="setting-info">
              <h4>默认指标</h4>
              <p>图表上默认显示的技术指标</p>
            </div>
            <div class="indicator-checkboxes">
              <label class="checkbox-item">
                <input type="checkbox" v-model="settings.defaultMA">
                <span>MA</span>
              </label>
              <label class="checkbox-item">
                <input type="checkbox" v-model="settings.defaultMACD">
                <span>MACD</span>
              </label>
              <label class="checkbox-item">
                <input type="checkbox" v-model="settings.defaultRSI">
                <span>RSI</span>
              </label>
              <label class="checkbox-item">
                <input type="checkbox" v-model="settings.defaultBOLL">
                <span>BOLL</span>
              </label>
            </div>
          </div>
        </div>

        <div class="settings-footer">
          <button class="btn btn-primary" @click="saveSettings">保存更改</button>
          <button class="btn btn-secondary" @click="resetSettings">重置默认</button>
        </div>
      </main>
    </div>
  </div>
</template>

<script setup lang="ts">
import { reactive, ref } from 'vue'
import { useLocale, type Locale } from '@/composables/useLocale'

const activeSection = ref('general')
const { locale, setLocale } = useLocale()

const sections = [
  { id: 'general', label: '通用', icon: '⚙️' },
  { id: 'data', label: '数据', icon: '📊' },
  { id: 'notifications', label: '通知', icon: '🔔' },
  { id: 'display', label: '显示', icon: '🎨' },
]

const settings = reactive({
  darkMode: true,
  language: locale.value as Locale,
  dateFormat: 'YYYY-MM-DD',
  autoRefresh: false,
  refreshInterval: '60',
  dataSource: 'eastmoney',
  priceAlerts: true,
  patternNotifications: true,
  limitAlerts: false,
  chartStyle: 'candlestick',
  showVolume: true,
  defaultMA: true,
  defaultMACD: true,
  defaultRSI: true,
  defaultBOLL: false,
})

const saveSettings = () => {
  setLocale(settings.language as Locale)
  console.log('Saving settings...')
}

const resetSettings = () => {
  settings.language = 'zh'
  setLocale('zh')
  console.log('Resetting settings...')
}
</script>

<style scoped lang="scss">
.settings-page {
  padding: 24px;
}

.page-header {
  margin-bottom: 24px;

  h1 {
    margin: 0;
    font-size: 28px;
    font-weight: 600;
  }

  .subtitle {
    margin: 4px 0 0;
    font-size: 14px;
    color: rgba(255, 255, 255, 0.5);
  }
}

.settings-layout {
  display: flex;
  gap: 24px;
}

.settings-nav {
  width: 200px;
  flex-shrink: 0;
  background: rgba(26, 26, 26, 0.5);
  border: 1px solid rgba(255, 255, 255, 0.08);
  border-radius: 12px;
  padding: 12px;
}

.nav-item {
  display: flex;
  align-items: center;
  gap: 12px;
  width: 100%;
  padding: 12px 16px;
  border: none;
  border-radius: 8px;
  background: transparent;
  color: rgba(255, 255, 255, 0.6);
  font-size: 14px;
  text-align: left;
  cursor: pointer;
  transition: all 0.2s;

  &:hover {
    background: rgba(255, 255, 255, 0.05);
    color: rgba(255, 255, 255, 0.9);
  }

  &.active {
    background: rgba(41, 98, 255, 0.15);
    color: #2962FF;
  }
}

.nav-icon {
  font-size: 16px;
}

.settings-content {
  flex: 1;
  background: rgba(26, 26, 26, 0.5);
  border: 1px solid rgba(255, 255, 255, 0.08);
  border-radius: 12px;
  padding: 24px;
}

.settings-section {
  margin-bottom: 32px;

  &:last-of-type {
    margin-bottom: 0;
  }

  h2 {
    margin: 0 0 24px;
    font-size: 18px;
    font-weight: 600;
    padding-bottom: 16px;
    border-bottom: 1px solid rgba(255, 255, 255, 0.08);
  }
}

.setting-item {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 16px 0;
  border-bottom: 1px solid rgba(255, 255, 255, 0.05);

  &:last-child {
    border-bottom: none;
  }
}

.setting-info {
  h4 {
    margin: 0 0 4px;
    font-size: 14px;
    font-weight: 500;
  }

  p {
    margin: 0;
    font-size: 12px;
    color: rgba(255, 255, 255, 0.4);
  }
}

.setting-select {
  padding: 8px 12px;
  border: 1px solid rgba(255, 255, 255, 0.12);
  border-radius: 6px;
  background: rgba(255, 255, 255, 0.05);
  color: rgba(255, 255, 255, 0.9);
  font-size: 13px;
  cursor: pointer;

  &:focus {
    outline: none;
    border-color: #2962FF;
  }
}

.toggle {
  position: relative;
  display: inline-block;
  width: 48px;
  height: 26px;

  input {
    opacity: 0;
    width: 0;
    height: 0;
  }
}

.toggle-slider {
  position: absolute;
  cursor: pointer;
  inset: 0;
  background: rgba(255, 255, 255, 0.12);
  border-radius: 26px;
  transition: all 0.3s;

  &::before {
    content: '';
    position: absolute;
    height: 20px;
    width: 20px;
    left: 3px;
    bottom: 3px;
    background: white;
    border-radius: 50%;
    transition: all 0.3s;
  }
}

input:checked + .toggle-slider {
  background: #2962FF;
}

input:checked + .toggle-slider::before {
  transform: translateX(22px);
}

.indicator-checkboxes {
  display: flex;
  gap: 16px;
}

.checkbox-item {
  display: flex;
  align-items: center;
  gap: 8px;
  cursor: pointer;

  input {
    accent-color: #2962FF;
  }

  span {
    font-size: 13px;
    color: rgba(255, 255, 255, 0.7);
  }
}

.settings-footer {
  display: flex;
  gap: 12px;
  padding-top: 24px;
  border-top: 1px solid rgba(255, 255, 255, 0.08);
  margin-top: 24px;
}

.btn {
  padding: 10px 20px;
  border: none;
  border-radius: 8px;
  font-size: 14px;
  font-weight: 500;
  cursor: pointer;

  &.btn-primary {
    background: #2962FF;
    color: white;

    &:hover {
      background: #1E53E5;
    }
  }

  &.btn-secondary {
    background: rgba(255, 255, 255, 0.08);
    color: rgba(255, 255, 255, 0.8);

    &:hover {
      background: rgba(255, 255, 255, 0.12);
    }
  }
}
</style>
