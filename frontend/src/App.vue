<script setup>
import ClaimUpload from './components/ClaimUpload.vue'
</script>

<template>
  <div class="app-container">
    <header>
      <h1>SmartClaim Validator</h1>
      <p>Powered by Gemini & MCP</p>
    </header>
    <main>
      <ClaimUpload />
    </main>
  </div>
</template>

<style scoped>
.app-container {
  max-width: 800px;
  margin: 0 auto;
  padding: 2rem;
}

header {
  margin-bottom: 2rem;
}

h1 {
  font-size: 2.5rem;
  color: #646cff;
}
</style>
