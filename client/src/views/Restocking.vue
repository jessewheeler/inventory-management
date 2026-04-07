<template>
  <div class="restocking">
    <div class="page-header">
      <h2>{{ t('restocking.title') }}</h2>
      <p>{{ t('restocking.description') }}</p>
    </div>

    <div v-if="loading" class="loading">{{ t('common.loading') }}</div>
    <div v-else-if="error && !orderSuccess" class="error">{{ error }}</div>
    <div v-else>
      <div v-if="orderSuccess" class="success-message">
        {{ t('restocking.orderPlaced') }}
      </div>

      <div class="budget-card">
        <label class="budget-label">{{ t('restocking.budgetSlider') }}</label>
        <div class="budget-display">{{ currencySymbol }}{{ budget.toLocaleString() }}</div>
        <input
          type="range"
          class="budget-slider"
          v-model.number="budget"
          :min="1000"
          :max="50000"
          :step="500"
        />
        <div class="slider-bounds">
          <span>{{ currencySymbol }}1,000</span>
          <span>{{ currencySymbol }}50,000</span>
        </div>
      </div>

      <div class="summary-stats">
        <div class="summary-stat-card">
          <div class="summary-stat-label">{{ t('restocking.totalCost') }}</div>
          <div class="summary-stat-value">{{ currencySymbol }}{{ totalCost.toLocaleString() }}</div>
        </div>
        <div class="summary-stat-card">
          <div class="summary-stat-label">{{ t('restocking.remainingBudget') }}</div>
          <div :class="['summary-stat-value', { 'over-budget': remainingBudget < 0 }]">
            {{ currencySymbol }}{{ remainingBudget.toLocaleString() }}
          </div>
        </div>
        <div class="summary-stat-card">
          <div class="summary-stat-label">{{ t('restocking.itemsSelected', { count: selectedRecommendations.length }) }}</div>
          <div class="summary-stat-value">{{ selectedRecommendations.length }}</div>
        </div>
      </div>

      <div class="card">
        <div class="card-header">
          <h3 class="card-title">{{ t('restocking.recommendations') }}</h3>
          <button
            class="place-order-btn"
            :disabled="selectedRecommendations.length === 0 || orderSubmitting"
            @click="placeOrder"
          >
            {{ t('restocking.placeOrder') }}
          </button>
        </div>

        <div v-if="selectedRecommendations.length === 0" class="no-recommendations">
          {{ t('restocking.noRecommendations') }}
        </div>
        <div v-else class="table-container">
          <table>
            <thead>
              <tr>
                <th>{{ t('restocking.table.sku') }}</th>
                <th>{{ t('restocking.table.itemName') }}</th>
                <th>{{ t('restocking.table.demandGap') }}</th>
                <th>{{ t('restocking.table.trend') }}</th>
                <th>{{ t('restocking.table.unitCost') }}</th>
                <th>{{ t('restocking.table.quantity') }}</th>
                <th>{{ t('restocking.table.totalCost') }}</th>
                <th>{{ t('restocking.table.priority') }}</th>
              </tr>
            </thead>
            <tbody>
              <tr v-for="rec in selectedRecommendations" :key="rec.item_sku">
                <td><strong>{{ rec.item_sku }}</strong></td>
                <td>{{ rec.item_name }}</td>
                <td>{{ rec.demand_gap }}</td>
                <td>
                  <span :class="['badge', rec.trend]">{{ t('trends.' + rec.trend) }}</span>
                </td>
                <td>{{ currencySymbol }}{{ rec.unit_cost.toLocaleString() }}</td>
                <td>{{ rec.recommended_quantity }}</td>
                <td><strong>{{ currencySymbol }}{{ rec.total_cost.toLocaleString() }}</strong></td>
                <td>{{ rec.priority_score.toFixed(1) }}</td>
              </tr>
            </tbody>
          </table>
        </div>
      </div>
    </div>
  </div>
</template>

<script>
import { ref, computed, onMounted } from 'vue'
import { api } from '../api'
import { useFilters } from '../composables/useFilters'
import { useI18n } from '../composables/useI18n'

export default {
  name: 'Restocking',
  setup() {
    const { t, currentCurrency } = useI18n()
    const { selectedLocation, selectedCategory, getCurrentFilters } = useFilters()

    const loading = ref(true)
    const error = ref(null)
    const allRecommendations = ref([])
    const budget = ref(10000)
    const orderSubmitting = ref(false)
    const orderSuccess = ref(false)

    const currencySymbol = computed(() => currentCurrency.value === 'JPY' ? '¥' : '$')

    const selectedRecommendations = computed(() => {
      const sorted = [...allRecommendations.value].sort((a, b) => b.priority_score - a.priority_score)
      const selected = []
      let runningCost = 0
      for (const rec of sorted) {
        if (runningCost + rec.total_cost <= budget.value) {
          selected.push(rec)
          runningCost += rec.total_cost
        }
      }
      return selected
    })

    const totalCost = computed(() => {
      return selectedRecommendations.value.reduce((sum, rec) => sum + rec.total_cost, 0)
    })

    const remainingBudget = computed(() => budget.value - totalCost.value)

    const loadRecommendations = async () => {
      try {
        loading.value = true
        error.value = null
        const data = await api.getRestockingRecommendations()
        allRecommendations.value = data
      } catch (err) {
        error.value = 'Failed to load restocking recommendations: ' + err.message
      } finally {
        loading.value = false
      }
    }

    const placeOrder = async () => {
      try {
        orderSubmitting.value = true
        orderSuccess.value = false
        error.value = null
        await api.createRestockingOrder({
          budget: budget.value,
          items: selectedRecommendations.value.map(r => ({
            item_sku: r.item_sku,
            item_name: r.item_name,
            quantity: r.recommended_quantity,
            unit_cost: r.unit_cost
          }))
        })
        orderSuccess.value = true
        setTimeout(() => { orderSuccess.value = false }, 3000)
      } catch (err) {
        error.value = 'Failed to place order: ' + err.message
      } finally {
        orderSubmitting.value = false
      }
    }

    onMounted(loadRecommendations)

    return {
      t,
      loading,
      error,
      budget,
      currencySymbol,
      selectedRecommendations,
      totalCost,
      remainingBudget,
      orderSubmitting,
      orderSuccess,
      placeOrder
    }
  }
}
</script>

<style scoped>
.budget-card {
  background: white;
  border: 1px solid #e2e8f0;
  border-radius: 10px;
  padding: 1.5rem;
  margin-bottom: 1.5rem;
}

.budget-label {
  display: block;
  font-size: 0.875rem;
  font-weight: 600;
  color: #64748b;
  text-transform: uppercase;
  letter-spacing: 0.05em;
  margin-bottom: 0.75rem;
}

.budget-display {
  font-size: 2.25rem;
  font-weight: 700;
  color: #0f172a;
  letter-spacing: -0.025em;
  margin-bottom: 1rem;
}

.budget-slider {
  width: 100%;
  height: 8px;
  -webkit-appearance: none;
  appearance: none;
  background: #e2e8f0;
  border-radius: 4px;
  outline: none;
  cursor: pointer;
}

.budget-slider::-webkit-slider-thumb {
  -webkit-appearance: none;
  appearance: none;
  width: 20px;
  height: 20px;
  border-radius: 50%;
  background: #3b82f6;
  cursor: pointer;
  box-shadow: 0 1px 3px rgba(0, 0, 0, 0.2);
  transition: background 0.2s;
}

.budget-slider::-webkit-slider-thumb:hover {
  background: #2563eb;
}

.budget-slider::-moz-range-thumb {
  width: 20px;
  height: 20px;
  border-radius: 50%;
  background: #3b82f6;
  cursor: pointer;
  border: none;
  box-shadow: 0 1px 3px rgba(0, 0, 0, 0.2);
}

.slider-bounds {
  display: flex;
  justify-content: space-between;
  margin-top: 0.5rem;
  font-size: 0.813rem;
  color: #64748b;
}

.summary-stats {
  display: flex;
  gap: 1.25rem;
  margin-bottom: 1.5rem;
}

.summary-stat-card {
  flex: 1;
  background: white;
  border: 1px solid #e2e8f0;
  border-radius: 10px;
  padding: 1.25rem;
  transition: all 0.2s ease;
}

.summary-stat-card:hover {
  border-color: #cbd5e1;
  box-shadow: 0 4px 12px rgba(0, 0, 0, 0.06);
}

.summary-stat-label {
  font-size: 0.875rem;
  font-weight: 600;
  color: #64748b;
  text-transform: uppercase;
  letter-spacing: 0.5px;
  margin-bottom: 0.625rem;
}

.summary-stat-value {
  font-size: 2.25rem;
  font-weight: 700;
  color: #0f172a;
  letter-spacing: -0.025em;
}

.summary-stat-value.over-budget {
  color: #ef4444;
}

.place-order-btn {
  background: #3b82f6;
  color: white;
  border: none;
  padding: 0.625rem 1.5rem;
  border-radius: 8px;
  font-size: 0.938rem;
  font-weight: 600;
  cursor: pointer;
  transition: background 0.2s ease;
}

.place-order-btn:hover:not(:disabled) {
  background: #2563eb;
}

.place-order-btn:disabled {
  opacity: 0.5;
  cursor: not-allowed;
}

.success-message {
  background: #d1fae5;
  color: #065f46;
  padding: 1rem;
  border-radius: 8px;
  margin-bottom: 1rem;
  font-size: 0.938rem;
  font-weight: 500;
}

.no-recommendations {
  padding: 2rem;
  text-align: center;
  color: #64748b;
  font-size: 0.938rem;
}
</style>
