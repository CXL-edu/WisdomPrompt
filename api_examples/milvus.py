import os
from dotenv import load_dotenv
from pymilvus import MilvusClient
import numpy as np

load_dotenv()

# 临时禁用代理（如果环境变量中设置了代理但代理不可用）
os.environ.pop('HTTP_PROXY', None)
os.environ.pop('HTTPS_PROXY', None)
os.environ.pop('http_proxy', None)
os.environ.pop('https_proxy', None)

# 初始化 Milvus 客户端
uri = os.getenv('MILVUS_URI', '')
token = os.getenv('MILVUS_TOKEN', '')

print(f"连接到 Milvus: {uri}")

client = MilvusClient(
    uri=uri,
    token=token
)

# 集合名称
collection_name = "test_collection"
vector_dimension = 128  # 向量维度，根据实际需求调整

# 1. 创建集合（如果不存在）
print(f"\n创建集合: {collection_name}")
try:
    client.create_collection(
        collection_name=collection_name,
        dimension=vector_dimension
    )
    print(f"集合 {collection_name} 创建成功")
except Exception as e:
    print(f"集合可能已存在或创建失败: {e}")

# 2. 插入向量数据
print(f"\n插入向量数据到集合: {collection_name}")

# 生成示例向量数据
num_vectors = 5
vectors = []
for i in range(num_vectors):
    # 生成随机向量（实际应用中应使用真实的嵌入向量）
    vector = np.random.rand(vector_dimension).tolist()
    vectors.append({
        'id': i,
        'vector': vector,
        'text': f'这是第 {i} 个文档的内容',
        'metadata': f'metadata_{i}'
    })

# 插入数据
insert_result = client.insert(
    collection_name=collection_name,
    data=vectors
)
print(f"插入结果: {insert_result}")
print(f"成功插入 {insert_result.get('insert_count', 0)} 条记录")

# 3. 创建索引（可选，Milvus 会自动创建默认索引）
# 如果需要自定义索引参数，可以显式创建
print(f"\n创建索引（使用默认索引）")
# 注意：Milvus Cloud 通常会自动创建索引，如果需要自定义可以调用：
# client.create_index(
#     collection_name=collection_name,
#     index_params={"metric_type": "L2", "index_type": "AUTOINDEX"}
# )

# 4. 向量搜索
print(f"\n执行向量搜索")
# 生成查询向量
query_vector = np.random.rand(vector_dimension).tolist()

search_results = client.search(
    collection_name=collection_name,
    data=[query_vector],
    limit=3,  # 返回前3个最相似的结果
    output_fields=["text", "metadata"]  # 返回的字段
)

print(f"搜索结果:")
for i, result in enumerate(search_results[0]):
    print(f"  结果 {i+1}:")
    print(f"    ID: {result.get('id')}")
    print(f"    距离: {result.get('distance')}")
    print(f"    文本: {result.get('text')}")
    print(f"    元数据: {result.get('metadata')}")

# 5. 查看集合信息
print(f"\n集合信息:")
collections = client.list_collections()
print(f"所有集合: {collections}")

# 清理：删除集合（可选，取消注释以删除）
# print(f"\n删除集合: {collection_name}")
# client.drop_collection(collection_name=collection_name)
# print(f"集合 {collection_name} 已删除")

print("\n完成！")
