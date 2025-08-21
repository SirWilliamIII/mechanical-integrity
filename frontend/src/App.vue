<script setup lang="ts">
import { RouterLink, RouterView } from 'vue-router'
</script>

<template>
  <div class="app-layout">
    <header class="app-header">
      <div class="header-content">
        <div class="logo-section">
          <i class="pi pi-cog" style="font-size: 2rem; color: var(--p-primary-color);"></i>
          <h1>Mechanical Integrity</h1>
        </div>
        
        <nav class="main-nav">
          <RouterLink to="/" class="nav-link">
            <i class="pi pi-home"></i>
            Dashboard
          </RouterLink>
          <RouterLink to="/inspections" class="nav-link">
            <i class="pi pi-wrench"></i>
            Inspections
          </RouterLink>
        </nav>
      </div>
    </header>

    <main class="app-main">
      <RouterView />
    </main>
    
    <Toast />
  </div>
</template>

<style scoped>
.app-layout {
  min-height: 100vh;
  display: flex;
  flex-direction: column;
}

.app-header {
  background: var(--p-surface-card);
  border-bottom: 1px solid var(--p-surface-border);
  padding: 1rem 0;
  box-shadow: 0 2px 4px rgba(0, 0, 0, 0.1);
}

.header-content {
  max-width: 1200px;
  margin: 0 auto;
  padding: 0 1rem;
  display: flex;
  align-items: center;
  justify-content: space-between;
}

.logo-section {
  display: flex;
  align-items: center;
  gap: 0.75rem;
}

.logo-section h1 {
  margin: 0;
  font-size: 1.5rem;
  font-weight: 600;
  color: var(--p-text-color);
}

.main-nav {
  display: flex;
  gap: 0.5rem;
}

.nav-link {
  display: flex;
  align-items: center;
  gap: 0.5rem;
  padding: 0.75rem 1rem;
  border-radius: var(--p-border-radius);
  text-decoration: none;
  color: var(--p-text-color-secondary);
  font-weight: 500;
  transition: all 0.2s ease;
}

.nav-link:hover {
  background: var(--p-surface-hover);
  color: var(--p-text-color);
}

.nav-link.router-link-active {
  background: var(--p-primary-color);
  color: var(--p-primary-contrast-color);
}

.app-main {
  flex: 1;
  background: var(--p-surface-ground);
}

@media (max-width: 768px) {
  .header-content {
    flex-direction: column;
    gap: 1rem;
  }
  
  .main-nav {
    justify-content: center;
    width: 100%;
  }
  
  .nav-link {
    flex: 1;
    justify-content: center;
  }
}
</style>
