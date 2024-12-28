/*
 * @Author: pink-soda luckyli0127@gmail.com
 * @Date: 2024-12-27 10:11:06
 * @LastEditors: pink-soda luckyli0127@gmail.com
 * @LastEditTime: 2024-12-27 11:11:17
 * @FilePath: \Case_KB_Vue\src\api.js
 * @Description: 这是默认设置,请设置`customMade`, 打开koroFileHeader查看配置 进行设置: https://github.com/OBKoro1/koro1FileHeader/wiki/%E9%85%8D%E7%BD%AE
 */
import axios from 'axios'

const api = axios.create({
  baseURL: '/api',
  timeout: 10000
})

export default {
  async collectInfo(caseId) {
    const response = await api.post('/collect-info', { case_id: caseId })
    return response.data
  },

  async generateEmail(data) {
    const response = await api.post('/generate-email', data)
    return response.data
  },

  async processEmails(folder) {
    const response = await api.post('/process-emails', { email_folder: folder })
    return response.data
  },

  async saveClassification(caseId, tags) {
    const response = await api.post('/save-classification', {
      case_id: caseId,
      tags: tags
    });
    return response.data;
  },

  async queryCaseCategory(description) {
    const response = await api.post('/query-category', { description });
    return response.data;
  },

  async getReferenceCases() {
    const response = await api.get('/reference-cases');
    return response.data;
  }
} 