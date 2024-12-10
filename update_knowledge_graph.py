from knowledge_graph import KnowledgeGraph
import logging

def update_knowledge_graph():
    try:
        # 更新知识图谱
        kg = KnowledgeGraph()
        success, message = kg.import_categories_from_json()
        
        if not success:
            logging.error(f"更新知识图谱失败: {message}")
        else:
            if kg.verify_data():
                print("知识图谱更新成功")
            else:
                print("更新知识图谱可能有问题")
            
    except Exception as e:
        logging.error(f"更新知识图谱过程发生错误: {str(e)}")

if __name__ == "__main__":
    update_knowledge_graph() 