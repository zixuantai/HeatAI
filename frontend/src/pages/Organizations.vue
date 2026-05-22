<template>
  <div class="organizations-container">
    <div class="organizations-header">
      <h1 class="organizations-title">组织管理</h1>
    </div>
    <div class="organizations-content">
      <el-empty description="功能开发中" />
    </div>
  </div>
</template>

<script setup lang="ts">
</script>

<style scoped>
.organizations-container {
  height: 100%;
  display: flex;
  flex-direction: column;
  background: var(--color-bg);
}

.organizations-header {
  padding: 40px 48px 0;
  border-bottom: 1px solid var(--color-border);
  background: var(--color-surface);
}

.organizations-title {
  font-size: 28px;
  font-weight: var(--font-weight-bold);
  color: var(--color-text-main);
  margin-bottom: 16px;
  letter-spacing: -0.01em;
}

.organizations-content {
  flex: 1;
  padding: 24px 48px;
  overflow-y: auto;
  display: flex;
  align-items: center;
  justify-content: center;
}
</style>
