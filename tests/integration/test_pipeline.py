"""
Test script for the Intelligent Pipeline with agent-based validation.

Usage:
    python test_intelligent_pipeline.py
"""

import sys
import logging
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent / "src"))

from webis.core.pipeline.intelligent_pipeline import IntelligentPipeline

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)

def test_basic_pipeline():
    """Test basic pipeline functionality."""
    print("=" * 70)
    print("Testing Intelligent Pipeline with Agent-Based Validation")
    print("=" * 70)
    
    pipeline = IntelligentPipeline()
    
    # Test query
    query = "Python 3.12 new features"
    
    print(f"\nQuery: {query}")
    print(f"Requirements: 10 documents, relevance threshold 0.7")
    print()
    
    # Run pipeline
    result = pipeline.run(
        query=query,
        requirements={
            'min_count': 10,
            'relevance_threshold': 0.7,
            'max_iterations': 3
        }
    )
    
    # Display results
    print("\n" + "=" * 70)
    print("RESULTS")
    print("=" * 70)
    
    stats = result['stats']
    print(f"\n✓ Success: {stats['success']}")
    print(f"  Accepted: {stats['accepted_count']} documents")
    print(f"  Rejected: {stats['rejected_count']} documents")
    print(f"  Iterations: {stats['iterations']}")
    
    print("\n" + "-" * 70)
    print("ACCEPTED DOCUMENTS:")
    print("-" * 70)
    for i, doc in enumerate(result['documents'][:5], 1):  # Show first 5
        print(f"\n{i}. {doc.url or doc.id}")
        if doc.clean_content:
            preview = doc.clean_content[:200].replace('\n', ' ')
            print(f"   Preview: {preview}...")
    
    if len(result['documents']) > 5:
        print(f"\n... and {len(result['documents']) - 5} more documents")
    
    if result['rejected']:
        print("\n" + "-" * 70)
        print(f"REJECTED DOCUMENTS: {len(result['rejected'])}")
        print("-" * 70)
        for i, doc in enumerate(result['rejected'][:3], 1):  # Show first 3
            print(f"{i}. {doc.url or doc.id}")
    
    print("\n" + "=" * 70)
    print("Test completed!")
    print("=" * 70)

def test_quantity_check():
    """Test quantity checking and re-crawling."""
    print("\n" + "=" * 70)
    print("Testing Quantity Check")
    print("=" * 70)
    
    pipeline = IntelligentPipeline()
    
    result = pipeline.run(
        query="Latest AI research papers",
        requirements={
            'min_count': 5,  # Small number for faster testing
            'relevance_threshold': 0.6,
            'max_iterations': 2
        }
    )
    
    print(f"\nResult: {result['stats']}")

def test_relevance_filtering():
    """Test relevance filtering."""
    print("\n" + "=" * 70)
    print("Testing Relevance Filtering")
    print("=" * 70)
    
    pipeline = IntelligentPipeline()
    
    # Query with very specific intent
    result = pipeline.run(
        query="React hooks tutorial",
        requirements={
            'min_count': 8,
            'relevance_threshold': 0.75,  # Higher threshold
            'max_iterations': 3
        }
    )
    
    print(f"\nAccepted: {result['stats']['accepted_count']}")
    print(f"Rejected: {result['stats']['rejected_count']}")
    print(f"Rejection rate: {result['stats']['rejected_count'] / (result['stats']['accepted_count'] + result['stats']['rejected_count']):.2%}")

if __name__ == "__main__":
    test_basic_pipeline()
    # test_quantity_check()
    # test_relevance_filtering()
