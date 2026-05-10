<template>
  <div class="browse-page">
    <n-h2>Browse Data</n-h2>
    <n-p depth="3">View the uploaded factor and price data with pagination.</n-p>

    <n-tabs type="line" default-value="factor">
      <n-tab-pane name="factor" tab="Factor Data">
        <div class="table-toolbar">
          <n-input
            v-model:value="factorFilter"
            placeholder="Filter by asset..."
            clearable
            style="width: 200px;"
          />
          <n-text depth="3">Total: {{ factorTotal }} rows</n-text>
        </div>
        <n-data-table
          data-testid="factor-data-table"
          :columns="factorColumns"
          :data="factorData"
          :loading="factorLoading"
          :pagination="factorPagination"
          :bordered="false"
          :single-line="false"
        />
      </n-tab-pane>

      <n-tab-pane name="prices" tab="Price Data">
        <div class="table-toolbar">
          <n-input
            v-model:value="priceFilter"
            placeholder="Filter by asset..."
            clearable
            style="width: 200px;"
          />
          <n-text depth="3">Total: {{ priceTotal }} rows</n-text>
        </div>
        <n-data-table
          data-testid="price-data-table"
          :columns="priceColumns"
          :data="priceData"
          :loading="priceLoading"
          :pagination="pricePagination"
          :bordered="false"
          :single-line="false"
        />
      </n-tab-pane>
    </n-tabs>
  </div>
</template>

<script setup lang="ts">
import { ref, computed, watch, onMounted, h } from 'vue';
import { useRoute } from 'vue-router';
import { NButton, NTag } from 'naive-ui';
import { getFactorData, getPriceData } from '@/api/data';

const route = useRoute();
const sessionId = computed(() => route.params.sid as string);

// Factor data
const factorData = ref<any[]>([]);
const factorTotal = ref(0);
const factorLoading = ref(false);
const factorPage = ref(1);
const factorPageSize = ref(50);
const factorFilter = ref('');

// Price data
const priceData = ref<any[]>([]);
const priceTotal = ref(0);
const priceLoading = ref(false);
const pricePage = ref(1);
const pricePageSize = ref(50);
const priceFilter = ref('');

const factorColumns = [
  { title: 'Date', key: 'date', width: 120, sortable: true },
  { title: 'Asset', key: 'asset', width: 100 },
  { title: 'Factor Value', key: 'factor_value', width: 120 },
];

const priceColumns = [
  { title: 'Date', key: 'date', width: 120, sortable: true },
  { title: 'Asset', key: 'asset', width: 100 },
  { title: 'Price', key: 'price', width: 120 },
];

const factorPagination = computed(() => ({
  page: factorPage.value,
  pageSize: factorPageSize.value,
  itemCount: factorTotal.value,
  onChange: (p: number) => { factorPage.value = p; loadFactorData(); },
  onUpdatePageSize: (s: number) => { factorPageSize.value = s; factorPage.value = 1; loadFactorData(); },
}));

const pricePagination = computed(() => ({
  page: pricePage.value,
  pageSize: pricePageSize.value,
  itemCount: priceTotal.value,
  onChange: (p: number) => { pricePage.value = p; loadPriceData(); },
  onUpdatePageSize: (s: number) => { pricePageSize.value = s; pricePage.value = 1; loadPriceData(); },
}));

async function loadFactorData() {
  factorLoading.value = true;
  try {
    const resp = await getFactorData(sessionId.value, {
      page: factorPage.value,
      page_size: factorPageSize.value,
      asset: factorFilter.value || undefined,
    });
    factorData.value = resp.data;
    factorTotal.value = resp.total_rows;
  } catch {
    factorData.value = [];
  } finally {
    factorLoading.value = false;
  }
}

async function loadPriceData() {
  priceLoading.value = true;
  try {
    const resp = await getPriceData(sessionId.value, {
      page: pricePage.value,
      page_size: pricePageSize.value,
      asset: priceFilter.value || undefined,
    });
    priceData.value = resp.data;
    priceTotal.value = resp.total_rows;
  } catch {
    priceData.value = [];
  } finally {
    priceLoading.value = false;
  }
}

watch(factorFilter, () => { factorPage.value = 1; loadFactorData(); });
watch(priceFilter, () => { pricePage.value = 1; loadPriceData(); });

onMounted(() => {
  loadFactorData();
  loadPriceData();
});
</script>

<style scoped>
.browse-page {
  max-width: 1200px;
  margin: 0 auto;
}
.table-toolbar {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 16px;
}
</style>
