<script setup>
import { ref } from 'vue';
import { validateClaim } from '../services/api';

const file = ref(null);
const previewUrl = ref(null);
const claimType = ref('medical');
const loading = ref(false);
const result = ref(null);
const error = ref(null);

const onFileChange = (e) => {
  const selected = e.target.files[0];
  if (selected) {
    file.value = selected;
    previewUrl.value = URL.createObjectURL(selected);
    result.value = null;
    error.value = null;
  }
};

const convertToBase64 = (file) => {
  return new Promise((resolve, reject) => {
    const reader = new FileReader();
    reader.readAsDataURL(file);
    reader.onload = () => resolve(reader.result);
    reader.onerror = error => reject(error);
  });
};

const submitClaim = async () => {
  if (!file.value) return;
  
  loading.value = true;
  error.value = null;
  result.value = null;
  
  try {
    const base64 = await convertToBase64(file.value);
    const response = await validateClaim(base64, claimType.value);
    
    // Parse the ADK response structure
    // Expected: [{ content: { parts: [{ text: JSON_STRING }] } }]
    if (response && response.length > 0 && response[0].content && response[0].content.parts) {
       const text = response[0].content.parts[0].text;
       // Try to clean markdown code blocks if any
       const jsonStr = text.replace(/```json\n|\n```/g, '');
       result.value = JSON.parse(jsonStr);
    } else {
       error.value = "Unexpected response format";
    }
  } catch (err) {
    error.value = err.message || "Failed to validate claim";
  } finally {
    loading.value = false;
  }
};
</script>

<template>
  <div class="upload-container">
    <div class="form-group">
      <label>Claim Type:</label>
      <select v-model="claimType">
        <option value="medical">Medical</option>
        <option value="dental">Dental</option>
        <option value="vision">Vision</option>
      </select>
    </div>

    <div class="drop-zone">
      <input type="file" @change="onFileChange" accept="image/*" />
      <p v-if="!file">Drag & drop or click to upload claim image</p>
      <div v-else class="preview">
        <img :src="previewUrl" alt="Claim Preview" />
      </div>
    </div>

    <button @click="submitClaim" :disabled="!file || loading" class="submit-btn">
      {{ loading ? 'Validating...' : 'Validate Claim' }}
    </button>

    <div v-if="error" class="error-alert">
      {{ error }}
    </div>

    <div v-if="result" class="result-card" :class="result.status">
      <h3>Validation Result: {{ result.status.toUpperCase() }}</h3>
      <p>{{ result.reason }}</p>
      <div v-if="result.data" class="data-dump">
        <pre>{{ JSON.stringify(result.data, null, 2) }}</pre>
      </div>
    </div>
  </div>
</template>

<style scoped>
.upload-container {
  display: flex;
  flex-direction: column;
  gap: 1.5rem;
  max-width: 500px;
  margin: 0 auto;
}

.form-group {
  display: flex;
  flex-direction: column;
  align-items: flex-start;
}

select {
  padding: 0.5rem;
  width: 100%;
  font-size: 1rem;
}

.drop-zone {
  border: 2px dashed #646cff;
  border-radius: 8px;
  padding: 2rem;
  text-align: center;
  position: relative;
  min-height: 200px;
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  cursor: pointer;
}

.drop-zone input {
  position: absolute;
  width: 100%;
  height: 100%;
  opacity: 0;
  cursor: pointer;
}

.preview img {
  max-width: 100%;
  max-height: 300px;
  border-radius: 4px;
}

.submit-btn {
  padding: 1rem;
  background-color: #646cff;
  color: white;
  border: none;
  border-radius: 4px;
  font-size: 1.1rem;
  cursor: pointer;
  transition: background-color 0.2s;
}

.submit-btn:disabled {
  background-color: #4a4a4a;
  cursor: not-allowed;
}

.submit-btn:hover:not(:disabled) {
  background-color: #535bf2;
}

.result-card {
  padding: 1.5rem;
  border-radius: 8px;
  background-color: #2a2a2a;
  text-align: left;
}

.result-card.valid {
  border-left: 5px solid #4CAF50;
}

.result-card.invalid {
  border-left: 5px solid #F44336;
}

.error-alert {
  color: #F44336;
  padding: 1rem;
  background-color: #ffebee;
  border-radius: 4px;
}

.data-dump {
  background: #1a1a1a;
  padding: 1rem;
  margin-top: 1rem;
  border-radius: 4px;
  overflow-x: auto;
}
</style>
