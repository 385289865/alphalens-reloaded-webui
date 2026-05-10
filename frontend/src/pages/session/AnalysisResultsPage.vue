<template>
  <div class="results-page">
    <n-h2>Analysis Results</n-h2>

    <n-spin :show="resultsStore.loading">
      <template v-if="resultsStore.results">
        <div class="config-summary" data-testid="config-summary-bar">
          <n-tag v-for="p in configPeriods" :key="p" size="small">Period: {{ p }}d</n-tag>
          <n-tag size="small" :type="configLongShort ? 'success' : 'default'">
            {{ configLongShort ? 'Long/Short' : 'Long Only' }}
          </n-tag>
          <n-tag size="small">Quantiles: {{ configQuantiles }}</n-tag>
        </div>

        <n-tabs type="line" default-value="summary" @update:value="handleTabSwitch">
          <n-tab-pane name="summary" tab="Summary" data-testid="tab-summary">
            <n-grid :cols="4" :x-gap="12" :y-gap="12" style="margin-bottom: 24px;">
              <n-gi v-for="m in summaryMetrics" :key="m.label">
                <n-card :title="m.label" size="small" hoverable>
                  <n-text :type="m.color || 'default'" style="font-size: 20px; font-weight: 700;">
                    {{ m.value !== null && m.value !== undefined ? m.value : '-' }}
                  </n-text>
                </n-card>
              </n-gi>
            </n-grid>

            <n-card title="Alpha / Beta" size="small" style="margin-bottom: 16px;">
              <n-data-table
                :columns="alphaBetaColumns"
                :data="alphaBetaData"
                :bordered="false"
                :loading="resultsStore.summaryLoading"
                :max-height="300"
              />
            </n-card>

            <n-card title="IC Summary" size="small">
              <n-data-table
                :columns="icSummaryColumns"
                :data="icSummaryData"
                :bordered="false"
                :loading="resultsStore.summaryLoading"
                :max-height="300"
              />
            </n-card>
          </n-tab-pane>

          <n-tab-pane name="ic" tab="IC Analysis" data-testid="tab-ic">
            <div v-if="icChartUrl" style="margin-bottom: 16px;">
              <img :src="icChartUrl" alt="IC Time Series" style="max-width: 100%;" />
            </div>
            <n-card title="IC Detail" size="small">
              <n-data-table
                data-testid="ic-detail-table"
                :columns="icDetailColumns"
                :data="icDetailData"
                :loading="resultsStore.icLoading"
                :bordered="false"
                :max-height="500"
              />
            </n-card>
          </n-tab-pane>

          <n-tab-pane name="returns" tab="Returns">
            <n-grid :cols="2" :x-gap="16" :y-gap="16">
              <n-gi>
                <img v-if="returnsBarChartUrl" :src="returnsBarChartUrl" alt="Quantile Returns" style="max-width: 100%;" />
              </n-gi>
              <n-gi>
                <img v-if="cumulativeReturnsChartUrl" :src="cumulativeReturnsChartUrl" alt="Cumulative Returns" style="max-width: 100%;" />
              </n-gi>
            </n-grid>
            <n-card title="Returns Detail" size="small" style="margin-top: 16px;">
              <n-data-table
                :columns="returnsColumns"
                :data="returnsData"
                :loading="resultsStore.returnsLoading"
                :bordered="false"
                :max-height="400"
              />
            </n-card>
          </n-tab-pane>

          <n-tab-pane name="alpha-beta" tab="Alpha / Beta">
            <n-card title="Alpha & Beta by Period" size="small">
              <n-data-table
                :columns="alphaBetaColumns"
                :data="alphaBetaData"
                :loading="resultsStore.alphaBetaLoading"
                :bordered="false"
              />
            </n-card>
          </n-tab-pane>

          <n-tab-pane name="turnover" tab="Turnover">
            <n-grid :cols="2" :x-gap="16" :y-gap="16">
              <n-gi>
                <img v-if="turnoverChartUrl" :src="turnoverChartUrl" alt="Turnover" style="max-width: 100%;" />
              </n-gi>
              <n-gi>
                <img v-if="autocorrelationChartUrl" :src="autocorrelationChartUrl" alt="Autocorrelation" style="max-width: 100%;" />
              </n-gi>
            </n-grid>
            <n-card title="Turnover Detail" size="small" style="margin-top: 16px;">
              <n-data-table
                :columns="turnoverColumns"
                :data="turnoverData"
                :loading="resultsStore.turnoverLoading"
                :bordered="false"
                :max-height="400"
              />
            </n-card>
          </n-tab-pane>

          <n-tab-pane name="charts" tab="Charts" data-testid="tab-charts">
            <n-grid :cols="2" :x-gap="16" :y-gap="16">
              <n-gi v-for="(url, ct) in chartUrls" :key="ct">
                <n-card :title="chartLabels[ct] || ct" size="small" hoverable>
                  <img :src="url" :alt="ct" style="max-width: 100%;" loading="lazy" />
                </n-card>
              </n-gi>
            </n-grid>
          </n-tab-pane>
        </n-tabs>

        <div class="results-actions" style="margin-top: 24px;">
          <n-button @click="rerun" data-testid="btn-rerun-analysis">Re-run Analysis</n-button>
        </div>
      </template>

      <n-empty v-else-if="!resultsStore.loading" description="No results data loaded." />
    </n-spin>
  </div>
</template>

<script setup lang="ts">
import { computed, onMounted, ref } from 'vue';
import { useRoute, useRouter } from 'vue-router';
import { useResultsStore } from '@/stores/resultsStore';

const route = useRoute();
const router = useRouter();
const resultsStore = useResultsStore();

const sessionId = computed(() => route.params.sid as string);
const analysisId = computed(() => route.params.aid as string);

const configPeriods = computed(() => (resultsStore.config?.periods as number[]) || []);
const configQuantiles = computed(() => resultsStore.config?.quantiles ?? 5);
const configLongShort = computed(() => resultsStore.config?.long_short ?? true);

// ── Charts ──
const chartUrls = ref<Record<string, string>>({});
const icChartUrl = computed(() => chartUrls.value['ic_time_series']);
const returnsBarChartUrl = computed(() => chartUrls.value['quantile_returns_bar']);
const cumulativeReturnsChartUrl = computed(() => chartUrls.value['cumulative_returns']);
const turnoverChartUrl = computed(() => chartUrls.value['quantile_turnover']);
const autocorrelationChartUrl = computed(() => chartUrls.value['rank_autocorrelation']);

const chartLabels: Record<string, string> = {
  ic_time_series: 'IC Time Series',
  ic_histogram: 'IC Histogram',
  ic_qq_plot: 'IC Q-Q Plot',
  quantile_returns_bar: 'Quantile Returns',
  cumulative_returns: 'Cumulative Returns',
  mean_quantile_spread: 'Mean Quantile Spread',
  quantile_turnover: 'Quantile Turnover',
  rank_autocorrelation: 'Rank Autocorrelation',
};

// ── Summary metrics ──
const summaryMetrics = computed(() => {
  const ab = resultsStore.results?.summary_tables?.alpha_beta || [];
  const alphaRow = ab.find((r: any) => r.metric === 'Alpha');
  const betaRow = ab.find((r: any) => r.metric === 'Beta');
  const icData = resultsStore.results?.ic?.data || [];
  const meanIc = icData.length ? icData.reduce((s: number, r: any) => s + (r.ic_value || 0), 0) / icData.length : null;

  return [
    { label: 'Mean IC', value: meanIc?.toFixed(4), color: meanIc && meanIc > 0 ? 'success' : 'error' },
    { label: 'Alpha (1D)', value: alphaRow ? alphaRow['1D']?.toFixed(6) : '-', color: 'info' },
    { label: 'Beta (1D)', value: betaRow ? betaRow['1D']?.toFixed(4) : '-', color: 'info' },
    { label: 'Periods', value: configPeriods.value.join(', '), color: 'default' },
  ];
});

// ── Table columns ──
const alphaBetaColumns = [
  { title: 'Metric', key: 'metric', width: 100 },
  { title: 'Period 1D', key: '1D', width: 100 },
  { title: 'Period 5D', key: '5D', width: 100 },
  { title: 'Period 10D', key: '10D', width: 100 },
];

const icSummaryColumns = [
  { title: 'Date', key: 'date', width: 120 },
  { title: 'Period', key: 'period', width: 80 },
  { title: 'IC Value', key: 'ic_value', width: 100 },
];

const icDetailColumns = [
  { title: 'Date', key: 'date', width: 120 },
  { title: 'IC Value', key: 'ic_value', width: 120 },
];

const returnsColumns = [
  { title: 'Quantile', key: 'factor_quantile', width: 100 },
  { title: 'Period', key: 'period', width: 80 },
  { title: 'Mean Return', key: 'mean_return', width: 120 },
];

const turnoverColumns = [
  { title: 'Date', key: 'date', width: 120 },
  { title: 'Period', key: 'period', width: 80 },
  { title: 'Quantile', key: 'quantile', width: 80 },
  { title: 'Turnover', key: 'turnover', width: 100 },
];

// ── Table data ──
const alphaBetaData = computed(() => {
  const ab = resultsStore.results?.summary_tables?.alpha_beta || [];
  // Group by metric
  const grouped: Record<string, any> = {};
  for (const row of ab) {
    if (!grouped[row.metric]) grouped[row.metric] = { metric: row.metric };
    grouped[row.metric][row.period] = row.value;
  }
  return Object.values(grouped);
});

const icSummaryData = computed(() => resultsStore.results?.ic?.data || []);
const icDetailData = computed(() => {
  const icData = resultsStore.results?.ic?.data || [];
  // Group by date, use mean IC value across periods
  const byDate: Record<string, any> = {};
  for (const row of icData) {
    if (!byDate[row.date]) byDate[row.date] = { date: row.date, ic_value: 0, count: 0 };
    byDate[row.date].ic_value += row.ic_value;
    byDate[row.date].count += 1;
  }
  return Object.values(byDate).map((d: any) => ({ date: d.date, ic_value: +(d.ic_value / d.count).toFixed(4) }));
});

const returnsData = computed(() => resultsStore.results?.summary_tables?.returns_by_quantile || []);

const turnoverData = computed(() => resultsStore.results?.turnover?.turnover || []);

// ── Actions ──
async function loadTabData(tab: string) {
  const aid = analysisId.value;
  if (tab === 'summary') {
    await resultsStore.fetchSummaryTables(aid);
  } else if (tab === 'ic') {
    const ic = await resultsStore.fetchIc(aid);
    if (ic?.data) icDetailData; // trigger reactivity
  } else if (tab === 'returns') {
    await resultsStore.fetchReturns(aid);
  } else if (tab === 'alpha-beta') {
    await resultsStore.fetchAlphaBeta(aid);
  } else if (tab === 'turnover') {
    await resultsStore.fetchTurnover(aid);
  }
}

async function loadCharts() {
  chartUrls.value = await resultsStore.fetchAllCharts(analysisId.value);
}

function handleTabSwitch(tab: string) {
  loadTabData(tab);
}

function rerun() {
  router.push(`/sessions/${sessionId.value}/configure`);
}

onMounted(async () => {
  await resultsStore.fetchAllResults(analysisId.value);
  await resultsStore.fetchSummaryTables(analysisId.value);
  loadCharts();
});
</script>

<style scoped>
.results-page {
  max-width: 1200px;
  margin: 0 auto;
}
.config-summary {
  display: flex;
  gap: 8px;
  margin-bottom: 16px;
  flex-wrap: wrap;
}
</style>
