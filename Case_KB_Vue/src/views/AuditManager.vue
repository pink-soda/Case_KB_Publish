<template>
  <base-layout>
    <div class="toast-container position-fixed top-0 end-0 p-3"></div>

    <div class="container mt-4">
      <h2>案例审核管理</h2>
      
      <!-- 待审核案例 -->
      <div class="card mb-4">
        <div class="card-header">
          <h5 class="card-title mb-0">待审核案例</h5>
        </div>
        <div class="card-body" style="height: 400px; overflow-y: auto;">
          <template v-if="cases && cases.length > 0">
            <!-- 按case_owner分组展示 -->
            <div class="accordion" id="ownerAccordion">
              <div v-for="(owner_cases, owner, index) in groupedCases" 
                   :key="owner" 
                   class="accordion-item">
                <h2 class="accordion-header" :id="'heading' + index">
                  <button class="accordion-button" 
                          :class="{ collapsed: index !== 0 }"
                          type="button" 
                          data-bs-toggle="collapse" 
                          :data-bs-target="'#collapse' + index"
                          :aria-expanded="index === 0 ? 'true' : 'false'"
                          :aria-controls="'collapse' + index">
                    {{ owner || '未分配' }} ({{ owner_cases.length }}个案例)
                  </button>
                </h2>
                <div :id="'collapse' + index" 
                     class="accordion-collapse collapse"
                     :class="{ show: index === 0 }"
                     :aria-labelledby="'heading' + index" 
                     data-bs-parent="#ownerAccordion">
                  <div class="accordion-body p-0">
                    <div class="table-responsive">
                      <table class="table table-hover mb-0">
                        <thead>
                          <tr>
                            <th>案例ID</th>
                            <th>当前分类</th>
                            <th>置信度</th>
                            <th>操作</th>
                          </tr>
                        </thead>
                        <tbody>
                          <tr v-for="case_item in owner_cases" :key="case_item.case_id">
                            <td>{{ case_item.case_id }}</td>
                            <td>
                              <div class="categories">
                                <template v-if="case_item.category">
                                  <div v-for="(cat, idx) in case_item.category" :key="idx">
                                    {{ idx === 0 ? '一' : idx === 1 ? '二' : '三' }}级分类：{{ cat }}
                                  </div>
                                </template>
                                <div v-else>未分类</div>
                              </div>
                            </td>
                            <td>N/A</td>
                            <td>
                              <button class="btn btn-sm btn-primary audit-btn" 
                                      @click="openAuditModal(case_item.case_id, case_item.category)">
                                审核
                              </button>
                            </td>
                          </tr>
                        </tbody>
                      </table>
                    </div>
                  </div>
                </div>
              </div>
            </div>
          </template>
          <p v-else class="text-muted text-center my-5">暂无待审核案例</p>
        </div>
      </div>

      <!-- 已审核案例 -->
      <div class="card">
        <div class="card-header">
          <h5 class="card-title mb-0">已审核案例</h5>
        </div>
        <div class="card-body" style="height: 400px; overflow-y: auto;">
          <template v-if="completed_cases && completed_cases.length > 0">
            <div class="table-responsive">
              <table class="table table-hover">
                <thead>
                  <tr>
                    <th>案例ID</th>
                    <th>分类</th>
                    <th>审核意见</th>
                  </tr>
                </thead>
                <tbody>
                  <tr v-for="case_item in completed_cases" :key="case_item.case_id">
                    <td>{{ case_item.case_id }}</td>
                    <td>
                      <div class="categories">
                        <template v-if="case_item.category">
                          <div v-for="(cat, idx) in case_item.category" :key="idx">
                            {{ idx === 0 ? '一' : idx === 1 ? '二' : '三' }}级分类：{{ cat }}
                          </div>
                        </template>
                        <div v-else>未分类</div>
                      </div>
                    </td>
                    <td>{{ case_item.audit_comment || '无' }}</td>
                  </tr>
                </tbody>
              </table>
            </div>
          </template>
          <p v-else class="text-muted text-center my-5">暂无已审核案例</p>
        </div>
      </div>
    </div>

    <!-- 审核表单模态框 -->
    <div class="modal fade" id="auditModal" tabindex="-1" ref="auditModal">
      <div class="modal-dialog">
        <div class="modal-content">
          <div class="modal-header">
            <h5 class="modal-title">案例审核</h5>
            <button type="button" class="btn-close" data-bs-dismiss="modal"></button>
          </div>
          <div class="modal-body">
            <form id="auditForm" @submit.prevent="submitAudit">
              <input type="hidden" v-model="currentCaseId">
              
              <div class="mb-3">
                <label class="form-label">案例ID</label>
                <p class="form-control-plaintext">{{ currentCaseId }}</p>
              </div>
              
              <!-- 当前分类 -->
              <div class="mb-3">
                <label class="form-label">当前分类</label>
                <div class="row g-3">
                  <div class="col-md-4">
                    <input type="text" class="form-control" v-model="currentLevel1" readonly placeholder="一级分类">
                  </div>
                  <div class="col-md-4">
                    <input type="text" class="form-control" v-model="currentLevel2" readonly placeholder="二级分类">
                  </div>
                  <div class="col-md-4">
                    <input type="text" class="form-control" v-model="currentLevel3" readonly placeholder="三级分类">
                  </div>
                </div>
              </div>
              
              <!-- 修正分类 -->
              <div class="mb-3">
                <label class="form-label">修正分类</label>
                <div class="row g-3">
                  <div class="col-md-4">
                    <select class="form-select" v-model="newLevel1" @change="handleLevel1Change">
                      <option value="">选择一级分类</option>
                      <option value="new">+ 新增分类</option>
                      <option v-for="level1 in Object.keys(categoryHierarchy)" 
                              :key="level1" 
                              :value="level1">
                        {{ level1 }}
                      </option>
                    </select>
                    <input type="text" 
                           class="form-control mt-2" 
                           :class="{ 'd-none': newLevel1 !== 'new' }"
                           v-model="newLevel1Input" 
                           placeholder="输入新的一级分类">
                  </div>
                  <div class="col-md-4">
                    <select class="form-select" 
                            v-model="newLevel2" 
                            :disabled="!canSelectLevel2"
                            @change="handleLevel2Change">
                      <option value="">选择二级分类</option>
                      <option value="new">+ 新增分类</option>
                      <option v-for="level2 in level2Options" 
                              :key="level2" 
                              :value="level2">
                        {{ level2 }}
                      </option>
                    </select>
                    <input type="text" 
                           class="form-control mt-2" 
                           :class="{ 'd-none': newLevel2 !== 'new' }"
                           v-model="newLevel2Input" 
                           placeholder="输入新的二级分类">
                  </div>
                  <div class="col-md-4">
                    <select class="form-select" 
                            v-model="newLevel3" 
                            :disabled="!canSelectLevel3"
                            @change="handleLevel3Change">
                      <option value="">选择三级分类</option>
                      <option value="new">+ 新增分类</option>
                      <option v-for="level3 in level3Options" 
                              :key="level3" 
                              :value="level3">
                        {{ level3 }}
                      </option>
                    </select>
                    <input type="text" 
                           class="form-control mt-2" 
                           :class="{ 'd-none': newLevel3 !== 'new' }"
                           v-model="newLevel3Input" 
                           placeholder="输入新的三级分类">
                  </div>
                </div>
              </div>
              
              <div class="mb-3">
                <label for="auditComment" class="form-label">审核意见</label>
                <textarea class="form-control" 
                          v-model="auditComment" 
                          rows="3">
                </textarea>
              </div>
            </form>
          </div>
          <div class="modal-footer">
            <button type="button" class="btn btn-secondary" data-bs-dismiss="modal">取消</button>
            <button type="button" class="btn btn-primary" @click="submitAudit">提交审核</button>
          </div>
        </div>
      </div>
    </div>
  </base-layout>
</template>

<script>
import BaseLayout from '@/layouts/BaseLayout.vue'
import { Modal } from 'bootstrap'

export default {
  name: 'AuditManager',
  components: {
    BaseLayout
  },
  data() {
    return {
      cases: [],
      completed_cases: [],
      categoryHierarchy: {},
      modal: null,
      
      // 当前审核的案例数据
      currentCaseId: '',
      currentLevel1: '',
      currentLevel2: '', 
      currentLevel3: '',
      
      // 新分类数据
      newLevel1: '',
      newLevel2: '',
      newLevel3: '',
      newLevel1Input: '',
      newLevel2Input: '',
      newLevel3Input: '',
      
      auditComment: ''
    }
  },
  computed: {
    groupedCases() {
      const grouped = {}
      this.cases.forEach(case_item => {
        const owner = case_item.case_owner || '未分配'
        if (!grouped[owner]) {
          grouped[owner] = []
        }
        grouped[owner].push(case_item)
      })
      return grouped
    },
    canSelectLevel2() {
      return this.newLevel1 && this.newLevel1 !== 'new'
    },
    canSelectLevel3() {
      return this.newLevel2 && this.newLevel2 !== 'new'
    },
    level2Options() {
      if (this.newLevel1 && this.newLevel1 !== 'new') {
        return Object.keys(this.categoryHierarchy[this.newLevel1] || {})
      }
      return []
    },
    level3Options() {
      if (this.newLevel1 && this.newLevel2 && 
          this.newLevel1 !== 'new' && this.newLevel2 !== 'new') {
        return this.categoryHierarchy[this.newLevel1][this.newLevel2] || []
      }
      return []
    }
  },
  methods: {
    showToast(type, message) {
      const toastContainer = document.querySelector('.toast-container')
      const toastEl = document.createElement('div')
      toastEl.className = `toast ${type} fade show`
      toastEl.innerHTML = `
        <div class="toast-header">
          <strong class="me-auto">${type === 'success' ? '成功' : '错误'}</strong>
          <button type="button" class="btn-close" data-bs-dismiss="toast"></button>
        </div>
        <div class="toast-body">${message}</div>
      `
      
      toastContainer.appendChild(toastEl)
      const toast = new Modal(toastEl, { delay: 5000 })
      toast.show()
      
      toastEl.addEventListener('hidden.bs.toast', () => {
        toastEl.remove()
      })
    },
    
    async loadCategoryHierarchy() {
      try {
        const response = await fetch('/category_hierarchy.json')
        this.categoryHierarchy = await response.json()
      } catch (error) {
        console.error('加载分类层级失败:', error)
        this.showToast('error', '加载分类层级失败')
      }
    },
    
    openAuditModal(caseId, currentCategory) {
      this.currentCaseId = caseId
      
      // 分割当前分类并显示
      const categories = currentCategory || ['', '', '']
      this.currentLevel1 = categories[0] || ''
      this.currentLevel2 = categories[1] || ''
      this.currentLevel3 = categories[2] || ''
      
      // 重置修正分类的下拉框
      this.newLevel1 = this.currentLevel1
      this.newLevel2 = this.currentLevel2
      this.newLevel3 = this.currentLevel3
      
      // 重置新增分类输入框
      this.newLevel1Input = ''
      this.newLevel2Input = ''
      this.newLevel3Input = ''
      
      // 重置审核意见
      this.auditComment = ''
      
      // 显示模态框
      if (!this.modal) {
        this.modal = new Modal(this.$refs.auditModal)
      }
      this.modal.show()
    },
    
    handleLevel1Change() {
      if (this.newLevel1 === 'new') {
        this.newLevel2 = ''
        this.newLevel3 = ''
      }
    },
    
    handleLevel2Change() {
      if (this.newLevel2 === 'new') {
        this.newLevel3 = ''
      }
    },
    
    handleLevel3Change() {
      // 处理三级分类变化
    },
    
    async submitAudit() {
      const getSelectedValue = (level, input) => {
        return level === 'new' ? input : level
      }
      
      const level1 = getSelectedValue(this.newLevel1, this.newLevel1Input)
      const level2 = getSelectedValue(this.newLevel2, this.newLevel2Input)
      const level3 = getSelectedValue(this.newLevel3, this.newLevel3Input)
      
      if (!level1 || !level2 || !level3) {
        this.showToast('error', '请完整填写所有级别的分类')
        return
      }
      
      try {
        const response = await fetch('/audit-case', {
          method: 'POST',
          headers: {
            'Content-Type': 'application/json',
          },
          body: JSON.stringify({
            case_id: this.currentCaseId,
            audit_result: {
              category: [level1, level2, level3],
              comment: this.auditComment,
              auditor: 'admin',
              has_new_category: this.newLevel1 === 'new' || 
                              this.newLevel2 === 'new' || 
                              this.newLevel3 === 'new'
            }
          })
        })

        const data = await response.json()
        if (data.status === 'success') {
          this.showToast('success', '审核提交成功')
          this.modal.hide()
          this.loadData() // 重新加载数据
        } else {
          throw new Error(data.message || '审核提交失败')
        }
      } catch (error) {
        this.showToast('error', `提交失败: ${error.message}`)
      }
    },
    
    async loadData() {
      try {
        const response = await fetch('/get-audit-cases')
        const data = await response.json()
        this.cases = data.pending_cases || []
        this.completed_cases = data.completed_cases || []
      } catch (error) {
        console.error('加载案例数据失败:', error)
        this.showToast('error', '加载案例数据失败')
      }
    }
  },
  async created() {
    await this.loadCategoryHierarchy()
    await this.loadData()
  }
}
</script>

<style scoped>
.table th {
  background-color: #f8f9fa;
}

.toast-container {
  z-index: 9999;
}

.toast {
  min-width: 300px;
  background-color: white;
  box-shadow: 0 0.5rem 1rem rgba(0, 0, 0, 0.15);
}

.toast.success {
  border-left: 4px solid #28a745;
}

.toast.error {
  border-left: 4px solid #dc3545;
}

.categories div {
  margin-bottom: 0.25rem;
}

.categories div:last-child {
  margin-bottom: 0;
}

.form-control-plaintext {
  padding: 0.375rem 0;
  margin-bottom: 0;
  font-size: 1rem;
  line-height: 1.5;
}

.accordion-button:not(.collapsed) {
  background-color: #e7f1ff;
  color: #0c63e4;
}

.accordion-body {
  padding: 0;
}

.accordion-body .table {
  margin-bottom: 0;
}

.accordion-body .table td,
.accordion-body .table th {
  padding: 0.75rem 1rem;
}
</style> 