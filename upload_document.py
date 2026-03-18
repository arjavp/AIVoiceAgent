#!/usr/bin/env python3
"""
Script to upload documents to the RAG knowledge base.
Usage: python upload_document.py <file_path> [description]
"""

import requests
import os
import sys

# Configuration
API_BASE_URL = "http://localhost:8000/api/v1/ai"

def upload_document(file_path, description=""):
    """Upload a document to the RAG knowledge base."""
    if not os.path.exists(file_path):
        print(f"❌ Error: File not found: {file_path}")
        return None
    
    url = f"{API_BASE_URL}/upload/"
    
    print(f"📤 Uploading: {os.path.basename(file_path)}")
    print(f"   Path: {file_path}")
    
    try:
        with open(file_path, 'rb') as file:
            # Determine content type
            file_ext = os.path.splitext(file_path)[1].lower()
            content_type_map = {
                '.pdf': 'application/pdf',
                '.txt': 'text/plain',
                '.md': 'text/markdown',
            }
            content_type = content_type_map.get(file_ext, 'application/octet-stream')
            
            files = {'file': (os.path.basename(file_path), file, content_type)}
            data = {'description': description} if description else {}
            
            response = requests.post(url, files=files, data=data, timeout=60)
            
            if response.status_code == 201:
                result = response.json()
                print("\n✅ Upload successful!")
                print(f"📄 File: {result['document']['filename']}")
                print(f"📊 Chunks created: {result['document']['chunk_count']}")
                print(f"💾 File size: {result['document']['file_size']:,} bytes")
                print(f"📅 Uploaded at: {result['document']['uploaded_at']}")
                if result['document'].get('description'):
                    print(f"📝 Description: {result['document']['description']}")
                return result
            else:
                print(f"\n❌ Upload failed: HTTP {response.status_code}")
                try:
                    error = response.json()
                    print(f"   Error: {error.get('error', 'Unknown error')}")
                except:
                    print(f"   Response: {response.text}")
                return None
                
    except requests.exceptions.ConnectionError:
        print("\n❌ Error: Could not connect to server.")
        print("   Make sure Django server is running: python manage.py runserver")
        return None
    except Exception as e:
        print(f"\n❌ Error: {e}")
        return None

def list_documents():
    """List all uploaded documents."""
    url = f"{API_BASE_URL}/documents/"
    
    try:
        response = requests.get(url, timeout=10)
        
        if response.status_code == 200:
            result = response.json()
            print(f"\n📚 Total documents: {result['count']}")
            print("-" * 60)
            
            if result['count'] == 0:
                print("   No documents uploaded yet.")
            else:
                for i, doc in enumerate(result['documents'], 1):
                    print(f"\n{i}. {doc['filename']}")
                    print(f"   Type: {doc['file_type']}")
                    print(f"   Chunks: {doc['chunk_count']}")
                    print(f"   Size: {doc['file_size']:,} bytes")
                    print(f"   Uploaded: {doc['uploaded_at']}")
                    if doc.get('description'):
                        print(f"   Description: {doc['description']}")
            
            print("-" * 60)
            return result
        else:
            print(f"❌ Failed to list documents: HTTP {response.status_code}")
            return None
            
    except requests.exceptions.ConnectionError:
        print("\n❌ Error: Could not connect to server.")
        print("   Make sure Django server is running: python manage.py runserver")
        return None
    except Exception as e:
        print(f"❌ Error: {e}")
        return None

if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python upload_document.py <file_path> [description]")
        print("\nExamples:")
        print("  python upload_document.py document.pdf")
        print("  python upload_document.py notes.txt 'My study notes'")
        print("  python upload_document.py --list  # List all documents")
        sys.exit(1)
    
    if sys.argv[1] == "--list" or sys.argv[1] == "-l":
        list_documents()
    else:
        file_path = sys.argv[1]
        description = sys.argv[2] if len(sys.argv) > 2 else ""
        
        # Upload document
        result = upload_document(file_path, description)
        
        # List all documents after upload
        if result:
            print("\n" + "=" * 60)
            list_documents()
