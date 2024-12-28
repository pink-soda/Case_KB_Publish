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
            # 分割长文本
            #desc_chunks = self._split_text(description)
            #hierarchy_chunks = self._split_text(category_hierarchy)
            
            # 构建提示，只使用文本的前部分
            prompt = f"""
            请分析以下技术支持描述，并从给定的类别层级中选择最合适的最小子类别进行分类。
            请只返回一个最具体的子类别（最深层级的类别）。

            描述文本：
            {description}

            可选的类别层级：
            {category_hierarchy}

            请以JSON格式返回结果，必须严格按照以下格式：
            {{
                "categories": ["具体类别名称"],
                "confidence_scores": [0.8],
                "explanation": "选择该类别的理由说明"
            }}
            """

            messages = [
                {
                    "role": "system", 
                    "content": "你是一个专业的技术支持分类专家。请严格按照要求的JSON格式返回结果。"
                },
                {"role": "user", "content": prompt}
            ]

            response = self.client.chat.completions.create(
                model=self.model,
                messages=messages
            )

            result = response.choices[0].message.content
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

                # 验证结果格式
                if not all(key in parsed_result for key in ['categories', 'confidence_scores', 'explanation']):
                    raise ValueError("响应缺少必要的字段")

                logger.info(f"Kimi分析结果: {parsed_result}")
                return parsed_result

            except json.JSONDecodeError as je:
                logger.error(f"JSON解析错误: {str(je)}")
                logger.error(f"原始响应内容: {result}")
                return {
                    "categories": ["未分类"],
                    "confidence_scores": [0.5],
                    "explanation": "响应格式解析失败"
                }

        except Exception as e:
            logger.error(f"Kimi分析失败: {str(e)}")
            logger.error(f"错误类型: {type(e).__name__}")
            logger.error(traceback.format_exc())
            return {
                "categories": ["未分类"],
                "confidence_scores": [0.5],
                "explanation": "Kimi分析服务暂时不可用"
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

            描述文本：
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

            try:
                # 尝试使用 Azure OpenAI
                response = self._call_azure_llm(prompt)
                result = self._parse_llm_response(response)
                logger.info(f"Azure LLM分析成功: {result}")
                return self._format_result(result)
            except Exception as azure_error:
                logger.warning(f"Azure LLM失败，切换到Kimi: {str(azure_error)}")
                # 如果 Azure 失败，使用 Kimi
                result = self.kimi_handler.analyze_text(description, formatted_hierarchy)
                logger.info(f"Kimi分析结果: {result}")
                return self._format_result(result)

        except Exception as e:
            logger.error(f"所有分析方法都失败: {str(e)}")
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

    def _call_azure_llm_basic(self, prompt: str) -> str:
        """
        调用Azure OpenAI API，如果失败则切换到Kimi
        """
        try:
            # 首先尝试使用Azure LLM
            logger.info("开始调用Azure LLM")
            logger.debug(f"发送的prompt: {prompt[:200]}...")
            
            response = self.client.chat.completions.create(
                model=self.deployment_name,
                messages=[
                    {"role": "system", "content": "你是一个专业的技术支持工程师，擅长总结技术问题和解决方案。"},
                    {"role": "user", "content": prompt}
                ],
                temperature=0.7,
                max_tokens=1000
            )
            
            result = response.choices[0].message.content
            logger.info(f"Azure LLM响应成功，返回内容长度: {len(result)}")
            logger.debug(f"返回内容预览: {result[:200]}...")
            
            return result
            
        except Exception as azure_error:
            logger.warning(f"Azure LLM调用失败，切换到Kimi: {str(azure_error)}")
            try:
                # 使用Kimi作为备选
                response = self.kimi_handler.client.chat.completions.create(
                    model=self.kimi_handler.model,
                    messages=[
                        {"role": "system", "content": "你是一个专业的技术支持工程师，擅长总结技术问题和解决方案。"},
                        {"role": "user", "content": prompt}
                    ]
                )
                result = response.choices[0].message.content
                logger.info("Kimi响应成功")
                logger.info(f"Kimi响应内容: {result}")
                return result
                
            except Exception as kimi_error:
                logger.error(f"Kimi调用也失败了: {str(kimi_error)}")
                logger.error(traceback.format_exc())
                raise Exception("Azure和Kimi都调用失败了") from kimi_error

    @retry(
        stop=stop_after_attempt(3),  # 最多重试3次
        wait=wait_exponential(multiplier=1, min=3, max=10),  # 指数退避，最少等待3秒
        reraise=False  # 不重新抛出异常
    )

    def _call_azure_llm(self, prompt: str) -> str:
        """
        调用Azure OpenAI API，带有重试机制
        """
        try:
            response = self.client.chat.completions.create(
                model=self.deployment_name,
                messages=[
                    {
                        "role": "system",
                        "content": "你是一个专业的技术支持分类专家，擅长分析技术问题并进行准确分类。"
                    },
                    {
                        "role": "user",
                        "content": prompt
                    }
                ],
                temperature=0.3
            )
            return response.choices[0].message.content.strip()
        except Exception as e:
            logger.error(f"调用Azure LLM失败: {str(e)}")
            if "429" in str(e):  # 如果是速率限制错误
                logger.info("触发速率限制，等待后重试...")
                time.sleep(3)  # 强制等待3秒
                raise Exception("Azure LLM调用失败") from e # 重新抛出异常以触发重试
            elif "401" in str(e):  # 如果是认证错误
                logger.info("认证失败，切换到Kimi...")
                raise Exception("Azure LLM认证失败") from e # 抛出异常以触发切换到Kimi
            return self._get_default_response()  # 如果是其他错误，返回默认响应

    def _get_default_response(self) -> str:
        """
        当LLM调用失败时返回的默认响应
        """
        return json.dumps({
            "categories": ["未分类"],
            "confidence_scores": [0.5],
            "explanation": "由于系统限制，暂时无法进行分类分析。请稍后重试。"
        })

    def _parse_llm_response(self, response: str) -> dict:
        """
        解析LLM的响应内容为字典格式
        """
        try:
            # 打印原始响应以便调试
            print("原始响应:", response)
            
            # 如果响应已经是字典格式，直接返回
            if isinstance(response, dict):
                return response
            
            # 确保响应不是空的
            if not response or not isinstance(response, str):
                raise ValueError(f"无效的响应格式: {type(response)}")
            
            # 清理响应文本，移除多余的空格和换行
            cleaned_response = response.strip().replace('\n', '').replace('    ', '')
            print("清理后的响应:", cleaned_response)
            
            # 尝试直接解析JSON
            try:
                result = json.loads(cleaned_response)
                print("成功解析JSON:", result)
            except json.JSONDecodeError:
                # 如果解析失败，尝试提取JSON部分
                import re
                json_pattern = r'\{[^{}]*\}'
                match = re.search(json_pattern, cleaned_response)
                if match:
                    json_str = match.group()
                    print("提取的JSON字符串:", json_str)
                    try:
                        result = json.loads(json_str)
                        print("成功解析提取的JSON:", result)
                    except json.JSONDecodeError as e:
                        print(f"JSON解析错误位置: 行 {e.lineno}, 列 {e.colno}")
                        print(f"JSON解析错误信息: {e.msg}")
                        raise
                else:
                    raise Exception("无法从响应中提取有效的JSON格式")
            
            # 确保所有必需的字段都存在
            required_fields = ['categories', 'confidence_scores']
            missing_fields = [field for field in required_fields if field not in result]
            if missing_fields:
                logger.warning(f"LLM响应缺少必要字段: {missing_fields}，使用默认值")
                return {
                    "categories": result.get('categories', ["未分类"]),
                    "confidence_scores": [0.5] * len(result.get('categories', ["未分类"])),
                    "explanations": result.get('explanations', ["无解释"])
                }
            
            # 确保置信度在0-1之间
            result['confidence_scores'] = [
                min(max(float(score), 0), 1) 
                for score in result['confidence_scores']
            ]
            
            print("最终处理结果:", result)
            return result
            
        except Exception as e:
            print(f"解析LLM响应时出现错误: {type(e).__name__}")
            print(f"错误信息: {str(e)}")
            print(f"原始响应内容: {response}")
            logger.error(f"解析LLM响应失败: {str(e)}")
            return {
                "categories": ["未分类"],
                "confidence_scores": [0.5],
                "explanations": ["解析失败"]
            }

    def generate_email(self, reference_emails: str, progress_description: str, case_info: dict) -> str:
        """
        生成邮件内容，如果Azure失败则使用Kimi
        """

        try:
            # 先尝试使用Azure
            try:
                return self._generate_email_azure(reference_emails, progress_description, case_info)
            except Exception as azure_error:
                logger.warning(f"Azure邮件生成失败，切换到Kimi: {str(azure_error)}")
                return self._generate_email_kimi(reference_emails, progress_description, case_info)
            
        except Exception as e:
            logger.error(f"邮件生成失败: {str(e)}")
            raise

    def _generate_email_azure(self, reference_emails: str, progress_description: str, case_info: dict) -> str:
        """使用Azure生成邮件"""
        try:
            # 分割长文本
            #ref_chunks = self._split_text(reference_emails)
            
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

            response = self.client.chat.completions.create(
                model=self.deployment_name,
                messages=[
                    {
                        "role": "system",
                        "content": "你是一个专业的技术支持工程师，擅长编写技术支持邮件。"
                    },
                    {
                        "role": "user",
                        "content": prompt
                    }
                ],
                temperature=0.7,  # 适当提高创造性
                max_tokens=1000   # 允许较长的回复
            )

            email_content = response.choices[0].message.content.strip()
            
            # 如果返回的内容包含多余的引号或格式标，清理它们
            email_content = email_content.strip('`').strip('"')
            
            return email_content
            
        except Exception as e:
            logger.error(f"Azure邮件生成失败: {str(e)}")
            raise
    
    def _generate_email_kimi(self, reference_emails: str, progress_description: str, case_info: dict) -> str:
        """使用Kimi生成邮件"""
        try:
            # 分割长文本
            #ref_chunks = self.kimi_handler._split_text(reference_emails)
            
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

            messages = [
                {"role": "system", "content": "你是一个专业的技术支持工程师，擅长编写技术支持邮件。"},
                {"role": "user", "content": prompt}
            ]

            response = self.kimi_handler.client.chat.completions.create(
                model=self.kimi_handler.model,
                messages=messages
            )

            email_content = response.choices[0].message.content.strip()
            
            # 如果返回的内容包含多余的引号或格式标，清理它们
            email_content = email_content.strip('`').strip('"')
            
            return email_content

        except Exception as e:
            logger.error(f"生成邮件失败: {str(e)}")
            raise Exception(f"生成邮件失败: {str(e)}")

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
            # 打印输入参数
            logger.info(f"计算置信度 - 输入分类: {assigned_categories}")
            
            # 提取案例文本内容
            text_content = '\n'.join([page.get('text', '') for page in case_content.get('pages', [])])
            
            # 构建提示
            prompt = f"""
            请分析以下案例内容，并评估其与给定分类的匹配程度。

            案例内容：
            {text_content}
            
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
            
            # 调用LLM获取评分
            response = self._call_azure_llm_basic(prompt)
            logger.info(f"LLM原始响应: {response}")
            
            # 解析响应
            try:
                result = json.loads(response)
                logger.info(f"解析后的结果: {result}")
                
                # 确保所有必要的字段都存在
                if not all(key in result.get('category_scores', {}) for key in ['level1', 'level2', 'level3']):
                    raise ValueError("响应缺少必要的评分字段")
                
                # 返回标准化的置信度分数
                confidence_scores = {
                    'level1': float(result['category_scores'].get('level1', 0)),
                    'level2': float(result['category_scores'].get('level2', 0)),
                    'level3': float(result['category_scores'].get('level3', 0)),
                    'explanations': result.get('explanations', {}),
                    'reasoning': result.get('reasoning', {})
                }
                
                logger.info(f"最终置信度分数: {confidence_scores}")
                return confidence_scores
                
            except json.JSONDecodeError as e:
                logger.error(f"JSON解析错误: {str(e)}")
                logger.error(f"原始响应: {response}")
                raise
                
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
        try:
            response = self._call_azure_llm_basic("Hello")
            print("连接测试成功!")
            return True
        except Exception as e:
            print(f"连接测试失败: {str(e)}")
            return False
