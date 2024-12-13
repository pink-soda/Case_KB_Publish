'''
Author: pink-soda luckyli0127@gmail.com
Date: 2024-12-03 15:41:12
LastEditors: pink-soda luckyli0127@gmail.com
LastEditTime: 2024-12-13 10:46:45
FilePath: \test\knowledge_graph.py
Description: 这是默认设置,请设置`customMade`, 打开koroFileHeader查看配置 进行设置: https://github.com/OBKoro1/koro1FileHeader/wiki/%E9%85%8D%E7%BD%AE
'''
from py2neo import Graph, Node, Relationship
import json
from neo4j import GraphDatabase
import logging

class KnowledgeGraph:
    def __init__(self):
        self.graph = Graph("bolt://localhost:7687", auth=("neo4j", "P@ssw0rd!"))
        # Neo4j连接配置
        self.uri = "bolt://localhost:7687"
        self.user = "neo4j"
        self.password = "P@ssw0rd!"
        self.driver = GraphDatabase.driver(self.uri, auth=(self.user, self.password))
        
    def get_category_hierarchy(self):
        """获取完整的分类层级结构"""
        try:
            with self.driver.session() as session:
                # 1. 找到所有根节点
                root_query = session.run("""
                    MATCH (root:Category)
                    WHERE NOT ()-[:HAS_SUBCATEGORY]->(root)
                    RETURN collect(root.name) as root_names
                """)
                result = root_query.single()
                if not result or not result['root_names']:
                    logging.warning("未找到根节点")
                    return {}
                    
                root_names = result['root_names']
                logging.info(f"找到根节点: {root_names}")

                # 如果有多个根节点，创建一个虚拟的顶层节点
                hierarchy = {
                    'name': '所有分类',
                    'children': []
                }
                nodes = {'所有分类': hierarchy}

                # 2. 获取所有节点和它们的关系
                result = session.run("""
                    MATCH p = (n:Category)-[:HAS_SUBCATEGORY*0..]->(m:Category)
                    WITH m, 
                         CASE WHEN ()-[:HAS_SUBCATEGORY]->(m) 
                              THEN [(parent)-[:HAS_SUBCATEGORY]->(m) | parent.name][0]
                              ELSE null
                         END as parent_name,
                         length(p) as depth
                    RETURN m.name as name, parent_name, depth
                    ORDER BY depth
                """)

                # 处理��个节点
                for record in result:
                    name = record['name']
                    parent_name = record['parent_name']
                    
                    if name not in nodes:
                        nodes[name] = {'name': name, 'children': []}

                    # 如果是根节点，将其添加到虚拟顶层节点下
                    if not parent_name and name in root_names:
                        hierarchy['children'].append(nodes[name])
                    # 否则添加到其父节点下
                    elif parent_name and parent_name in nodes:
                        nodes[parent_name]['children'].append(nodes[name])

                logging.info(f"构建的层级结构: {hierarchy}")
                
                # 如果只有一个根节点，直接返回该根节点的结构
                if len(root_names) == 1:
                    return nodes[root_names[0]]
                return hierarchy

        except Exception as e:
            logging.error(f"获取类别层级结构失败: {str(e)}")
            logging.error(f"错误详情: ", exc_info=True)  # 添加详细的错误信息
            return {}

    def import_categories_from_json(self):
        try:
             # 首先检查是否已有数据
            with self.driver.session() as session:
                result = session.run("""
                    MATCH (n:Category) 
                    RETURN count(n) as count
                """)
                count = result.single()['count']
                if count > 0:
                    return False, "分类数据已存在于Neo4j中，无需重复导入"
            # 读取JSON文件
            with open('category_hierarchy.json', 'r', encoding='utf-8') as file:
                categories = json.load(file)
            
            with self.driver.session() as session:
                # 清除现有数据
                session.run("MATCH (n) DETACH DELETE n")
                
                # 遍历层级结构并创建节点和关系
                for level1, level2_dict in categories.items():
                    # 创建一级分类节点
                    session.run("""
                        MERGE (n:Category {name: $name})
                    """, name=level1)
                    
                    # 遍历二级分类
                    for level2, level3_list in level2_dict.items():
                        # 创建二级分类节点并与一级分类建立关系
                        session.run("""
                            MATCH (parent:Category {name: $parent_name})
                            MERGE (child:Category {name: $child_name})
                            MERGE (parent)-[:HAS_SUBCATEGORY]->(child)
                        """, parent_name=level1, child_name=level2)
                        
                        # 遍历三级分类
                        for level3 in level3_list:
                            # 创建三级分类节点并与二级分类建立关系
                            session.run("""
                                MATCH (parent:Category {name: $parent_name})
                                MERGE (child:Category {name: $child_name})
                                MERGE (parent)-[:HAS_SUBCATEGORY]->(child)
                            """, parent_name=level2, child_name=level3)
                
                return True, "分类导入成功"
            
        except Exception as e:
            logging.error(f"导入分类失败: {str(e)}")
            return False, str(e)

    def verify_data(self):
        try:
            with self.driver.session() as session:
                result = session.run("""
                    MATCH (n:Category) 
                    RETURN n.name as name, count(*) as count
                """)
                categories = list(result)
                logging.info(f"数据库中的类别: {categories}")
                return len(categories) > 0
        except Exception as e:
            logging.error(f"验证数据失败: {str(e)}")
            return False
