<!--
 * @Author: pink-soda luckyli0127@gmail.com
 * @Date: 2024-12-27 10:15:02
 * @LastEditors: pink-soda luckyli0127@gmail.com
 * @LastEditTime: 2024-12-27 11:05:14
 * @FilePath: \Case_KB_Vue\src\components\EmailGenerator.vue
 * @Description: 这是默认设置,请设置`customMade`, 打开koroFileHeader查看配置 进行设置: https://github.com/OBKoro1/koro1FileHeader/wiki/%E9%85%8D%E7%BD%AE
-->
<template>
  <div class="container">
    <!-- 案例信息收集部分 -->
    <div class="section">
      <h2>案例信息收集</h2>
      <input type="text" v-model="caseId" class="input-field" placeholder="请输入案例编号">
      <button @click="collectInfo" class="button">收集信息</button>
      <div class="result-area">
        <div v-if="caseInfo" class="info-row">
          <span class="info-label">客户名称：</span>
          <span>{{ caseInfo.customer_name }}</span>
        </div>
        <!-- 其他信息展示... -->
      </div>
    </div>

    <!-- 邮件生成部分 -->
    <div class="section">
      <h2>邮件生成</h2>
      <textarea v-model="progressDescription" class="progress-input" placeholder="请输入当前进度描述..."></textarea>
      <div class="d-flex align-items-center">
        <button class="button" @click="generateEmail">
          <i class="fas fa-envelope"></i> 生成邮件
        </button>
        <span v-show="tipVisible" :class="['ms-2', tipError ? 'text-danger' : 'text-muted']">
          {{ tipMessage }}
        </span>
      </div>
      <div class="generated-email-container">
        <div v-html="emailContent" class="generated-email" contenteditable="true"></div>
      </div>
    </div>
  </div>
</template>

<script>
import { mapState, mapActions } from 'vuex'

export default {
  name: 'Show',
  data() {
    return {
      caseId: '',
      progressDescription: '',
      tipVisible: false,
      tipError: false,
      tipMessage: ''
    }
  },
  computed: {
    ...mapState(['caseInfo', 'emailContent'])
  },
  methods: {
    ...mapActions(['fetchCaseInfo', 'generateEmail']),
    
    showTip(message, isError = false) {
      this.tipMessage = message;
      this.tipError = isError;
      this.tipVisible = true;
      setTimeout(() => {
        this.tipVisible = false;
      }, 3000);
    },
    
    async collectInfo() {
      if (!this.caseId) {
        this.showTip('请输入案例编号', true);
        return;
      }
      try {
        await this.fetchCaseInfo(this.caseId);
        this.showTip('信息收集成功');
      } catch (error) {
        this.showTip(error.message || '信息收集失败', true);
      }
    },
    
    async handleGenerateEmail() {
      if (!this.progressDescription) {
        this.showTip('请输入进度描述', true);
        return;
      }
      try {
        await this.generateEmail({
          progress_description: this.progressDescription,
          case_info: this.caseInfo
        });
        this.showTip('邮件生成成功');
      } catch (error) {
        this.showTip(error.message || '邮件生成失败', true);
      }
    }
  },
  mounted() {
    this.$store.dispatch('fetchReferenceCases');
  }
}
</script> 