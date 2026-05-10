import { ref, computed } from 'vue';

export function usePagination(defaultPageSize = 50) {
  const page = ref(1);
  const pageSize = ref(defaultPageSize);
  const total = ref(0);

  const pagination = computed(() => ({
    page: page.value,
    pageSize: pageSize.value,
    itemCount: total.value,
    onChange: (p: number) => { page.value = p; },
    onUpdatePageSize: (s: number) => {
      pageSize.value = s;
      page.value = 1;
    },
  }));

  function reset() {
    page.value = 1;
    total.value = 0;
  }

  return { page, pageSize, total, pagination, reset };
}
