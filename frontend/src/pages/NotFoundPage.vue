<template>
  <div class="not-found">
    <n-result status="404" title="Page Not Found" description="The page you're looking for doesn't exist.">
      <template #footer>
        <n-button type="primary" @click="$router.push('/sessions')">Back to Sessions</n-button>
      </template>
    </n-result>
  </div>
</template>

<style scoped>
.not-found {
  display: flex;
  justify-content: center;
  align-items: center;
  min-height: 60vh;
}
</style>
