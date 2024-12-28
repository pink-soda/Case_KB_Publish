'''
Author: pink-soda luckyli0127@gmail.com
Date: 2024-12-03 10:00:49
LastEditors: pink-soda luckyli0127@gmail.com
LastEditTime: 2024-12-28 14:31:37
FilePath: \test\app.py
Description: 这是默认设置,请设置`customMade`, 打开koroFileHeader查看配置 进行设置: https://github.com/OBKoro1/koro1FileHeader/wiki/%E9%85%8D%E7%BD%AE
'''
from flask import Flask, jsonify, request, flash, redirect, url_for, render_template, Response
from flask_cors import CORS
from case_data_handler import CaseDataHandler
from mongo_handler import MongoHandler
from audit_handler import AuditHandler
from scheduler import SchedulerManager
from knowledge_graph import KnowledgeGraph
from llm_handler import LLMHandler
import logging
import traceback
import sys
import pandas as pd
from case_manager import case_manager
from PyPDF2 import PdfReader
import base64
import os
from PIL import Image
import io
import fitz  # PyMuPDF
from docx import Document
from docx.shared import Inches
import shutil
from process_emails_hierarchy import create_initial_hierarchy, update_hierarchy
import json
import time
import math

# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('app.log', encoding='utf-8'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)
logger.setLevel(logging.DEBUG)

app = Flask(__name__, static_url_path='', static_folder='static')
app.config['JSON_AS_ASCII'] = False
app.config['JSONIFY_MIMETYPE'] = "application/json; charset=utf-8"
CORS(app, resources={
    r"/*": {
        "origins": "*",
        "methods": ["GET", "POST", "OPTIONS"],
        "allow_headers": ["Content-Type"]
    }
})

try:
    #logger.debug("开始初始化 CaseDataHandler...")
    case_handler = CaseDataHandler()
    
    #logger.debug("开始初始化 MongoHandler...")
    mongo_handler = MongoHandler()
    mongo_db = mongo_handler.db
    
    #logger.debug("开始初始化 AuditHandler...")
    audit_handler = AuditHandler()
    
    # logger.debug("开始初始化 SchedulerManager...")
    # scheduler = SchedulerManager()
    
    # logger.debug("启动定时任务...")
    # scheduler.start()
    #logger.info("所有服务初始化完成")
except Exception as e:
    #logger.error(f"服务初始化失败: {str(e)}")
    #logger.error(f"错误类型: {type(e).__name__}")
    #logger.error(traceback.format_exc())
    raise

@app.route('/')
def index():
    """首页"""
    return render_template('index.html')

@app.route('/show')
def show():
    try:
        #logger.info("访问 show 页面")
        with open('show.html', 'r', encoding='utf-8') as f:
            content = f.read()
            #logger.info("成功读取 show.html")
            return content
    except Exception as e:
        #logger.error(f"读取show.html失败: {str(e)}")
        return "页面加载失败", 500

@app.route('/collect-info', methods=['POST'])
def collect_info():
    try:
        data = request.get_json()
        #logger.info(f"收到收集信息请求: {data}")
        
        case_id = data.get('case_id')
        if not case_id:
            return jsonify({
                'status': 'error',
                'message': '未提供案例编号'
            }), 400
            
        result = case_handler.get_case_info(case_id)
        #logger.info(f"案例信息获取结果: {result}")
        
        # 转换 numpy.int64 为 Python int
        if 'contact_phone' in result and hasattr(result['contact_phone'], 'item'):
            result['contact_phone'] = int(result['contact_phone'])
        
        # 确保所有数值类型都是 JSON 可序列化的
        for key, value in result.items():
            if hasattr(value, 'item'):  # 检查是否是 numpy 数值类型
                result[key] = value.item()  # 转换为 Python 原生类型
        
        if result['status'] == 'success':
            return jsonify(result)
        else:
            return jsonify(result), 400
            
    except Exception as e:
        logger.error(f"收集信息失败: {str(e)}")
        logger.error(traceback.format_exc())
        return jsonify({
            'status': 'error',
            'message': str(e)
        }), 500

@app.route('/get-case-details', methods=['POST'])
def get_case_details():
    try:
        data = request.get_json()
        case_id = data.get('case_id')
        
        if not case_id:
            return jsonify({
                'status': 'error',
                'message': '未提供案例ID'
            }), 400
            
        # PDF文件路径
        pdf_path = os.path.join('emails', f'{case_id}.pdf')
        
        if not os.path.exists(pdf_path):
            return jsonify({
                'status': 'error',
                'message': '未找到案例详情'
            }), 404
            
        # 使用PyMuPDF读取PDF
        doc = fitz.open(pdf_path)
        result = {
            'pages': []
        }
        
        # 遍历每一页
        for page_num in range(len(doc)):
            page = doc[page_num]
            
            # 获取文本内容
            text = page.get_text()
            
            # 获取图片
            images = []
            image_list = page.get_images()
            
            for img_index, img in enumerate(image_list):
                xref = img[0]
                base_image = doc.extract_image(xref)
                image_bytes = base_image["image"]
                
                # 将图片转换为base64
                image_base64 = base64.b64encode(image_bytes).decode('utf-8')
                image_type = base_image["ext"]  # 获取图片类型（例如：jpeg, png）
                images.append({
                    'data': f'data:image/{image_type};base64,{image_base64}',
                    'type': image_type
                })
            
            # 将页面内容添加到结果中
            result['pages'].append({
                'text': text,
                'images': images
            })
        
        doc.close()
        
        return jsonify({
            'status': 'success',
            'details': result
        })
        
    except Exception as e:
        logger.error(f"获取案例详情失败: {str(e)}")
        return jsonify({
            'status': 'error',
            'message': str(e)
        }), 500

@app.route('/get_pending_audits')
def get_pending_audits():
    try:
        app.logger.info("开始获取待审核案例")
        audit_handler = AuditHandler()
        cases = audit_handler.get_pending_audits()
        
        app.logger.info(f"从 AuditHandler 获取到 {len(cases)} 个案例")
        app.logger.debug(f"原始案例数据: {cases}")
        
        # 确保所有案例都有必要的字段，并处理特殊值
        formatted_cases = []
        for case in cases:
            app.logger.debug(f"处理案例数据: {case}")
            
            # 处理 case_score，确保它是 JSON 可序列化的
            case_score = case.get('case_score')
            if case_score is None or (isinstance(case_score, float) and (math.isnan(case_score) or math.isinf(case_score))):
                case_score = None
            
            formatted_case = {
                'case_id': case.get('case_id', '未知ID'),
                'category': case.get('category', []),
                'case_score': case_score,  # 使用处理后的 case_score
                'case_review': case.get('case_review', '待审核')
            }
            formatted_cases.append(formatted_case)
        
        app.logger.info(f"返回待审核案例数量: {len(formatted_cases)}")
        app.logger.debug(f"格式化后的案例数据: {formatted_cases}")
        
        response_data = {
            'status': 'success',
            'cases': formatted_cases
        }
        app.logger.debug(f"最终返回的JSON数据: {response_data}")
        
        #return jsonify(response_data)
        return jsonify(formatted_cases)

    except Exception as e:
        app.logger.error(f"获取待审核案例失败: {str(e)}")
        app.logger.exception("详细错误信息：")
        return jsonify({
            'status': 'error',
            'message': str(e)
        }), 500

@app.route('/audit-case', methods=['POST'])
def audit_case():
    """提交审核结果"""
    try:
        data = request.get_json()
        case_id = data.get('case_id')
        audit_result = data.get('audit_result')
        
        if not case_id or not audit_result:
            return jsonify({
                'status': 'error',
                'message': '缺少必要参数'
            }), 400
        
        # 1. 更新 MongoDB
        success = audit_handler.audit_case(case_id, audit_result)
        if not success:
            return jsonify({
                'status': 'error',
                'message': '更新MongoDB失败'
            }), 500

        # 2. 检查并更新 Neo4j 分类关系
        kg = KnowledgeGraph()
        categories = audit_result['category']  # [level1, level2, level3]
        success = kg.ensure_category_hierarchy(categories)
        if not success:
            return jsonify({
                'status': 'error',
                'message': '更新Neo4j分类关系失败'
            }), 500

        # 3. 如果包含新分类，更新本地文件
        if audit_result.get('has_new_category'):
            try:
                # 更新 category_hierarchy.json
                with open('category_hierarchy.json', 'r', encoding='utf-8') as f:
                    hierarchy = json.load(f)
                
                level1, level2, level3 = categories
                if level1 not in hierarchy:
                    hierarchy[level1] = {}
                if level2 not in hierarchy[level1]:
                    hierarchy[level1][level2] = []
                if level3 not in hierarchy[level1][level2]:
                    hierarchy[level1][level2].append(level3)
                
                with open('category_hierarchy.json', 'w', encoding='utf-8') as f:
                    json.dump(hierarchy, f, ensure_ascii=False, indent=2)

                # 更新 classified_cases.json
                try:
                    with open('classified_cases.json', 'r', encoding='utf-8') as f:
                        classified_cases = json.load(f)
                except FileNotFoundError:
                    classified_cases = []

                # 查找并更新或添加案例分类
                case_found = False
                for case in classified_cases:
                    if case.get('file_path', '').endswith(f'{case_id}.pdf'):
                        case['classification'] = {
                            'level1': level1,
                            'level2': level2,
                            'level3': level3
                        }
                        case_found = True
                        break

                # 如果没找到案例，添加新的
                if not case_found:
                    classified_cases.append({
                        'file_path': f'./emails/{case_id}.pdf',
                        'classification': {
                            'level1': level1,
                            'level2': level2,
                            'level3': level3
                        }
                    })

                # 保存更新后的分类结果
                with open('classified_cases.json', 'w', encoding='utf-8') as f:
                    json.dump(classified_cases, f, ensure_ascii=False, indent=2)

            except Exception as e:
                logger.error(f"更新分类文件失败: {str(e)}")
                return jsonify({
                    'status': 'error',
                    'message': '更新分类文件失败'
                }), 500
        
        return jsonify({
            'status': 'success',
            'message': '审核完成'
        })
            
    except Exception as e:
        logger.error(f"审核失败: {str(e)}")
        return jsonify({
            'status': 'error',
            'message': str(e)
        }), 500

@app.route('/get-category-hierarchy', methods=['GET'])
@app.route('/category_hierarchy.json')  # 添加别名路由
def get_category_hierarchy():
    """获取分类层级结构"""
    try:
        # 优先从本地 JSON 文件读取
        with open('category_hierarchy.json', 'r', encoding='utf-8') as f:
            hierarchy = json.load(f)
        return jsonify(hierarchy)
    except Exception as e:
        logger.error(f"读取分类层级失败: {str(e)}")
        return jsonify({
            'status': 'error',
            'message': '读取分类层级失败'
        }), 500

@app.route('/query-category', methods=['POST'])
def query_category():
    try:
        data = request.get_json()
        case_id = data.get('case_id')
        logger.info(f"收到分类请求，case_id: {case_id}")
        
        if not case_id:
            logger.error("未提供案例编号")
            return jsonify({
                'status': 'error',
                'message': '未提供案例编号'
            }), 400
        
        # 从 CaseDataHandler 中读取案例描述
        case_handler = CaseDataHandler()
        case_definition = case_handler.get_case_description(case_id)
        
        # 详细记录案例定义的状态
        if case_definition is None:
            logger.error(f"案例 {case_id} 未找到描述")
            return jsonify({
                'status': 'error',
                'message': '未找到案例描述'
            }), 404
            
        logger.info(f"获取到案例定义: {case_definition[:100]}...")
        
        # 获取知识图谱实例
        kg = KnowledgeGraph()
        try:
            category_hierarchy = kg.get_category_hierarchy() or {}
            logger.info(f"获取到分类层级结构: {list(category_hierarchy.keys())}")
            
            if not category_hierarchy:
                logger.error("分类层级结构为空")
                return jsonify({
                    'status': 'error',
                    'message': '分类层级结构为空，请先导入分类数据'
                }), 500
                
        except Exception as e:
            logger.error(f"获取知识图谱数据失败: {str(e)}")
            logger.error(traceback.format_exc())
            return jsonify({
                'status': 'error',
                'message': '知识图谱数据库连接失败，请检查连接设置'
            }), 500

        # 使用 LLM 进行分类
        try:
            llm_handler = LLMHandler()
            analysis_result = llm_handler.analyze_description_with_categories(
                description=case_definition,
                category_hierarchy=category_hierarchy
            )
            logger.info(f"LLM分析结果: {analysis_result}")
            
            if not analysis_result:
                logger.error("LLM返回空结果")
                return jsonify({
                    'status': 'error',
                    'message': 'LLM分析失败，请稍后重试'
                }), 500
                
        except Exception as e:
            logger.error(f"LLM分析失败: {str(e)}")
            logger.error(traceback.format_exc())
            return jsonify({
                'status': 'error',
                'message': f'LLM分析出错: {str(e)}'
            }), 500
        
        # 格式化返回结果
        formatted_result = {
            'status': 'success',
            'result': {
                'analysis': analysis_result.get('categories', []),
                'confidence': analysis_result.get('confidence_scores', []),
                'explanation': analysis_result.get('explanation', '')
            }
        }
        
        logger.info(f"返回格式化结果: {formatted_result}")
        return jsonify(formatted_result)
        
    except Exception as e:
        logger.error(f"查询类别失败: {str(e)}")
        logger.error(traceback.format_exc())
        return jsonify({
            'status': 'error',
            'message': str(e)
        }), 500

@app.route('/generate-tag', methods=['POST'])
def generate_tag():
    """使用Azure LLM生成新标签"""
    try:
        data = request.get_json()
        input_text = data.get('text')
        
        if not input_text:
            return jsonify({
                'status': 'error',
                'message': '未提供输入文本'
            }), 400
            
        llm_handler = LLMHandler()
        generated_tags = llm_handler.generate_tags(input_text)
        
        return jsonify({
            'status': 'success',
            'tags': generated_tags
        })
        
    except Exception as e:
        return jsonify({
            'status': 'error',
            'message': str(e)
        }), 500

@app.route('/tag-description', methods=['POST'])
def tag_description():
    """处理标签描述识别请求"""
    try:
        data = request.get_json()
        description = data.get('description')
        
        if not description:
            return jsonify({
                'status': 'error',
                'message': '未提供描述文本'
            }), 400
            
        # 获取知识图谱实例
        kg = KnowledgeGraph()
        try:
            # 尝试获取类别层级结构，如果为空也是允许的
            category_hierarchy = kg.get_category_hierarchy() or {}
        except Exception as e:
            logger.error(f"获取知识图谱数据失败: {str(e)}")
            raise Exception("知识图谱数据库连接失败，请检查连接设置")
        # 从Neo4j获取完整的类别级结构
        category_hierarchy = kg.get_category_hierarchy()
        #print("类别层级结构",category_hierarchy)
        llm_handler = LLMHandler()
        # 将类别层级结构作为上下文，分析描述文本
        analysis_result = llm_handler.analyze_description_with_categories(
            description=description,
            category_hierarchy=category_hierarchy
        )
        
        # 打印原始的析结果
        #logger.info(f"LLM分析原始结果: {analysis_result}")
        
        # 修改回格式，使其更适合前端示
        formatted_result = {
            'status': 'success',
            'result': {
                'analysis': analysis_result.get('categories', []),  # 分类结果列表
                'confidence': analysis_result.get('confidence_scores', []),  # 置信度列表
                'explanation': analysis_result.get('explanation', ''),  # 分析解释（如果有）
            }
        }
        
        #logger.info(f"分析完成，返回结果: {formatted_result}")
        return jsonify(formatted_result)
        
    except Exception as e:
        logger.error(f"标签描述识别失败: {str(e)}")
        logger.error(traceback.format_exc())
        return jsonify({
            'status': 'error',
            'message': str(e)
        }), 500

@app.errorhandler(404)
def not_found(e):
    return jsonify({
        'status': 'error',
        'message': '未找到请求的资源'
    }), 404

@app.errorhandler(500)
def server_error(e):
    return jsonify({
        'status': 'error',
        'message': '服务器内部错误'
    }), 500

@app.route('/search-similar-cases', methods=['POST'])
def search_similar_cases():
    data = request.get_json()
    tags = data.get('tags', [])
    
    try:
        #logger.info(f"Searching for tags: {tags}")
        
        # 先获取所有案例，看看实际的分类是什么样的
        sample_cases = list(mongo_db.cases.find({}, {'category': 1}).limit(5))
        #logger.debug(f"Sample categories in database: {[case.get('category') for case in sample_cases]}")
        
        # 修复查询条件，确保所有标签都被包含在查询中
        query = {
            '$or': [
                {'category': tag} for tag in tags  # 直接匹配标签
            ]
        }
        
        #logger.debug(f"MongoDB query: {query}")
        
        # 从MongoDB查询匹配的案例
        cases = list(mongo_db.cases.find(query))
        #logger.debug(f"Raw query results: {cases[:2]}")  # 只打印前两个结果避免日志过长
        
        cases_list = []
        for case in cases:
            case['_id'] = str(case['_id'])
            
            # 统一处理 categories 字段
            case_categories = []
            if 'category' in case and case['category']:
                case_categories.extend(case['category'] if isinstance(case['category'], list) else [cat.strip() for cat in case['category'].split(',')])
            
            case['categories'] = list(set(case_categories))  # 重
            #logger.debug(f"Processed categories for case {case['case_id']}: {case['categories']}")
            
            # 计算匹配分数 - 使用更宽松的匹配逻辑
            matched_tags = sum(1 for tag in tags for cat in case['categories'] 
                             if tag.lower() in cat.lower() or cat.lower() in tag.lower())
            case['similarity_score'] = (matched_tags / len(tags)) * 100
            cases_list.append(case)
        
        # 按相似得排序降序）
        cases_list.sort(key=lambda x: x['similarity_score'], reverse=True)
        
        #logger.info(f"Found {len(cases_list)} matching cases")
        
        return jsonify({
            'status': 'success',
            'cases': cases_list,
            'total': len(cases_list)
        })
    except Exception as e:
        logger.error(f"Error searching similar cases: {str(e)}")
        logger.error(traceback.format_exc())  # 添加完整的错误栈
        return jsonify({
            'status': 'error',
            'message': str(e)
        }), 500

@app.route('/generate-email', methods=['POST'])
def generate_email():
    try:
        data = request.get_json()
        reference_case_id = data.get('reference_case_id')
        progress_description = data.get('progress_description')
        reference_emails = data.get('reference_emails', '')  # 获取历史件内容
        case_info = data.get('case_info', {})
        #logger.debug(f"用户进度描述: {progress_description}")
        #logger.debug(f"参考案例历史邮件: {reference_emails}")
        #logger.debug(f"参考案例基本信息: {case_info}")
        if not reference_case_id or not progress_description:
            return jsonify({
                'success': False,
                'message': '缺少必要参数'
            }), 400
            
        # 使用 LLM 生成邮件
        llm_handler = LLMHandler()
        email_content = llm_handler.generate_email(
            reference_emails=reference_emails,
            progress_description=progress_description,
            case_info=case_info
        )
        
        return jsonify({
            'success': True,
            'email': email_content
        })
        
    except Exception as e:
        logger.error(f"生成邮件失败: {str(e)}")
        logger.error(traceback.format_exc())  # 添加错误栈跟踪
        return jsonify({
            'success': False,
            'message': str(e)
        }), 500

@app.route('/load-case-email', methods=['POST'])
def load_case_email():
    try:
        data = request.get_json()
        case_id = data.get('case_id')
        
        # 建PDF文件路径
        pdf_path = f'e:/Case_KB/emails/{case_id}.pdf'
        
        if not os.path.exists(pdf_path):
            return jsonify({
                'success': False,
                'message': f'未找到案例 {case_id} 的历史邮件'
            })
        
        # 读取PDF文件
        doc = fitz.open(pdf_path)
        pages = []
        
        for page in doc:
            # 获取文本内容
            text = page.get_text()
            
            # 获取图片内容
            images = []
            for img in page.get_images():
                xref = img[0]
                base = doc.extract_image(xref)
                image_data = base64.b64encode(base['image']).decode()
                images.append(f"data:image/{base['ext']};base64,{image_data}")
            
            pages.append({
                'text': text,
                'images': images
            })
        
        doc.close()
        
        return jsonify({
            'success': True,
            'pages': pages
        })
        
    except Exception as e:
        return jsonify({
            'success': False,
            'message': str(e)
        })

@app.route('/get-case-summary', methods=['POST'])
def get_case_summary():
    try:
        data = request.get_json()
        case_id = data.get('case_id')
        
        if not case_id:
            return jsonify({
                'success': False,
                'message': '未提供案例ID'
            }), 400
            
        # 从数据库获取案例评估信息
        case = mongo_db.cases.find_one({'case_id': case_id})
        
        if not case:
            return jsonify({
                'success': False,
                'message': '未找到案例'
            }), 404
            
        # 获取案例评估
        summary = case.get('case_evaluation', '暂无案例评估')
        
        return jsonify({
            'success': True,
            'summary': summary
        })
        
    except Exception as e:
        logger.error(f"获取案例评估失败: {str(e)}")
        return jsonify({
            'success': False,
            'message': str(e)
        }), 500

@app.route('/upload-pdf', methods=['POST'])
def upload_pdf():
    try:
        if 'file' not in request.files:
            return jsonify({
                'success': False,
                'message': '有文件被上传'
            })
            
        file = request.files['file']
        if file.filename == '':
            return jsonify({
                'success': False,
                'message': '未选择文件'
            })
            
        if file and file.filename.endswith('.pdf'):
            # 保存上传的PDF文件到临时目录
            temp_path = os.path.join('temp', file.filename)
            os.makedirs('temp', exist_ok=True)
            file.save(temp_path)
            
            # 使用PyMuPDF取PDF内容
            doc = fitz.open(temp_path)
            content_blocks = []
            
            for page in doc:
                # 获取文本
                text = page.get_text()
                if text.strip():
                    content_blocks.append({'type': 'text', 'content': text})
                
                # 获取图片
                for img in page.get_images():
                    try:
                        xref = img[0]
                        base = doc.extract_image(xref)
                        image_data = base64.b64encode(base['image']).decode()
                        content_blocks.append({
                            'type': 'image',
                            'content': f"data:image/{base['ext']};base64,{image_data}"
                        })
                    except Exception as img_error:
                        logger.error(f"处理PDF图片时出错: {str(img_error)}")
                        continue
            
            doc.close()
            # 清理临时文件
            os.remove(temp_path)
            
            return jsonify({
                'success': True,
                'content_blocks': content_blocks
            })
        else:
            return jsonify({
                'success': False,
                'message': '不支持的文件式'
            })
            
    except Exception as e:
        logger.error(f"处理PDF上传失败: {str(e)}")
        return jsonify({
            'success': False,
            'message': str(e)
        }), 500

@app.route('/get-template-content', methods=['POST'])
def get_template_content():
    try:
        data = request.get_json()
        template_path = data.get('path')
        
        if not template_path or not os.path.exists(template_path):
            return jsonify({
                'success': False,
                'message': '模板文件不存在'
            })

        file_ext = os.path.splitext(template_path)[1].lower()
        
        if file_ext == '.docx':
            doc = Document(template_path)
            content_blocks = []
            
            # 遍历文档中的所有元素
            for element in doc.element.body:
                if element.tag.endswith('p'):  # 段落
                    paragraph = element.xpath('.//w:t')
                    if paragraph:
                        text = ''.join(p.text for p in paragraph)
                        if text.strip():  # 只添加非空文本
                            content_blocks.append({'type': 'text', 'content': text})
                
                elif element.tag.endswith('drawing'):  # 图片
                    for rel in doc.part.rels.values():
                        if "image" in rel.target_ref:
                            try:
                                image_part = rel.target_part
                                image_bytes = image_part.blob
                                image_type = image_part.content_type.split('/')[-1]
                                
                                if image_type != 'x-emf':  # 跳过EMF格式
                                    img_base64 = base64.b64encode(image_bytes).decode()
                                    content_blocks.append({
                                        'type': 'image',
                                        'content': f"data:image/{image_type};base64,{img_base64}"
                                    })
                            except Exception as img_error:
                                logger.error(f"处理图片时出错: {str(img_error)}")
                                continue
                                
        elif file_ext == '.pdf':
            doc = fitz.open(template_path)
            content_blocks = []
            
            for page in doc:
                # 获取文本
                text = page.get_text()
                if text.strip():
                    content_blocks.append({'type': 'text', 'content': text})
                
                # 获取图片
                for img in page.get_images():
                    try:
                        xref = img[0]
                        base = doc.extract_image(xref)
                        image_data = base64.b64encode(base['image']).decode()
                        content_blocks.append({
                            'type': 'image',
                            'content': f"data:image/{base['ext']};base64,{image_data}"
                        })
                    except Exception as img_error:
                        logger.error(f"处理PDF图片时出错: {str(img_error)}")
                        continue
            
            doc.close()
        else:
            return jsonify({
                'success': False,
                'message': '不支持的文件格式'
            })
            
        return jsonify({
            'success': True,
            'content_blocks': content_blocks
        })
        
    except Exception as e:
        logger.error(f"获取模板内容失败: {str(e)}")
        logger.error(traceback.format_exc())
        return jsonify({
            'success': False,
            'message': str(e)
        }), 500

@app.route('/scan-local-pdfs')
def scan_local_pdfs():
    pdf_dir = 'email_template'  # PDF文件目录
    pdfs = []
    
    try:
        for file in os.listdir(pdf_dir):
            if file.endswith('.pdf'):
                pdfs.append({
                    'name': file,
                    'path': os.path.join(pdf_dir, file)
                })
        return jsonify({
            'success': True,
            'pdfs': pdfs
        })
    except Exception as e:
        logger.error(f"扫描PDF文件失败: {str(e)}")
        return jsonify({
            'success': False,
            'message': str(e)
        }), 500

def decode_unicode_dict(d):
    """递归解码字典中的Unicode字符串"""
    if isinstance(d, dict):
        return {decode_unicode_dict(k): decode_unicode_dict(v) for k, v in d.items()}
    elif isinstance(d, list):
        return [decode_unicode_dict(i) for i in d]
    elif isinstance(d, str):
        try:
            return d.encode().decode('unicode_escape')
        except:
            return d
    else:
        return d

@app.route('/email-classification')
def email_classification():
    # 获取初始数据
    email_folder = "./emails"
    hierarchy_file = "./category_hierarchy.json"
    cases_file = "./classified_cases.json"
    
    # 检查文件是否存在
    hierarchy_exists = os.path.exists(hierarchy_file)
    cases_exists = os.path.exists(cases_file)
    
    # 读取分类数据
    cases_data = {}
    if cases_exists:
        try:
            with open(cases_file, 'r', encoding='utf-8') as f:
                cases = json.load(f)
                # 创建文件名到分类的映射
                for case in cases:
                    file_path = case.get('file_path', '')
                    if file_path:
                        # 统一路径分隔符并获取文件名
                        normalized_path = file_path.replace('\\', '/')
                        file_name = os.path.basename(normalized_path)
                        cases_data[file_name] = {
                            'classification': case.get('classification', {
                                'level1': '',
                                'level2': '',
                                'level3': ''
                            }),
                            'category_score': case.get('category_score', {  # 从 category_score 字段读取置信度
                                'level1': 0.0,
                                'level2': 0.0,
                                'level3': 0.0
                            })
                        }
        except Exception as e:
            logger.error(f"读取分类文件失败: {str(e)}")
            cases_data = {}  # 出错时使用空字典
    # 获取邮件文件列表
    email_files = []
    if os.path.exists(email_folder):
        for file in os.listdir(email_folder):
            if file.endswith('.pdf'):
                case_info = cases_data.get(file, {
                    'classification': {
                        'level1': '',
                        'level2': '',
                        'level3': ''
                    },
                    'category_score': {
                        'level1': 0.0,
                        'level2': 0.0,
                        'level3': 0.0
                    }
                })
                
                email_files.append({
                    'name': file,
                    'processed': file in cases_data,
                    'classification': case_info['classification'],
                    'category_score': case_info['category_score']
                })
    
    # 获取分类层级
    hierarchy = {}
    if hierarchy_exists:
        try:
            with open(hierarchy_file, 'r', encoding='utf-8') as f:
                hierarchy = json.load(f)
        except Exception as e:
            logger.error(f"读取层级结构失败: {str(e)}")
    
    return render_template('email_classification.html', 
                         email_files=email_files, 
                         hierarchy=hierarchy,
                         hierarchy_exists=hierarchy_exists,
                         cases_exists=cases_exists)

@app.route('/get-classification-status')
def get_classification_status():
    try:
        email_folder = "./emails"
        hierarchy_file = "./category_hierarchy.json"
        cases_file = "./classified_cases.json"

        # 获取邮件文件列表
        email_files = []
        if os.path.exists(email_folder):
            for file in os.listdir(email_folder):
                if file.endswith('.pdf'):
                    processed = False
                    if os.path.exists(cases_file):
                        with open(cases_file, 'r', encoding='utf-8') as f:
                            cases = json.load(f)
                            processed = any(case.get('file_path', '').endswith(file) for case in cases)
                    
                    email_files.append({
                        'name': file,
                        'processed': processed
                    })

        # 获取分类层级
        hierarchy = {}
        if os.path.exists(hierarchy_file):
            with open(hierarchy_file, 'r', encoding='utf-8') as f:
                hierarchy = json.load(f)

        # 确保中文字符正确编码
        def encode_chinese(obj):
            if isinstance(obj, dict):
                return {encode_chinese(k): encode_chinese(v) for k, v in obj.items()}
            elif isinstance(obj, list):
                return [encode_chinese(i) for i in obj]
            elif isinstance(obj, str):
                return obj.encode('utf-8').decode('utf-8')
            return obj

        hierarchy = encode_chinese(hierarchy)
                
        return jsonify({
            'status': 'success',
            'email_files': email_files,
            'hierarchy': hierarchy
        })

    except Exception as e:
        return jsonify({
            'status': 'error',
            'message': str(e)
        }), 500

@app.route('/process-emails', methods=['POST'])
def process_emails_api():
    try:
        print("开始处理邮件请求")
        email_folder = request.form.get('email_folder')
        print(f"收到邮件文件夹路径: {email_folder}")
        
        hierarchy_file = "./category_hierarchy.json"
        cases_file = "./classified_cases.json"

        # 检查文件是否存在
        files_exist = os.path.exists(hierarchy_file) and os.path.exists(cases_file)
        print(f"文件是否存在: {files_exist}")
        
        try:
            if not files_exist:
                create_initial_hierarchy(email_folder, hierarchy_file, cases_file)
                message = "分类层级结构创建成功"
            else:
                update_hierarchy(email_folder, hierarchy_file, cases_file)
                message = "分类层级结构更新成功"
            
            # 读取最新的分结果
            with open(hierarchy_file, 'r', encoding='utf-8') as f:
                hierarchy = json.load(f)
            
            # 获取最新的文件处理状态
            email_files = []
            if os.path.exists(email_folder):
                for file in os.listdir(email_folder):
                    if file.endswith('.pdf'):
                        processed = False
                        if os.path.exists(cases_file):
                            with open(cases_file, 'r', encoding='utf-8') as f:
                                cases = json.load(f)
                                processed = any(case.get('file_path', '').endswith(file) for case in cases)
                        email_files.append({
                            'name': file,
                            'processed': processed
                        })
            
            print("处理完成，准备返回结果")
            response_data = {
                'status': 'success',
                'message': message,
                'hierarchy': hierarchy,
                'email_files': email_files,
                'redirect': '/email-classification'  # 添加重定向URL
            }
            print(f"返回数据: {response_data}")
            #return jsonify(response_data)
            return redirect(url_for('email_classification'))
            
        except Exception as e:
            # 果处理过程中错，删除可能创建的不完整文件
            if not files_exist:
                for file in [hierarchy_file, cases_file]:
                    if os.path.exists(file):
                        os.remove(file)
            
            error_message = str(e)
            error_detail = traceback.format_exc()
            print(f"处理过程中出错: {str(e)}")  # 调试日志
            return jsonify({
                'status': 'error',
                'message': '处理失败',
                'error': f"错误信息: {error_message}\n\n详细信息:\n{error_detail}"
            }), 500

    except Exception as e:
        print(f"请求处理失败: {str(e)}")  # 调试日志
        return jsonify({
            'status': 'error',
            'message': '处理失败',
            'error': str(e)
        }), 500

app.register_blueprint(case_manager)

# 添加自定义过滤器
@app.template_filter('yesno')
def yesno_filter(value, choices='yes,no'):
    """
    将布尔值转换为自定义的是/否符串
    用法: {{ value | yesno('已处理,未处理') }}
    """
    choices_list = choices.split(',')
    if len(choices_list) != 2:
        return value
    return choices_list[0] if value else choices_list[1]

@app.template_filter('tojson_pretty')
def tojson_pretty_filter(value):
    """
    将对象转换为格式化的 JSON 字符串，确保中文正确显示
    """
    return json.dumps(value, ensure_ascii=False, indent=2)

@app.route('/process-progress')
def process_progress():
    def generate():
        folder = request.args.get('folder', '')
        if not folder or not os.path.exists(folder):
            yield f"data: {json.dumps({'progress': 0, 'message': '无效的文件夹路径'})}\n\n"
            return

        total_files = len([f for f in os.listdir(folder) if f.endswith('.pdf')])
        if total_files == 0:
            yield f"data: {json.dumps({'progress': 0, 'message': '文件夹中没有PDF文件'})}\n\n"
            return

        cases_file = "./classified_cases.json"
        processed = 0
        last_processed = -1  # 用于跟踪上次的处理数量

        while processed < total_files:
            if os.path.exists(cases_file):
                with open(cases_file, 'r', encoding='utf-8') as f:
                    cases = json.load(f)
                    processed = len([case for case in cases 
                                  if case.get('file_path', '').startswith(folder)])
            
            # 只在处理数量发生变化时发送更新
            if processed != last_processed:
                progress = (processed / total_files) if total_files > 0 else 0
                data = {
                    'progress': progress,
                    'message': f'已处理 {processed}/{total_files} 个文件'
                }
                yield f"data: {json.dumps(data)}\n\n"
                last_processed = processed
            
            time.sleep(0.5)  # 降低检查频率
            
            # 如果处理完成，发送最后的消息
            if processed >= total_files:
                yield f"data: {json.dumps({'progress': 1, 'message': '处理完成'})}\n\n"
                break
    
    return Response(generate(), mimetype='text/event-stream')

def is_file_processed(filename):
    # 检查文件是否已处理
    with open('classified_cases.json', 'r', encoding='utf-8') as f:
        cases = json.load(f)
        return any(case.get('file_path', '').endswith(filename) for case in cases)

@app.route('/import-to-neo4j', methods=['POST'])
def import_to_neo4j():
    try:
        # 创建KnowledgeGraph实例
        knowledge_graph = KnowledgeGraph()
        
        # 调用导入方法
        success, message = knowledge_graph.import_categories_from_json()
        
        if success:
            return jsonify({
                'success': True,
                'message': message
            })
        else:
            return jsonify({
                'success': False,
                'message': message
            })
            
    except Exception as e:
        logger.error(f"导入到Neo4j失败: {str(e)}\n{traceback.format_exc()}")
        return jsonify({
            'success': False,
            'message': f'导入失败: {str(e)}'
        }), 500

@app.route('/update-file-categories', methods=['POST'])
def update_file_categories():
    try:
        data = request.get_json()
        file_name = data.get('file_name')
        categories = data.get('categories')
        confidence_scores = data.get('confidence', {  # 添加置信度参数
            'level1': 0.0,
            'level2': 0.0,
            'level3': 0.0
        })
        
        if not file_name or not categories:
            return jsonify({
                'success': False,
                'message': '缺少必要参数'
            })
        
        # 读取现有的分类数据
        with open('classified_cases.json', 'r', encoding='utf-8') as f:
            cases = json.load(f)
        
        # 构建完整的文件路径
        full_path = os.path.join('./emails', file_name)
        
        # 更新指定文件的分类和置信度
        case_updated = False
        for case in cases:
            if case.get('file_path', '').endswith(file_name):
                case['classification'] = categories
                case['category_score'] = confidence_scores  # 添加置信度更新
                case_updated = True
                break
        
        # 如果没有找到对应的案例，添加新的
        if not case_updated:
            cases.append({
                'file_path': full_path,
                'classification': categories,
                'category_score': confidence_scores  # 添加置信度
            })
        
        # 保存更新后的数据
        with open('classified_cases.json', 'w', encoding='utf-8') as f:
            json.dump(cases, f, ensure_ascii=False, indent=2)
        
        # 重新生成层级结构
        hierarchy = {}
        for case in cases:
            classification = case.get('classification', {})
            level1 = classification.get('level1')
            level2 = classification.get('level2')
            level3 = classification.get('level3')
            
            if level1 and level2 and level3:
                if level1 not in hierarchy:
                    hierarchy[level1] = {}
                if level2 not in hierarchy[level1]:
                    hierarchy[level1][level2] = []
                if level3 not in hierarchy[level1][level2]:
                    hierarchy[level1][level2].append(level3)
        
        # 保存更新后的层级结构
        with open('category_hierarchy.json', 'w', encoding='utf-8') as f:
            json.dump(hierarchy, f, ensure_ascii=False, indent=2)
        
        return jsonify({
            'success': True,
            'hierarchy': hierarchy
        })
        
    except Exception as e:
        logger.error(f"更新分类失败: {str(e)}")
        return jsonify({
            'success': False,
            'message': str(e)
        }), 500

@app.route('/audit-manager')
def audit_manager():
    """案例审核管理页面"""
    try:
        audit_handler = AuditHandler()
        pending_cases = audit_handler.get_pending_audits()
        completed_cases = audit_handler.get_completed_audits()
        
        return render_template('audit_manager.html', 
                             cases=pending_cases,
                             completed_cases=completed_cases)
    except Exception as e:
        app.logger.error(f"加载审核管理页面失败: {str(e)}")
        return render_template('audit_manager.html', 
                             cases=[], 
                             completed_cases=[],
                             error=str(e))

@app.route('/test-audit-data')
def test_audit_data():
    """测试端点，用于检查审核数据"""
    try:
        mongo_handler = MongoHandler()
        
        # 检查总案例数
        total_count = mongo_handler.db.cases.count_documents({})
        
        # 获取一样本案例
        sample = mongo_handler.db.cases.find_one()
        
        # 获取待审核案例
        audit_handler = AuditHandler()
        pending_cases = audit_handler.get_pending_audits()
        
        return jsonify({
            'status': 'success',
            'total_cases': total_count,
            'sample_case': str(sample),
            'pending_cases_count': len(pending_cases),
            'pending_cases': [str(case) for case in pending_cases[:5]]  # 只返回前5个案例
        })
    except Exception as e:
        return jsonify({
            'status': 'error',
            'message': str(e)
        }), 500

@app.route('/test-cases')
def test_cases():
    """测试路由，用于检查案例例数据"""
    try:
        mongo_handler = MongoHandler()
        
        # 获取所有案例
        all_cases = list(mongo_handler.db.cases.find())
        sample_cases = all_cases[:5]  # 只取前5个
        
        # 处理ObjectId
        for case in sample_cases:
            case['_id'] = str(case['_id'])
        
        return jsonify({
            'total_cases': len(all_cases),
            'sample_cases': sample_cases,
            'fields_info': {
                'case_score_exists': any('case_score' in case for case in sample_cases),
                'category_exists': any('category' in case for case in sample_cases),
                'case_review_exists': any('case_review' in case for case in sample_cases)
            }
        })
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/recalculate-confidence', methods=['POST'])
def recalculate_confidence():
    try:
        data = request.get_json()
        case_content = data.get('case_content')
        categories = data.get('categories')
        file_path = data.get('file_path')
        
        if not case_content or not categories or not file_path:
            return jsonify({
                'success': False,
                'message': '缺少必要参数'
            }), 400
            
        # 使用LLM重新计算置信度
        llm_handler = LLMHandler()
        confidence_scores = llm_handler.calculate_category_confidence(
            case_content=case_content,
            assigned_categories=categories
        )

        # 检查是否需要更新分类层级
        hierarchy_updated = False
        try:
            with open('category_hierarchy.json', 'r', encoding='utf-8') as f:
                hierarchy = json.load(f)
            
            level1 = categories.get('level1')
            level2 = categories.get('level2')
            level3 = categories.get('level3')
            
            # 检查分类层级是否需要更新
            if level1 and level2 and level3:  # 确保所有层级都有值
                if level1 not in hierarchy:
                    hierarchy_updated = True
                elif level2 not in hierarchy.get(level1, {}):
                    hierarchy_updated = True
                elif level3 not in hierarchy.get(level1, {}).get(level2, []):
                    hierarchy_updated = True
                    
        except Exception as e:
            logger.error(f"检查分类层级时出错: {str(e)}")
            
        return jsonify({
            'success': True,
            'confidence_scores': confidence_scores,
            'hierarchy_updated': hierarchy_updated,  # 添加这个标志
            'message': '置信度计算成功'
        })
        
    except Exception as e:
        logger.error(f"计算置信度失败: {str(e)}")
        return jsonify({
            'success': False,
            'message': str(e)
        }), 500

@app.route('/update-classification-files', methods=['POST'])
def update_classification_files():
    try:
        data = request.json
        file_name = data.get('file_name')
        categories = data.get('categories')
        confidence_scores = data.get('confidence_scores')

        if not file_name or not categories or not confidence_scores:
            return jsonify({
                'success': False,
                'message': '缺少必要参数'
            }), 400

        # 更新 classified_cases.json
        with open('classified_cases.json', 'r', encoding='utf-8') as f:
            cases = json.load(f)
            
        # 查找并更新案例
        case_found = False
        file_path = f'./emails/{file_name}'
        
        for case in cases:
            if case['file_path'] == file_path:
                case['classification'] = categories
                case['category_score'] = confidence_scores
                case_found = True
                break
                
        if not case_found:
            # 如果没找到，添加新案例
            cases.append({
                'file_path': file_path,
                'classification': categories,
                'category_score': confidence_scores
            })
            
        # 保存更新后的案例
        with open('classified_cases.json', 'w', encoding='utf-8') as f:
            json.dump(cases, f, ensure_ascii=False, indent=2)
            
        # 更新 category_hierarchy.json
        with open('category_hierarchy.json', 'r', encoding='utf-8') as f:
            hierarchy = json.load(f)
            
        # 确保分类层级存在
        level1 = categories['level1']
        level2 = categories['level2']
        level3 = categories['level3']
        
        if level1 not in hierarchy:
            hierarchy[level1] = {}
        if level2 not in hierarchy[level1]:
            hierarchy[level1][level2] = []
        if level3 and level3 not in hierarchy[level1][level2]:
            hierarchy[level1][level2].append(level3)
            
        # 保存更新后的层级
        with open('category_hierarchy.json', 'w', encoding='utf-8') as f:
            json.dump(hierarchy, f, ensure_ascii=False, indent=2)
            
        return jsonify({
            'success': True,
            'message': '分类文件更新成功'
        })
    except Exception as e:
        logger.error(f"更新分类文件失败: {str(e)}\n{traceback.format_exc()}")
        return jsonify({
            'success': False,
            'message': str(e)
        }), 500

@app.route('/get-classification-result')
def get_classification_result():
    try:
        # 读取最新的分类结果
        with open('category_hierarchy.json', 'r', encoding='utf-8') as f:
            hierarchy = json.load(f)
            
        # 将分类结果转换为HTML格式
        html = render_template('classification_result.html', hierarchy=hierarchy)
        
        return jsonify({
            'success': True,
            'html': html,
            'hierarchy': hierarchy  # 添加原始层级数据
        })
    except Exception as e:
        logger.error(f"获取分类结果失败: {str(e)}\n{traceback.format_exc()}")
        return jsonify({
            'success': False,
            'message': str(e)
        }), 500

@app.route('/check-neo4j-status')
def check_neo4j_status():
    try:
        # 检查Neo4j中是否已存在分类数据
        knowledge_graph = KnowledgeGraph()
        exists = knowledge_graph.check_categories_exist()
        
        return jsonify({
            'success': True,
            'exists': exists
        })
    except Exception as e:
        logger.error(f"检查Neo4j状态失败: {str(e)}")
        return jsonify({
            'success': False,
            'message': str(e)
        }), 500

if __name__ == '__main__':
    try:
        import socket
        # 检查端口是否可用
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        result = sock.connect_ex(('127.0.0.1', 5000))
        if result == 0:
            print("警告：端口 5000 已被占")
        sock.close()
        
        #print("正在启动Flask应用...")
        #print(f"Python版本: {sys.version}")
        app.run(
            host='0.0.0.0', 
            port=5000, 
            debug=True, 
            use_reloader=False  # 禁用重载器
        )
    except Exception as e:
        print(f"启动失败: {str(e)}")
        print(traceback.format_exc())
        sys.exit(1)
  