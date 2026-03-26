<template>
  <div class="tradingview-widget-shell" :class="{ workspace: isWorkspace, compact: !isWorkspace }">
    <div v-if="tvSymbol" ref="widgetHost" class="widget-host"></div>
    <div v-else class="widget-empty">
      {{ t('tv_no_symbol') }}
    </div>

    <div v-if="showFooter" class="widget-footer">
      <span>
        {{ t('tv_footer_prefix') }}
        {{ dataLevelNote }}
      </span>
      <a
        v-if="symbolPageHref"
        :href="symbolPageHref"
        target="_blank"
        rel="noopener noreferrer nofollow"
      >
        {{ t('tv_open_full_chart') }}
      </a>
    </div>
  </div>
</template>

<script setup lang="ts">
import { computed, onMounted, onUnmounted, ref, watch } from 'vue'
import { useLocale } from '@/composables/useLocale'

interface Props {
  code: string
  exchange?: string
  theme?: 'dark' | 'light'
  interval?: string
  mode?: 'embedded' | 'workspace'
  showFooter?: boolean
}

const props = withDefaults(defineProps<Props>(), {
  exchange: '',
  theme: 'dark',
  interval: 'D',
  mode: 'embedded',
  showFooter: true,
})

const { locale, t } = useLocale()
const widgetHost = ref<HTMLDivElement>()
let widgetScript: HTMLScriptElement | null = null
const isCompact = ref(false)

const normalizedCode = computed(() => String(props.code || '').trim().toUpperCase())

const tradingViewExchange = computed(() => {
  const exchange = String(props.exchange || '').trim().toUpperCase()
  if (exchange === 'SH' || exchange === 'SSE') return 'SSE'
  if (exchange === 'SZ' || exchange === 'SZSE') return 'SZSE'
  if (exchange === 'BJ' || exchange === 'BSE') return 'BSE'
  return ''
})

const tvSymbol = computed(() => {
  if (!normalizedCode.value || !tradingViewExchange.value) return ''
  return `${tradingViewExchange.value}:${normalizedCode.value}`
})

const symbolPageHref = computed(() => {
  if (!normalizedCode.value || !tradingViewExchange.value) return ''
  return `https://www.tradingview.com/symbols/${tradingViewExchange.value}-${normalizedCode.value}/`
})

const dataLevelNote = computed(() => {
  if (tradingViewExchange.value === 'SSE' || tradingViewExchange.value === 'SZSE') {
    return t('tv_data_level_a_share')
  }
  if (tradingViewExchange.value === 'BSE') {
    return t('tv_data_level_bj')
  }
  return ''
})

const showFooter = computed(() => props.showFooter)
const isWorkspace = computed(() => props.mode === 'workspace')

const refreshCompactMode = () => {
  if (isWorkspace.value) {
    isCompact.value = false
    return
  }
  isCompact.value = window.innerWidth < 1200
}

const cleanupWidget = () => {
  if (widgetScript?.parentNode) {
    widgetScript.parentNode.removeChild(widgetScript)
  }
  widgetScript = null
  if (widgetHost.value) {
    widgetHost.value.innerHTML = ''
  }
}

const mountWidget = () => {
  cleanupWidget()

  if (!widgetHost.value || !tvSymbol.value) return

  const container = document.createElement('div')
  container.className = 'tradingview-widget-container'
  container.style.height = '100%'
  container.style.width = '100%'

  const widget = document.createElement('div')
  widget.className = 'tradingview-widget-container__widget'
  widget.style.height = 'calc(100% - 32px)'
  widget.style.width = '100%'

  const copyright = document.createElement('div')
  copyright.className = 'tradingview-widget-copyright'

  const link = document.createElement('a')
  link.href = symbolPageHref.value || 'https://www.tradingview.com/'
  link.target = '_blank'
  link.rel = 'noopener nofollow'

  const text = document.createElement('span')
  text.className = 'blue-text'
  text.textContent = `${tvSymbol.value} 图表`

  const trademark = document.createElement('span')
  trademark.className = 'trademark'
  trademark.textContent = ' by TradingView'

  link.appendChild(text)
  copyright.appendChild(link)
  copyright.appendChild(trademark)

  widgetScript = document.createElement('script')
  widgetScript.type = 'text/javascript'
  widgetScript.src = 'https://s3.tradingview.com/external-embedding/embed-widget-advanced-chart.js'
  widgetScript.async = true
  widgetScript.text = JSON.stringify({
    autosize: true,
    symbol: tvSymbol.value,
    interval: props.interval,
    timezone: 'Asia/Shanghai',
    theme: props.theme,
    style: '1',
    locale: locale.value === 'en' ? 'en' : 'zh_CN',
    allow_symbol_change: isWorkspace.value,
    withdateranges: isWorkspace.value,
    details: isWorkspace.value,
    hide_side_toolbar: isCompact.value,
    hide_top_toolbar: !isWorkspace.value,
    calendar: false,
    support_host: 'https://www.tradingview.com',
  })

  container.appendChild(widget)
  container.appendChild(copyright)
  container.appendChild(widgetScript)
  widgetHost.value.appendChild(container)
}

watch(
  () => [tvSymbol.value, props.theme, props.interval, props.mode, isCompact.value, locale.value],
  () => {
    mountWidget()
  }
)

onMounted(() => {
  refreshCompactMode()
  window.addEventListener('resize', refreshCompactMode)
  mountWidget()
})

onUnmounted(() => {
  window.removeEventListener('resize', refreshCompactMode)
  cleanupWidget()
})
</script>

<style scoped lang="scss">
.tradingview-widget-shell {
  display: flex;
  flex-direction: column;
  height: 100%;
  min-height: 0;
  overflow: hidden;
}

.widget-host {
  flex: 1;
  min-height: 0;
  width: 100%;
  min-width: 0;
}

.widget-empty {
  display: flex;
  align-items: center;
  justify-content: center;
  flex: 1;
  min-height: 0;
  padding: 24px;
  color: rgba(255, 255, 255, 0.52);
  text-align: center;
  width: 100%;
  min-width: 0;
}

.widget-footer {
  display: flex;
  justify-content: space-between;
  gap: 16px;
  padding: 10px 16px 14px;
  color: rgba(255, 255, 255, 0.5);
  font-size: 12px;
  border-top: 1px solid rgba(255, 255, 255, 0.08);

  a {
    color: #4da3ff;
    text-decoration: none;
    white-space: nowrap;

    &:hover {
      text-decoration: underline;
    }
  }
}

.tradingview-widget-shell.workspace {
  min-height: 100%;

  .widget-host,
  .widget-empty {
    min-height: min(680px, calc(100vh - 180px));
  }
}

@media (max-width: 768px) {
  .widget-footer {
    flex-direction: column;
  }
}
</style>
