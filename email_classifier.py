import os
import re
from typing import List, Dict, Tuple
import json
import logging
from llm_handler import LLMHandler

# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

class EmailClassifier:
    def __init__(self, email_dir: str, similarity_threshold: float = 0.8):
        self.email_dir = email_dir
        self.similarity_threshold = similarity_threshold
        self.categories = {}  # 存储已有的分类及其示例
        self.llm = LLMHandler()
        
    def _parse_email_file(self, file_path: str) -> List[str]:
        """解析邮件文件，返回邮件内容列表"""
        with open(file_path, 'r', encoding='utf-8') as f:
            content = f.read()
            
        # 使用正则表达式分割邮件
        emails = re.split(r'====第\d+封邮件====', content)
        # 过滤空白邮件
        return [email.strip() for email in emails if email.strip()]
    
    def _is_valid_email_content(self, content: str) -> bool:
        """判断邮件内容是否有效且相关"""
        try:
            # 如果内容少于50个字符，认为无效
            if len(content) < 50:
                return False
            
            # 使用LLM判断内容是否与案例处理阶段相关
            prompt = f"""
            请判断以下邮件内容是否与技术支持案例的处理阶段相关。
            邮件内容应该体现案例处理的某个阶段，如问题定义、方案讨论、测试实施等。
            如果内容仅包含简单的确认、问候等信息，则视为不相关。

            邮件内容：
            {content}

            请只回答"相关"或"不相关"（不要添加任何其他内容）。
            """
            
            try:
                response = self.llm._call_azure_llm_basic(prompt)
                response = response.strip().lower()
                logger.debug(f"内容相关性判断结果: {response}")
                return "相关" in response
                
            except Exception as e:
                logger.error(f"调用LLM判断内容相关性时出错: {str(e)}")
                return False
                
        except Exception as e:
            logger.error(f"判断邮件内容有效性时出错: {str(e)}")
            return False
    
    def _classify_email(self, email_content: str) -> Tuple[str, float]:
        """使用LLM对单封邮件进行分类"""
        try:
            # 如果没有已存在的分类，使用预定义的分类系统
            if not self.categories:
                prompt = f"""
                请分析以下技术支持邮件内容，判断它属于哪个处理阶段。请严格按照以下JSON格式返回结果。

                可选的处理阶段：
                1. 问题定义阶段：明确问题症状、影响范围、紧急程度等
                2. 方案探讨阶段：讨论可能的解决方案、评估可行性
                3. 方案确认与测试阶段：确定解决方案并进行测试验证
                4. 实施与反馈阶段：执行解决方案并收集反馈
                5. 后续支持与优化阶段：优化方案、预防类似问题

                邮件内容：
                {email_content}

                请严格按照以下格式返回（不要添加任何其他内容）：
                {{
                    "category": "问题定义阶段",
                    "confidence": 0.95,
                    "reasoning": "这封邮件主要描述了问题的具体症状和影响范围"
                }}
                """
            else:
                # 如果有已存在的分类，让LLM判断是否属于现有分类
                categories_desc = "\n".join([f"- {cat}: {examples[0][:200]}..." 
                                           for cat, examples in self.categories.items()])
                prompt = f"""
                请分析以下技术支持邮件内容，判断它是否属于已有的处理阶段分类。请严格按照JSON格式返回结果。
                如果不属于任何已有分类（相似度低于80%），请创建新的阶段分类。

                已有的阶段分类及示例：
                {categories_desc}

                邮件内容：
                {email_content}

                请严格按照以下格式返回（不要添加任何其他内容）：
                {{
                    "category": "方案探讨阶段",
                    "confidence": 0.85,
                    "reasoning": "这封邮件主要讨论了可能的解决方案",
                    "is_new_category": false
                }}
                """
            
            # 调用LLM并获取响应
            response = self.llm._call_azure_llm_basic(prompt)
            logger.debug(f"LLM原始响应: {response}")
            
            # 清理响应文本，确保是有效的JSON
            cleaned_response = response.strip()
            if cleaned_response.startswith("```json"):
                cleaned_response = cleaned_response[7:]
            if cleaned_response.endswith("```"):
                cleaned_response = cleaned_response[:-3]
            cleaned_response = cleaned_response.strip()
            
            # 尝试解析JSON
            try:
                result = json.loads(cleaned_response)
                logger.debug(f"解析后的JSON结果: {result}")
                
                # 验证必要的字段
                if 'category' not in result or 'confidence' not in result:
                    raise ValueError("响应缺少必要的字段")
                    
                # 确保confidence是浮点数
                confidence = float(result['confidence'])
                if not 0 <= confidence <= 1:
                    confidence = 0.5  # 如果置信度不在有效范围内，使用默认值
                    
                return (result['category'], confidence)
                
            except json.JSONDecodeError as e:
                logger.error(f"JSON解析错误: {str(e)}")
                logger.error(f"清理后的响应: {cleaned_response}")
                return (None, 0.0)
                
        except Exception as e:
            logger.error(f"邮件分类过程出错: {str(e)}")
            logger.error(f"错误详情: ", exc_info=True)
            return (None, 0.0)
    
    def classify_emails(self) -> Dict:
        """对所有邮件进行分类"""
        results = {}
        logger.info(f"开始扫描目录: {self.email_dir}")
        
        # 按文件名排序处理文件
        files = sorted(os.listdir(self.email_dir))
        for filename in files:
            if not filename.endswith('.txt'):
                continue
                
            logger.info(f"处理文件: {filename}")
            file_path = os.path.join(self.email_dir, filename)
            file_results = []
            
            try:
                emails = self._parse_email_file(file_path)
                logger.info(f"从 {filename} 中解析出 {len(emails)} 封邮件")
                
                for i, email in enumerate(emails, 1):
                    if not self._is_valid_email_content(email):
                        logger.debug(f"跳过无效或不相关邮件: {filename} 第 {i} 封邮件")
                        continue
                    
                    category, confidence = self._classify_email(email)
                    
                    if category:
                        if confidence >= self.similarity_threshold or not self.categories:
                            # 添加到已有分类或创建新分类
                            if category not in self.categories:
                                self.categories[category] = []
                            self.categories[category].append(email)
                            
                            file_results.append({
                                'content': email,
                                'category': category,
                                'confidence': confidence
                            })
                            logger.info(f"邮件已分类: {category} (置信度: {confidence})")
                
                if file_results:
                    results[filename] = file_results
                    
            except Exception as e:
                logger.error(f"处理文件 {filename} 时出错: {str(e)}")
                continue
        
        return results

    def save_results(self, results: Dict, output_file: str):
        """保存分类结果到JSON文件"""
        with open(output_file, 'w', encoding='utf-8') as f:
            json.dump(results, f, ensure_ascii=False, indent=2)