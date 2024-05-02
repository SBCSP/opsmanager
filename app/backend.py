# import os
# from flask import current_app, jsonify
# import bs4
# import getpass
# from langchain import hub
# from dotenv import load_dotenv
# from bs4 import BeautifulSoup
# from langchain_community.vectorstores import Chroma
# from langchain_openai import ChatOpenAI, OpenAIEmbeddings
# from langchain_core.messages import HumanMessage, SystemMessage
# from langchain.text_splitter import RecursiveCharacterTextSplitter
# from langchain_community.document_loaders import WebBaseLoader
# from langchain_core.output_parsers import StrOutputParser
# from langchain_core.runnables import RunnablePassthrough
# from langchain_core.prompts import PromptTemplate
# from langchain.schema import (
#     SystemMessage,
#     HumanMessage,
#     AIMessage
# )

# def format_docs(html_docs):
#     texts = []
#     for html in html_docs:
#         soup = BeautifulSoup(html, 'html.parser')
#         texts.append(soup.get_text())
#     return "\n\n".join(texts)

# # Define a utility function to retrieve config values
# def get_config_value(key, default=None):
#     # Use the current_app proxy to access the app context
#     with current_app.app_context():
#         # Import AppConfig inside the function to avoid circular imports
#         from database.models import AppConfig
#         config_item = AppConfig.query.filter_by(key=key).first()
#     return config_item.value if config_item else default

# def response(user_query):
#     # Load OpenAI api key from config
#     openai_api_key = get_config_value("OPENAI_API_KEY")

#     # Instantiating the WebBaseLoader
#     loader = WebBaseLoader(web_paths=["https://technotim.live/posts/ansible-automation/"])
#     docs = loader.load()
    
#     print("Loaded docs type:", type(docs))
#     print("Loaded docs content:", docs)  # This will help us understand what's loaded

#     # Let's assume the correct usage after knowing what 'docs' is
#     # Placeholder if docs is an iterable or contains certain properties, adjust this line accordingly.
#     formatted_docs = format_docs([docs])  # Hypothetical adjustment

#     # Use OpenAI to generate a response
#     llm = ChatOpenAI(model_name="gpt-4-turbo", openai_api_key=openai_api_key)
#     response_generator = llm.generate([{"prompt": "Summarize this content: " + formatted_docs, "max_tokens": 150}])
    
#     try:
#         for response_chunk in response_generator:
#             yield response_chunk["choices"][0]["text"]
#     except Exception as e:
#         raise e