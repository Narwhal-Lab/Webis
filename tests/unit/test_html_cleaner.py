"""
Test script for the LLM-based HTML cleaner plugin.

Usage:
    python test_html_cleaner.py
"""

from webis.plugins.processors.html_cleaner_plugin import HTMLCleanerPlugin
from webis.core.schema import WebisDocument

# Sample HTML with various noise elements
TEST_HTML = """
<!DOCTYPE html>
<html>
<head>
    <title>Sample Article - News Site</title>
    <script>
        console.log('analytics');
    </script>
    <style>
        .ad { display: block; }
    </style>
</head>
<body>
    <header>
        <nav>
            <a href="/">Home</a>
            <a href="/news">News</a>
            <a href="/about">About</a>
        </nav>
    </header>
    
    <div class="breadcrumb">
        Home > News > Technology
    </div>
    
    <article>
        <h1>Revolutionary AI Breakthrough Announced</h1>
        
        <div class="author-info">
            By John Doe | January 21, 2026
        </div>
        
        <p>Scientists at a leading research institution have announced a groundbreaking 
        advancement in artificial intelligence that could transform how machines understand 
        natural language.</p>
        
        <p>The new system, developed over three years, demonstrates unprecedented capabilities 
        in understanding context and nuance in human communication. Researchers believe this 
        could lead to more natural interactions between humans and AI systems.</p>
        
        <p>"This represents a significant leap forward," said Dr. Jane Smith, lead researcher 
        on the project. "We've achieved what many thought was years away."</p>
        
        <div class="related-articles">
            <h3>Related Articles</h3>
            <ul>
                <li><a href="/article1">Previous AI Advances</a></li>
                <li><a href="/article2">Future of Machine Learning</a></li>
                <li><a href="/article3">Interview with Dr. Smith</a></li>
            </ul>
        </div>
    </article>
    
    <aside class="sidebar">
        <div class="ad-banner">Advertisement</div>
        <div class="social-share">
            Share on: Facebook | Twitter | LinkedIn
        </div>
    </aside>
    
    <footer>
        <p>&copy; 2026 News Site. All rights reserved.</p>
        <div class="cookie-notice">
            This site uses cookies. By continuing, you accept our cookie policy.
        </div>
    </footer>
</body>
</html>
"""

def test_llm_cleaning():
    """Test LLM-based HTML cleaning."""
    print("=" * 60)
    print("Testing LLM-Based HTML Cleaner")
    print("=" * 60)
    
    # Create plugin instance
    cleaner = HTMLCleanerPlugin()
    
    # Create test document
    doc = WebisDocument(
        id="test_001",
        url="https://example.com/article",
        content=TEST_HTML,
        content_type="html"
    )
    
    print(f"\nOriginal HTML length: {len(doc.content)} characters")
    print("\n" + "-" * 60)
    
    # Test LLM cleaning
    print("\n[1] Testing LLM-based cleaning...")
    cleaner.use_llm = True
    result_llm = cleaner.process(doc)
    
    if result_llm and result_llm.clean_content:
        print(f"\nLLM Cleaned content length: {len(result_llm.clean_content)} characters")
        print(f"\nLLM Cleaned content:\n{'-' * 60}")
        print(result_llm.clean_content)
        print("-" * 60)
    else:
        print("LLM cleaning failed or returned no content")
    
    # Test fallback cleaning
    print("\n[2] Testing fallback (rule-based) cleaning...")
    doc2 = WebisDocument(
        id="test_002",
        url="https://example.com/article",
        content=TEST_HTML,
        content_type="html"
    )
    cleaner.use_llm = False
    result_fallback = cleaner.process(doc2)
    
    if result_fallback and result_fallback.clean_content:
        print(f"\nFallback cleaned content length: {len(result_fallback.clean_content)} characters")
        print(f"\nFallback cleaned content:\n{'-' * 60}")
        print(result_fallback.clean_content)
        print("-" * 60)
    else:
        print("Fallback cleaning failed or returned no content")
    
    print("\n" + "=" * 60)
    print("Test completed!")
    print("=" * 60)

if __name__ == "__main__":
    test_llm_cleaning()
