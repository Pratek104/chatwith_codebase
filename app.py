import os
from langchain.text_splitter import RecursiveCharacterTextSplitter
from langchain_community.document_loaders.generic import GenericLoader
from langchain_community.document_loaders.parsers.txt import TextParser
from langchain_chroma import Chroma
from langchain_huggingface import HuggingFaceEmbeddings
from langchain_groq import ChatGroq
from langchain.chains import ConversationalRetrievalChain
from langchain.memory import ConversationBufferMemory
import tempfile
import git

def clone_repo(repo_url, local_path):
    """Clone the GitHub repository to a local directory."""
    if not os.path.exists(local_path):
        git.Repo.clone_from(repo_url, local_path)
    else:
        repo = git.Repo(local_path)
        repo.remotes.origin.pull()

def load_and_split_code(repo_path, suffixes=None):
    """Load and split code files from the repository."""
    if suffixes is None:
        suffixes = [".py", ".js", ".java", ".cpp", ".c", ".h", ".cs", ".go", ".rb", ".php", ".ts", ".tsx"]
    
    # Use TextParser instead of LanguageParser to avoid tree-sitter dependency
    loader = GenericLoader.from_filesystem(
        path=repo_path,
        glob="**/*",
        suffixes=suffixes,
        parser=TextParser(),
    )
    documents = loader.load()
    
    # Use general-purpose splitter for code
    splitter = RecursiveCharacterTextSplitter(
        chunk_size=2000,
        chunk_overlap=200,
        separators=["\n\n", "\n", " ", ""]
    )
    
    texts = splitter.split_documents(documents)
    return texts

def setup_vectorstore(texts, persist_dir="./chroma_db"):
    """Set up Chroma vector store with embeddings."""
    embeddings = HuggingFaceEmbeddings(model_name="all-MiniLM-L6-v2")
    vectordb = Chroma.from_documents(
        documents=texts,
        embedding=embeddings,
        persist_directory=persist_dir
    )
    return vectordb

def setup_llm():
    """Initialize the Groq model."""
    from dotenv import load_dotenv
    load_dotenv()
    
    llm = ChatGroq(
        temperature=0.1,
        model_name=os.getenv("GROQ_MODEL", "openai/gpt-oss-120b"),
        groq_api_key=os.getenv("GROQ_API_KEY")
    )
    return llm

def setup_conversation_chain(vectordb, llm):
    """Set up the conversational retrieval chain."""
    memory = ConversationBufferMemory(
        memory_key='chat_history',
        output_key='answer',
        return_source_documents=True
    )
    
    qa = ConversationalRetrievalChain.from_llm(
        llm=llm,
        retriever=vectordb.as_retriever(search_kwargs={"k": 3}),
        memory=memory,
        return_source_documents=True
    )
    return qa

def chat_with_repo(repo_url, query):
    """Main function to chat with the repository."""
    # Create temporary directory for cloning
    with tempfile.TemporaryDirectory() as temp_dir:
        repo_path = os.path.join(temp_dir, "repo")
        
        # Clone the repository
        clone_repo(repo_url, repo_path)
        
        # Load and split code
        texts = load_and_split_code(repo_path)
        
        # Set up vector store
        vectordb = setup_vectorstore(texts)
        
        # Initialize LLM
        llm = setup_llm()
        
        # Setup conversation chain
        qa = setup_conversation_chain(vectordb, llm)
        
        # Get response
        result = qa({"question": query})
        return result['answer'], result.get('source_documents', [])

# Example usage
if __name__ == "__main__":
    REPO_URL = "https://github.com/poudelsanchit/recovery-ally"  # Replace with target repo
    QUERY = "What is this project about?"
    
    answer, sources = chat_with_repo(REPO_URL, QUERY)
    print("Answer:", answer)
    print("\nSources:")
    for src in sources[:2]:  # Show first 2 sources
        print(f"- {src.metadata.get('source')} (lines {src.metadata.get('start_line')}-{src.metadata.get('end_line')})")