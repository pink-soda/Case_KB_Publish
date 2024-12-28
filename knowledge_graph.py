'''
Author: pink-soda luckyli0127@gmail.com
Date: 2024-12-03 15:41:12
LastEditors: pink-soda luckyli0127@gmail.com
LastEditTime: 2024-12-28 15:23:16
FilePath: \test\knowledge_graph.py
Description: 这是默认设置,请设置`customMade`, 打开koroFileHeader查看配置 进行设置: https://github.com/OBKoro1/koro1FileHeader/wiki/%E9%85%8D%E7%BD%AE
'''
from py2neo import Graph, Node, Relationship
import json
from neo4j import GraphDatabase
import logging
import traceback
import logging

logger = logging.getLogger(__name__)

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
                # 1. 找到所有根节点（一级分类）
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
                #logging.info(f"找到根节点: {root_names}")

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

                # 创建节点字典
                nodes = {}
                hierarchy = {}  # 直接使用字典存储一级分类

                # 处理所有节点
                for record in result:
                    name = record['name']
                    parent_name = record['parent_name']
                    
                    if name not in nodes:
                        nodes[name] = {'name': name, 'children': []}

                    # 如果是根节点（一级分类）
                    if not parent_name and name in root_names:
                        hierarchy[name] = nodes[name]
                    # 否则添加到其父节点下
                    elif parent_name and parent_name in nodes:
                        nodes[parent_name]['children'].append(nodes[name])

                #logging.info(f"构建的层级结构: {hierarchy}")
                return hierarchy

        except Exception as e:
            logging.error(f"获取类别层级结构失败: {str(e)}")
            logging.error(f"错误详情: ", exc_info=True)
            return {}

    def import_categories_from_json(self):
        """从JSON文件导入分类到Neo4j，采用增量导入策略"""
        try:
            # 读取JSON文件
            with open('category_hierarchy.json', 'r', encoding='utf-8') as file:
                categories = json.load(file)
            
            with self.driver.session() as session:
                # 获取导入前的节点数
                before_count = session.run("MATCH (n:Category) RETURN count(n) as count").single()['count']
                
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
                
                # 获取导入后的节点数
                after_count = session.run("MATCH (n:Category) RETURN count(n) as count").single()['count']
                new_nodes = after_count - before_count
                
                if new_nodes > 0:
                    logger.info(f"新增了 {new_nodes} 个分类节点，当前共有 {after_count} 个节点")
                    return True, f"成功导入 {new_nodes} 个新分类节点"
                else:
                    logger.info("没有新的分类节点需要导入")
                    return True, "所有分类节点已存在，无需导入"
            
        except Exception as e:
            error_msg = f"导入分类失败: {str(e)}\n{traceback.format_exc()}"
            logger.error(error_msg)
            return False, error_msg

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

    def ensure_category_hierarchy(self, categories):
        """确保分类层级关系存在，如果不存在则创建"""
        try:
            level1, level2, level3 = categories
            
            with self.driver.session() as session:
                # 创建或获取各级节点
                session.run("""
                    MERGE (l1:Category {name: $level1})
                    MERGE (l2:Category {name: $level2})
                    MERGE (l3:Category {name: $level3})
                    MERGE (l1)-[:HAS_SUBCATEGORY]->(l2)
                    MERGE (l2)-[:HAS_SUBCATEGORY]->(l3)
                """, level1=level1, level2=level2, level3=level3)
                
            return True
        except Exception as e:
            logging.error(f"确保分类层级关系失败: {str(e)}")
            return False

    def check_categories_exist(self):
        """检查Neo4j中是否已存在分类数据，通过比较分类层级结构"""
        try:
            # 获取本地最新的分类层级
            with open('category_hierarchy.json', 'r', encoding='utf-8') as f:
                local_hierarchy = json.load(f)

            # 获取Neo4j中的分类层级
            neo4j_hierarchy = {}
            
            # 使用 driver.session() 而不是直接使用 session
            with self.driver.session() as session:
                # 查询所有分类关系
                query = """
                MATCH (l1:Category)-[r1:HAS_SUBCATEGORY]->(l2:Category)-[r2:HAS_SUBCATEGORY]->(l3:Category)
                RETURN l1.name as level1, l2.name as level2, l3.name as level3
                """
                result = session.run(query)
                
                # 构建Neo4j中的层级结构
                for record in result:
                    level1 = record['level1']
                    level2 = record['level2']
                    level3 = record['level3']
                    
                    if level1 not in neo4j_hierarchy:
                        neo4j_hierarchy[level1] = {}
                    if level2 not in neo4j_hierarchy[level1]:
                        neo4j_hierarchy[level1][level2] = []
                    if level3 not in neo4j_hierarchy[level1][level2]:
                        neo4j_hierarchy[level1][level2].append(level3)

                # 比较两个层级结构
                for level1, level2_dict in local_hierarchy.items():
                    # 检查一级分类
                    if level1 not in neo4j_hierarchy:
                        return False
                    
                    for level2, level3_list in level2_dict.items():
                        # 检查二级分类
                        if level2 not in neo4j_hierarchy[level1]:
                            return False
                        
                        # 检查三级分类
                        for level3 in level3_list:
                            if level3 not in neo4j_hierarchy[level1][level2]:
                                return False

                # 如果所有检查都通过，说明Neo4j中包含了所有本地分类
                return True

        except Exception as e:
            logger.error(f"检查Neo4j分类数据时出错: {str(e)}\n{traceback.format_exc()}")
            return False
