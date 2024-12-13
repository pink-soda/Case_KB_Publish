'''
Author: pink-soda luckyli0127@gmail.com
Date: 2024-12-05 14:49:25
LastEditors: pink-soda luckyli0127@gmail.com
LastEditTime: 2024-12-13 10:20:24
FilePath: \test\case_manager.py
Description: 这是默认设置,请设置`customMade`, 打开koroFileHeader查看配置 进行设置: https://github.com/OBKoro1/koro1FileHeader/wiki/%E9%85%8D%E7%BD%AE
'''
from flask import Blueprint, render_template, jsonify, request
import pandas as pd
import numpy as np  # 直接导入 numpy
from llm_handler import LLMHandler
from mongo_handler import MongoHandler
from knowledge_graph import KnowledgeGraph
import logging

logger = logging.getLogger(__name__)
case_manager = Blueprint('case_manager', __name__, url_prefix='/case_manager')
mongo_handler = MongoHandler()
kg = KnowledgeGraph()
if not kg.verify_data():
    raise Exception("知识图谱数据库验证失败，请检查数据")
llm_handler = LLMHandler()

def get_completed_cases_from_csv():
    try:
        df = pd.read_csv('e:\\Case_KB\\cases.csv', encoding='gbk')
        df['案例进度'] = df['案例进度'].str.strip()
        completed_cases = df[df['案例进度'].str.contains('已完结', na=False)]
        
        # 准备返回的数据，保存所有列
        result = []
        for _, row in completed_cases.iterrows():
            # 将Series转换为字典，并确保数值类型转换为Python原生类型
            case_data = row.to_dict()
            # 转换所有数值类型为Python原生类型
            case_data = {k: int(v) if isinstance(v, pd.Int64Dtype) or isinstance(v, np.int64)  # 使用 np.int64
                        else float(v) if isinstance(v, np.float64)  # 使用 np.float64
                        else str(v) if pd.isna(v)
                        else v 
                        for k, v in case_data.items()}
            
            # 确保某些关键字段的存在
            case = {
                'case_id': case_data['案例编号'],
                'title': str(case_data.get('案例标题', '')),
                'category': [cat.strip().strip("'") for cat in str(case_data.get('所属类别', '[]')).strip('[]').split(',') if cat.strip()],
                'contact': str(case_data.get('联系人', '')),
                'phone': str(case_data.get('联系电话', '')),
                'case_owner': str(case_data.get('case_owner', '')),
                'system_version': str(case_data.get('系统版本', '')),
                'case_definition': str(case_data.get('案例定义', '')),
                'case_status': str(case_data.get('案例进度', '')),
                'case_log': str(case_data.get('有无上传日志', '')),
                'case_evaluation': str(case_data.get('案例总结', '')),
                'case_email': str(case_data.get('案例详情', '')),
                'case_review': str(case_data.get('案例评审', '')),
                'case_score': str(case_data.get('案例置信度评分', '')),
            }
            result.append(case)
        
        return result
    except Exception as e:
        print(f"错误信息: {str(e)}")
        logger.error(f"Error reading CSV file: {str(e)}")
        return []

@case_manager.route('/')
def show_case_manager():
    cases = mongo_handler.get_all_cases()
    cases_count = mongo_handler.get_cases_count()
    return render_template('case_manager.html', cases=cases, cases_count=cases_count)

@case_manager.route('/build_library', methods=['POST'])
def build_library():
    try:
        if mongo_handler.get_cases_count() > 0:
            return jsonify({
                'success': False,
                'message': '案例库不为空，请使用更新功能'
            })
        
        completed_cases = get_completed_cases_from_csv()
        if not completed_cases:
            return jsonify({
                'success': False,
                'message': '没有找到已完结的案例'
            })
            
        inserted_count = mongo_handler.bulk_insert_cases(completed_cases)
        return jsonify({
            'success': True,
            'message': f'成功导入 {inserted_count} 个案例'
        })
    except Exception as e:
        logger.error(f"Error building library: {str(e)}")
        return jsonify({
            'success': False,
            'message': f'构建案例库失败: {str(e)}'
        }), 500

@case_manager.route('/update_library', methods=['POST'])
def update_library():
    try:
        completed_cases = get_completed_cases_from_csv()
        current_count = mongo_handler.get_cases_count()
        
        if len(completed_cases) <= current_count:
            return jsonify({
                'success': True,
                'message': '案例库已是最新状态'
            })
        
        # 获取现有案例的ID列表
        existing_cases = mongo_handler.get_all_cases()
        existing_ids = set(case['case_id'] for case in existing_cases)
        
        # 找出需要新增的案例
        new_cases = [case for case in completed_cases 
                    if case['case_id'] not in existing_ids]
        
        if new_cases:
            inserted_count = mongo_handler.bulk_insert_cases(new_cases)
            return jsonify({
                'success': True,
                'message': f'成功新增 {inserted_count} 个案例'
            })
        return jsonify({
            'success': True,
            'message': '没有新的案例需要添加'
        })
    except Exception as e:
        logger.error(f"Error updating library: {str(e)}")
        return jsonify({
            'success': False,
            'message': f'更新案例库失败: {str(e)}'
        })

@case_manager.route('/get_categories', methods=['POST'])
def get_categories():
    try:
        data = request.get_json()
        case_id = data.get('case_id')
        
        if not case_id:
            return jsonify({
                'success': False,
                'message': '请输入案例编号'
            })
        
        # 从CSV文件中读取案例定义
        df = pd.read_csv('e:\\Case_KB\\cases.csv', encoding='gbk')
        case_row = df[df['案例编号'] == case_id]
        
        if case_row.empty:
            return jsonify({
                'success': False,
                'message': '未找到该案例'
            })
        
        # 使用案例定义列
        case_definition = case_row['案例定义'].iloc[0]
        
        if not case_definition or pd.isna(case_definition):
            return jsonify({
                'success': False,
                'message': '该案例没有案例定义'
            })
            
        # 获取类别层级结构
        category_hierarchy = kg.get_category_hierarchy()
        if not category_hierarchy:
            return jsonify({
                'success': False,
                'message': '获取类别层级结构失败'
            })
            
        # 使用 llm_handler 分析案例
        try:
            analysis_result = llm_handler.analyze_description_with_categories(
                description=case_definition,
                category_hierarchy=category_hierarchy
            )
            
            # 确保返回结果是字典类型
            if not isinstance(analysis_result, dict):
                logger.error(f"LLM返回了非预期的结果类型: {type(analysis_result)}")
                return jsonify({
                    'success': False,
                    'message': 'LLM分析返回了非预期的结果类型'
                })
            
            # 使用 get 方法安全地获取结果
            return jsonify({
                'success': True,
                'categories': analysis_result.get('categories', []),
                'confidence_scores': analysis_result.get('confidence_scores', []),
                'explanation': analysis_result.get('explanation', '无分析说明')
            })
            
        except Exception as e:
            logger.error(f"LLM分析过程出错: {str(e)}")
            return jsonify({
                'success': False,
                'message': f'LLM分析失败: {str(e)}'
            })
            
    except Exception as e:
        logger.error(f"Error analyzing categories: {str(e)}")
        logger.error("详细错误信息:", exc_info=True)  # 添加详细的错误堆栈
        return jsonify({
            'success': False,
            'message': f'分析类别失败: {str(e)}'
        }) 