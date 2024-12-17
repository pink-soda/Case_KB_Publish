import pandas as pd
import json
import os
import logging
from datetime import datetime
from llm_handler import LLMHandler

# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('case_sync.log', encoding='utf-8'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

def get_default_columns():
    """返回CSV文件的默认列名"""
    return [
        '案例编号', '客户名称', '所属类别', '联系人', '联系电话', 
        '案例标题', 'case_owner', '系统版本', '案例定义', '案例进度',
        '有无上传日志', '案例总结', '案例详情', '案例评审', '案例置信度评分', '案例评价'
    ]

def create_empty_csv():
    """创建空的CSV文件"""
    try:
        df = pd.DataFrame(columns=get_default_columns())
        df.to_csv('e:\\Case_KB\\cases.csv', index=False, encoding='utf-8')
        logger.info("成功创建空的cases.csv文件")
        return True
    except Exception as e:
        logger.error(f"创建cases.csv文件失败: {str(e)}")
        return False

def convert_category_to_string(category_dict):
    """将分类字典转换为字符串"""
    if not category_dict:
        return ""
    return f"{category_dict.get('level1', '')},{category_dict.get('level2', '')},{category_dict.get('level3', '')}"

def process_case_entry(case_data, df):
    """处理单个案例条目"""
    try:
        # 从文件路径中提取案例编号
        case_id = os.path.splitext(os.path.basename(case_data['file_path']))[0]
        
        # 转换分类为字符串
        category_str = convert_category_to_string(case_data.get('classification', {}))
        
        # 获取置信度评分
        confidence_score = 0
        if 'category_score' in case_data:
            # 按照固定顺序获取分数
            scores = [
                case_data['category_score'].get('level1', 0),
                case_data['category_score'].get('level2', 0),
                case_data['category_score'].get('level3', 0)
            ]
            
            # 过滤掉所有为0的分数，只保留有效分数
            valid_scores = [score for score in scores if score > 0]
            
            if len(valid_scores) == 3:
                # 如果有三个有效分数，使用加权计算
                confidence_score = scores[0] * 0.4 + scores[1] * 0.1 + scores[2] * 0.5
            elif valid_scores:
                # 如果有效分数不足3个但大于0个，使用平均值
                confidence_score = sum(valid_scores) / len(valid_scores)
            else:
                # 如果没有有效分数，置信度为0
                confidence_score = 0

            
        # 检查案例是否已存在
        existing_case = df[df['案例编号'] == case_id]
        
        if len(existing_case) > 0:
            # 案例已存在，检查分类是否相同
            if existing_case['所属类别'].iloc[0] != category_str:
                # 更新分类和相关字段
                df.loc[df['案例编号'] == case_id, '所属类别'] = category_str
                df.loc[df['案例编号'] == case_id, '案例评审'] = 'pending'
                df.loc[df['案例编号'] == case_id, '案例置信度评分'] = confidence_score
                logger.info(f"更新案例 {case_id} 的分类信息")
            else:
                # 分类相同，只更新评审状态和置信度
                df.loc[df['案例编号'] == case_id, '案例评审'] = 'pending'
                df.loc[df['案例编号'] == case_id, '案例置信度评分'] = confidence_score
                logger.info(f"更新案例 {case_id} 的评审状态和置信度")
        else:
            # 案例不存在，创建新记录
            new_case = {
                '案例编号': case_id,
                '客户名称': '',
                '所属类别': category_str,
                '联系人': '',
                '联系电话': '',
                '案例标题': '',
                'case_owner': '',
                '系统版本': '',
                '案例定义': '',
                '案例进度': '已完结',
                '有无上传日志': '',
                '案例总结': '',
                '案例详情': case_data.get('file_path', ''),
                '案例评审': 'pending',
                '案例置信度评分': confidence_score,
                '案例评价': case_data.get('reasoning', '')
            }
            df = pd.concat([df, pd.DataFrame([new_case])], ignore_index=True)
            logger.info(f"添加新案例 {case_id}")
            
        # 获取案例总结
        case_summary = ''
        email_file_path = os.path.join('E:', 'Case_KB', 'emails_words', f'{case_id}.txt')
        if os.path.exists(email_file_path):
            try:
                with open(email_file_path, 'r', encoding='utf-8') as f:
                    email_content = f.read()
                
                # 使用LLM生成案例总结
                llm = LLMHandler()
                prompt = f"""
                请根据以下技术支持邮件内容，生成一个简洁的案例总结。总结应该包含：
                1. 问题的核心描述
                2. 解决方案要点
                3. 关键的技术细节

                要求：
                1. 总结长度控制在200字以内
                2. 使用客观、专业的语言
                3. 突出重点，去除冗余信息
                4. 保持技术准确性

                邮件内容：
                {email_content}

                请直接输出总结内容，不需要任何额外的格式或说明。
                """
                
                response = llm._call_azure_llm(prompt)
                case_summary = response.strip()
                logger.info(f"成功生成案例 {case_id} 的总结")
            except Exception as e:
                logger.error(f"生成案例 {case_id} 总结时出错: {str(e)}")
                case_summary = ''
        
        # 更新案例总结字段
        if len(existing_case) > 0:
            df.loc[df['案例编号'] == case_id, '案例总结'] = case_summary
        else:
            new_case['案例总结'] = case_summary
            
        return df
        
    except Exception as e:
        logger.error(f"处理案例 {case_id} 时出错: {str(e)}")
        return df

def sync_cases(is_update=False):
    """同步案例数据"""
    try:
        csv_path = 'e:\\Case_KB\\cases.csv'
        json_path = 'classified_cases.json'
        
        # 检查JSON文件是否存在
        if not os.path.exists(json_path):
            return False, "classified_cases.json 文件不存在"
            
        # 读取JSON文件
        try:
            with open(json_path, 'r', encoding='utf-8') as f:
                classified_cases = json.load(f)
        except Exception as e:
            logger.error(f"读取JSON文件失败: {str(e)}")
            return False, f"读取classified_cases.json失败: {str(e)}"
            
        if not classified_cases:
            return False, "classified_cases.json 文件为空"
            
        # 检查CSV文件是否存在
        if not os.path.exists(csv_path):
            if is_update:
                return False, "cases.csv 文件不存在，无法执行更新操作"
            else:
                if not create_empty_csv():
                    return False, "创建 cases.csv 文件失败"
                    
        # 读取CSV文件
        try:
            # 尝试不同的编码方式
            try:
                df = pd.read_csv(csv_path, encoding='utf-8')
            except UnicodeDecodeError:
                try:
                    df = pd.read_csv(csv_path, encoding='gbk')
                except UnicodeDecodeError:
                    # 如果都失败了，创建新的空DataFrame
                    logger.warning("无法读取现有CSV文件，创建新的DataFrame")
                    df = pd.DataFrame(columns=get_default_columns())
        except Exception as e:
            logger.error(f"读取CSV文件失败: {str(e)}")
            if not is_update:
                if not create_empty_csv():
                    return False, "创建 cases.csv 文件失败"
                df = pd.DataFrame(columns=get_default_columns())
            else:
                return False, f"读取 cases.csv 文件失败: {str(e)}"
                
        # 处理每个案例
        for case in classified_cases:
            df = process_case_entry(case, df)
            
        # 保存更新后的CSV文件
        try:
            df.to_csv(csv_path, index=False, encoding='utf-8')
        except Exception as e:
            logger.error(f"保存CSV文件失败: {str(e)}")
            return False, f"保存cases.csv失败: {str(e)}"
        
        action = "更新" if is_update else "构建"
        return True, f"成功{action}案例库"
        
    except Exception as e:
        logger.error(f"同步案例数据失败: {str(e)}")
        return False, f"同步案例数据失败: {str(e)}"

def build_case_library():
    """构建案例库"""
    return sync_cases(is_update=False)

def update_case_library():
    """更新案例库"""
    return sync_cases(is_update=True)

def main():
    """主函数：提供命令行交互界面"""
    print("案例库同步工具")
    print("1. 构建案例库")
    print("2. 更新案例库")
    choice = input("请选择操作 (1/2): ")
    
    if choice == "1":
        success, message = build_case_library()
    elif choice == "2":
        success, message = update_case_library()
    else:
        print("无效的选择")
        return
    
    print(f"执行结果: {'成功' if success else '失败'}")
    print(f"消息: {message}")

if __name__ == "__main__":
    main() 