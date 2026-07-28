# tests/evaluate_full.py
import json
import time
import requests
import numpy as np
import re
from rouge_score import rouge_scorer
from sentence_transformers import SentenceTransformer
from sklearn.metrics.pairwise import cosine_similarity
from collections import defaultdict
import pandas as pd
from colorama import init, Fore, Style
import sys
import io

# Принудительно используем UTF-8 для вывода (исправление ошибки кодировки)
if sys.stdout.encoding != 'utf-8':
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')
    sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8')

init(autoreset=True)

API_URL = "http://localhost:8000/chat"

class RAGEvaluator:
    def __init__(self, test_file: str):
        with open(test_file, 'r', encoding='utf-8') as f:
            self.test_data = json.load(f)
        self.scorer = rouge_scorer.RougeScorer(['rouge1', 'rouge2', 'rougeL'], use_stemmer=True)
        self.embedder = SentenceTransformer('intfloat/multilingual-e5-small')
        self.results = []

    def normalize_text(self, text: str) -> str:
        """Приводит текст к нормализованному виду для сравнения."""
        if not text:
            return ""
        text = text.lower().strip()
        text = re.sub(r'[^\w\s]', '', text)   # удаляем пунктуацию
        text = re.sub(r'\s+', ' ', text)      # схлопываем пробелы
        return text

    def evaluate_generation(self, predicted: str, expected: str) -> dict:
        """Вычисляет все метрики генерации."""
        if not predicted or not expected:
            return {
                "rouge1": 0, "rouge2": 0, "rougeL": 0,
                "similarity": 0, "faithfulness": 0,
                "exact_match": 0, "keyword_recall": 0
            }

        # ROUGE
        rouge_scores = self.scorer.score(expected, predicted)

        # Семантическое сходство
        exp_emb = self.embedder.encode(expected)
        pred_emb = self.embedder.encode(predicted)
        sim = cosine_similarity([exp_emb], [pred_emb])[0][0]
        sim = float(sim)

        # Faithfulness: доля слов из ожидаемого, присутствующих в ответе
        expected_words = set(expected.lower().split())
        predicted_words = set(predicted.lower().split())
        overlap = len(expected_words.intersection(predicted_words)) / len(expected_words) if expected_words else 0

        # Exact Match (после нормализации)
        norm_exp = self.normalize_text(expected)
        norm_pred = self.normalize_text(predicted)
        exact_match = 1.0 if norm_exp == norm_pred else 0.0

        # Keyword recall: доля ключевых слов (длиной > 3 символов) из ожидаемого, найденных в ответе
        key_exp = [w for w in expected_words if len(w) > 3]
        key_pred = set(predicted_words)
        keyword_recall = len([w for w in key_exp if w in key_pred]) / len(key_exp) if key_exp else 0.0

        return {
            "rouge1": rouge_scores['rouge1'].fmeasure,
            "rouge2": rouge_scores['rouge2'].fmeasure,
            "rougeL": rouge_scores['rougeL'].fmeasure,
            "similarity": sim,
            "faithfulness": overlap,
            "exact_match": exact_match,
            "keyword_recall": keyword_recall
        }

    def run_evaluation(self) -> dict:
        results = []
        latencies = []
        errors = 0

        for item in self.test_data:
            query = item["query"]
            expected = item["expected_answer"]
            classification = ""
            explanation = ""
            start = time.time()
            latency = 0.0
            answer = ""
            sources = []
            gen_metrics = {
                "rouge1": 0, "rouge2": 0, "rougeL": 0,
                "similarity": 0, "faithfulness": 0,
                "exact_match": 0, "keyword_recall": 0
            }
            resp = None

            try:
                resp = requests.post(API_URL, json={"question": query, "history": []}, timeout=30)
                latency = time.time() - start
                if resp.status_code == 200:
                    data = resp.json()
                    answer = data.get("answer", "")
                    sources = data.get("sources", [])
                    gen_metrics = self.evaluate_generation(answer, expected)
                    classification = self.classify_answer(gen_metrics)
                    explanation = self.explain_result(gen_metrics)
                else:
                    # HTTP error – treat as failure but still record a response
                    answer = f"HTTP Error {resp.status_code}"
            except Exception as e:
                latency = time.time() - start
                answer = f"Exception: {str(e)}"

            # Always append a complete record
            results.append({
                "query": query,
                "expected": expected,
                "predicted": answer,
                "sources_count": len(sources),
                "latency": latency,
                **gen_metrics,
                "classification": classification,
                "analysis": explanation
            })

            if resp is not None and resp.status_code != 200:
                errors += 1
            elif "Exception" in answer:
                errors += 1

            latencies.append(latency)

        self.results = results
        total = len(results)
        success = total - errors

        return {
            "total": total,
            "errors": errors,
            "success_rate": success / total if total > 0 else 0,
            "avg_latency": np.mean(latencies) if latencies else 0,
            "p95_latency": np.percentile(latencies, 95) if latencies else 0,
            "p99_latency": np.percentile(latencies, 99) if latencies else 0,
            "avg_rouge1": np.mean([r["rouge1"] for r in results if "rouge1" in r]) if results else 0,
            "avg_rouge2": np.mean([r["rouge2"] for r in results if "rouge2" in r]) if results else 0,
            "avg_rougeL": np.mean([r["rougeL"] for r in results if "rougeL" in r]) if results else 0,
            "avg_similarity": np.mean([r["similarity"] for r in results if "similarity" in r]) if results else 0,
            "avg_faithfulness": np.mean([r["faithfulness"] for r in results if "faithfulness" in r]) if results else 0,
            "avg_exact_match": np.mean([r["exact_match"] for r in results if "exact_match" in r]) if results else 0,
            "avg_keyword_recall": np.mean([r["keyword_recall"] for r in results if "keyword_recall" in r]) if results else 0,
            "avg_sources": np.mean([r["sources_count"] for r in results if "sources_count" in r]) if results else 0
        }

    def print_detailed_table(self):

        if not self.results:
            print("No results to display.")
            return

        df = pd.DataFrame(self.results)

        cols = [
            "query",
            "classification",
            "similarity",
            "faithfulness",
            "rougeL",
            "keyword_recall",
            "sources_count",
            "latency"
        ]

        df_display = df[cols].copy()

        # Round numeric columns
        for c in df_display.columns:
            if c not in ["query", "classification", "sources_count"]:
                df_display[c] = df_display[c].round(3)

        # Rename columns
        df_display.columns = [
            "Question",
            "Classification",
            "Similarity",
            "Faithfulness",
            "ROUGE-L",
            "Keyword Recall",
            "Sources",
            "Latency (s)"
        ]

        # Shorten long questions
        df_display["Question"] = df_display["Question"].apply(
            lambda x: x[:70] + "..." if len(x) > 70 else x
        )

        print(Fore.CYAN + "\n" + "=" * 120)
        print(Fore.CYAN + Style.BRIGHT + "DETAILED QUESTION EVALUATION")
        print(Fore.CYAN + "=" * 120)

        print(df_display.to_string(index=False))

        print("\n" + "=" * 120)
        print(Fore.CYAN + Style.BRIGHT + "QUESTION-BY-QUESTION ANALYSIS")
        print("=" * 120)

        for i, r in enumerate(self.results, 1):

            # Color according to classification
            if r["classification"] == "Correct":
               color = Fore.GREEN
            elif r["classification"] == "Partially Correct":
                color = Fore.YELLOW
            else:
                color = Fore.RED

            print("\n" + "-" * 120)
            print(Fore.CYAN + f"Question {i}")
            print("-" * 120)

            print(Fore.WHITE + "Query:")
            print(r["query"])

            print(Fore.GREEN + "\nExpected Answer:")
            print(r["expected"])

            print(Fore.CYAN + "\nPredicted Answer:")
            print(r["predicted"])

            print(color + f"\nClassification: {r['classification']}")

            print(Fore.MAGENTA + "\nExplanation:")
            print(r["analysis"])

            print("\nMetrics:")
            print(f"  Similarity       : {r['similarity']:.3f}")
            print(f"  Faithfulness     : {r['faithfulness']:.3f}")
            print(f"  ROUGE-L          : {r['rougeL']:.3f}")
            print(f"  Keyword Recall   : {r['keyword_recall']:.3f}")
            print(f"  Sources Retrieved: {r['sources_count']}")
            print(f"  Latency          : {r['latency']:.3f}s")
            
    def print_report(self, metrics: dict):

        print("\n" + "=" * 90)
        print(Fore.CYAN + Style.BRIGHT + "RAG SYSTEM EVALUATION REPORT")
        print("=" * 90)

        print(Fore.YELLOW + "\nGENERAL STATISTICS")
        print(f"  Total Questions : {metrics['total']}")
        print(f"  Successful      : {metrics['total'] - metrics['errors']}")
        print(f"  Errors          : {metrics['errors']}")
        print(f"  Success Rate    : {metrics['success_rate'] * 100:.1f}%")

        print(Fore.YELLOW + "\nGENERATION QUALITY")
        print(f"  ROUGE-1         : {metrics['avg_rouge1']:.4f}")
        print(f"  ROUGE-2         : {metrics['avg_rouge2']:.4f}")
        print(f"  ROUGE-L         : {metrics['avg_rougeL']:.4f}")
        print(f"  Similarity      : {metrics['avg_similarity']:.4f}")
        print(f"  Faithfulness    : {metrics['avg_faithfulness']:.4f}")
        print(f"  Exact Match     : {metrics['avg_exact_match']:.4f}")
        print(f"  Keyword Recall  : {metrics['avg_keyword_recall']:.4f}")

        print(Fore.YELLOW + "\nPERFORMANCE")
        print(f"  Avg Latency     : {metrics['avg_latency'] * 1000:.0f} ms")
        print(f"  P95 Latency     : {metrics['p95_latency'] * 1000:.0f} ms")
        print(f"  P99 Latency     : {metrics['p99_latency'] * 1000:.0f} ms")

        print(Fore.YELLOW + "\nRETRIEVAL")
        print(f"  Avg Sources     : {metrics['avg_sources']:.1f}")

        def grade(value,
                  thresholds=[
                      (0.7, "Excellent"),
                      (0.5, "Good"),
                      (0.3, "Needs Improvement"),
                      (0, "Poor")
                  ]):
            for th, label in thresholds:
                if value >= th:
                    return label
            return "Poor"

        print(Fore.YELLOW + "\nQUALITY ASSESSMENT")

        print(f"  ROUGE-L       : {metrics['avg_rougeL']:.3f} ({grade(metrics['avg_rougeL'])})")
        print(f"  Similarity    : {metrics['avg_similarity']:.3f} ({grade(metrics['avg_similarity'])})")
        print(f"  Faithfulness  : {metrics['avg_faithfulness']:.3f} ({grade(metrics['avg_faithfulness'])})")
        print(f"  Exact Match   : {metrics['avg_exact_match']:.3f} ({grade(metrics['avg_exact_match'])})")
        print(f"  Keyword Recall: {metrics['avg_keyword_recall']:.3f} ({grade(metrics['avg_keyword_recall'])})")

    # ---------------------------------------------------------
    # Classification summary
    # ---------------------------------------------------------

        correct = sum(r["classification"] == "Correct" for r in self.results)
        partial = sum(r["classification"] == "Partially Correct" for r in self.results)
        incorrect = sum(r["classification"] == "Incorrect" for r in self.results)

        total = len(self.results)

        print(Fore.YELLOW + "\nANSWER CLASSIFICATION")
        print(Fore.GREEN + f"  Correct            : {correct} ({100*correct/total:.1f}%)")
        print(Fore.YELLOW + f"  Partially Correct  : {partial} ({100*partial/total:.1f}%)")
        print(Fore.RED + f"  Incorrect          : {incorrect} ({100*incorrect/total:.1f}%)")

        print(Fore.YELLOW + "\nOVERALL ANALYSIS")

        if metrics["avg_similarity"] >= 0.85:
            print(Fore.GREEN + "✓ The model has strong semantic understanding of the expected answers.")
        elif metrics["avg_similarity"] >= 0.70:
            print(Fore.YELLOW + "• The model captures most of the intended meaning.")
        else:
            print(Fore.RED + "• Semantic similarity is low.")

        if metrics["avg_faithfulness"] < 0.35:
            print(Fore.RED + "• Low faithfulness indicates many answers contain unsupported or hallucinated information.")

        if metrics["avg_keyword_recall"] < 0.30:
            print(Fore.YELLOW + "• Important keywords from the expected answers are frequently missing.")

        if metrics["avg_exact_match"] == 0:
            print("• Exact match is zero, which is expected when answers are paraphrased.")

        print(Fore.YELLOW + "\nCOMMON ERROR PATTERNS")
        print("  • Hallucinated information")
        print("  • Adding unsupported implementation details")
        print("  • Missing documented information")
        print("  • Answering a related but different question")
        print("  • Mixing features from different products")

        # Existing functions
        self.print_top_bottom(metric="rougeL", top_n=3)
        self.print_detailed_table()
        self.print_analysis()
        self.print_overall_summary()
    
    def print_analysis(self):

        print("\n" + "="*90)
        print(Fore.CYAN + Style.BRIGHT + "DETAILED ANSWER ANALYSIS")
        print("="*90)

        for i, r in enumerate(self.results, 1):

            print(Fore.YELLOW + f"\nQuestion {i}")
            print("-"*90)

            print(Fore.WHITE + "Query:")
            print(r["query"])

            print(Fore.GREEN + "\nExpected:")
            print(r["expected"])

            print(Fore.CYAN + "\nPredicted:")
            print(r["predicted"])

            print(Fore.MAGENTA + f"\nClassification: {r['classification']}")

            print("Analysis:")
            print(r["analysis"])

            print(
                f"\nMetrics:"
                f"\n  Similarity      : {r['similarity']:.3f}"
                f"\n  Faithfulness    : {r['faithfulness']:.3f}"
                f"\n  ROUGE-L         : {r['rougeL']:.3f}"
                f"\n  Keyword Recall  : {r['keyword_recall']:.3f}"
            ) 
    def print_top_bottom(self, metric='rougeL', top_n=3):
        valid = [r for r in self.results if metric in r and r[metric] > 0]
        if not valid:
            return

        sorted_by_metric = sorted(valid, key=lambda x: x[metric], reverse=True)
        best = sorted_by_metric[:top_n]
        worst = sorted_by_metric[-top_n:][::-1]

        print(Fore.YELLOW + f"\n TOP {top_n} BEST RESPONSES (by {metric.upper()})")
        for i, r in enumerate(best, 1):
            print(f"  {i}. {Fore.GREEN}{r['query'][:60]}... {r[metric]:.3f}")

        print(Fore.YELLOW + f"\n TOP {top_n} WORST RESPONSES (by {metric.upper()})")
        for i, r in enumerate(worst, 1):
            print(f"  {i}. {Fore.RED}{r['query'][:60]}... {r[metric]:.3f}")
            if 'error' in r:
                print(f"     Error: {r['error']}")

    def save_results(self, metrics: dict):
        with open("tests/detailed_results.json", "w", encoding="utf-8") as f:
            json.dump({
                "summary": metrics,
                "details": self.results
            }, f, ensure_ascii=False, indent=2)
        print(Fore.GREEN + "\n Подробные результаты сохранены в tests/detailed_results.json")


    def classify_answer(self, result):
  

        sim = result["similarity"]
        faith = result["faithfulness"]
        rouge = result["rougeL"]
        keyword = result["keyword_recall"]

        # Correct
        if sim >= 0.85 and faith >= 0.50 and rouge >= 0.30:
            return "Correct"

        # Partially Correct
        elif sim >= 0.65:
            return "Partially Correct"

        # Incorrect
        else:
            return "Incorrect"
        
    def explain_result(self, result):
  

        comments = []

        if result["similarity"] >= 0.90:
            comments.append("Very high semantic similarity.")
        elif result["similarity"] >= 0.75:
            comments.append("Moderate semantic similarity.")
        else:
            comments.append("Low semantic similarity.")

        if result["faithfulness"] < 0.30:
            comments.append(
                "Answer contains unsupported or hallucinated information."
            )
        elif result["faithfulness"] < 0.60:
            comments.append(
                "Answer is only partially grounded in the expected documentation."
            )
        else:
            comments.append(
                "Answer is well grounded in the documentation."
            )

        if result["keyword_recall"] < 0.20:
            comments.append(
                "Many important keywords from the expected answer are missing."
            )

        if result["exact_match"] == 1:
            comments.append("Exact match.")

        return " ".join(comments)
    def print_overall_summary(self):

        total = len(self.results)

        correct = sum(r["classification"] == "Correct"
                  for r in self.results)

        partial = sum(r["classification"] == "Partially Correct"
                  for r in self.results)

        incorrect = sum(r["classification"] == "Incorrect"
                    for r in self.results)

        print("\n" + "="*90)
        print(Fore.CYAN + Style.BRIGHT + "OVERALL QUALITY SUMMARY")
        print("="*90)

        print(f"Correct:            {correct} ({correct/total:.0%})")
        print(f"Partially Correct:  {partial} ({partial/total:.0%})")
        print(f"Incorrect:          {incorrect} ({incorrect/total:.0%})")
    
        print("\nMain observations:")
 
        if np.mean([r["similarity"] for r in self.results]) > 0.85:
            print("- Strong semantic understanding.")

        if np.mean([r["faithfulness"] for r in self.results]) < 0.35:
            print("- Low grounding to documentation.")
            print("- Model frequently hallucinates unsupported information.")

        if np.mean([r["keyword_recall"] for r in self.results]) < 0.30:
            print("- Important keywords are often omitted.")

        print("\nCommon error patterns:")
        print("- Hallucinated features.")
        print("- Overly detailed answers beyond the documentation.")
        print("- Missing documented information.")
        print("- Mixing unrelated products or APIs.")
    
    
if __name__ == "__main__":
    evaluator = RAGEvaluator("tests/test_questions.json")
    metrics = evaluator.run_evaluation()
    evaluator.print_report(metrics)
    evaluator.save_results(metrics)