'''
Author: pink-soda luckyli0127@gmail.com
Date: 2024-12-03 14:12:58
LastEditors: pink-soda luckyli0127@gmail.com
LastEditTime: 2024-12-17 21:57:45
FilePath: \test\case_data_handler.py
Description: 这是默认设置,请设置`customMade`, 打开koroFileHeader查看配置 进行设置: https://github.com/OBKoro1/koro1FileHeader/wiki/%E9%85%8D%E7%BD%AE
'''
import pandas as pd
import logging
import chardet
import os
import traceback

logger = logging.getLogger(__name__)

def detect_encoding(file_path):
    """检测文件编码"""
    try:
        with open(file_path, 'rb') as file:
            raw_data = file.read()
            result = chardet.detect(raw_data)
            return result['encoding']
    except Exception as e:
        logger.error(f"检测文件编码失败: {str(e)}")
        return 'utf-8'  # 默认返回 utf-8

class CaseDataHandler:
    def __init__(self):
        try:
            # 使用完整路径
            csv_path = 'e:\\Case_KB\\unfinished_cases.csv'
            
            # 检查文件是否存在
            if not os.path.exists(csv_path):
                logger.error(f"文件不存在: {csv_path}")
                raise FileNotFoundError(f"找不到文件: {csv_path}")
            
            # 尝试不同的编码方式
            try:
                # 首先尝试 UTF-8
                self.df = pd.read_csv(csv_path, encoding='utf-8')
            except UnicodeDecodeError:
                try:
                    # 然后尝试 GBK
                    self.df = pd.read_csv(csv_path, encoding='gbk')
                except UnicodeDecodeError:
                    # 最后使用检测到的编码
                    detected_encoding = detect_encoding(csv_path)
                    self.df = pd.read_csv(csv_path, encoding=detected_encoding)
            
            #logger.info("CaseDataHandler 初始化成功")
            
        except Exception as e:
            logger.error(f"CaseDataHandler 初始化失败: {str(e)}")
            # 创建空的 DataFrame 作为后备
            self.df = pd.DataFrame(columns=[
                '案例编号', '客户名称', '所属类别', '联系人', '联系电话', 
                '案例标题', 'case_owner', '系统版本', '案例定义', '案例进度',
                '有无上传日志', '案例总结', '案例详情', '案例评审', '案例置信度评分', '案例评价'
            ])
            logger.info("已创建空的数据框架")

    def get_case_info(self, case_id):
        try:
            case = self.df[self.df['案例编号'] == case_id].iloc[0]
            return {
                'status': 'success',
                'customer_name': case['客户名称'],
                'contact_person': case['联系人'],
                'contact_phone': case['联系电话'],
                'project_subject': case['案例标题'],
                'system_version': case['系统版本'],
                'project_owner': case['case_owner'],
                'project_scale': case['案例进度']
            }
        except Exception as e:
            logger.error(f"获取案例信息失败: {str(e)}")
            return {'status': 'error', 'message': str(e)}

    def get_case_emails(self, case_id):
        try:
            case = self.df[self.df['案例编号'] == case_id].iloc[0]
            return case['案例详情']
        except Exception as e:
            logger.error(f"获取案例邮件失败: {str(e)}")
            return None
    
    def get_case_description(self, case_id):
        """获取案例描述"""
        try:
            logger.info(f"尝试获取案例 {case_id} 的描述")
            # 检查数据框是否为空
            if self.df.empty:
                logger.error("数据框为空")
                return None
            
            # 检查是否存在匹配的案例
            matching_cases = self.df[self.df['案例编号'] == case_id]
            if matching_cases.empty:
                logger.error(f"未找到案例ID: {case_id}")
                return None
            
            case = matching_cases.iloc[0]
            description = case['案例定义']
            
            # 检查描述是否为空
            if pd.isna(description) or description == '':
                logger.error(f"案例 {case_id} 的描述为空")
                return None
            
            logger.info(f"成功获取案例描述: {description[:100]}...")
            return description
        
        except Exception as e:
            logger.error(f"获取案例描述失败: {str(e)}")
            logger.error(traceback.format_exc())
            return None