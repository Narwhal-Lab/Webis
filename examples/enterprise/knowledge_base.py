"""
Enterprise Knowledge Base Example

This example demonstrates how to build an enterprise-grade knowledge base with Webis.
"""
import asyncio
from webis import WebisClient
from webis.core.pipeline import Pipeline, PipelineContext
from typing import Dict, List


async def build_competitive_intelligence_kb():
    """Build knowledge base for competitive intelligence"""

    print("=" * 60)
    print("Enterprise: Competitive Intelligence Knowledge Base")
    print("=" * 60)

    client = WebisClient()

    # Define competitors and queries
    competitors = {
        "openai": ["OpenAI products", "GPT features", "ChatGPT pricing"],
        "anthropic": ["Anthropic Claude", "Claude features", "Claude pricing"],
        "google": ["Google AI", "Gemini features", "Google AI pricing"],
    }

    # Collect data for each competitor
    all_results = {}

    for company, queries in competitors.items():
        print(f"\nAnalyzing {company.upper()}...")
        print("-" * 60)

        company_results = []
        for query in queries:
            print(f"  Query: {query}")

            result = await client.run(
                query=query,
                sources=["tavily_search", "gnews"],
                limit=10,
                output=f"./output/competitors/{company}"
            )

            company_results.append(result)

        all_results[company] = company_results
        print(f"  Found {sum(len(r.documents) for r in company_results)} articles")

    # Build unified knowledge base
    print("\n\nBuilding Unified Knowledge Base")
    print("=" * 60)

    unified_kb = {}
    for company, results in all_results.items():
        unified_kb[company] = {
            "total_articles": sum(len(r.documents) for r in results),
            "sources": list(set(doc.metadata.get('source', 'Unknown') for r in results for doc in r.documents)),
            "key_topics": _extract_key_topics(r.documents for r in results)
        }

    # Display summary
    print("\nKnowledge Base Summary:")
    print("-" * 60)
    for company, stats in unified_kb.items():
        print(f"\n{company.upper()}:")
        print(f"  Total Articles: {stats['total_articles']}")
        print(f"  Sources: {', '.join(stats['sources'][:5])}")
        print(f"  Key Topics: {', '.join(stats['key_topics'][:3])}")

    return unified_kb


async def build_research_knowledge_base():
    """Build knowledge base for research purposes"""

    print("\n\n" + "=" * 60)
    print("Enterprise: Research Knowledge Base")
    print("=" * 60)

    client = WebisClient()

    # Research topics
    research_topics = [
        "large language models",
        "reinforcement learning",
        "computer vision",
        "natural language processing",
        "graph neural networks"
    ]

    # Collect research papers
    research_kb = {}

    for topic in research_topics:
        print(f"\nCollecting research on: {topic}")
        print("-" * 60)

        result = await client.run(
            query=f"{topic} recent advances 2024",
            sources=["semantic_scholar", "arxiv"],
            limit=20,
            rag_mode=True,
            output=f"./output/research/{topic.replace(' ', '_')}"
        )

        research_kb[topic] = {
            "total_papers": len(result.documents),
            "knowledge_base": result.metadata.get('rag_store_path'),
            "years": list(set(doc.metadata.get('year', 2024) for doc in result.documents if doc.metadata))
        }

        print(f"  Found {len(result.documents)} papers")
        print(f"  Knowledge base: {result.metadata.get('rag_store_path')}")

    # Generate research summary
    print("\n\nResearch Summary:")
    print("-" * 60)
    for topic, stats in research_kb.items():
        print(f"\n{topic.title()}:")
        print(f"  Total Papers: {stats['total_papers']}")
        print(f"  Years: {', '.join(map(str, sorted(stats['years'], reverse=True)[:5])}")
        if stats['knowledge_base']:
            print(f"  RAG Store: {stats['knowledge_base']}")

    return research_kb


async def build_company_knowledge_base():
    """Build internal company knowledge base"""

    print("\n\n" + "=" * 60)
    print("Enterprise: Company Knowledge Base")
    print("=" * 60)

    client = WebisClient()

    # Company data sources
    company_queries = [
        ("company news", ["tavily_search", "gnews"]),
        ("company press releases", ["tavily_search"]),
        ("company research", ["semantic_scholar"]),
        ("industry trends", ["tavily_search", "hackernews"])
    ]

    company_kb = {}

    for category, sources in company_queries:
        print(f"\nCollecting: {category}")
        print("-" * 60)

        result = await client.run(
            query="Webis AI knowledge pipeline recent developments",
            sources=sources,
            limit=15,
            rag_mode=True,
            output=f"./output/company/{category.replace(' ', '_')}"
        )

        company_kb[category] = {
            "documents": len(result.documents),
            "rag_enabled": True,
            "output_path": result.metadata.get('output_path')
        }

        print(f"  Found {len(result.documents)} documents")
        print(f"  RAG mode: Enabled")

    # Generate company dashboard data
    print("\n\nCompany Knowledge Base Dashboard:")
    print("-" * 60)
    print("\nCategories:")
    for category, stats in company_kb.items():
        print(f"  {category}: {stats['documents']} documents")

    total_docs = sum(stats['documents'] for stats in company_kb.values())
    print(f"\nTotal Documents: {total_docs}")

    return company_kb


def _extract_key_topics(documents: List) -> List[str]:
    """Extract key topics from documents"""
    # Simple keyword frequency analysis
    topic_keywords = {}
    tech_keywords = [
        "ai", "model", "training", "data", "learning",
        "api", "pricing", "feature", "product", "launch"
    ]

    for doc in documents:
        content = doc.content.lower()
        for keyword in tech_keywords:
            if keyword in content:
                topic_keywords[keyword] = topic_keywords.get(keyword, 0) + 1

    # Sort by frequency
    sorted_topics = sorted(topic_keywords.items(), key=lambda x: x[1], reverse=True)
    return [topic for topic, freq in sorted_topics[:5]]


async def generate_reports():
    """Generate reports from knowledge bases"""

    print("\n\n" + "=" * 60)
    print("Generating Reports")
    print("=" * 60)

    # Build all knowledge bases
    competitive_kb = await build_competitive_intelligence_kb()
    research_kb = await build_research_knowledge_base()
    company_kb = await build_company_knowledge_base()

    # Generate summary report
    report = {
        "competitive_intelligence": competitive_kb,
        "research": research_kb,
        "company": company_kb,
        "generated_at": "2024-01-15T00:00:00Z"
    }

    print("\n\nReports generated successfully!")
    print("Knowledge bases are ready for:")
    print("  - Competitive analysis")
    print("  - Research support")
    print("  - Internal knowledge sharing")
    print("  - AI-powered search")


async def setup_maintenance_schedule():
    """Set up periodic knowledge base updates"""

    print("\n\n" + "=" * 60)
    print("Maintenance Schedule")
    print("=" * 60)

    print("\nRecommended update schedule:")
    print("  - Competitive Intelligence: Daily")
    print("  - Research Knowledge Base: Weekly")
    print("  - Company Data: Daily")

    print("\nExample cron jobs:")
    print("\n# Daily competitive intelligence update")
    print("0 */4 * * * /usr/bin/python3 -m webis.update_competitive_kb")

    print("\n# Weekly research update")
    print("0 0 * * 0 /usr/bin/python3 -m webis.update_research_kb")

    print("\n# Daily company data update")
    print("0 */6 * * * /usr/bin/python3 -m webis.update_company_kb")


if __name__ == "__main__":
    # Run all examples
    asyncio.run(generate_reports())
    asyncio.run(setup_maintenance_schedule())

    print("\n\n" + "=" * 60)
    print("Enterprise knowledge base setup complete!")
    print("=" * 60)
    print("\nNext steps:")
    print("  1. Configure API keys in .env")
    print("  2. Set up cron jobs for periodic updates")
    print("  3. Deploy to production environment")
    print("  4. Set up monitoring and alerts")
    print("  5. Configure user access and permissions")