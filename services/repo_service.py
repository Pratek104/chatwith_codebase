import os
import tempfile
import git
import hashlib
import shutil
import time
from datetime import datetime, timedelta
from typing import List, Tuple, Dict, Optional
from pathlib import Path
from langchain.text_splitter import RecursiveCharacterTextSplitter
from langchain_community.document_loaders.generic import GenericLoader
from langchain_community.document_loaders.parsers.txt import TextParser
from langchain_chroma import Chroma
from langchain_huggingface import HuggingFaceEmbeddings
from langchain_groq import ChatGroq
from langchain.chains import ConversationalRetrievalChain
from langchain.memory import ConversationBufferMemory
from langchain.prompts import PromptTemplate
from config import settings


class RepoService:
    def __init__(self):
        self.embeddings = HuggingFaceEmbeddings(model_name=settings.EMBEDDING_MODEL)
        self.llm = ChatGroq(
            temperature=0.1,
            model_name=settings.GROQ_MODEL,
            groq_api_key=settings.GROQ_API_KEY,
            max_tokens=settings.MAX_TOKENS
        )
        self.supported_suffixes = [
            # Programming languages
            ".py", ".js", ".java", ".cpp", ".c", ".h", ".cs", ".go", ".rb", 
            ".php", ".ts", ".tsx", ".jsx", ".rs", ".swift", ".kt", ".scala",
            ".r", ".m", ".mm", ".dart", ".lua", ".perl", ".sh", ".bash",
            # Web files
            ".html", ".htm", ".css", ".scss", ".sass", ".less", ".vue",
            # Config files
            ".json", ".yaml", ".yml", ".toml", ".ini", ".cfg", ".conf",
            ".xml", ".properties", ".env", ".gitignore", ".dockerignore",
            # Documentation
            ".md", ".txt", ".rst", ".adoc", ".tex",
            # Other
            ".sql", ".graphql", ".proto", ".thrift"
        ]
        self.priority_files = [
            "README.md", "package.json", "requirements.txt", "setup.py",
            "pyproject.toml", "Cargo.toml", "go.mod", "pom.xml",
            "build.gradle", "composer.json", "Gemfile", "Makefile"
        ]
        
        # Ensure base directory exists
        os.makedirs(settings.CHROMA_BASE_DIR, exist_ok=True)
        
        # Clean up old databases on initialization
        self._cleanup_old_databases()

    def _get_repo_identifier(self, repo_url: str) -> str:
        """Generate a unique identifier for the repository from its URL."""
        # Extract repo name from URL (e.g., 'username/repo-name')
        repo_name = repo_url.rstrip('/').split('/')[-2:]
        repo_id = '_'.join(repo_name).replace('.git', '')
        
        # Create a hash for uniqueness (in case of special characters)
        url_hash = hashlib.md5(repo_url.encode()).hexdigest()[:8]
        return f"{repo_id}_{url_hash}"

    def _get_db_path(self, repo_identifier: str) -> str:
        """Get the path for a specific repository's ChromaDB."""
        return os.path.join(settings.CHROMA_BASE_DIR, repo_identifier)

    def _db_exists(self, repo_identifier: str) -> bool:
        """Check if a ChromaDB already exists for this repository."""
        db_path = self._get_db_path(repo_identifier)
        return os.path.exists(db_path) and os.path.isdir(db_path)

    def _create_timestamp_file(self, repo_identifier: str) -> None:
        """Create a timestamp file to track when the DB was created."""
        db_path = self._get_db_path(repo_identifier)
        timestamp_file = os.path.join(db_path, '.timestamp')
        with open(timestamp_file, 'w') as f:
            f.write(str(time.time()))

    def _get_db_age(self, repo_identifier: str) -> Optional[float]:
        """Get the age of the database in hours."""
        db_path = self._get_db_path(repo_identifier)
        timestamp_file = os.path.join(db_path, '.timestamp')
        
        if not os.path.exists(timestamp_file):
            return None
        
        try:
            with open(timestamp_file, 'r') as f:
                creation_time = float(f.read().strip())
            age_seconds = time.time() - creation_time
            return age_seconds / 3600  # Convert to hours
        except Exception:
            return None

    def _cleanup_old_databases(self) -> None:
        """Remove ChromaDB directories older than the configured cleanup time."""
        if not os.path.exists(settings.CHROMA_BASE_DIR):
            return
        
        for item in os.listdir(settings.CHROMA_BASE_DIR):
            item_path = os.path.join(settings.CHROMA_BASE_DIR, item)
            
            if not os.path.isdir(item_path):
                continue
            
            timestamp_file = os.path.join(item_path, '.timestamp')
            
            if os.path.exists(timestamp_file):
                try:
                    with open(timestamp_file, 'r') as f:
                        creation_time = float(f.read().strip())
                    
                    age_hours = (time.time() - creation_time) / 3600
                    
                    if age_hours > settings.DB_CLEANUP_HOURS:
                        print(f"Cleaning up old database: {item} (age: {age_hours:.2f} hours)")
                        shutil.rmtree(item_path)
                except Exception as e:
                    print(f"Error cleaning up {item}: {e}")

    def get_folder_structure(self, repo_path: str, max_depth: int = 3) -> str:
        """
        Generate a tree structure of the repository.
        Excludes common large/irrelevant folders.
        """
        excluded_dirs = {
            'node_modules', '.next', 'dist', 'build', '__pycache__', 
            '.git', 'venv', '.venv', 'vendor', 'target', 'out',
            '.cache', 'coverage', '.pytest_cache', '.mypy_cache',
            'bower_components', '.nuxt', '.output'
        }
        
        def build_tree(path: str, prefix: str = "", depth: int = 0) -> list:
            if depth > max_depth:
                return []
            
            lines = []
            try:
                items = sorted(os.listdir(path))
                dirs = [i for i in items if os.path.isdir(os.path.join(path, i)) and i not in excluded_dirs and not i.startswith('.')]
                files = [i for i in items if os.path.isfile(os.path.join(path, i)) and not i.startswith('.')]
                
                # Show important files first
                priority_files = [f for f in files if f in self.priority_files]
                other_files = [f for f in files if f not in self.priority_files]
                
                all_items = priority_files + other_files + dirs
                
                for idx, item in enumerate(all_items[:30]):  # Limit to 30 items per level
                    is_last = idx == len(all_items) - 1
                    item_path = os.path.join(path, item)
                    
                    if os.path.isdir(item_path):
                        lines.append(f"{prefix}{'└── ' if is_last else '├── '}{item}/")
                        extension = "    " if is_last else "│   "
                        lines.extend(build_tree(item_path, prefix + extension, depth + 1))
                    else:
                        lines.append(f"{prefix}{'└── ' if is_last else '├── '}{item}")
                        
            except PermissionError:
                pass
            
            return lines
        
        tree_lines = [os.path.basename(repo_path) + "/"]
        tree_lines.extend(build_tree(repo_path))
        return "\n".join(tree_lines[:200])  # Limit total lines

    def get_project_metadata(self, repo_path: str) -> Dict[str, str]:
        """Extract key metadata from priority files."""
        metadata = {}
        
        for file_name in self.priority_files:
            file_path = os.path.join(repo_path, file_name)
            if os.path.exists(file_path):
                try:
                    with open(file_path, 'r', encoding='utf-8', errors='ignore') as f:
                        content = f.read()
                        metadata[file_name] = content[:3000]
                except Exception:
                    pass
        
        return metadata

    def clone_repo(self, repo_url: str, local_path: str) -> None:
        """Clone the GitHub repository to a local directory."""
        if not os.path.exists(local_path):
            git.Repo.clone_from(repo_url, local_path)
        else:
            repo = git.Repo(local_path)
            repo.remotes.origin.pull()

    def get_folder_structure(self, repo_path: str, max_depth: int = 3) -> str:
        """
        Generate a tree structure of the repository.
        Excludes common large/irrelevant folders.
        """
        excluded_dirs = {
            'node_modules', '.next', 'dist', 'build', '__pycache__', 
            '.git', 'venv', '.venv', 'vendor', 'target', 'out',
            '.cache', 'coverage', '.pytest_cache', '.mypy_cache',
            'bower_components', '.nuxt', '.output'
        }
        
        def build_tree(path: str, prefix: str = "", depth: int = 0) -> list:
            if depth > max_depth:
                return []
            
            lines = []
            try:
                items = sorted(os.listdir(path))
                dirs = [i for i in items if os.path.isdir(os.path.join(path, i)) and i not in excluded_dirs and not i.startswith('.')]
                files = [i for i in items if os.path.isfile(os.path.join(path, i)) and not i.startswith('.')]
                
                # Show important files first
                priority_files = [f for f in files if f in self.priority_files]
                other_files = [f for f in files if f not in self.priority_files]
                
                all_items = priority_files + other_files + dirs
                
                for idx, item in enumerate(all_items[:30]):  # Limit to 30 items per level
                    is_last = idx == len(all_items) - 1
                    item_path = os.path.join(path, item)
                    
                    if os.path.isdir(item_path):
                        lines.append(f"{prefix}{'└── ' if is_last else '├── '}{item}/")
                        extension = "    " if is_last else "│   "
                        lines.extend(build_tree(item_path, prefix + extension, depth + 1))
                    else:
                        lines.append(f"{prefix}{'└── ' if is_last else '├── '}{item}")
                        
            except PermissionError:
                pass
            
            return lines
        
        tree_lines = [os.path.basename(repo_path) + "/"]
        tree_lines.extend(build_tree(repo_path))
        return "\n".join(tree_lines[:200])  # Limit total lines
        """Extract key metadata from priority files."""
        metadata = {}
        
        for file_name in self.priority_files:
            file_path = os.path.join(repo_path, file_name)
            if os.path.exists(file_path):
                try:
                    with open(file_path, 'r', encoding='utf-8', errors='ignore') as f:
                        content = f.read()
                        # Limit content size for metadata
                        metadata[file_name] = content[:2000]
                except Exception:
                    pass
        
        return metadata

    def load_and_split_code(self, repo_path: str) -> List:
        """Load and split code files from the repository."""
        loader = GenericLoader.from_filesystem(
            path=repo_path,
            glob="**/*",
            suffixes=self.supported_suffixes,
            parser=TextParser(),
            exclude=["**/node_modules/**", "**/.git/**", "**/dist/**", 
                    "**/build/**", "**/__pycache__/**", "**/venv/**",
                    "**/.venv/**", "**/vendor/**", "**/target/**",
                    "**/package-lock.json", "**/yarn.lock", "**/pnpm-lock.yaml",
                    "**/.next/**", "**/out/**", "**/.cache/**"]
        )
        documents = loader.load()
        
        # Clean up source paths to show relative paths only
        for doc in documents:
            if 'source' in doc.metadata:
                # Convert absolute path to relative path from repo root
                abs_path = doc.metadata['source']
                try:
                    rel_path = os.path.relpath(abs_path, repo_path)
                    doc.metadata['source'] = rel_path
                except:
                    # Fallback to just filename
                    doc.metadata['source'] = os.path.basename(abs_path)
        
        # Add priority files with higher priority
        for file_name in self.priority_files:
            file_path = os.path.join(repo_path, file_name)
            if os.path.exists(file_path):
                try:
                    with open(file_path, 'r', encoding='utf-8', errors='ignore') as f:
                        content = f.read()
                        # Mark priority files in metadata
                        doc = type('Document', (), {
                            'page_content': content,
                            'metadata': {'source': file_name, 'priority': True}
                        })()
                        documents.append(doc)
                except Exception:
                    pass
        
        splitter = RecursiveCharacterTextSplitter(
            chunk_size=settings.CHUNK_SIZE,
            chunk_overlap=settings.CHUNK_OVERLAP,
            separators=["\n\n", "\n", " ", ""]
        )
        
        texts = splitter.split_documents(documents)
        return texts

    def setup_vectorstore(self, texts: List, repo_identifier: str) -> Chroma:
        """Set up Chroma vector store with embeddings."""
        db_path = self._get_db_path(repo_identifier)
        
        vectordb = Chroma.from_documents(
            documents=texts,
            embedding=self.embeddings,
            persist_directory=db_path
        )
        
        # Create timestamp file for cleanup tracking
        self._create_timestamp_file(repo_identifier)
        
        return vectordb

    def load_existing_vectorstore(self, repo_identifier: str) -> Chroma:
        """Load an existing ChromaDB for a repository."""
        db_path = self._get_db_path(repo_identifier)
        
        vectordb = Chroma(
            persist_directory=db_path,
            embedding_function=self.embeddings
        )
        
        return vectordb

    def create_optimized_prompt(self, question: str, metadata: Dict[str, str]) -> str:
        """Create an optimized prompt with only relevant metadata."""
        
        # Determine what metadata is relevant based on question keywords
        relevant_files = []
        question_lower = question.lower()
        
        # Map question types to relevant files
        if any(word in question_lower for word in ['what', 'about', 'purpose', 'does', 'project']):
            relevant_files.extend(['README.md', 'package.json', 'requirements.txt', 'setup.py'])
        if any(word in question_lower for word in ['depend', 'library', 'package', 'install']):
            relevant_files.extend(['package.json', 'requirements.txt', 'Gemfile', 'go.mod'])
        if any(word in question_lower for word in ['build', 'compile', 'make']):
            relevant_files.extend(['Makefile', 'build.gradle', 'pom.xml'])
        if any(word in question_lower for word in ['docker', 'container', 'deploy']):
            relevant_files.extend(['Dockerfile', 'docker-compose.yml'])
        
        # Include only relevant metadata
        context_parts = []
        for file_name in set(relevant_files):
            if file_name in metadata:
                context_parts.append(f"=== {file_name} ===\n{metadata[file_name][:1000]}\n")
        
        if context_parts:
            return "\n".join(context_parts)
        return ""

    def setup_conversation_chain(self, vectordb: Chroma, metadata: Dict[str, str]) -> ConversationalRetrievalChain:
        """Set up the conversational retrieval chain with optimized prompt."""
        
        prompt_template = """You are an expert code analyst. Answer questions about this repository directly and concisely.

Context from codebase:
{context}

Question: {question}

Instructions:
- Start with a direct answer (1-2 sentences)
- Then provide supporting details if needed
- Reference specific files/functions when relevant
- Be conversational, not formal
- Skip tables unless specifically asked

Answer:"""

        # Create a custom retriever that prioritizes based on query
        retriever = vectordb.as_retriever(
            search_type="mmr",  # Maximum Marginal Relevance for diversity
            search_kwargs={
                "k": settings.RETRIEVER_K,
                "fetch_k": 15  # Fetch more, then filter to k
            }
        )
        
        memory = ConversationBufferMemory(
            memory_key='chat_history',
            output_key='answer',
            return_source_documents=True,
            max_token_limit=1000  # Limit chat history
        )
        
        # Store metadata for use in prompt
        self.metadata = metadata
        
        qa = ConversationalRetrievalChain.from_llm(
            llm=self.llm,
            retriever=retriever,
            memory=memory,
            return_source_documents=True,
            verbose=False
        )
        return qa

    def process_repository(self, repo_url: str) -> bool:
        """
        Process and index a repository upfront.
        This does all the heavy lifting: cloning, parsing, chunking, and embedding.
        Returns True if successful.
        """
        try:
            # Generate unique identifier for this repo
            repo_identifier = self._get_repo_identifier(repo_url)
            
            # Check if we already have a vector DB for this repo
            if self._db_exists(repo_identifier):
                db_age = self._get_db_age(repo_identifier)
                
                # If DB is too old, delete it and recreate
                if db_age and db_age > settings.DB_CLEANUP_HOURS:
                    print(f"Database expired ({db_age:.2f} hours old), recreating...")
                    shutil.rmtree(self._get_db_path(repo_identifier))
                else:
                    print(f"Repository already processed: {repo_identifier}")
                    return True
            
            # Process the repository
            print(f"Processing new repository: {repo_identifier}")
            
            with tempfile.TemporaryDirectory() as temp_dir:
                repo_path = os.path.join(temp_dir, "repo")
                
                # Clone the repository
                print("Cloning repository...")
                self.clone_repo(repo_url, repo_path)
                
                # Extract folder structure
                print("Extracting folder structure...")
                folder_structure = self.get_folder_structure(repo_path)
                
                # Get project metadata
                print("Reading key project files...")
                metadata = self.get_project_metadata(repo_path)
                
                # Store folder structure and metadata for later use
                db_path = self._get_db_path(repo_identifier)
                os.makedirs(db_path, exist_ok=True)
                
                with open(os.path.join(db_path, 'folder_structure.txt'), 'w', encoding='utf-8') as f:
                    f.write(folder_structure)
                
                with open(os.path.join(db_path, 'metadata.txt'), 'w', encoding='utf-8') as f:
                    for key, value in metadata.items():
                        f.write(f"=== {key} ===\n{value}\n\n")
                
                # Load and split code - ENTIRE REPO
                print("Parsing and chunking code files...")
                texts = self.load_and_split_code(repo_path)
                
                if not texts:
                    print("No supported code files found")
                    return False
                
                # Set up vector store with persistent storage
                print(f"Creating embeddings and storing in vector DB... ({len(texts)} chunks)")
                self.setup_vectorstore(texts, repo_identifier)
                
                print(f"Repository processed successfully: {repo_identifier}")
                return True
                
        except Exception as e:
            print(f"Error processing repository: {e}")
            return False

    def chat_with_repo(self, repo_url: str, query: str) -> Tuple[str, List]:
        """
        Chat with a repository that has already been processed.
        This is fast because it only queries the existing vector DB.
        """
        
        # Generate unique identifier for this repo
        repo_identifier = self._get_repo_identifier(repo_url)
        
        # Check if we have a vector DB for this repo
        if not self._db_exists(repo_identifier):
            raise Exception("Repository not processed yet. Please process it first using /api/process endpoint.")
        
        db_age = self._get_db_age(repo_identifier)
        
        # If DB is too old, raise error
        if db_age and db_age > settings.DB_CLEANUP_HOURS:
            raise Exception("Repository cache expired. Please process it again.")
        
        print(f"Using cached vector database for {repo_identifier}")
        
        # Load folder structure and metadata
        db_path = self._get_db_path(repo_identifier)
        folder_structure = ""
        metadata_content = ""
        
        try:
            with open(os.path.join(db_path, 'folder_structure.txt'), 'r', encoding='utf-8') as f:
                folder_structure = f.read()
        except:
            pass
        
        try:
            with open(os.path.join(db_path, 'metadata.txt'), 'r', encoding='utf-8') as f:
                metadata_content = f.read()
        except:
            pass
        
        # Load existing vector store - NO re-chunking or re-embedding!
        vectordb = self.load_existing_vectorstore(repo_identifier)
        
        # Setup conversation chain
        qa = self.setup_conversation_chain(vectordb, {})
        
        # Build enhanced query with folder structure context
        enhanced_query = f"""Repository Structure:
```
{folder_structure}
```

Key Files Overview:
{metadata_content[:2000] if metadata_content else 'Not available'}

User Question: {query}

Please provide a direct, concise answer based on the repository structure and code."""
        
        # Get response with smart retrieval (only relevant docs)
        result = qa({"question": enhanced_query})
        return result['answer'], result.get('source_documents', [])