#!/usr/bin/env python3
"""
Script to test RAG queries directly without voice agent.
Usage: python test_rag.py "Your question here"
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
    print("\nMake sure you're in the voice-agent directory and Django is installed.")
    sys.exit(1)

from apps.ai.services.graph_service import WorkflowOrchestrator

def test_rag_query(query):
    """Test RAG query directly."""
    print(f"\n🔍 Query: {query}")
    print("=" * 70)
    
    try:
        print("⏳ Processing...")
        orchestrator = WorkflowOrchestrator()
        answer = orchestrator.run(query)
        
        print(f"\n✅ Answer:")
        print("-" * 70)
        print(answer)
        print("-" * 70)
        
        return answer
    except Exception as e:
        print(f"\n❌ Error: {e}")
        import traceback
        traceback.print_exc()
        return None

def interactive_mode():
    """Run in interactive mode for multiple queries."""
    print("\n" + "=" * 70)
    print("🤖 RAG Testing - Interactive Mode")
    print("=" * 70)
    print("Type your questions (or 'quit' to exit)")
    print("-" * 70)
    
    while True:
        try:
            query = input("\n💬 Your question: ").strip()
            
            if not query:
                continue
                
            if query.lower() in ['quit', 'exit', 'q']:
                print("\n👋 Goodbye!")
                break
            
            test_rag_query(query)
            
        except KeyboardInterrupt:
            print("\n\n👋 Goodbye!")
            break
        except Exception as e:
            print(f"\n❌ Error: {e}")

if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python test_rag.py 'Your question here'")
        print("   or: python test_rag.py --interactive")
        print("\nExamples:")
        print("  python test_rag.py 'What is machine learning?'")
        print("  python test_rag.py --interactive")
        sys.exit(1)
    
    if sys.argv[1] == "--interactive" or sys.argv[1] == "-i":
        interactive_mode()
    else:
        query = " ".join(sys.argv[1:])
        test_rag_query(query)
