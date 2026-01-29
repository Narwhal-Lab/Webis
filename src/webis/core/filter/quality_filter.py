"""
Quality Filter module for Webis.

Implements RedPajama-style heuristics to filter out low-quality content
before it reaches expensive processing stages.
"""

import math
import re
from collections import Counter
from typing import Dict, Tuple, Any, List

import trafilatura

class QualityFilter:
    """
    Assesses document quality using heuristic metrics.
    """
    
    def __init__(self, thresholds: Dict[str, float] = None):
        # Default thresholds based on RedPajama recommendations
        self.thresholds = {
            "max_frac_no_alph_words": 0.6,
            "min_mean_word_length": 1.0, 
            "max_mean_word_length": 50.0,
            "min_frac_unique_words": 0.05,
            "max_frac_unique_words": 1.0,
            "min_unigram_entropy": 1.0,
            "min_word_count": 25,
            "max_word_count": 200000,
            "min_frac_ending_sentence": 0.25,
            "max_frac_numerical_lines": 0.6,
            "max_frac_uppercase_lines": 0.8,
            "max_frac_top_2gram": 0.4,
            "max_frac_top_3gram": 0.36,
        }
        if thresholds:
            self.thresholds.update(thresholds)

    def assess(self, html_content: str) -> Tuple[bool, Dict[str, Any]]:
        """
        Assess HTML content quality.
        
        Returns:
            Tuple[bool, Dict]: (is_passed, debug_scores)
        """
        # 1. Cheap extraction
        text = None
        # Check if content looks like HTML
        if html_content and ("<html" in html_content or "<body" in html_content or "<div" in html_content):
             text = trafilatura.extract(html_content, include_comments=False, include_tables=False)
        
        if not text:
            # Fallback: Content might be plain text or markdown (Tavily style)
            # If it has reasonable length and doesn't look like HTML, assume it's text.
            if html_content and len(html_content) > 50:
                 text = html_content
            else:
                 return False, {"error": "trafilatura_extraction_failed_and_fallback_failed"}

        return self.assess_text(text)

    def assess_text(self, text: str) -> Tuple[bool, Dict[str, Any]]:
        """
        Assess plain text quality using RedPajama metrics.
        """
        metrics = self._calculate_metrics(text)
        
        # Check against thresholds
        reasons = []
        is_passed = True
        
        t = self.thresholds
        
        if metrics["frac_no_alph_words"] > t["max_frac_no_alph_words"]:
            reasons.append(f"too_many_symbols ({metrics['frac_no_alph_words']:.2f} > {t['max_frac_no_alph_words']})")
            
        if not (t["min_mean_word_length"] <= metrics["mean_word_length"] <= t["max_mean_word_length"]):
             reasons.append(f"bad_word_length ({metrics['mean_word_length']:.2f})")
             
        if not (t["min_frac_unique_words"] <= metrics["frac_unique_words"] <= t["max_frac_unique_words"]):
             reasons.append(f"bad_unique_ratio ({metrics['frac_unique_words']:.2f})")
             
        if metrics["unigram_entropy"] < t["min_unigram_entropy"]:
             reasons.append(f"low_entropy ({metrics['unigram_entropy']:.2f})")
             
        if not (t["min_word_count"] <= metrics["word_count"] <= t["max_word_count"]):
             reasons.append(f"bad_word_count ({metrics['word_count']})")
             
        if metrics["frac_ending_sentence"] < t["min_frac_ending_sentence"]:
             reasons.append(f"incomplete_sentences ({metrics['frac_ending_sentence']:.2f})")

        if metrics["frac_numerical_lines"] > t["max_frac_numerical_lines"]:
             reasons.append(f"too_many_numbers ({metrics['frac_numerical_lines']:.2f})")

        if metrics["frac_uppercase_lines"] > t["max_frac_uppercase_lines"]:
             reasons.append(f"too_much_caps ({metrics['frac_uppercase_lines']:.2f})")

        if metrics["frac_top_2gram"] > t["max_frac_top_2gram"]:
             reasons.append(f"repetitive_2gram ({metrics['frac_top_2gram']:.2f})")
             
        if metrics["frac_top_3gram"] > t["max_frac_top_3gram"]:
             reasons.append(f"repetitive_3gram ({metrics['frac_top_3gram']:.2f})")
             
        if reasons:
            is_passed = False
            
        metrics["passed"] = is_passed
        metrics["reasons"] = reasons
        
        return is_passed, metrics

    def _calculate_metrics(self, text: str) -> Dict[str, float]:
        # Core metric calculation logic.
        # Improved tokenization for CJK support
        # Match sequences of non-whitespace, but split CJK chars? 
        # Or just match word-like tokens: English words or individual CJK chars.
        # Regex: English/Number sequences OR individual CJK characters.
        # This treats each CJK char as a "word", which is a common heuristic for stats like this.
        token_pattern = re.compile(r'[a-zA-Z0-9-]+|[\u4e00-\u9fff]')
        words = token_pattern.findall(text)
        
        if not words:
            # Fallback to simple split if no match (e.g. only symbols)
            words = text.split()
            
        if not words:
            return {k: 0.0 for k in self.thresholds.keys()} | {"word_count": 0}

        # Basic Word Stats
        word_count = len(words)
        mean_word_length = sum(len(w) for w in words) / word_count
        
        # Alpha words
        alpha_count = sum(1 for w in words if any(c.isalpha() for c in w))
        frac_no_alph_words = 1.0 - (alpha_count / word_count)
        
        # Unique
        frac_unique_words = len(set(words)) / word_count
        
        # Entropy
        counts = Counter(words)
        probs = [c / word_count for c in counts.values()]
        unigram_entropy = -sum(p * math.log(p) for p in probs)
        
        # Line-based stats
        lines = [l.strip() for l in text.split('\n') if l.strip()]
        total_lines = len(lines) or 1
        
        ending_punct = sum(1 for l in lines if l[-1] in ".!?;。！？")
        frac_ending_sentence = ending_punct / total_lines
        
        numerical_lines = sum(1 for l in lines if self._is_numerical(l))
        frac_numerical_lines = numerical_lines / total_lines
        
        uppercase_lines = 0
        for l in lines:
            # Only count as uppercase if it has cased characters and is fully uppercase
            # But for Chinese mixed with GDP, isupper() is True.
            # We should check if the ratio of uppercase chars is high relative to TOTAL length (including uncased CJK).
            # If line is "中国GDP", len=5, upper=3. Ratio 0.6.
            # If line is "HELLO WORLD", len=11, upper=10. Ratio ~0.9.
            # If "This is a normal line", upper=1.
            
            clean_l = re.sub(r'\s+', '', l)
            if not clean_l: continue
            
            upper_count = sum(1 for c in clean_l if c.isupper())
            # heuristic: if > 60% of characters are uppercase, flag it.
            if (upper_count / len(clean_l)) > 0.6:
                uppercase_lines += 1
        
        frac_uppercase_lines = uppercase_lines / total_lines
        
        # N-grams (Character level as per RedPajama typically, or word? 
        # RedPajama usually does char-level n-gram overlap for dedupe, but here 
        # "belong to top ngram" implies text repetition. 
        # Let's map "frac_chars_top_ngrams" logic:
        # Calculate n-grams of words or chars? Usually chars for this specific metric in literature.
        # But let's simplify to word n-grams for readability or stick to char n-grams if standard.
        # The prompt said "doc_frac_chars_top_2gram", so we look at characters.)
        
        frac_top_2gram = self._calc_top_ngram_frac(text, 2)
        frac_top_3gram = self._calc_top_ngram_frac(text, 3)
        
        return {
            "word_count": word_count,
            "mean_word_length": mean_word_length,
            "frac_no_alph_words": frac_no_alph_words,
            "frac_unique_words": frac_unique_words,
            "unigram_entropy": unigram_entropy,
            "frac_ending_sentence": frac_ending_sentence,
            "frac_numerical_lines": frac_numerical_lines,
            "frac_uppercase_lines": frac_uppercase_lines,
            "frac_top_2gram": frac_top_2gram,
            "frac_top_3gram": frac_top_3gram,
            "num_sentences": len(re.split(r'[.!?。！？]+', text))
        }

    def _is_numerical(self, line: str) -> bool:
        """Heuristic for mostly numerical line."""
        clean = re.sub(r'\s+', '', line)
        if not clean: return False
        digits = sum(1 for c in clean if c.isdigit())
        return (digits / len(clean)) > 0.5

    def _calc_top_ngram_frac(self, text: str, n: int) -> float:
        """Fraction of characters belonging to the most frequent n-gram."""
        if len(text) < n: return 0.0
        
        # Generate char n-grams
        grams = [text[i:i+n] for i in range(len(text) - n + 1)]
        if not grams: return 0.0
        
        counts = Counter(grams)
        if not counts: return 0.0
        
        top_gram, top_count = counts.most_common(1)[0]
        
        # If top gram appears only once, it's not "repetitive" in a harmful way usu.
        # But rigorous formula is just count/total.
        
        # However, RedPajama metric is: proportion of *characters* that are part of the top n-gram.
        # If "AB" is top, and text is "ABAB", both ABs contribute.
        # Simplification: top_count * length_of_gram / total_chars 
        # But overlapping? "AAAA" -> top 2-gram "AA". indices 0,1,2.
        # Let's stick to the simplest proxy: top_count / total_grams
        
        return top_count / len(grams)
