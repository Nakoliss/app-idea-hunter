"""
SHA-1 based deduplication service for complaint texts
"""
import hashlib
import re
from typing import Optional, Set
from app.logging_config import logger


class DeduplicationService:
    """Service for detecting duplicate complaints using SHA-1 hashing"""
    
    def __init__(self, token_limit: int = 120):
        """
        Initialize deduplication service
        
        Args:
            token_limit: Number of tokens to use for hash generation (default: 120)
        """
        self.token_limit = token_limit
        self._hash_cache: Set[str] = set()
        logger.info(f"Deduplication service initialized with token limit: {token_limit}")
    
    def _tokenize(self, text: str) -> list[str]:
        """
        Tokenize text into words, removing punctuation and converting to lowercase
        
        Args:
            text: Text to tokenize
            
        Returns:
            List of tokens
        """
        # Remove URLs
        text = re.sub(r'http[s]?://(?:[a-zA-Z]|[0-9]|[$-_@.&+]|[!*\\(\\),]|(?:%[0-9a-fA-F][0-9a-fA-F]))+', '', text)
        
        # Convert to lowercase and split by word boundaries
        tokens = re.findall(r'\b\w+\b', text.lower())
        
        return tokens
    
    def generate_hash(self, text: str) -> str:
        """
        Generate SHA-1 hash from first N tokens of text
        
        Args:
            text: Text to hash
            
        Returns:
            SHA-1 hash string
        """
        try:
            # Tokenize and limit to first N tokens
            tokens = self._tokenize(text)[:self.token_limit]
            
            # Join tokens and create hash
            normalized_text = ' '.join(tokens)
            hash_object = hashlib.sha1(normalized_text.encode('utf-8'))
            hash_string = hash_object.hexdigest()
            
            logger.debug(f"Generated hash {hash_string} from {len(tokens)} tokens")
            return hash_string
            
        except Exception as e:
            logger.error(f"Error generating hash: {str(e)}")
            raise
    
    def is_duplicate(self, text: str, existing_hashes: Optional[Set[str]] = None) -> bool:
        """
        Check if text is a duplicate based on its hash
        
        Args:
            text: Text to check
            existing_hashes: Optional set of existing hashes to check against
                           If not provided, uses internal cache
            
        Returns:
            True if text is a duplicate
        """
        text_hash = self.generate_hash(text)
        
        # Use provided hashes or internal cache
        hashes_to_check = existing_hashes if existing_hashes is not None else self._hash_cache
        
        is_dup = text_hash in hashes_to_check
        
        if is_dup:
            logger.debug(f"Duplicate detected with hash: {text_hash}")
        
        return is_dup
    
    def add_to_cache(self, text: str) -> str:
        """
        Add text hash to internal cache and return the hash
        
        Args:
            text: Text to add
            
        Returns:
            Generated hash
        """
        text_hash = self.generate_hash(text)
        self._hash_cache.add(text_hash)
        logger.debug(f"Added hash to cache: {text_hash}, Cache size: {len(self._hash_cache)}")
        return text_hash
    
    def clear_cache(self):
        """Clear the internal hash cache"""
        cache_size = len(self._hash_cache)
        self._hash_cache.clear()
        logger.info(f"Cleared hash cache, removed {cache_size} entries")
    
    def get_cache_size(self) -> int:
        """Get current size of hash cache"""
        return len(self._hash_cache)
    
    def batch_check_duplicates(self, texts: list[str], existing_hashes: Optional[Set[str]] = None) -> list[tuple[str, str, bool]]:
        """
        Check multiple texts for duplicates
        
        Args:
            texts: List of texts to check
            existing_hashes: Optional set of existing hashes
            
        Returns:
            List of tuples (text, hash, is_duplicate)
        """
        results = []
        hashes_to_check = existing_hashes if existing_hashes is not None else self._hash_cache
        
        for text in texts:
            try:
                text_hash = self.generate_hash(text)
                is_dup = text_hash in hashes_to_check
                results.append((text, text_hash, is_dup))
                
                # Add to checking set for subsequent checks in this batch
                if not is_dup and existing_hashes is None:
                    self._hash_cache.add(text_hash)
                    
            except Exception as e:
                logger.error(f"Error checking duplicate for text: {text[:50]}... Error: {str(e)}")
                continue
        
        duplicates_found = sum(1 for _, _, is_dup in results if is_dup)
        logger.info(f"Batch duplicate check completed - {duplicates_found}/{len(texts)} duplicates found")
        
        return results