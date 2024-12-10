'''
Author: pink-soda luckyli0127@gmail.com
Date: 2024-12-03 10:00:49
LastEditors: pink-soda luckyli0127@gmail.com
LastEditTime: 2024-12-10 20:55:16
FilePath: \test\app.py
Description: 这是默认设置,请设置`customMade`, 打开koroFileHeader查看配置 进行设置: https://github.com/OBKoro1/koro1FileHeader/wiki/%E9%85%8D%E7%BD%AE
'''
from flask import Flask, jsonify, request
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
    #logger.info("访问首页")
    return """
    <!DOCTYPE html>
    <html>
    <head>
        <title>案例管理系统</title>
        <meta charset="UTF-8">
    </head>
    <body>
        <h1>案例管理系统</h1>
        <p>API 端点列表：</p>
        <ul>
            <li>POST /collect-info - 收集案例信息</li>
            <li>POST /get-case-list - 获取案例列表</li>
            <li>POST /get-case-details - 获取案例详情</li>
            <li>GET /get-pending-audits - 获取待审核案例</li>
            <li>POST /audit-case - 提交审核结果</li>
            <li>GET /get-category-hierarchy - 获取分类层级</li>
        </ul>
        <p><a href="/show">进入主界面</a></p>
        <p><a href="/case_manager">进入案例管理</a></p>
    </body>
    </html>
    """

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
        pdf_path = os.path.join('E:\\Case_KB\\emails', f'{case_id}.pdf')
        
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

@app.route('/get-pending-audits', methods=['GET'])
def get_pending_audits():
    """获取待审核的案例列表"""
    try:
        pending_cases = audit_handler.get_pending_audits()
        return jsonify({
            'status': 'success',
            'cases': pending_cases
        })
    except Exception as e:
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
        
        success = audit_handler.audit_case(case_id, audit_result)
        
        if success:
            return jsonify({
                'status': 'success',
                'message': '审核完成'
            })
        else:
            return jsonify({
                'status': 'error',
                'message': '审核失败'
            }), 500
            
    except Exception as e:
        return jsonify({
            'status': 'error',
            'message': str(e)
        }), 500

@app.route('/get-category-hierarchy', methods=['GET'])
def get_category_hierarchy():
    """获取分类层级结构"""
    try:
        kg = KnowledgeGraph()
        if not kg.verify_data():
            raise Exception("知识图谱数据库验证失败，请检查数据")
        hierarchy = kg.get_category_hierarchy()
        return jsonify({
            'status': 'success',
            'hierarchy': hierarchy
        })
    except Exception as e:
        return jsonify({
            'status': 'error',
            'message': str(e)
        }), 500

@app.route('/query-category', methods=['POST'])
def query_category():
    try:
        data = request.get_json()
        case_id = data.get('case_id')
        
        if not case_id:
            return jsonify({
                'status': 'error',
                'message': '未提供案例编号'
            }), 400
            
        # 从CSV读取案例描述
        case_description = case_handler.get_case_description(case_id)
        
        # 获取知识图谱实例
        kg = KnowledgeGraph()
        if not kg.verify_data():
            raise Exception("知识图谱数据库验证失败，请检查数据")
        category_hierarchy = kg.get_category_hierarchy()
        
        # 使用LLM进行分类（这里会自动进行最多3次尝试）
        llm_handler = LLMHandler()
        analysis_result = llm_handler.analyze_description_with_categories(
            description=case_description,
            category_hierarchy=category_hierarchy
        )
        
        # 格式化返回结果
        formatted_result = {
            'status': 'success',
            'result': {
                'analysis': analysis_result.get('categories', []),
                'confidence': analysis_result.get('confidence_scores', []),
                'explanation': analysis_result.get('explanation', '')
            }
        }
        
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
        if not kg.verify_data():
            raise Exception("知识图谱数据库验证失败，请检查数据")
        # 从Neo4j获取完整的类别层级结构
        category_hierarchy = kg.get_category_hierarchy()
        #print("类别层级结构",category_hierarchy)
        llm_handler = LLMHandler()
        # 将类别层级结构作为上下文，分析描述文本
        analysis_result = llm_handler.analyze_description_with_categories(
            description=description,
            category_hierarchy=category_hierarchy
        )
        
        # 打印原始的分析结果
        #logger.info(f"LLM分析原始结果: {analysis_result}")
        
        # 修改返回格式，使其更适合前端显示
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
            
            case['categories'] = list(set(case_categories))  # 去重
            #logger.debug(f"Processed categories for case {case['case_id']}: {case['categories']}")
            
            # 计算匹配分数 - 使用更宽松的匹配逻辑
            matched_tags = sum(1 for tag in tags for cat in case['categories'] 
                             if tag.lower() in cat.lower() or cat.lower() in tag.lower())
            case['similarity_score'] = (matched_tags / len(tags)) * 100
            cases_list.append(case)
        
        # 按相似度得排序降序）
        cases_list.sort(key=lambda x: x['similarity_score'], reverse=True)
        
        #logger.info(f"Found {len(cases_list)} matching cases")
        
        return jsonify({
            'status': 'success',
            'cases': cases_list,
            'total': len(cases_list)
        })
    except Exception as e:
        logger.error(f"Error searching similar cases: {str(e)}")
        logger.error(traceback.format_exc())  # 添加完整的错误堆栈
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
        reference_emails = data.get('reference_emails', '')  # 获取历史邮件内容
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
        logger.error(traceback.format_exc())  # 添加错误堆栈跟踪
        return jsonify({
            'success': False,
            'message': str(e)
        }), 500

@app.route('/load-case-email', methods=['POST'])
def load_case_email():
    try:
        data = request.get_json()
        case_id = data.get('case_id')
        
        # 构建PDF文件路径
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
            
        # 获取案例评估字段
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
                'message': '没有文件被上传'
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
            
            # 使用PyMuPDF提取PDF内容
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
                'message': '不支持的文件格式'
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
    pdf_dir = 'E:\\Case_KB\\email_template'  # PDF文件目录
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

app.register_blueprint(case_manager)

if __name__ == '__main__':
    try:
        import socket
        # 检查端口是否可用
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        result = sock.connect_ex(('127.0.0.1', 5000))
        if result == 0:
            print("警告：端口 5000 已被占用")
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
  