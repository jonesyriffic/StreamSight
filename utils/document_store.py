import datetime
import logging
from typing import Dict, List, Any, Optional

logger = logging.getLogger(__name__)

class DocumentStore:
    """
    Simple in-memory document store for storing and retrieving
    document data and metadata.
    """
    
    def __init__(self):
        # Initialize empty stores
        self._documents = {}  # dict mapping doc_id to document data
        self._category_index = {}  # dict mapping category to list of doc_ids
        logger.debug("Initialized DocumentStore")
    
    def add_document(self, document: Dict[str, Any]) -> str:
        """
        Add a document to the store
        
        Args:
            document: Document data dictionary that must include 'id' and 'category'
            
        Returns:
            Document ID
        """
        if 'id' not in document:
            raise ValueError("Document must have an 'id' field")
        
        doc_id = document['id']
        self._documents[doc_id] = document
        
        # Index by category
        category = document.get('category', 'Uncategorized')
        if category not in self._category_index:
            self._category_index[category] = []
        self._category_index[category].append(doc_id)
        
        logger.debug(f"Added document {doc_id} with category {category}")
        return doc_id
    
    def get_document(self, doc_id: str) -> Optional[Dict[str, Any]]:
        """
        Retrieve a document by ID
        
        Args:
            doc_id: Document ID
            
        Returns:
            Document data dictionary or None if not found
        """
        return self._documents.get(doc_id)
    
    def get_all_documents(self) -> List[Dict[str, Any]]:
        """
        Get all documents
        
        Returns:
            List of all document data dictionaries
        """
        return list(self._documents.values())
    
    def get_documents_by_category(self, category: str) -> List[Dict[str, Any]]:
        """
        Get all documents in a specific category
        
        Args:
            category: Category name
            
        Returns:
            List of document data dictionaries in that category
        """
        doc_ids = self._category_index.get(category, [])
        return [self._documents[doc_id] for doc_id in doc_ids if doc_id in self._documents]
    
    def get_all_categories(self) -> List[str]:
        """
        Get all categories
        
        Returns:
            List of category names
        """
        return list(self._category_index.keys())
    
    def delete_document(self, doc_id: str) -> bool:
        """
        Delete a document
        
        Args:
            doc_id: Document ID
            
        Returns:
            True if document was deleted, False if not found
        """
        if doc_id not in self._documents:
            return False
        
        # Remove from category index
        document = self._documents[doc_id]
        category = document.get('category', 'Uncategorized')
        if category in self._category_index and doc_id in self._category_index[category]:
            self._category_index[category].remove(doc_id)
        
        # Remove document
        del self._documents[doc_id]
        logger.debug(f"Deleted document {doc_id}")
        return True
    
    def update_document(self, doc_id: str, updates: Dict[str, Any]) -> bool:
        """
        Update a document
        
        Args:
            doc_id: Document ID
            updates: Dictionary of fields to update
            
        Returns:
            True if document was updated, False if not found
        """
        if doc_id not in self._documents:
            return False
        
        # Check if category is changing
        old_category = self._documents[doc_id].get('category', 'Uncategorized')
        new_category = updates.get('category', old_category)
        
        if old_category != new_category:
            # Update category index
            if old_category in self._category_index and doc_id in self._category_index[old_category]:
                self._category_index[old_category].remove(doc_id)
            
            if new_category not in self._category_index:
                self._category_index[new_category] = []
            self._category_index[new_category].append(doc_id)
        
        # Update document
        self._documents[doc_id].update(updates)
        logger.debug(f"Updated document {doc_id}")
        return True
    
    def search_by_keyword(self, keyword: str) -> List[Dict[str, Any]]:
        """
        Simple keyword search (case-insensitive)
        
        Args:
            keyword: Search term
            
        Returns:
            List of matching document data dictionaries
        """
        keyword = keyword.lower()
        results = []
        
        for doc in self._documents.values():
            text = doc.get('text', '').lower()
            if keyword in text:
                results.append(doc)
        
        return results
    
    def get_current_time(self) -> str:
        """
        Get current time in ISO format
        
        Returns:
            Current time string
        """
        return datetime.datetime.now().isoformat()
