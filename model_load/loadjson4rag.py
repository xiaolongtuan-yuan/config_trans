import os
import json
from langchain.text_splitter import RecursiveCharacterTextSplitter
from langchain.docstore.document import Document
import yang2json as y2j

from langchain.embeddings import HuggingFaceEmbeddings
from langchain.vectorstores import FAISS

def load_json_files_from_directory(json_dir, files):

    documents = []

    # 遍历文件夹中的所有 JSON 文件
    for subdir in files.keys():
        json_subdir = json_dir + subdir
        for file in files[subdir]:            
            json_file_path = json_subdir + "/{}.json".format(file)

            # 读取 JSON 文件内容
            with open(json_file_path, "r") as f:
                data = json.load(f)
            # print(data)

            # 将整个 JSON 数据转换为 Document
            filename = subdir+"/{}.json".format(file)
            document = Document(page_content=str(data), metadata={"filename": filename})
            documents.append(document)
    
    return documents


if __name__ == "__main__":
    # 文件夹路径
    directory_path = "UCM_JSON/"
    file_extension = ".json"
    # 获取所有json文件的文件名用于加载
    files = y2j.get_files_in_subdirectories(directory_path, file_extension)

    '''for file_name in files.keys():
        print(file_name, ', ')

    print(len(files))'''

    

    # 读取文件夹中所有 JSON 文件并转换为 Document 格式
    documents = load_json_files_from_directory(directory_path, files)

    # 可选：将内容分片，便于检索
    # chunk_size：表示每个文本块（chunk）的最大字符数
    # chunk_overlap：表示在相邻文本块之间的重叠字符数，保证上下文的连通性
    text_splitter = RecursiveCharacterTextSplitter(chunk_size=1000, chunk_overlap=0)

    docs = text_splitter.split_documents(documents)

    print(f"Total documents after splitting: {len(docs)}")

    # 使用句子嵌入模型
    embedding_model = HuggingFaceEmbeddings(model_name="EmbeddingModel/all-MiniLM-L6-v2")
    vector_store = FAISS.from_documents(docs, embedding_model)
    print(vector_store)
