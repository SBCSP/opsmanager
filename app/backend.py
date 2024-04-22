import os
from flask import current_app, jsonify
import bs4
import getpass
from langchain import hub
from dotenv import load_dotenv
from langchain_community.vectorstores import Chroma
from langchain_openai import ChatOpenAI, OpenAIEmbeddings
from langchain_core.messages import HumanMessage, SystemMessage
from langchain.text_splitter import RecursiveCharacterTextSplitter
from langchain_community.document_loaders import WebBaseLoader
from langchain_core.output_parsers import StrOutputParser
from langchain_core.runnables import RunnablePassthrough
from langchain_core.prompts import PromptTemplate
from langchain.schema import (
    SystemMessage,
    HumanMessage,
    AIMessage
)

# Define a utility function to retrieve config values
def get_config_value(key, default=None):
    # Use the current_app proxy to access the app context
    with current_app.app_context():
        # Import AppConfig inside the function to avoid circular imports
        from database.models import AppConfig
        config_item = AppConfig.query.filter_by(key=key).first()
    return config_item.value if config_item else default

def response(user_query):

    # Load environment and get your openAI api key
    openai_api_key = get_config_value("OPENAI_API_KEY")


    # Select a webpage to load the context information from
    loader = WebBaseLoader(
        web_paths=("https://technotim.live/posts/ansible-automation/",),
    )
    docs = loader.load()


    # Restructure to process the info in chunks
    text_splitter = RecursiveCharacterTextSplitter(chunk_size=1000, chunk_overlap=200)
    splits = text_splitter.split_documents(docs)
    vectorstore = Chroma.from_documents(documents=splits, embedding=OpenAIEmbeddings())


    # Retrieve info from chosen source
    retriever = vectorstore.as_retriever(search_type="similarity")
    prompt = hub.pull("rlm/rag-prompt")
    llm = ChatOpenAI(model_name="gpt-4-turbo", temperature=0, openai_api_key=openai_api_key)

    def format_docs(docs):
        return "\n\n".join(doc.page_content for doc in docs)



    template = """Use the following pieces of context to answer the question at the end.
    Say that you don't know when asked a question you don't know, do not make up an answer. Be precise and concise in your answer.

    {context}

    Question: {question}

    Helpful Answer:"""

    # Add the context to your user query
    custom_rag_prompt = PromptTemplate.from_template(template)

    rag_chain = (
        {"context": retriever | format_docs, "question": RunnablePassthrough()}
        | custom_rag_prompt
        | llm
        | StrOutputParser()
    )

    try:
        return rag_chain.invoke(user_query)
    except Exception as e:
        return jsonify({'error': 'Error processing the request', 'details': str(e)}), 500