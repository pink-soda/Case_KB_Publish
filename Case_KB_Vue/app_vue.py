from flask import Flask, jsonify, request, send_file
from flask_cors import CORS
from handlers.case_data_handler import CaseDataHandler
from handlers.mongo_handler import MongoHandler
from handlers.audit_handler import AuditHandler
from handlers.llm_handler import LLMHandler
import logging
import traceback
import os
import json

app = Flask(__name__)
CORS(app)

# 配置日志
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

try:
    # 初始化handlers
    case_handler = CaseDataHandler()
    mongo_handler = MongoHandler()
    audit_handler = AuditHandler()
    llm_handler = LLMHandler()
except Exception as e:
    logger.error(f"初始化失败: {str(e)}")
    logger.error(traceback.format_exc())
    raise

@app.route('/api/collect-info', methods=['POST'])
def collect_info():
    try:
        data = request.get_json()
        case_id = data.get('case_id')
        if not case_id:
            return jsonify({
                'status': 'error',
                'message': '未提供案例编号'
            }), 400
            
        result = case_handler.get_case_info(case_id)
        return jsonify(result)
        
    except Exception as e:
        logger.error(f"收集信息失败: {str(e)}")
        return jsonify({
            'status': 'error',
            'message': str(e)
        }), 500

@app.route('/api/generate-email', methods=['POST'])
def generate_email():
    try:
        data = request.get_json()
        email_content = llm_handler.generate_email(
            reference_emails=data.get('reference_emails', ''),
            progress_description=data.get('progress_description'),
            case_info=data.get('case_info', {})
        )
        
        return jsonify({
            'success': True,
            'email': email_content
        })
        
    except Exception as e:
        logger.error(f"生成邮件失败: {str(e)}")
        return jsonify({
            'success': False,
            'message': str(e)
        }), 500

# 添加其他API路由...

if __name__ == '__main__':
    try:
        app.run(debug=True, port=5000)
    except Exception as e:
        logger.error(f"启动失败: {str(e)}")
        logger.error(traceback.format_exc()) 