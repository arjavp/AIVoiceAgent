#!/usr/bin/env python3
"""
Direct test script to debug RAG retrieval issues.
Tests the RAG service directly without going through the full workflow.
"""

import os
import sys
import django

# Setup Django
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'config'))
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')

try:
    django.setup()
except Exception as e:
    print(f"❌ Error setting up Django: {e}")
    sys.exit(1)

from apps.ai.services.rag_service import get_rag_service
from apps.ai.models import KnowledgeBaseDocument

def test_database_connection():
    """Test if documents are in the database."""
    print("\n" + "="*70)
    print("📊 DATABASE CHECK")
    print("="*70)
    
    try:
        doc_count = KnowledgeBaseDocument.objects.count()
        print(f"✅ Documents in database: {doc_count}")
        
        if doc_count > 0:
            docs = KnowledgeBaseDocument.objects.all()
            for doc in docs:
                print(f"\n  📄 {doc.filename}")
                print(f"     Type: {doc.file_type}")
                print(f"     Chunks: {doc.chunk_count}")
                print(f"     Size: {doc.file_size:,} bytes")
                print(f"     Uploaded: {doc.uploaded_at}")
        else:
            print("⚠️ No documents found in database!")
            print("   Upload a document first using: python upload_document.py <file>")
            return False
    except Exception as e:
        print(f"❌ Database error: {e}")
        return False
    
    return True

def test_vector_db():
    """Test vector database connection and count."""
    print("\n" + "="*70)
    print("🔍 VECTOR DATABASE CHECK")
    print("="*70)
    
    try:
        rag_service = get_rag_service()
        
        # Try to get collection info
        print("✅ RAG service initialized")
        print(f"   Collection: knowledge_base")
        print(f"   Connection: {rag_service.conn_str.split('@')[1] if '@' in rag_service.conn_str else 'hidden'}")
        
        # Try a simple query to see if there are any documents
        test_query = "test"
        try:
            docs = rag_service.vector_db.similarity_search(test_query, k=1)
            print(f"   Vector search test: Found {len(docs)} documents")
        except Exception as e:
            print(f"   ⚠️ Vector search test failed: {e}")
            
    except Exception as e:
        print(f"❌ Error initializing RAG service: {e}")
        import traceback
        traceback.print_exc()
        return False
    
    return True

def test_retrieval(query):
    """Test retrieval with a specific query."""
    print("\n" + "="*70)
    print(f"🔎 TESTING RETRIEVAL: '{query}'")
    print("="*70)
    
    try:
        rag_service = get_rag_service()
        context = rag_service.retrieve(query, k=3)
        
        print(f"\n📝 Retrieved Context:")
        print("-" * 70)
        if context and context != "No relevant documents found.":
            print(context[:500] + "..." if len(context) > 500 else context)
            print(f"\n✅ Successfully retrieved {len(context)} characters")
        else:
            print("⚠️ No relevant documents found")
            print("\nPossible reasons:")
            print("  1. No documents uploaded yet")
            print("  2. Query doesn't match document content")
            print("  3. Embeddings not generated correctly")
            print("  4. Vector database connection issue")
        
        return context
        
    except Exception as e:
        print(f"❌ Error during retrieval: {e}")
        import traceback
        traceback.print_exc()
        return None

def test_full_workflow(query):
    """Test the full workflow including LLM."""
    print("\n" + "="*70)
    print(f"🚀 TESTING FULL WORKFLOW: '{query}'")
    print("="*70)
    
    try:
        from apps.ai.services.graph_service import WorkflowOrchestrator
        
        orchestrator = WorkflowOrchestrator()
        answer = orchestrator.run(query)
        
        print(f"\n💬 Final Answer:")
        print("-" * 70)
        print(answer)
        print("-" * 70)
        
        return answer
        
    except Exception as e:
        print(f"❌ Error in workflow: {e}")
        import traceback
        traceback.print_exc()
        return None

if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python test_rag_direct.py 'Your question here'")
        print("\nThis script will:")
        print("  1. Check if documents are in the database")
        print("  2. Test vector database connection")
        print("  3. Test retrieval")
        print("  4. Test full workflow")
        print("\nExample:")
        print("  python test_rag_direct.py 'What is machine learning?'")
        sys.exit(1)
    
    query = " ".join(sys.argv[1:])
    
    # Step 1: Check database
    if not test_database_connection():
        print("\n❌ Please upload documents first!")
        sys.exit(1)
    
    # Step 2: Check vector DB
    if not test_vector_db():
        print("\n❌ Vector database issue!")
        sys.exit(1)
    
    # Step 3: Test retrieval
    context = test_retrieval(query)
    
    # Step 4: Test full workflow
    if context and context != "No relevant documents found.":
        test_full_workflow(query)
    else:
        print("\n⚠️ Skipping full workflow test - no context retrieved")
        print("   Try a different query that matches your document content")
