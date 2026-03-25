<template>
  <div class="workspace-page">
    <header class="workspace-toolbar">
      <div class="toolbar-left">
        <div class="search-cluster">
          <label class="control-label">标的</label>
          <div class="search-box">
            <svg
              class="search-icon"
              xmlns="http://www.w3.org/2000/svg"
              width="16"
              height="16"
              viewBox="0 0 24 24"
              fill="none"
              stroke="currentColor"
              stroke-width="2"
            >
              <circle cx="11" cy="11" r="8" />
              <line x1="21" y1="21" x2="16.65" y2="16.65" />
            </svg>
            <input
              v-model="searchQuery"
              type="text"
              class="search-input"
              placeholder="搜索股票代码或名称"
              @focus="searchOpen = true"
              @blur="handleSearchBlur"
              @keydown.enter.prevent="handleSearchSubmit"
            />
            <button
              v-if="searchQuery"
              class="clear-btn"
              @click="clearSearch"
              aria-label="清空搜索"
            >
              ×
            </button>

            <div
              v-if="searchOpen && visibleSearchResults.length > 0"
              class="search-results"
            >
              <button
                v-for="stock in visibleSearchResults"
                :key="`${stock.exchange}-${stock.code}`"
                class="search-result"
                @mousedown.prevent="activateStock(stock)"
              >
                <div class="search-result-main">
                  <span class="result-code">{{ stock.code }}</span>
                  <span class="result-name">{{ stock.name }}</span>
                </div>
                <span class="result-exchange">{{
                  exchangeLabel(stock.exchange)
                }}</span>
              </button>
            </div>
          </div>
        </div>

        <div class="control-group">
          <label class="control-label" for="workspace-exchange">市场</label>
          <select
            id="workspace-exchange"
            v-model="exchangeFilter"
            class="control-select"
          >
            <option value="ALL">全部市场</option>
            <option value="SH">上海证券交易所</option>
            <option value="SZ">深圳证券交易所</option>
            <option value="BJ">北京证券交易所</option>
          </select>
        </div>

        <div class="control-group period-group">
          <label class="control-label">周期</label>
          <div class="period-switcher">
            <button
              v-for="option in intervalOptions"
              :key="option.value"
              class="period-btn"
              :class="{ active: selectedInterval === option.value }"
              @click="selectedInterval = option.value"
            >
              {{ option.label }}
            </button>
          </div>
        </div>
      </div>

      <div class="toolbar-right">
        <div class="symbol-chip">
          <span class="chip-label">TradingView</span>
          <span class="chip-value">{{ mappedSymbol || "--" }}</span>
        </div>
        <div class="status-chip" :class="{ loading: loadingDetail }">
          <span class="status-dot"></span>
          <span>{{ loadingDetail ? "同步行情中" : "工作台就绪" }}</span>
        </div>
      </div>
    </header>

    <div
      class="workspace-body"
      :class="{
        'left-collapsed': !leftDrawerOpen,
        'right-collapsed': !rightDrawerOpen,
      }"
    >
      <aside
        class="side-drawer left-drawer"
        :class="{ collapsed: !leftDrawerOpen }"
      >
        <div class="drawer-header">
          <div v-if="leftDrawerOpen" class="drawer-title-group">
            <span class="drawer-label">导航</span>
            <h2>监控列表</h2>
          </div>
          <button
            class="drawer-toggle"
            @click="leftDrawerOpen = !leftDrawerOpen"
            :aria-label="leftDrawerOpen ? '收起左侧面板' : '展开左侧面板'"
          >
            <svg
              xmlns="http://www.w3.org/2000/svg"
              width="18"
              height="18"
              viewBox="0 0 24 24"
              fill="none"
              stroke="currentColor"
              stroke-width="2"
            >
              <polyline
                :points="leftDrawerOpen ? '15 18 9 12 15 6' : '9 18 15 12 9 6'"
              />
            </svg>
          </button>
        </div>

        <template v-if="leftDrawerOpen">
          <div class="drawer-tabs">
            <button
              class="drawer-tab"
              :class="{ active: activeList === 'watchlist' }"
              @click="activeList = 'watchlist'"
            >
              自选
              <span>{{ watchlist.length }}</span>
            </button>
            <button
              class="drawer-tab"
              :class="{ active: activeList === 'recent' }"
              @click="activeList = 'recent'"
            >
              最近查看
              <span>{{ recentStocks.length }}</span>
            </button>
          </div>

          <div class="drawer-content">
            <div v-if="activeListItems.length === 0" class="drawer-empty">
              <p>
                {{
                  activeList === "watchlist" ? "暂无自选股" : "暂无最近查看记录"
                }}
              </p>
              <span>{{
                activeList === "watchlist"
                  ? "可在右侧面板快速添加当前股票。"
                  : "在工作台切换股票后会自动记录。"
              }}</span>
            </div>

            <button
              v-for="stock in activeListItems"
              v-else
              :key="`${activeList}-${stock.exchange}-${stock.code}`"
              class="stock-list-item"
              :class="{ active: stock.code === currentCode }"
              @click="activateStock(stock)"
            >
              <div class="stock-list-main">
                <span class="stock-list-code">{{ stock.code }}</span>
                <span class="stock-list-name">{{ stock.name }}</span>
              </div>
              <span class="stock-list-exchange">{{
                exchangeLabel(stock.exchange)
              }}</span>
            </button>
          </div>
        </template>

        <div v-else class="drawer-rail">
          <button class="rail-pill" @click="activeList = 'watchlist'">
            自选
          </button>
          <button class="rail-pill" @click="activeList = 'recent'">最近</button>
        </div>
      </aside>

      <main class="chart-stage">
        <div class="stage-header">
          <div class="stage-title">
            <div class="title-row">
              <h1>{{ currentName }}</h1>
              <span class="exchange-badge">{{
                exchangeLabel(currentExchange)
              }}</span>
            </div>
            <div class="title-meta">
              <span>{{ currentCode || "--" }}</span>
              <span>{{ mappedSymbol || "--" }}</span>
              <span v-if="selectedIntervalLabel">{{
                selectedIntervalLabel
              }}</span>
            </div>
          </div>

          <div class="quote-strip">
            <div class="quote-card">
              <span class="quote-label">最新价</span>
              <strong :class="priceToneClass">{{
                formatPrice(latestClose)
              }}</strong>
            </div>
            <div class="quote-card">
              <span class="quote-label">涨跌</span>
              <strong :class="priceToneClass">{{
                formatSignedNumber(priceChange)
              }}</strong>
            </div>
            <div class="quote-card">
              <span class="quote-label">涨跌幅</span>
              <strong :class="priceToneClass">{{
                formatSignedPercent(priceChangeRate)
              }}</strong>
            </div>
          </div>
        </div>

        <section class="chart-shell">
          <TradingViewWidget
            :code="currentCode"
            :exchange="currentExchange"
            :interval="selectedInterval"
            mode="workspace"
            :show-footer="false"
            theme="dark"
          />
        </section>
      </main>

      <aside
        class="side-drawer right-drawer"
        :class="{ collapsed: !rightDrawerOpen }"
      >
        <div class="drawer-header">
          <div v-if="rightDrawerOpen" class="drawer-title-group">
            <span class="drawer-label">概览</span>
            <h2>股票信息</h2>
          </div>
          <button
            class="drawer-toggle"
            @click="rightDrawerOpen = !rightDrawerOpen"
            :aria-label="rightDrawerOpen ? '收起右侧面板' : '展开右侧面板'"
          >
            <svg
              xmlns="http://www.w3.org/2000/svg"
              width="18"
              height="18"
              viewBox="0 0 24 24"
              fill="none"
              stroke="currentColor"
              stroke-width="2"
            >
              <polyline
                :points="rightDrawerOpen ? '9 18 15 12 9 6' : '15 18 9 12 15 6'"
              />
            </svg>
          </button>
        </div>

        <template v-if="rightDrawerOpen">
          <div class="drawer-content info-drawer">
            <div class="panel-card">
              <div class="panel-card-header">
                <span>行情速览</span>
                <button
                  class="ghost-btn"
                  @click="refreshCurrentStock"
                  :disabled="!currentCode || loadingDetail"
                >
                  刷新
                </button>
              </div>

              <div v-if="loadingDetail" class="panel-loading">
                <div class="spinner"></div>
                <p>正在加载股票信息...</p>
              </div>

              <template v-else>
                <div class="metric-grid">
                  <div class="metric-item">
                    <span>开盘</span>
                    <strong>{{ formatPrice(latestBar?.open) }}</strong>
                  </div>
                  <div class="metric-item">
                    <span>最高</span>
                    <strong>{{ formatPrice(latestBar?.high) }}</strong>
                  </div>
                  <div class="metric-item">
                    <span>最低</span>
                    <strong>{{ formatPrice(latestBar?.low) }}</strong>
                  </div>
                  <div class="metric-item">
                    <span>成交量</span>
                    <strong>{{ formatVolume(latestBar?.vol) }}</strong>
                  </div>
                  <div class="metric-item">
                    <span>成交额</span>
                    <strong>{{ formatAmount(latestBar?.amount) }}</strong>
                  </div>
                  <div class="metric-item">
                    <span>振幅</span>
                    <strong>{{ formatPercent(dayRangeRate) }}</strong>
                  </div>
                </div>

                <div class="info-list">
                  <div class="info-row">
                    <span>证券名称</span>
                    <strong>{{ currentName }}</strong>
                  </div>
                  <div class="info-row">
                    <span>代码</span>
                    <strong>{{ currentCode || "--" }}</strong>
                  </div>
                  <div class="info-row">
                    <span>市场</span>
                    <strong>{{ exchangeLabel(currentExchange) }}</strong>
                  </div>
                  <div class="info-row">
                    <span>TradingView</span>
                    <strong>{{ mappedSymbol || "--" }}</strong>
                  </div>
                  <div class="info-row">
                    <span>行业</span>
                    <strong>{{ stockDetail?.industry || "--" }}</strong>
                  </div>
                  <div class="info-row">
                    <span>上市日期</span>
                    <strong>{{
                      formatListDate(stockDetail?.list_date)
                    }}</strong>
                  </div>
                </div>
              </template>
            </div>

            <div class="panel-card">
              <div class="panel-card-header">
                <span>快捷操作</span>
              </div>
              <div class="action-stack">
                <button
                  class="action-btn primary"
                  @click="toggleWatchlist"
                  :disabled="!currentCode"
                >
                  {{ isInWatchlist ? "移出自选" : "加入自选" }}
                </button>
                <button
                  class="action-btn"
                  @click="openStockDetail"
                  :disabled="!currentCode"
                >
                  打开个股详情页
                </button>
                <button
                  class="action-btn"
                  @click="openBacktestPage"
                  :disabled="!currentCode"
                >
                  前往策略回测
                </button>
              </div>
            </div>
          </div>
        </template>

        <div v-else class="drawer-rail info-rail">
          <span>信息</span>
        </div>
      </aside>
    </div>

    <section class="bottom-panel" :class="{ collapsed: !bottomPanelOpen }">
      <div class="bottom-header">
        <div>
          <span class="drawer-label">策略区</span>
          <h2>回测结果</h2>
        </div>
        <button
          class="drawer-toggle"
          @click="bottomPanelOpen = !bottomPanelOpen"
          :aria-label="bottomPanelOpen ? '收起回测面板' : '展开回测面板'"
        >
          <svg
            xmlns="http://www.w3.org/2000/svg"
            width="18"
            height="18"
            viewBox="0 0 24 24"
            fill="none"
            stroke="currentColor"
            stroke-width="2"
          >
            <polyline
              :points="bottomPanelOpen ? '6 15 12 9 18 15' : '6 9 12 15 18 9'"
            />
          </svg>
        </button>
      </div>

      <div v-if="bottomPanelOpen" class="bottom-content">
        <div class="placeholder-card">
          <span class="placeholder-label">占位模块</span>
          <h3>策略回测集成预留</h3>
          <p>
            后续可在此接入收益曲线、交易记录、参数快照和指标对比，当前工作台先保留完整布局与入口。
          </p>
        </div>

        <div class="placeholder-metrics">
          <div class="placeholder-metric">
            <span>当前标的</span>
            <strong>{{ currentCode || "--" }}</strong>
          </div>
          <div class="placeholder-metric">
            <span>默认市场</span>
            <strong>{{ exchangeLabel(currentExchange) }}</strong>
          </div>
          <div class="placeholder-metric">
            <span>推荐入口</span>
            <strong>策略回测页</strong>
          </div>
        </div>
      </div>
    </section>
  </div>
</template>

<script setup lang="ts">
import { computed, inject, onMounted, ref } from "vue";
import { useRoute, useRouter } from "vue-router";
import { attentionApi, stockApi } from "@/api";
import TradingViewWidget from "@/components/charts/TradingViewWidget.vue";

interface StockRecord {
  code: string;
  name: string;
  exchange: string;
  industry?: string;
  list_date?: string;
}

interface StockBar {
  trade_date?: string;
  open?: number;
  high?: number;
  low?: number;
  close?: number;
  vol?: number;
  amount?: number;
}

interface StockDetailRecord extends StockRecord {
  bars: StockBar[];
  adjust_note?: string;
}

const RECENT_STORAGE_KEY = "workspace_recent_stocks";
const intervalOptions = [
  { label: "1D", value: "D" },
  { label: "1W", value: "W" },
  { label: "1M", value: "M" },
  { label: "60m", value: "60" },
];

const route = useRoute();
const router = useRouter();
const showNotification =
  inject<
    (
      type: "success" | "error" | "warning" | "info",
      message: string,
      title?: string,
    ) => void
  >("showNotification");

const searchQuery = ref("");
const searchOpen = ref(false);
const exchangeFilter = ref<"ALL" | "SH" | "SZ" | "BJ">("ALL");
const selectedInterval = ref("D");
const leftDrawerOpen = ref(true);
const rightDrawerOpen = ref(true);
const bottomPanelOpen = ref(true);
const activeList = ref<"watchlist" | "recent">("watchlist");
const loadingStocks = ref(false);
const loadingDetail = ref(false);
const stockUniverse = ref<StockRecord[]>([]);
const watchlist = ref<StockRecord[]>([]);
const recentStocks = ref<StockRecord[]>([]);
const selectedStock = ref<StockRecord | null>(null);
const stockDetail = ref<StockDetailRecord | null>(null);

let detailRequestId = 0;

const normalizeExchange = (value: string | undefined | null, code = "") => {
  const exchange = String(value || "")
    .trim()
    .toUpperCase();
  if (exchange === "SSE" || exchange === "SH") return "SH";
  if (exchange === "SZSE" || exchange === "SZ") return "SZ";
  if (exchange === "BSE" || exchange === "BJ") return "BJ";
  if (exchange.endsWith(".SH")) return "SH";
  if (exchange.endsWith(".SZ")) return "SZ";
  if (exchange.endsWith(".BJ")) return "BJ";

  const rawCode = String(code || "").trim();
  if (/^(60|68|90)/.test(rawCode)) return "SH";
  if (/^(00|30)/.test(rawCode)) return "SZ";
  if (/^(4|8)/.test(rawCode)) return "BJ";
  return "";
};

const exchangeLabel = (value: string | undefined) => {
  const exchange = normalizeExchange(value);
  if (exchange === "SH") return "SSE";
  if (exchange === "SZ") return "SZSE";
  if (exchange === "BJ") return "BSE";
  return "--";
};

const normalizeStock = (item: any): StockRecord => {
  const rawCode = String(
    item?.code || item?.symbol || item?.ts_code?.split(".")?.[0] || "",
  )
    .trim()
    .toUpperCase();
  const rawTsCode = String(item?.ts_code || "")
    .trim()
    .toUpperCase();
  const name = String(
    item?.name || item?.stock_name || item?.security_name || rawCode || "--",
  ).trim();
  const exchange = normalizeExchange(item?.exchange || rawTsCode, rawCode);

  return {
    code: rawCode,
    name,
    exchange,
    industry: item?.industry || "",
    list_date: item?.list_date || "",
  };
};

const dedupeStocks = (...groups: StockRecord[][]) => {
  const map = new Map<string, StockRecord>();
  groups.flat().forEach((item) => {
    if (!item?.code) return;
    const normalized = normalizeStock(item);
    map.set(normalized.code, {
      ...(map.get(normalized.code) || {}),
      ...normalized,
      name:
        normalized.name || map.get(normalized.code)?.name || normalized.code,
      exchange: normalized.exchange || map.get(normalized.code)?.exchange || "",
    });
  });
  return Array.from(map.values());
};

const getLatestTradeDate = () => {
  const now = new Date();
  const year = now.getFullYear();
  const month = String(now.getMonth() + 1).padStart(2, "0");
  const day = String(now.getDate()).padStart(2, "0");
  return `${year}${month}${day}`;
};

const getStartDate = (daysBack: number) => {
  const date = new Date();
  date.setDate(date.getDate() - daysBack);
  const year = date.getFullYear();
  const month = String(date.getMonth() + 1).padStart(2, "0");
  const day = String(date.getDate()).padStart(2, "0");
  return `${year}${month}${day}`;
};

const persistRecentStocks = (stock: StockRecord) => {
  const next = [
    stock,
    ...recentStocks.value.filter((item) => item.code !== stock.code),
  ].slice(0, 10);
  recentStocks.value = next;
  localStorage.setItem(RECENT_STORAGE_KEY, JSON.stringify(next));
};

const loadRecentStocks = () => {
  try {
    const raw = localStorage.getItem(RECENT_STORAGE_KEY);
    if (!raw) return;
    const parsed = JSON.parse(raw);
    if (Array.isArray(parsed)) {
      recentStocks.value = parsed
        .map((item) => normalizeStock(item))
        .filter((item) => !!item.code);
    }
  } catch {
    recentStocks.value = [];
  }
};

const loadWatchlist = async () => {
  try {
    const data = await attentionApi.getList();
    watchlist.value = (Array.isArray(data) ? data : [])
      .map((item) => normalizeStock(item))
      .filter((item) => !!item.code);
  } catch (error) {
    watchlist.value = [];
    console.error("Failed to load workspace watchlist:", error);
  }
};

const loadStockUniverse = async () => {
  loadingStocks.value = true;
  try {
    const pageSize = 1000;
    const pages: StockRecord[] = [];
    let page = 1;
    let total = Number.MAX_SAFE_INTEGER;

    while (pages.length < total && page <= 10) {
      const response = await stockApi.getStocks({ page, page_size: pageSize });
      const items = Array.isArray(response?.items) ? response.items : [];
      total = Number(response?.total || items.length);
      pages.push(
        ...items
          .map((item: any) => normalizeStock(item))
          .filter((item: StockRecord) => !!item.code),
      );

      if (items.length < pageSize) break;
      page += 1;
    }

    stockUniverse.value = dedupeStocks(pages);
  } catch (error) {
    console.error("Failed to load stock universe:", error);
    showNotification?.(
      "warning",
      "股票搜索列表加载失败，仍可直接输入代码查看图表",
    );
  } finally {
    loadingStocks.value = false;
  }
};

const fetchStockDetail = async (stock: StockRecord) => {
  const requestId = ++detailRequestId;
  loadingDetail.value = true;

  try {
    const detail = await stockApi.getStockDetail(stock.code, {
      start_date: getStartDate(180),
      end_date: getLatestTradeDate(),
      adjust: "qfq",
    });

    if (requestId !== detailRequestId) return;

    const normalized = normalizeStock(detail);
    stockDetail.value = {
      ...stock,
      ...normalized,
      bars: Array.isArray(detail?.bars)
        ? detail.bars.map((bar: any) => ({
            trade_date: bar.trade_date || "",
            open: Number(bar.open),
            high: Number(bar.high),
            low: Number(bar.low),
            close: Number(bar.close),
            vol: Number(bar.vol),
            amount: Number(bar.amount),
          }))
        : [],
      adjust_note: detail?.adjust_note || "",
      industry: detail?.industry || normalized.industry || stock.industry || "",
      list_date:
        detail?.list_date || normalized.list_date || stock.list_date || "",
    };

    selectedStock.value = {
      ...stock,
      ...normalized,
      industry: stockDetail.value.industry,
      list_date: stockDetail.value.list_date,
    };
    persistRecentStocks(selectedStock.value);
  } catch (error) {
    if (requestId !== detailRequestId) return;
    stockDetail.value = {
      ...stock,
      bars: [],
    };
    console.error("Failed to load stock detail:", error);
    showNotification?.("error", `加载 ${stock.code} 股票详情失败`);
  } finally {
    if (requestId === detailRequestId) {
      loadingDetail.value = false;
    }
  }
};

const activateStock = async (stockLike: Partial<StockRecord>) => {
  const stock = normalizeStock(stockLike);
  if (!stock.code) return;

  selectedStock.value = stock;
  stockDetail.value = null;
  searchQuery.value = `${stock.code} ${stock.name}`.trim();
  searchOpen.value = false;

  const query: Record<string, string> = { code: stock.code };
  if (stock.exchange) {
    query.exchange = stock.exchange;
  }
  router.replace({ path: "/workspace", query });

  await fetchStockDetail(stock);
};

const resolveDirectInput = () => {
  const query = searchQuery.value.trim().toUpperCase();
  if (!query) return null;

  if (/^\d{6}$/.test(query)) {
    return normalizeStock({
      code: query,
      exchange:
        exchangeFilter.value === "ALL"
          ? normalizeExchange("", query)
          : exchangeFilter.value,
      name: query,
    });
  }
  return null;
};

const handleSearchSubmit = async () => {
  const direct = resolveDirectInput();
  if (direct) {
    await activateStock(direct);
    return;
  }

  const next = visibleSearchResults.value[0];
  if (next) {
    await activateStock(next);
    return;
  }

  showNotification?.(
    "warning",
    "未找到匹配股票，请输入 6 位股票代码或从候选列表选择",
  );
};

const handleSearchBlur = () => {
  window.setTimeout(() => {
    searchOpen.value = false;
  }, 120);
};

const clearSearch = () => {
  searchQuery.value = "";
  searchOpen.value = true;
};

const refreshCurrentStock = async () => {
  if (!selectedStock.value) return;
  await fetchStockDetail(selectedStock.value);
};

const toggleWatchlist = async () => {
  if (!currentCode.value) return;
  try {
    if (isInWatchlist.value) {
      await attentionApi.remove(currentCode.value);
      showNotification?.("success", `已将 ${currentCode.value} 移出自选`);
    } else {
      await attentionApi.add(currentCode.value);
      showNotification?.("success", `已将 ${currentCode.value} 加入自选`);
    }
    await loadWatchlist();
  } catch (error) {
    console.error("Failed to update workspace watchlist:", error);
    showNotification?.("error", "更新自选股失败");
  }
};

const openStockDetail = () => {
  if (!currentCode.value) return;
  router.push(`/stock/${currentCode.value}`);
};

const openBacktestPage = () => {
  if (!currentCode.value) return;
  router.push({ path: "/backtest", query: { code: currentCode.value } });
};

const mergedStocks = computed(() =>
  dedupeStocks(
    watchlist.value,
    recentStocks.value,
    stockUniverse.value,
    selectedStock.value ? [selectedStock.value] : [],
  ),
);

const visibleSearchResults = computed(() => {
  const query = searchQuery.value.trim().toLowerCase();
  const exchange = exchangeFilter.value;

  let items = mergedStocks.value;
  if (exchange !== "ALL") {
    items = items.filter(
      (item) => normalizeExchange(item.exchange, item.code) === exchange,
    );
  }

  if (!query) {
    return items.slice(0, 8);
  }

  return items
    .filter((item) => {
      const code = item.code.toLowerCase();
      const name = item.name.toLowerCase();
      return code.includes(query) || name.includes(query);
    })
    .slice(0, 12);
});

const activeListItems = computed(() =>
  activeList.value === "watchlist" ? watchlist.value : recentStocks.value,
);
const currentCode = computed(
  () => selectedStock.value?.code || stockDetail.value?.code || "",
);
const currentName = computed(
  () => stockDetail.value?.name || selectedStock.value?.name || "请选择股票",
);
const currentExchange = computed(
  () => stockDetail.value?.exchange || selectedStock.value?.exchange || "",
);
const mappedSymbol = computed(() => {
  if (!currentCode.value) return "";
  const exchange = exchangeLabel(currentExchange.value);
  return exchange === "--" ? "" : `${exchange}:${currentCode.value}`;
});
const selectedIntervalLabel = computed(
  () =>
    intervalOptions.find((item) => item.value === selectedInterval.value)
      ?.label || "",
);
const isInWatchlist = computed(() =>
  watchlist.value.some((item) => item.code === currentCode.value),
);
const latestBar = computed<StockBar | null>(() => {
  const bars = stockDetail.value?.bars || [];
  return bars.length > 0 ? bars[bars.length - 1] : null;
});
const previousBar = computed<StockBar | null>(() => {
  const bars = stockDetail.value?.bars || [];
  return bars.length > 1 ? bars[bars.length - 2] : null;
});
const latestClose = computed(() => latestBar.value?.close ?? null);
const previousClose = computed(
  () => previousBar.value?.close ?? latestBar.value?.open ?? null,
);
const priceChange = computed(() => {
  if (latestClose.value == null || previousClose.value == null) return null;
  return latestClose.value - previousClose.value;
});
const priceChangeRate = computed(() => {
  if (priceChange.value == null || !previousClose.value) return null;
  return (priceChange.value / previousClose.value) * 100;
});
const dayRangeRate = computed(() => {
  const high = latestBar.value?.high;
  const low = latestBar.value?.low;
  const base = previousClose.value || latestBar.value?.open;
  if (high == null || low == null || !base) return null;
  return ((high - low) / base) * 100;
});
const priceToneClass = computed(() => {
  if ((priceChange.value || 0) > 0) return "price-up";
  if ((priceChange.value || 0) < 0) return "price-down";
  return "price-flat";
});

const formatPrice = (value: number | null | undefined) => {
  if (value == null || Number.isNaN(value)) return "--";
  return value.toFixed(2);
};

const formatSignedNumber = (value: number | null | undefined) => {
  if (value == null || Number.isNaN(value)) return "--";
  const sign = value > 0 ? "+" : "";
  return `${sign}${value.toFixed(2)}`;
};

const formatPercent = (value: number | null | undefined) => {
  if (value == null || Number.isNaN(value)) return "--";
  return `${value.toFixed(2)}%`;
};

const formatSignedPercent = (value: number | null | undefined) => {
  if (value == null || Number.isNaN(value)) return "--";
  const sign = value > 0 ? "+" : "";
  return `${sign}${value.toFixed(2)}%`;
};

const formatVolume = (value: number | null | undefined) => {
  if (value == null || Number.isNaN(value)) return "--";
  if (value >= 100000000) return `${(value / 100000000).toFixed(2)}亿`;
  if (value >= 10000) return `${(value / 10000).toFixed(2)}万`;
  return value.toFixed(0);
};

const formatAmount = (value: number | null | undefined) => {
  if (value == null || Number.isNaN(value)) return "--";
  if (value >= 100000000) return `${(value / 100000000).toFixed(2)}亿`;
  if (value >= 10000) return `${(value / 10000).toFixed(2)}万`;
  return value.toFixed(2);
};

const formatListDate = (value: string | undefined) => {
  if (!value) return "--";
  const raw = String(value).trim();
  if (/^\d{8}$/.test(raw)) {
    return `${raw.slice(0, 4)}-${raw.slice(4, 6)}-${raw.slice(6)}`;
  }
  return raw;
};

const pickInitialStock = () => {
  const queryCode =
    typeof route.query.code === "string"
      ? route.query.code.trim().toUpperCase()
      : "";
  const queryExchange =
    typeof route.query.exchange === "string"
      ? route.query.exchange.trim().toUpperCase()
      : "";

  const candidates = dedupeStocks(
    queryCode
      ? [
          normalizeStock({
            code: queryCode,
            exchange: queryExchange,
            name: queryCode,
          }),
        ]
      : [],
    recentStocks.value,
    watchlist.value,
    stockUniverse.value,
  );

  return candidates[0] || null;
};

onMounted(async () => {
  loadRecentStocks();
  await Promise.all([loadWatchlist(), loadStockUniverse()]);

  const initialStock = pickInitialStock();
  if (initialStock) {
    await activateStock(initialStock);
  } else if (!loadingStocks.value) {
    showNotification?.("info", "未找到默认股票，可通过顶部搜索框选择标的");
  }
});
</script>

<style scoped lang="scss">
.workspace-page {
  --workspace-bg: #07111f;
  --workspace-panel: rgba(8, 18, 32, 0.92);
  --workspace-panel-strong: rgba(12, 26, 46, 0.98);
  --workspace-border: rgba(148, 163, 184, 0.15);
  --workspace-text: rgba(241, 245, 249, 0.94);
  --workspace-muted: rgba(148, 163, 184, 0.78);
  --workspace-blue: #37a6ff;
  --workspace-green: #1ed760;
  --workspace-red: #ff5c7a;
  --workspace-amber: #f6c453;
  min-height: calc(100vh - 60px);
  padding: 18px;
  color: var(--workspace-text);
  background:
    radial-gradient(
      circle at top left,
      rgba(55, 166, 255, 0.12),
      transparent 24%
    ),
    radial-gradient(
      circle at top right,
      rgba(30, 215, 96, 0.08),
      transparent 20%
    ),
    linear-gradient(180deg, #081320 0%, #040b14 100%);
  display: flex;
  flex-direction: column;
  gap: 16px;
}

.workspace-toolbar,
.side-drawer,
.bottom-panel,
.chart-shell,
.stage-header {
  border: 1px solid var(--workspace-border);
  background: var(--workspace-panel);
  box-shadow: 0 18px 50px rgba(2, 8, 23, 0.34);
}

.workspace-toolbar {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 18px;
  padding: 14px 18px;
  border-radius: 20px;
  backdrop-filter: blur(18px);
}

.toolbar-left,
.toolbar-right {
  display: flex;
  align-items: center;
  gap: 16px;
  flex-wrap: wrap;
}

.search-cluster,
.control-group {
  display: flex;
  flex-direction: column;
  gap: 6px;
}

.control-label,
.drawer-label,
.placeholder-label,
.quote-label {
  font-size: 11px;
  letter-spacing: 0.12em;
  text-transform: uppercase;
  color: rgba(191, 219, 254, 0.66);
}

.search-box {
  position: relative;
  width: min(420px, 48vw);
}

.search-icon {
  position: absolute;
  top: 50%;
  left: 14px;
  transform: translateY(-50%);
  color: rgba(148, 163, 184, 0.72);
}

.search-input,
.control-select {
  height: 44px;
  border-radius: 14px;
  border: 1px solid rgba(148, 163, 184, 0.16);
  background: rgba(15, 23, 42, 0.86);
  color: var(--workspace-text);
  font-size: 14px;
}

.search-input {
  width: 100%;
  padding: 0 42px 0 40px;

  &:focus {
    outline: none;
    border-color: rgba(55, 166, 255, 0.75);
    box-shadow: 0 0 0 3px rgba(55, 166, 255, 0.18);
  }
}

.control-select {
  min-width: 172px;
  padding: 0 14px;

  &:focus {
    outline: none;
    border-color: rgba(55, 166, 255, 0.75);
  }
}

.clear-btn,
.drawer-toggle,
.ghost-btn,
.action-btn,
.period-btn,
.drawer-tab,
.rail-pill {
  cursor: pointer;
  transition: all 0.2s ease;
}

.clear-btn {
  position: absolute;
  top: 50%;
  right: 12px;
  transform: translateY(-50%);
  border: none;
  background: transparent;
  color: rgba(148, 163, 184, 0.72);
  font-size: 18px;
}

.search-results {
  position: absolute;
  top: calc(100% + 10px);
  left: 0;
  right: 0;
  z-index: 10;
  padding: 8px;
  border-radius: 16px;
  border: 1px solid rgba(148, 163, 184, 0.18);
  background: rgba(4, 11, 20, 0.98);
  box-shadow: 0 24px 60px rgba(2, 8, 23, 0.48);
}

.search-result {
  width: 100%;
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 12px;
  padding: 12px 14px;
  border: none;
  border-radius: 12px;
  background: transparent;
  color: inherit;
  text-align: left;

  &:hover {
    background: rgba(55, 166, 255, 0.12);
  }
}

.search-result-main,
.stock-list-main {
  display: flex;
  flex-direction: column;
  gap: 4px;
  min-width: 0;
}

.result-code,
.stock-list-code,
.title-meta span:first-child {
  font-family: "JetBrains Mono", "SFMono-Regular", monospace;
}

.result-code,
.stock-list-code {
  font-size: 14px;
  font-weight: 600;
}

.result-name,
.stock-list-name {
  color: var(--workspace-muted);
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.result-exchange,
.stock-list-exchange,
.exchange-badge,
.symbol-chip,
.status-chip {
  border-radius: 999px;
  border: 1px solid rgba(148, 163, 184, 0.18);
  background: rgba(15, 23, 42, 0.9);
}

.result-exchange,
.stock-list-exchange,
.exchange-badge {
  padding: 6px 10px;
  color: rgba(191, 219, 254, 0.85);
  font-size: 12px;
}

.period-group {
  min-width: 260px;
}

.period-switcher {
  display: flex;
  align-items: center;
  gap: 8px;
}

.period-btn {
  min-width: 58px;
  height: 42px;
  padding: 0 14px;
  border-radius: 12px;
  border: 1px solid rgba(148, 163, 184, 0.16);
  background: rgba(15, 23, 42, 0.86);
  color: rgba(226, 232, 240, 0.78);

  &.active,
  &:hover {
    border-color: rgba(55, 166, 255, 0.45);
    background: rgba(55, 166, 255, 0.14);
    color: #f8fbff;
  }
}

.symbol-chip,
.status-chip {
  display: inline-flex;
  align-items: center;
  gap: 10px;
  padding: 10px 14px;
  font-size: 13px;
}

.chip-label {
  color: var(--workspace-muted);
}

.chip-value {
  font-family: "JetBrains Mono", "SFMono-Regular", monospace;
}

.status-chip.loading {
  border-color: rgba(246, 196, 83, 0.36);
}

.status-dot {
  width: 8px;
  height: 8px;
  border-radius: 999px;
  background: var(--workspace-green);
  box-shadow: 0 0 12px rgba(30, 215, 96, 0.55);
}

.status-chip.loading .status-dot {
  background: var(--workspace-amber);
  box-shadow: 0 0 12px rgba(246, 196, 83, 0.5);
}

.workspace-body {
  flex: 1;
  min-height: 0;
  display: grid;
  grid-template-columns: 300px minmax(0, 1fr) 320px;
  gap: 16px;
}

.workspace-body.left-collapsed {
  grid-template-columns: 72px minmax(0, 1fr) 320px;
}

.workspace-body.right-collapsed {
  grid-template-columns: 300px minmax(0, 1fr) 72px;
}

.workspace-body.left-collapsed.right-collapsed {
  grid-template-columns: 72px minmax(0, 1fr) 72px;
}

.side-drawer {
  min-height: 0;
  border-radius: 20px;
  display: flex;
  flex-direction: column;
  overflow: hidden;
}

.side-drawer.collapsed {
  width: 72px;
}

.left-drawer.collapsed,
.right-drawer.collapsed {
  min-width: 72px;
}

.drawer-header,
.bottom-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 10px;
  padding: 16px 18px;
  border-bottom: 1px solid rgba(148, 163, 184, 0.12);
}

.drawer-title-group,
.bottom-header h2 {
  min-width: 0;
}

.drawer-title-group h2,
.bottom-header h2,
.stage-title h1 {
  margin: 4px 0 0;
  font-size: 22px;
  font-weight: 600;
}

.drawer-toggle,
.ghost-btn {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  border-radius: 12px;
  border: 1px solid rgba(148, 163, 184, 0.16);
  background: rgba(15, 23, 42, 0.78);
  color: rgba(226, 232, 240, 0.86);
}

.drawer-toggle {
  width: 36px;
  height: 36px;
}

.ghost-btn {
  height: 34px;
  padding: 0 12px;
}

.drawer-tabs {
  display: grid;
  grid-template-columns: repeat(2, minmax(0, 1fr));
  gap: 10px;
  padding: 14px 18px 0;
}

.drawer-tab {
  height: 42px;
  display: inline-flex;
  align-items: center;
  justify-content: space-between;
  padding: 0 14px;
  border-radius: 12px;
  border: 1px solid rgba(148, 163, 184, 0.14);
  background: rgba(15, 23, 42, 0.76);
  color: rgba(226, 232, 240, 0.82);

  &.active {
    border-color: rgba(55, 166, 255, 0.4);
    background: rgba(55, 166, 255, 0.14);
  }

  span {
    color: var(--workspace-muted);
  }
}

.drawer-content,
.info-drawer {
  flex: 1;
  min-height: 0;
  overflow: auto;
  padding: 18px;
}

.drawer-empty {
  display: flex;
  flex-direction: column;
  gap: 6px;
  padding: 18px;
  border-radius: 16px;
  background: rgba(15, 23, 42, 0.7);
  border: 1px dashed rgba(148, 163, 184, 0.18);
  color: var(--workspace-muted);

  p {
    margin: 0;
    color: var(--workspace-text);
  }

  span {
    font-size: 13px;
  }
}

.stock-list-item {
  width: 100%;
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 12px;
  margin-bottom: 10px;
  padding: 14px;
  border: 1px solid rgba(148, 163, 184, 0.12);
  border-radius: 16px;
  background: rgba(15, 23, 42, 0.66);
  color: inherit;
  text-align: left;

  &:hover,
  &.active {
    border-color: rgba(55, 166, 255, 0.36);
    background: rgba(55, 166, 255, 0.14);
  }
}

.drawer-rail {
  flex: 1;
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: flex-start;
  gap: 14px;
  padding: 20px 10px;
}

.rail-pill {
  width: 100%;
  min-height: 42px;
  border-radius: 999px;
  border: 1px solid rgba(148, 163, 184, 0.14);
  background: rgba(15, 23, 42, 0.82);
  color: rgba(226, 232, 240, 0.86);
  writing-mode: vertical-rl;
  text-orientation: mixed;
  padding: 10px 0;
}

.info-rail {
  justify-content: center;
  color: rgba(191, 219, 254, 0.8);
  letter-spacing: 0.18em;
  text-transform: uppercase;
}

.chart-stage {
  min-width: 0;
  display: flex;
  flex-direction: column;
  gap: 16px;
}

.stage-header {
  border-radius: 20px;
  padding: 18px 20px;
  display: flex;
  align-items: flex-start;
  justify-content: space-between;
  gap: 18px;
}

.stage-title {
  min-width: 0;
}

.title-row {
  display: flex;
  align-items: center;
  gap: 12px;
  flex-wrap: wrap;
}

.title-meta {
  display: flex;
  gap: 14px;
  margin-top: 10px;
  color: var(--workspace-muted);
  flex-wrap: wrap;
}

.quote-strip {
  display: grid;
  grid-template-columns: repeat(3, minmax(0, 1fr));
  gap: 10px;
  min-width: min(360px, 100%);
}

.quote-card,
.placeholder-metric,
.metric-item,
.placeholder-card,
.panel-card {
  border-radius: 18px;
  border: 1px solid rgba(148, 163, 184, 0.14);
  background: rgba(15, 23, 42, 0.7);
}

.quote-card {
  padding: 14px 16px;
  display: flex;
  flex-direction: column;
  gap: 6px;

  strong {
    font-size: 22px;
    font-family: "JetBrains Mono", "SFMono-Regular", monospace;
  }
}

.price-up {
  color: var(--workspace-green);
}

.price-down {
  color: var(--workspace-red);
}

.price-flat {
  color: rgba(226, 232, 240, 0.88);
}

.chart-shell {
  flex: 1;
  min-height: 0;
  border-radius: 24px;
  padding: 12px;
  background: linear-gradient(
    180deg,
    rgba(10, 20, 35, 0.96) 0%,
    rgba(6, 12, 20, 0.98) 100%
  );
}

.panel-card {
  padding: 16px;
  margin-bottom: 14px;
}

.panel-card-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 12px;
  margin-bottom: 16px;
  font-weight: 600;
}

.panel-loading {
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  gap: 12px;
  padding: 28px 12px;
  color: var(--workspace-muted);

  p {
    margin: 0;
    font-size: 13px;
  }
}

.spinner {
  width: 30px;
  height: 30px;
  border-radius: 999px;
  border: 3px solid rgba(148, 163, 184, 0.16);
  border-top-color: var(--workspace-blue);
  animation: spin 1s linear infinite;
}

@keyframes spin {
  to {
    transform: rotate(360deg);
  }
}

.metric-grid {
  display: grid;
  grid-template-columns: repeat(2, minmax(0, 1fr));
  gap: 10px;
}

.metric-item {
  padding: 14px;
  display: flex;
  flex-direction: column;
  gap: 6px;

  span {
    color: var(--workspace-muted);
    font-size: 12px;
  }

  strong {
    font-size: 16px;
  }
}

.info-list {
  margin-top: 16px;
  display: flex;
  flex-direction: column;
  gap: 12px;
}

.info-row {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 12px;
  padding-bottom: 12px;
  border-bottom: 1px solid rgba(148, 163, 184, 0.08);

  span {
    color: var(--workspace-muted);
  }

  strong {
    text-align: right;
  }
}

.action-stack {
  display: flex;
  flex-direction: column;
  gap: 10px;
}

.action-btn {
  min-height: 44px;
  border-radius: 14px;
  border: 1px solid rgba(148, 163, 184, 0.14);
  background: rgba(15, 23, 42, 0.82);
  color: var(--workspace-text);
  font-size: 14px;
  font-weight: 500;

  &:hover:not(:disabled) {
    border-color: rgba(55, 166, 255, 0.36);
    background: rgba(55, 166, 255, 0.12);
  }

  &:disabled {
    opacity: 0.48;
    cursor: not-allowed;
  }

  &.primary {
    background: linear-gradient(
      135deg,
      rgba(55, 166, 255, 0.28),
      rgba(30, 215, 96, 0.2)
    );
    border-color: rgba(55, 166, 255, 0.44);
  }
}

.bottom-panel {
  border-radius: 20px;
  overflow: hidden;
}

.bottom-panel.collapsed {
  .bottom-header {
    border-bottom: none;
  }
}

.bottom-content {
  display: grid;
  grid-template-columns: minmax(0, 1.4fr) minmax(280px, 0.9fr);
  gap: 14px;
  padding: 18px;
}

.placeholder-card {
  padding: 18px;

  h3 {
    margin: 10px 0 8px;
    font-size: 20px;
  }

  p {
    margin: 0;
    color: var(--workspace-muted);
    line-height: 1.6;
  }
}

.placeholder-metrics {
  display: grid;
  grid-template-columns: repeat(3, minmax(0, 1fr));
  gap: 12px;
}

.placeholder-metric {
  padding: 16px;
  display: flex;
  flex-direction: column;
  gap: 10px;

  span {
    color: var(--workspace-muted);
    font-size: 13px;
  }

  strong {
    font-size: 18px;
  }
}

@media (max-width: 1400px) {
  .workspace-body {
    grid-template-columns: 260px minmax(0, 1fr) 280px;
  }

  .quote-strip {
    min-width: 0;
  }
}

@media (max-width: 1180px) {
  .workspace-body {
    grid-template-columns: minmax(0, 1fr);
  }

  .left-drawer,
  .right-drawer {
    width: 100%;
  }

  .side-drawer.collapsed {
    width: 100%;
  }

  .drawer-rail {
    flex-direction: row;
    justify-content: flex-start;
  }

  .rail-pill {
    width: auto;
    writing-mode: initial;
    padding: 0 14px;
  }

  .stage-header,
  .bottom-content {
    grid-template-columns: 1fr;
  }
}

@media (max-width: 900px) {
  .workspace-page {
    padding: 12px;
  }

  .workspace-toolbar,
  .stage-header {
    padding: 14px;
  }

  .search-box {
    width: 100%;
  }

  .toolbar-left,
  .toolbar-right,
  .stage-header {
    width: 100%;
    flex-direction: column;
    align-items: stretch;
  }

  .quote-strip,
  .placeholder-metrics,
  .metric-grid {
    grid-template-columns: repeat(2, minmax(0, 1fr));
  }
}

@media (max-width: 640px) {
  .period-switcher,
  .quote-strip,
  .placeholder-metrics,
  .metric-grid {
    grid-template-columns: 1fr;
    display: grid;
  }

  .drawer-tabs {
    grid-template-columns: 1fr;
  }

  .title-row {
    align-items: flex-start;
    flex-direction: column;
  }

  .info-row {
    flex-direction: column;
    align-items: flex-start;

    strong {
      text-align: left;
    }
  }
}
</style>
