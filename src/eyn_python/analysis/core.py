from __future__ import annotations

import hashlib
import mimetypes
import magic
import os
from pathlib import Path
from typing import Dict, List, Any, Optional, Union
from collections import defaultdict
import json
from datetime import datetime

from eyn_python.logging import get_logger

log = get_logger(__name__)


def detect_file_type(file_path: Union[str, Path]) -> Dict[str, Any]:
    """Detect file type using multiple methods."""
    file_path = Path(file_path)
    
    if not file_path.exists():
        return {'error': 'File does not exist'}
    
    result = {
        'path': str(file_path),
        'size': file_path.stat().st_size,
        'extension': file_path.suffix.lower(),
        'mime_type': None,
        'magic_type': None,
        'is_text': False,
        'encoding': None
    }
    
    # MIME type detection
    try:
        mime_type, encoding = mimetypes.guess_type(str(file_path))
        result['mime_type'] = mime_type
        result['encoding'] = encoding
    except Exception as e:
        log.debug(f"MIME type detection failed: {e}")
    
    # Magic number detection
    try:
        with open(file_path, 'rb') as f:
            magic_type = magic.from_buffer(f.read(2048), mime=True)
            result['magic_type'] = magic_type
    except Exception as e:
        log.debug(f"Magic detection failed: {e}")
    
    # Text file detection
    try:
        with open(file_path, 'rb') as f:
            sample = f.read(1024)
            result['is_text'] = sample.isascii() and b'\x00' not in sample
    except Exception as e:
        log.debug(f"Text detection failed: {e}")
    
    return result


def find_duplicates(directory: Union[str, Path], 
                   min_size: int = 1024) -> Dict[str, List[str]]:
    """Find duplicate files by content hash."""
    directory = Path(directory)
    hash_groups = defaultdict(list)
    
    for file_path in directory.rglob('*'):
        if file_path.is_file() and file_path.stat().st_size >= min_size:
            try:
                # Calculate file hash
                hash_md5 = hashlib.md5()
                with open(file_path, 'rb') as f:
                    for chunk in iter(lambda: f.read(4096), b""):
                        hash_md5.update(chunk)
                
                file_hash = hash_md5.hexdigest()
                hash_groups[file_hash].append(str(file_path))
                
            except Exception as e:
                log.debug(f"Error processing {file_path}: {e}")
    
    # Return only groups with duplicates
    return {hash_val: files for hash_val, files in hash_groups.items() 
            if len(files) > 1}


def analyze_file_size(directory: Union[str, Path]) -> Dict[str, Any]:
    """Analyze file sizes in a directory."""
    directory = Path(directory)
    sizes = []
    total_size = 0
    file_count = 0
    
    for file_path in directory.rglob('*'):
        if file_path.is_file():
            try:
                size = file_path.stat().st_size
                sizes.append(size)
                total_size += size
                file_count += 1
            except Exception as e:
                log.debug(f"Error getting size for {file_path}: {e}")
    
    if not sizes:
        return {'error': 'No files found'}
    
    sizes.sort()
    
    return {
        'total_files': file_count,
        'total_size': total_size,
        'total_size_mb': total_size / (1024 * 1024),
        'total_size_gb': total_size / (1024 * 1024 * 1024),
        'average_size': total_size / file_count,
        'median_size': sizes[len(sizes) // 2],
        'min_size': sizes[0],
        'max_size': sizes[-1],
        'size_distribution': {
            'small': len([s for s in sizes if s < 1024 * 1024]),  # < 1MB
            'medium': len([s for s in sizes if 1024 * 1024 <= s < 100 * 1024 * 1024]),  # 1MB - 100MB
            'large': len([s for s in sizes if s >= 100 * 1024 * 1024])  # >= 100MB
        }
    }


def get_file_statistics(directory: Union[str, Path]) -> Dict[str, Any]:
    """Get comprehensive file statistics."""
    directory = Path(directory)
    stats = {
        'total_files': 0,
        'total_directories': 0,
        'total_size': 0,
        'file_types': defaultdict(int),
        'recent_files': [],
        'oldest_files': [],
        'largest_files': []
    }
    
    file_info = []
    
    for item in directory.rglob('*'):
        try:
            stat = item.stat()
            if item.is_file():
                stats['total_files'] += 1
                stats['total_size'] += stat.st_size
                
                # File type counting
                ext = item.suffix.lower()
                stats['file_types'][ext if ext else 'no_extension'] += 1
                
                # Collect file info for sorting
                file_info.append({
                    'path': str(item),
                    'size': stat.st_size,
                    'modified': stat.st_mtime,
                    'created': stat.st_ctime
                })
                
            elif item.is_dir():
                stats['total_directories'] += 1
                
        except Exception as e:
            log.debug(f"Error processing {item}: {e}")
    
    # Sort files by different criteria
    if file_info:
        # Recent files
        recent = sorted(file_info, key=lambda x: x['modified'], reverse=True)[:10]
        stats['recent_files'] = recent
        
        # Oldest files
        oldest = sorted(file_info, key=lambda x: x['modified'])[:10]
        stats['oldest_files'] = oldest
        
        # Largest files
        largest = sorted(file_info, key=lambda x: x['size'], reverse=True)[:10]
        stats['largest_files'] = largest
    
    # Convert defaultdict to regular dict
    stats['file_types'] = dict(stats['file_types'])
    
    return stats


def find_large_files(directory: Union[str, Path], 
                    min_size_mb: float = 100) -> List[Dict[str, Any]]:
    """Find files larger than specified size."""
    directory = Path(directory)
    min_size_bytes = int(min_size_mb * 1024 * 1024)
    large_files = []
    
    for file_path in directory.rglob('*'):
        if file_path.is_file():
            try:
                size = file_path.stat().st_size
                if size >= min_size_bytes:
                    large_files.append({
                        'path': str(file_path),
                        'size': size,
                        'size_mb': size / (1024 * 1024),
                        'size_gb': size / (1024 * 1024 * 1024),
                        'modified': datetime.fromtimestamp(file_path.stat().st_mtime)
                    })
            except Exception as e:
                log.debug(f"Error processing {file_path}: {e}")
    
    # Sort by size descending
    large_files.sort(key=lambda x: x['size'], reverse=True)
    return large_files


def analyze_directory_structure(directory: Union[str, Path], 
                              max_depth: int = 3) -> Dict[str, Any]:
    """Analyze directory structure and nesting."""
    directory = Path(directory)
    structure = {
        'root': str(directory),
        'total_items': 0,
        'max_depth': 0,
        'depth_distribution': defaultdict(int),
        'structure': {}
    }
    
    def analyze_path(path: Path, current_depth: int = 0):
        if current_depth > max_depth:
            return
        
        structure['max_depth'] = max(structure['max_depth'], current_depth)
        structure['depth_distribution'][current_depth] += 1
        
        if path.is_file():
            structure['total_items'] += 1
            return {'type': 'file', 'size': path.stat().st_size}
        elif path.is_dir():
            structure['total_items'] += 1
            children = {}
            
            try:
                for child in path.iterdir():
                    if child.name.startswith('.'):
                        continue  # Skip hidden files
                    children[child.name] = analyze_path(child, current_depth + 1)
            except PermissionError:
                children['<permission_denied>'] = {'type': 'error'}
            
            return {'type': 'directory', 'children': children}
    
    structure['structure'] = analyze_path(directory)
    structure['depth_distribution'] = dict(structure['depth_distribution'])
    
    return structure


def check_file_integrity(file_path: Union[str, Path]) -> Dict[str, Any]:
    """Check file integrity using multiple hash algorithms."""
    file_path = Path(file_path)
    
    if not file_path.exists():
        return {'error': 'File does not exist'}
    
    try:
        # Initialize hash objects
        md5_hash = hashlib.md5()
        sha1_hash = hashlib.sha1()
        sha256_hash = hashlib.sha256()
        
        # Read file and update hashes
        with open(file_path, 'rb') as f:
            for chunk in iter(lambda: f.read(4096), b""):
                md5_hash.update(chunk)
                sha1_hash.update(chunk)
                sha256_hash.update(chunk)
        
        stat = file_path.stat()
        
        return {
            'path': str(file_path),
            'size': stat.st_size,
            'modified': datetime.fromtimestamp(stat.st_mtime),
            'hashes': {
                'md5': md5_hash.hexdigest(),
                'sha1': sha1_hash.hexdigest(),
                'sha256': sha256_hash.hexdigest()
            },
            'integrity_check': 'passed'
        }
        
    except Exception as e:
        return {
            'path': str(file_path),
            'error': str(e),
            'integrity_check': 'failed'
        }


def find_empty_files(directory: Union[str, Path]) -> List[Dict[str, Any]]:
    """Find empty files in a directory."""
    directory = Path(directory)
    empty_files = []
    
    for file_path in directory.rglob('*'):
        if file_path.is_file():
            try:
                if file_path.stat().st_size == 0:
                    empty_files.append({
                        'path': str(file_path),
                        'modified': datetime.fromtimestamp(file_path.stat().st_mtime),
                        'created': datetime.fromtimestamp(file_path.stat().st_ctime)
                    })
            except Exception as e:
                log.debug(f"Error processing {file_path}: {e}")
    
    return empty_files


def get_file_metadata(file_path: Union[str, Path]) -> Dict[str, Any]:
    """Get comprehensive file metadata."""
    file_path = Path(file_path)
    
    if not file_path.exists():
        return {'error': 'File does not exist'}
    
    try:
        stat = file_path.stat()
        
        metadata = {
            'path': str(file_path),
            'name': file_path.name,
            'stem': file_path.stem,
            'suffix': file_path.suffix,
            'parent': str(file_path.parent),
            'size': stat.st_size,
            'size_human': _format_size(stat.st_size),
            'created': datetime.fromtimestamp(stat.st_ctime),
            'modified': datetime.fromtimestamp(stat.st_mtime),
            'accessed': datetime.fromtimestamp(stat.st_atime),
            'permissions': oct(stat.st_mode)[-3:],
            'is_file': file_path.is_file(),
            'is_dir': file_path.is_dir(),
            'is_symlink': file_path.is_symlink(),
            'exists': file_path.exists(),
            'absolute': str(file_path.absolute()),
            'relative': str(file_path.relative_to(Path.cwd())) if file_path.is_relative_to(Path.cwd()) else None
        }
        
        # Add file type detection
        file_type = detect_file_type(file_path)
        metadata.update(file_type)
        
        return metadata
        
    except Exception as e:
        return {
            'path': str(file_path),
            'error': str(e)
        }


def analyze_text_file(file_path: Union[str, Path]) -> Dict[str, Any]:
    """Analyze text file content."""
    file_path = Path(file_path)
    
    if not file_path.exists():
        return {'error': 'File does not exist'}
    
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            content = f.read()
        
        lines = content.splitlines()
        words = content.split()
        
        # Character analysis
        char_count = len(content)
        char_no_spaces = len(content.replace(' ', ''))
        
        # Line analysis
        empty_lines = len([line for line in lines if not line.strip()])
        non_empty_lines = len(lines) - empty_lines
        
        # Word analysis
        unique_words = len(set(words))
        avg_word_length = sum(len(word) for word in words) / len(words) if words else 0
        
        # Common words (excluding common stop words)
        stop_words = {'the', 'a', 'an', 'and', 'or', 'but', 'in', 'on', 'at', 'to', 'for', 'of', 'with', 'by'}
        word_freq = defaultdict(int)
        for word in words:
            clean_word = word.lower().strip('.,!?;:()[]{}"\'-')
            if clean_word and clean_word not in stop_words:
                word_freq[clean_word] += 1
        
        common_words = sorted(word_freq.items(), key=lambda x: x[1], reverse=True)[:10]
        
        return {
            'path': str(file_path),
            'size': file_path.stat().st_size,
            'encoding': 'utf-8',
            'lines': {
                'total': len(lines),
                'empty': empty_lines,
                'non_empty': non_empty_lines
            },
            'words': {
                'total': len(words),
                'unique': unique_words,
                'average_length': round(avg_word_length, 2)
            },
            'characters': {
                'total': char_count,
                'no_spaces': char_no_spaces,
                'spaces': char_count - char_no_spaces
            },
            'common_words': common_words,
            'readability': {
                'avg_words_per_line': len(words) / len(lines) if lines else 0,
                'avg_chars_per_word': char_no_spaces / len(words) if words else 0
            }
        }
        
    except UnicodeDecodeError:
        return {'error': 'File is not a valid text file (binary or wrong encoding)'}
    except Exception as e:
        return {'error': str(e)}


def _format_size(size_bytes: int) -> str:
    """Format file size in human readable format."""
    if size_bytes == 0:
        return "0B"
    
    size_names = ["B", "KB", "MB", "GB", "TB"]
    i = 0
    current_size = float(size_bytes)
    while current_size >= 1024 and i < len(size_names) - 1:
        current_size /= 1024.0
        i += 1
        
    return f"{current_size:.1f}{size_names[i]}"
