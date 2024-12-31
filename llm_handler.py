from openai import AzureOpenAI, OpenAI
import json
import os
from dotenv import load_dotenv
import logging
from azure.core.credentials import AzureKeyCredential
#from azure.ai.textanalytics import TextAnalyticsClient
import traceback
import time
from tenacity import retry, stop_after_attempt, wait_exponential
import requests

logger = logging.getLogger(__name__)

# 加载环境变量
load_dotenv()

class KimiHandler:
    def __init__(self):
        # 初始化 Kimi API 客户端
        self.client = OpenAI(
            api_key=os.getenv("KIMI_API_KEY").rstrip(','),
            base_url=os.getenv("KIMI_BASE_URL").rstrip(',')
        )
        self.model = os.getenv("KIMI_MODEL_NAME")
        self.max_tokens = 128000  # Kimi的token限制
        self.model = "moonshot-v1-auto"  # 使用指定的模型

    def _split_text(self, text: str, max_length: int = 128000) -> list:
        """
        将长文本分割成多个小块
        """
        words = text.split()
        chunks = []
        current_chunk = []
        current_length = 0
        
        for word in words:
            word_length = len(word) + 1  # +1 for space
            if current_length + word_length > max_length:
                chunks.append(' '.join(current_chunk))
                current_chunk = [word]
                current_length = word_length
            else:
                current_chunk.append(word)
                current_length += word_length
                
        if current_chunk:
            chunks.append(' '.join(current_chunk))
            
        return chunks

    def analyze_text(self, description: str, category_hierarchy: str) -> dict:
        """使用 Kimi 分析文本并返回分类结果"""
        try:
            # 构建提示
            sys_prompt = "你是一个专业的技术支持分类专家。请严格按照要求的JSON格式返回结果。"
            prompt = f"""
            请分析以下技术支持描述，并从给定的类别层级中选择最合适的最小子类别进行分类。
            请只返回一个最具体的子类别（最深层级的类别）。
            如果某一级别找不到合适的分类，请将该级别设置为"案例中不存在该级别分类"。

            描述文本：
            {description}

            可选的类别层级：
            {category_hierarchy}

            请以JSON格式返回结果，必须严格按照以下格式：
            {{
                "level1": "一级分类名称",
                "level2": "二级分类名称或'案例中不存在该级别分类'",
                "level3": "三级分类名称或'案例中不存在该级别分类'",
                "similarity": {{
                    "level1": 0.8,  // 与现有分类的相似度（0-1）
                    "level2": 0.8,
                    "level3": 0.8
                }},
                "matched_path_level1": "匹配到的一级分类路径",
                "matched_path_level2": "匹配到的二级分类路径",
                "matched_path_level3": "匹配到的三级分类路径",
                "reasoning": "选择该分类的理由说明"
            }}
            """

            completion = self.client.chat.completions.create(
                model=self.model,
                messages=[
                    {"role": "system", "content": sys_prompt},
                    {"role": "user", "content": prompt}
                ]
            )

            result = completion.choices[0].message.content
            logger.debug(f"Kimi原始响应: {result}")

            # 尝试提取JSON部分
            try:
                # 如果响应包含多余的文本，尝试提取JSON部分
                import re
                json_pattern = r'\{[^{}]*\}'
                match = re.search(json_pattern, result)
                if match:
                    json_str = match.group()
                    logger.debug(f"提取的JSON字符串: {json_str}")
                    parsed_result = json.loads(json_str)
                else:
                    # 如果没有找到JSON格式，尝试直接解析
                    parsed_result = json.loads(result)

                # 构造标准化的返回结果
                standardized_result = {
                    "level1": parsed_result.get('level1') or "案例中不存在该级别分类",
                    "level2": parsed_result.get('level2') or "案例中不存在该级别分类",
                    "level3": parsed_result.get('level3') or "案例中不存在该级别分类",
                    "similarity": {
                        "level1": float(parsed_result.get('similarity', {}).get('level1', 0)),
                        "level2": float(parsed_result.get('similarity', {}).get('level2', 0)),
                        "level3": float(parsed_result.get('similarity', {}).get('level3', 0))
                    },
                    "matched_path_level1": parsed_result.get('matched_path_level1', ''),
                    "matched_path_level2": parsed_result.get('matched_path_level2', ''),
                    "matched_path_level3": parsed_result.get('matched_path_level3', ''),
                    "reasoning": parsed_result.get('reasoning', '')
                }
                
                logger.info(f"标准化后的分析结果: {standardized_result}")
                return standardized_result
                
            except json.JSONDecodeError as je:
                logger.error(f"JSON解析错误: {str(je)}")
                return {
                    "level1": "LLM响应解析失败",
                    "level2": "LLM响应解析失败",
                    "level3": "LLM响应解析失败",
                    "similarity": {
                        "level1": 0.0,
                        "level2": 0.0,
                        "level3": 0.0
                    },
                    "matched_path_level1": "",
                    "matched_path_level2": "",
                    "matched_path_level3": "",
                    "reasoning": f"JSON解析错误: {str(je)}"
                }

        except Exception as e:
            logger.error(f"Kimi分析失败: {str(e)}")
            return {
                "level1": "LLM服务异常",
                "level2": "LLM服务异常",
                "level3": "LLM服务异常",
                "similarity": {
                    "level1": 0.0,
                    "level2": 0.0,
                    "level3": 0.0
                },
                "matched_path_level1": "",
                "matched_path_level2": "",
                "matched_path_level3": "",
                "reasoning": f"服务调用失败: {str(e)}"
            }

class LLMHandler:
    def __init__(self):
        load_dotenv()  # 加载.env文件
        self.api_key = os.getenv("AZURE_OPENAI_API_KEY_2")
        self.endpoint = os.getenv("AZURE_OPENAI_ENDPOINT").rstrip('/')
        self.api_version = os.getenv("AZURE_OPENAI_API_VERSION")
        
        # 添加调试日志
        logger.debug(f"API Key: {self.api_key[:5]}...")  # 只显示前5个字符
        logger.debug(f"Endpoint: {self.endpoint}")
        logger.debug(f"API Version: {self.api_version}")
        
        # 初始化Azure OpenAI客户端
        self.client = AzureOpenAI(
            api_key=self.api_key,
            api_version=self.api_version,
            azure_endpoint=self.endpoint
        )
        
        # 部署名称
        self.deployment_name = os.getenv("MODEL_NAME")
        
        # 初始化 Kimi 处理器作为备用
        self.kimi_handler = KimiHandler()
        #self.max_tokens = 128000  # Azure的token限制
    '''
    def _split_text(self, text: str, max_length: int = 128000) -> list:
        """
        将长文本分割成多个小块
        """
        words = text.split()
        chunks = []
        current_chunk = []
        current_length = 0
        
        for word in words:
            word_length = len(word) + 1  # +1 for space
            if current_length + word_length > max_length:
                chunks.append(' '.join(current_chunk))
                current_chunk = [word]
                current_length = word_length
            else:
                current_chunk.append(word)
                current_length += word_length
                
        if current_chunk:
            chunks.append(' '.join(current_chunk))
            
        return chunks    
    '''
    def analyze_description_with_categories(self, description: str, category_hierarchy: dict) -> dict:
        """
        使用Azure LLM分析描述文本，并根据知识图谱中的类别进行分类
        返回格式：只返回最小子类别及其置信度和解释
        如果失败则使用Kimi作为备选方案
        """
        try:
            # 格式化类别层级结构
            # 首先尝试使用 Azure OpenAI
            formatted_hierarchy = self._format_category_hierarchy(category_hierarchy)
            
            # 构建prompt
            prompt = f"""
            请分析以下技术支持描述，并从给定的类别层级中选择最合适的最小子类别进行分类。
            请只返回一个最具体的子类别（最深层级的类别）。

            案例描述：
            {description}

            可选的类别层级：
            {formatted_hierarchy}

            请以JSON格式返回结果，包含以下字段：
            1. categories: 包含一个元素的列表，表示最合适的最小子类别
            2. confidence_scores: 对应的置信度（0-1之间的浮点数）
            3. explanation: 选择该类别的理由说明

            示例返回格式：
            {{
                "categories": ["音频设备问题"],
                "confidence_scores": [0.9],
                "explanation": "根据描述中提到的音频设备故障特征，该问题属于音频设备问题类别。"
            }}
            """

            # 修改这里：使用统一的 call_llm 方法
            response = self.call_llm(prompt)
            
            try:
                result = json.loads(response)
                return {
                    'category': result.get('matched_category', '未分类'),
                    'confidence': float(result.get('confidence', 0.5)),
                    'explanation': result.get('explanation', '')
                }
            except json.JSONDecodeError:
                logger.error(f"JSON解析失败: {response}")
                return {
                    'category': '未分类',
                    'confidence': [0.5],
                    'explanation': '解析失败'
                }
            
        except Exception as e:
            logger.error(f"分析描述失败: {str(e)}")
            return {
                'categories': ['未分类'],
                'confidence_scores': [0.5],
                'explanation': f'分析失败: {str(e)}'
            }

    def _format_result(self, result: dict) -> dict:
        """统一格式化结果"""
        if result.get('categories'):
            category = result['categories'][0]
            if " - " in category:
                category = category.split(" - ")[-1].strip()
                result['categories'] = [category]

        return {
            'categories': result.get('categories', ['未分类']),
            'confidence_scores': result.get('confidence_scores', [0.5]),
            'explanation': result.get('explanation', '')
        }

    def _format_category_hierarchy(self, hierarchy: dict, level: int = 0) -> str:
        """
        递归格式化类别层级结构
        """
        if not hierarchy:
            return ""
        
        formatted_lines = []
        indent = "  " * level
        
        for category, value in hierarchy.items():
            # 添加当前类别
            formatted_lines.append(f"{indent}- {category}")
            
            if isinstance(value, dict):
                # 处理子类别
                if 'children' in value:
                    for child in value['children']:
                        if isinstance(child, dict) and 'name' in child:
                            # 添加子类别
                            formatted_lines.append(f"{indent}  - {child['name']}")
                            # 处理三级类别
                            if 'children' in child:
                                for grandchild in child['children']:
                                    if isinstance(grandchild, dict) and 'name' in grandchild:
                                        formatted_lines.append(f"{indent}    - {grandchild['name']}")
        
        return "\n".join(formatted_lines)

    def _get_all_categories(self, hierarchy: dict) -> set:
        """
        递归获取所有类别名称，包括所有层级
        """
        logger.debug(f"正在处理层级: {hierarchy}")
        categories = set()
        
        # 处理当前层级
        if isinstance(hierarchy, dict):
            for key, value in hierarchy.items():
                logger.debug(f"处理键: {key}, 值类型: {type(value)}")
                # 添加当前类别
                categories.add(key)
                
                if isinstance(value, dict):
                    # 处理子类别
                    if 'children' in value:
                        # 添加当前节点的名称
                        if 'name' in value:
                            categories.add(value['name'])
                        # 递归处理子节点
                        for child in value['children']:
                            if isinstance(child, dict) and 'name' in child:
                                categories.add(child['name'])
                                # 继续处理更深层的子节点
                                if 'children' in child:
                                    for grandchild in child['children']:
                                        if isinstance(grandchild, dict) and 'name' in grandchild:
                                            categories.add(grandchild['name'])
                    else:
                        # 处理没有children的节点
                        categories.update(self._get_all_categories(value))
        
        logger.debug(f"当前层级收集到的类别: {categories}")
        return categories - {''}  # 移除空字符串

    def call_llm(self, prompt: str, use_azure: bool = True) -> str:
        """统一的LLM调用方法，包含重试和fallback机制"""
        logger.info(f"开始LLM调用 (使用{'Azure' if use_azure else 'Kimi'})")
        
        try:
            if use_azure:
                try:
                    # Azure调用会通过装饰器自动重试3次
                    logger.debug("开始Azure调用")
                    result = self.__call_azure(prompt)
                    logger.info("Azure调用成功")
                    return result
                except Exception as azure_error:
                    logger.warning(f"Azure完全失败 (3次尝试)，切换到Kimi")
                    try:
                        # Kimi调用会通过装饰器自动重试3次
                        logger.debug("开始Kimi调用")
                        return self.__call_kimi(prompt)
                    except Exception as kimi_error:
                        logger.error("Kimi调用也完全失败 (3次尝试)")
                        # 不抛出异常，返回空字符串或特定的错误标记
                        return ""  # 或者返回 {"error": "LLM调用失败"}
            else:
                try:
                    return self.__call_kimi(prompt)
                except Exception as e:
                    logger.error(f"Kimi调用失败: {str(e)}")
                    return ""  # 或者返回 {"error": "LLM调用失败"}
                
        except Exception as e:
            logger.error(f"LLM调用完全失败 (Azure和Kimi各尝试3次)")
            return ""  # 或者返回 {"error": "LLM调用失败"}

    @retry(
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=3, max=10),
        reraise=True
    )
    def __call_azure(self, prompt: str) -> str:
        """内部Azure调用方法"""
        try:
            response = self.client.chat.completions.create(
                model=self.deployment_name,
                messages=[
                    {"role": "system", "content": "你是一个专业的技术支持工程师，擅长总结技术问题和解决方案。"},
                    {"role": "user", "content": prompt}
                ],
                temperature=0.7,
                max_tokens=1000
            )
            return response.choices[0].message.content.strip()
        except Exception as e:
            logger.error(f"Azure LLM调用失败: {str(e)}")
            raise

    @retry(
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=3, max=10),
        reraise=True
    )
    def __call_kimi(self, prompt: str) -> str:
        """内部Kimi调用方法"""
        try:
            completion = self.kimi_handler.client.chat.completions.create(
                model=self.kimi_handler.model,
                messages=[
                    {"role": "system", "content": "你是一个专业的技术支持工程师，擅长总结技术问题和解决方案。"},
                    {"role": "user", "content": prompt}
                ]
            )
            return completion.choices[0].message.content.strip()
        except Exception as e:
            logger.error(f"调用 Kimi 时出错: {str(e)}")
            raise

    def _get_category_with_parents(self, category: str, hierarchy: dict) -> list:
        """
        获取类别及其所有父类别
        返回格式: [一级分类, 二级分类, 三级分类]
        """
        logger.info(f"开始查找类别 '{category}' 的父类")
        
        # 如果输入的类别包含完整路径（用 " - " 分隔），先尝试提取最后一个类别
        if " - " in category:
            categories = category.split(" - ")
            target_category = categories[-1].strip()  # 获取最后一个类别名称
            logger.info(f"从完整路径中提取目标类别: {target_category}")
        else:
            target_category = category
        
        def search_in_hierarchy(current_category: str, current_hierarchy: dict, path: list = None) -> list:
            if path is None:
                path = []
                
            for level1, value1 in current_hierarchy.items():
                logger.debug(f"检查一级分类: {level1}")
                current_path = [level1]
                
                # 检查一级分类是否匹配
                if current_category == level1:
                    logger.info(f"找到一级分类匹配: {current_path}")
                    return current_path
                
                if isinstance(value1, dict):
                    logger.debug(f"检查 {level1} 的子分类")
                    # 检查二级分类
                    if 'children' in value1:
                        for child in value1['children']:
                            if isinstance(child, dict):
                                child_name = child.get('name')
                                logger.debug(f"检查二级分类: {child_name}")
                                if child_name == current_category:
                                    current_path.append(child_name)
                                    logger.info(f"找到二级分类匹配，完整路径: {current_path}")
                                    return current_path
                                
                                # 检查三级分类
                                if 'children' in child:
                                    for grandchild in child['children']:
                                        if isinstance(grandchild, dict):
                                            grandchild_name = grandchild.get('name')
                                            logger.debug(f"检查三级分类: {grandchild_name}")
                                            if grandchild_name == current_category:
                                                current_path.extend([child_name, grandchild_name])
                                                logger.info(f"找到三级分类匹配，完整路径: {current_path}")
                                                return current_path
            
            logger.warning(f"未找到类别 '{current_category}' 的父类")
            return []

        # 使用提取出的目标类别进行搜索
        result = search_in_hierarchy(target_category, hierarchy)
        if not result and " - " in category:
            # 如果使用最后一个类别没找到，尝试使用完整路径中的其他部分
            for cat in category.split(" - "):
                cat = cat.strip()
                result = search_in_hierarchy(cat, hierarchy)
                if result:
                    break
        
        logger.info(f"类别 '{category}' 的最终完整路径: {result}")
        return result

    def calculate_category_confidence(self, case_content, assigned_categories):
        """计算给定分类的置信度"""
        try:
            # 构建提示
            prompt = f"""
            请分析以下案例内容，并评估其与给定分类的匹配程度。

            案例内容：
            {case_content}
            
            分类：
            一级分类：{assigned_categories.get('level1', '')}
            二级分类：{assigned_categories.get('level2', '')}
            三级分类：{assigned_categories.get('level3', '')}
            
            请为每个级别的分类评分（0-1之间），评分标准：
            1. 完全匹配：0.9-1.0
            2. 高度相关：0.8-0.9
            3. 中度相关：0.6-0.8
            4. 低度相关：0.4-0.6
            5. 基本不相关：0-0.4

            请以JSON格式返回评分结果，必须包含以下字段：
            1. category_scores: 包含每个级别分类的得分
            2. explanations: 包含每个级别的评分理由
            3. reasoning: 如果得分低于0.8，需要提供改进建议

            示例返回格式：
            {{
                "category_scores": {{
                    "level1": 0.95,
                    "level2": 0.75,
                    "level3": 0.85
                }},
                "explanations": {{
                    "level1": "一级分类完全符合案例描述的问题性质",
                    "level2": "二级分类与案例内容相关但不够精确",
                    "level3": "三级分类准确匹配了具体错误类型"
                }},
                "reasoning": {{
                    "level2": "建议考虑更精确的二级分类，因为当前分类过于宽泛"
                }}
            }}
            """
            
            # 修改这里：使用统一的 call_llm 方法
            response = self.call_llm(prompt)
            result = json.loads(response)
            
            # 返回标准化的置信度分数
            confidence_scores = {
                'level1': float(result['category_scores'].get('level1', 0)),
                'level2': float(result['category_scores'].get('level2', 0)),
                'level3': float(result['category_scores'].get('level3', 0)),
                'explanations': result.get('explanations', {}),
                'reasoning': result.get('reasoning', {})
            }
            
            return confidence_scores
            
        except Exception as e:
            logger.error(f"计算置信度失败: {str(e)}")
            return {
                'level1': 0.0,
                'level2': 0.0,
                'level3': 0.0,
                'explanations': {},
                'reasoning': {}
            }

    def test_connection(self):
        """测试连接"""
        try:
            # 修改为使用统一的 call_llm 方法
            response = self.call_llm("Hello")
            print("连接测试成功!")
            return True
        except Exception as e:
            print(f"连接测试失败: {str(e)}")
            return False

    def generate_email(self, reference_emails: str, progress_description: str, case_info: dict) -> str:
        """生成邮件内容"""
        try:
            prompt = f"""
            你是一个专业的技术支持工程师，需要根据案例基本信息来对相关用户回复一封邮件，根据当前进度的描述，给出合适的指导意见，你需要以参考案例的历史邮件作为参考，生成一封新的进度更新邮件。

            参考邮件内容：
            {reference_emails}

            当前进度描述：
            {progress_description}

            案例基本信息：
            客户名称：{case_info.get('customer_name', '-')}
            联系人：{case_info.get('contact_person', '-')}
            案例标题：{case_info.get('project_subject', '-')}

            要求：
            1. 保持专业、礼貌的语气
            2. 参考历史邮件的格式和风格
            3. 包含问候语和结束语
            4. 清晰描述当前的处理进度
            5. 如果有下一步计划，请一并说明
            6. 保持邮件简洁明了
            7. 使用中文编写

            请直接生成邮件内容，不要添加任何额外的说明。
            """

            # 使用统一的 call_llm 方法
            email_content = self.call_llm(prompt)
            
            # 清理返回的内容
            email_content = email_content.strip('`').strip('"')
            return email_content
            
        except Exception as e:
            logger.error(f"邮件生成失败: {str(e)}")
            raise

