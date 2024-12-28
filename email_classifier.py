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
        self.output_base_dir = os.path.join(email_dir, "classified")  # 添加输出基础目录
        if not os.path.exists(self.output_base_dir):
            os.makedirs(self.output_base_dir)
        
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
            if len(content) < 50:
                return False
            
            prompt = f"""
            请判断以下邮件内容是否与技术支持案例的处理阶段相关。
            邮件内容应该体现案例处理的某个阶段，如问题定义、方案讨论、测试实施等。
            如果内容仅包含简单的确认、问候等信息，则视为不相关。

            邮件内容：
            {content}

            请只回答"相关"或"不相关"（不要添加任何其他内容）。
            """
            
            try:
                # 首先尝试使用 Azure LLM
                response = self.llm._call_azure_llm_basic(prompt)
            except Exception as azure_error:
                logger.warning(f"Azure LLM 调用失败: {str(azure_error)}, 尝试使用 Kimi")
                try:
                    # Azure 失败后尝试使用 Kimi
                    response = self.llm._call_kimi_basic(prompt)
                except Exception as kimi_error:
                    logger.error(f"Kimi 调用也失败: {str(kimi_error)}")
                    return False

            response = response.strip().lower()
            logger.debug(f"内容相关性判断结果: {response}")
            return "相关" in response
                
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

                可选的处理阶段(不限于以下阶段)：
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
                如果不属于任何已有分类（相似度低于80%），请根据邮件内容定义新的阶段分类。
                新的阶段分类命名要符合技术支持案例的处理阶段命名规范，不要使用"新"、"其他"、"未知"等模糊词汇。

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
            try:
                # 首先尝试使用 Azure LLM
                response = self.llm._call_azure_llm_basic(prompt)
            except Exception as azure_error:
                logger.warning(f"Azure LLM 调用失败: {str(azure_error)}, 尝试使用 Kimi")
                try:
                    # Azure 失败后尝试使用 Kimi
                    response = self.llm._call_kimi_basic(prompt)
                except Exception as kimi_error:
                    logger.error(f"Kimi 调用也失败: {str(kimi_error)}")
                    raise Exception("所有 LLM 调用都失败")

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
    
    def _save_email_to_category(self, category: str, case_id: str, email_content: str):
        """保存邮件到对应分类目录"""
        try:
            # 创建分类目录
            category_dir = os.path.join(self.output_base_dir, category)
            if not os.path.exists(category_dir):
                os.makedirs(category_dir)
            
            # 构建输出文件路径
            output_file = os.path.join(category_dir, f"{case_id}.txt")
            
            # 如果文件已存在，追加内容；否则创建新文件
            mode = 'a' if os.path.exists(output_file) else 'w'
            with open(output_file, 'a', encoding='utf-8') as f:
                if mode == 'a':
                    f.write(f"\n====第{self._get_email_count(output_file) + 1}封邮件====\n")
                else:
                    f.write(f"====第1封邮件====\n")
                f.write(email_content)
                
            logger.info(f"已保存邮件到 {output_file}")
            
        except Exception as e:
            logger.error(f"保存邮件到分类目录时出错: {str(e)}")

    def _get_email_count(self, file_path: str) -> int:
        """获取文件中已有的邮件数量"""
        try:
            if not os.path.exists(file_path):
                return 0
            with open(file_path, 'r', encoding='utf-8') as f:
                content = f.read()
            return len(re.findall(r'====第\d+封邮件====', content))
        except Exception:
            return 0

    def _is_case_processed(self, case_id: str) -> bool:
        """检查案例是否已经处理过"""
        # 检查是否在任何分类目录下存在该案例的文件
        if os.path.exists(self.output_base_dir):
            for category in os.listdir(self.output_base_dir):
                category_path = os.path.join(self.output_base_dir, category)
                if os.path.isdir(category_path):
                    case_file = os.path.join(category_path, f"{case_id}.txt")
                    if os.path.exists(case_file):
                        logger.info(f"案例 {case_id} 已在 {category} 分类中存在")
                        return True
        return False

    def classify_emails(self) -> Dict:
        """对所有邮件进行分类"""
        results = {}
        logger.info(f"开始扫描目录: {self.email_dir}")
        
        files = sorted(os.listdir(self.email_dir))
        for filename in files:
            if not filename.endswith('.txt'):
                continue
                
            # 从文件名中提取案例编号
            case_id = os.path.splitext(filename)[0]
            
            # 检查案例是否已处理
            if self._is_case_processed(case_id):
                logger.info(f"跳过已处理的案例: {case_id}")
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
                            
                            # 保存邮件到对应的分类目录
                            self._save_email_to_category(category, case_id, email)
                            
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