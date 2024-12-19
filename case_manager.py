'''
Author: pink-soda luckyli0127@gmail.com
Date: 2024-12-05 14:49:25
LastEditors: pink-soda luckyli0127@gmail.com
LastEditTime: 2024-12-19 10:54:49
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
from case_sync import build_case_library, update_case_library
import traceback

logger = logging.getLogger(__name__)
case_manager = Blueprint('case_manager', __name__, url_prefix='/case_manager')
mongo_handler = MongoHandler()
kg = KnowledgeGraph()
try:
    # 尝试获取类别层级结构，如果为空也是允许的
    category_hierarchy = kg.get_category_hierarchy() or {}
except Exception as e:
    logger.error(f"获取知识图谱数据失败: {str(e)}")
    raise Exception("知识图谱数据库连接失败，请检查连接设置")
llm_handler = LLMHandler()

def get_completed_cases_from_csv():
    try:
        csv_path = 'e:\\Case_KB\\cases.csv'
        
        # 尝试不同的编码方式读取CSV文件
        encodings = ['utf-8', 'utf-8-sig', 'gbk', 'gb18030', 'latin1']
        df = None
        
        for encoding in encodings:
            try:
                logger.info(f"尝试使用 {encoding} 编码读取CSV文件")
                df = pd.read_csv(csv_path, encoding=encoding)
                logger.info(f"成功使用 {encoding} 编码读取CSV文件")
                break
            except UnicodeDecodeError:
                continue
        
        if df is None:
            raise Exception("无法使用任何已知编码读取CSV文件")

        # 打印CSV文件的列名，用于调试
        logger.info(f"CSV文件列名: {df.columns.tolist()}")
        
        # 确保'案例进度'列存在且为字符串类型
        if '案例进度' not in df.columns:
            raise Exception("CSV文件中缺少'案例进度'列")
            
        df['案例进度'] = df['案例进度'].astype(str).str.strip()
        completed_cases = df[df['案例进度'].str.contains('已完结', na=False)]
        
        # 打印一个样本案例，用于调试
        if not completed_cases.empty:
            logger.info(f"样本案例数据: {completed_cases.iloc[0].to_dict()}")
        
        result = []
        for _, row in completed_cases.iterrows():
            case_data = row.to_dict()
            
            # 处理数值类型
            case_data = {k: (
                int(v) if isinstance(v, (pd.Int64Dtype, np.int64))
                else float(v) if isinstance(v, np.float64) and not pd.isna(v)
                else '' if pd.isna(v)
                else str(v)
            ) for k, v in case_data.items()}
            
            # 转换为标准格式，确保字段名称匹配
            case = {
                'case_id': case_data['案例编号'],
                'title': case_data.get('案例标题', ''),
                'category': [cat.strip() for cat in str(case_data.get('所属类别', '')).split(',') if cat.strip()],
                'contact': case_data.get('联系人', ''),
                'phone': case_data.get('联系电话', ''),
                'case_owner': case_data.get('case_owner', ''),
                'system_version': case_data.get('系统版本', ''),
                'case_definition': case_data.get('案例定义', ''),
                'case_status': case_data.get('案例进度', ''),
                'case_log': case_data.get('有无上传日志', ''),
                'case_evaluation': case_data.get('案例总结', ''),
                'case_email': case_data.get('案例详情', ''),
                'case_review': case_data.get('案例评审', ''),
                'case_score': case_data.get('案例置信度评分', '')
            }
            
            # 打印转换后的案例数据，用于调试
            logger.debug(f"转换后的案例数据: {case}")
            
            # 清理空字符串和'nan'值
            case = {k: ('' if v == 'nan' else v) for k, v in case.items()}
            result.append(case)
        
        return result
    except Exception as e:
        logger.error(f"读取CSV文件失败: {str(e)}")
        logger.error(traceback.format_exc())
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
        
        # 首先同步本地文件
        success, message = build_case_library()
        if not success:
            return jsonify({
                'success': False,
                'message': message
            })
            
        # 然后从CSV读取并导入MongoDB
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
        # 首先同步本地文件
        success, message = update_case_library()
        if not success:
            return jsonify({
                'success': False,
                'message': message
            })
            
        completed_cases = get_completed_cases_from_csv()
        if not completed_cases:
            logger.error("没有找到已完结的案例")
            return jsonify({
                'success': False,
                'message': '没有找到已完结的案例'
            })

        # 记录处理前的案例数和数据示例
        before_count = mongo_handler.get_cases_count()
        logger.info(f"更新前案例数: {before_count}")
        if before_count > 0:
            sample_case = mongo_handler.cases.find_one()
            logger.info(f"更新前样本案例: {sample_case}")
        
        updated_count = 0
        inserted_count = 0
        
        for case in completed_cases:
            try:
                # 检查案例是否存在
                existing_case = mongo_handler.cases.find_one({'case_id': case['case_id']})
                logger.info(f"处理案例 {case['case_id']}, 当前数据: {case}")
                
                if existing_case:
                    # 更新现有案例
                    update_data = {
                        'title': case['title'],
                        'category': case['category'],
                        'contact': case['contact'],
                        'phone': case['phone'],
                        'case_owner': case['case_owner'],  # 确保这个字段被包含在更新中
                        'system_version': case['system_version'],
                        'case_definition': case['case_definition'],
                        'case_status': case['case_status'],
                        'case_log': case['case_log'],
                        'case_evaluation': case['case_evaluation'],
                        'case_email': case['case_email'],
                        'case_review': case['case_review'],
                        'case_score': case['case_score']
                    }
                    
                    # 记录更新数据
                    logger.info(f"更新数据: {update_data}")
                    
                    # 过滤有效数据
                    filtered_data = {}
                    for k, v in update_data.items():
                        if isinstance(v, str):
                            if v and v != 'nan' and v.strip():
                                filtered_data[k] = v
                        elif v:
                            filtered_data[k] = v
                    
                    logger.info(f"过滤后的更新数据: {filtered_data}")

                    if filtered_data:
                        if mongo_handler.update_case(case['case_id'], filtered_data):
                            updated_count += 1
                            logger.info(f"成功更新案例: {case['case_id']}")
                else:
                    # 新增案例
                    mongo_handler.bulk_insert_cases([case])
                    inserted_count += 1
                    logger.info(f"新增案例: {case['case_id']}")
                    
            except Exception as e:
                logger.error(f"处理案例 {case['case_id']} 时出错: {str(e)}")
                continue
        
        # 记录处理后的案例数和数据示例
        after_count = mongo_handler.get_cases_count()
        logger.info(f"更新前案例数: {before_count}, 更新后案例数: {after_count}")
        logger.info(f"更新数: {updated_count}, 新增数: {inserted_count}")
        
        if after_count > 0:
            sample_case = mongo_handler.cases.find_one()
            logger.info(f"更新后样本案例: {sample_case}")
        
        message = f'更新完成: {updated_count} 个案例已更新, {inserted_count} 个案例新增'
        return jsonify({
            'success': True,
            'message': message
        })
        
    except Exception as e:
        logger.error(f"更新案例库失败: {str(e)}")
        logger.error(traceback.format_exc())
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