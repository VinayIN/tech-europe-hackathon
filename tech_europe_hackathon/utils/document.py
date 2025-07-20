"""
Document storage with Weaviate cloud vector database
"""
from typing import Dict, List, Any, Optional
from datetime import datetime
import weaviate
import weaviate.classes.config as wvc
import weaviate.classes.query as wvq
from tech_europe_hackathon.utils.config import CONFIG


class TextDocument:
    """Text document with content and footnotes"""
    
    def __init__(self, text: str = "", footnotes: List[str] = None, metadata: Dict[str, Any] = None):
        self.text = text
        self.footnotes = footnotes or []
        self.metadata = metadata or {}
        self.metadata['created_at'] = self.metadata.get('created_at', datetime.now().strftime('%Y-%m-%dT%H:%M:%SZ'))
    
    def update_text(self, new_text: str):
        """Update the document text"""
        self.text = new_text
        self.metadata['last_modified'] = datetime.now().strftime('%Y-%m-%dT%H:%M:%SZ')
    
    def update_footnotes(self, new_footnotes: List[str]):
        """Update the document footnotes"""
        self.footnotes = new_footnotes
        self.metadata['last_modified'] = datetime.now().strftime('%Y-%m-%dT%H:%M:%SZ')
    
    def add_footnote(self, footnote: str) -> int:
        """Add a footnote and return its number"""
        self.footnotes.append(footnote)
        self.metadata['last_modified'] = datetime.now().strftime('%Y-%m-%dT%H:%M:%SZ')
        return len(self.footnotes)
    
    def get_word_count(self) -> int:
        """Get word count of the main text"""
        return len(self.text.split()) if self.text else 0


class StorageManager:
    """Weaviate cloud document storage"""
    
    def __init__(self):
        self.client = None
        self.collection_name = "Documents"
        self._init_weaviate()
    
    def _init_weaviate(self):
        """Initialize Weaviate cloud client and create collection"""
        if not CONFIG.WEAVIATE_API_KEY:
            raise ValueError("WEAVIATE_API_KEY is required for cloud storage")
        
        self.client = weaviate.connect_to_weaviate_cloud(
            cluster_url=CONFIG.WEAVIATE_URL,
            auth_credentials=weaviate.auth.AuthApiKey(CONFIG.WEAVIATE_API_KEY),
            headers={"X-OpenAI-Api-Key": CONFIG.OPENAI_API_KEY}
        )
        
        self._create_collection()
        print("Weaviate cloud connected successfully")
    
    def _create_collection(self):
        """Create the Documents collection in Weaviate"""
        if self.client.collections.exists(self.collection_name):
            print(f"Collection '{self.collection_name}' already exists")
            return
            
        self.client.collections.create(
            name=self.collection_name,
            properties=[
                wvc.Property(name="title", data_type=wvc.DataType.TEXT),
                wvc.Property(name="content", data_type=wvc.DataType.TEXT),
                wvc.Property(name="summary", data_type=wvc.DataType.TEXT),
                wvc.Property(name="footnotes", data_type=wvc.DataType.TEXT_ARRAY),
                wvc.Property(name="keywords", data_type=wvc.DataType.TEXT_ARRAY),
                wvc.Property(name="word_count", data_type=wvc.DataType.INT),
                wvc.Property(name="created_at", data_type=wvc.DataType.DATE),
                wvc.Property(name="modified_at", data_type=wvc.DataType.DATE),
            ],
            vectorizer_config=wvc.Configure.Vectorizer.text2vec_openai(model="text-embedding-3-small"),
            generative_config=wvc.Configure.Generative.openai(model="gpt-3.5-turbo")
        )
        print(f"Created collection '{self.collection_name}' with OpenAI vectorization")

    def _format_date(self, date_str: str) -> str:
        """Format date to RFC3339 for Weaviate"""
        if not date_str:
            return datetime.now().strftime('%Y-%m-%dT%H:%M:%SZ')
        try:
            dt = datetime.fromisoformat(date_str.replace('Z', '+00:00'))
            return dt.strftime('%Y-%m-%dT%H:%M:%SZ')
        except:
            return datetime.now().strftime('%Y-%m-%dT%H:%M:%SZ')

    def save_document(self, document: TextDocument, title: str, summary: str = "", keywords: List[str] = None) -> bool:
        """Save document to Weaviate cloud"""
        keywords = keywords or []
        collection = self.client.collections.get(self.collection_name)
        
        data_object = {
            "title": title,
            "content": document.text,
            "summary": summary or document.text[:200] + "...",
            "footnotes": document.footnotes,
            "keywords": keywords,
            "word_count": document.get_word_count(),
            "created_at": self._format_date(document.metadata.get('created_at')),
            "modified_at": self._format_date(document.metadata.get('last_modified'))
        }
        
        # Check if document exists and update or create
        existing = self._find_by_title(title)
        if existing:
            collection.data.update(uuid=existing["uuid"], properties=data_object)
            print(f"Updated document '{title}'")
        else:
            collection.data.insert(properties=data_object)
            print(f"Saved new document '{title}'")
        
        return True
    
    def load_document(self, title: str) -> Optional[TextDocument]:
        """Load document by title from Weaviate cloud"""
        doc_data = self._find_by_title(title)
        if doc_data:
            return TextDocument(
                text=doc_data.get("content", ""),
                footnotes=doc_data.get("footnotes", []),
                metadata={
                    "created_at": doc_data.get("created_at", ""),
                    "last_modified": doc_data.get("modified_at", "")
                }
            )
        return None

    def search_documents(self, query: str, limit: int = 5) -> List[str]:
        """Search documents by summary and return matching filenames"""
        collection = self.client.collections.get(self.collection_name)
        response = collection.query.near_text(query=query, limit=limit)
        return [obj.properties.get("title", "") for obj in response.objects if obj.properties.get("title")]
    
    def list_documents(self) -> List[str]:
        """List document titles"""
        collection = self.client.collections.get(self.collection_name)
        response = collection.query.fetch_objects(limit=5)
        return [obj.properties.get("title", "") for obj in response.objects]
    
    def _find_by_title(self, title: str) -> Optional[Dict[str, Any]]:
        """Find document by title in Weaviate cloud"""
        collection = self.client.collections.get(self.collection_name)
        response = collection.query.bm25(query=title, limit=1)
        
        for obj in response.objects:
            if obj.properties.get("title") == title:
                return {"uuid": str(obj.uuid), **obj.properties}
        return None
    
    def close(self):
        """Close Weaviate connection"""
        if self.client:
            self.client.close()
            print("Weaviate client connection closed")
    
    def __enter__(self):
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        self.close()
