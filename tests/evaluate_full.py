import json
import time
import requests
import numpy as np
from rouge_score import rouge_scorer
from sentence_transformers import SentenceTransformer
from sklearn.metrics.pairwise import cosine_similarity
from collections import defaultdict
import pandas as pd
from colorama import init, Fore, Style

# Инициализация цветного вывода
init(autoreset=True)

API_URL = "http://localhost:8000/chat"

class RAGEvaluator:
    def __init__(self, test_file: str):
        with open(test_file, 'r', encoding='utf-8') as f:
            self.test_data = json.load(f)
        self.scorer = rouge_scorer.RougeScorer(['rouge1', 'rouge2', 'rougeL'], use_stemmer=True)
        self.embedder = SentenceTransformer('intfloat/multilingual-e5-small')
        self.results = []

    def evaluate_generation(self, predicted: str, expected: str) -> dict:
        """Вычисляет метрики генерации."""
        if not predicted or not expected:
            return {"rouge1": 0, "rouge2": 0, "rougeL": 0, "similarity": 0, "faithfulness": 0}
        
        rouge_scores = self.scorer.score(expected, predicted)
        exp_emb = self.embedder.encode(expected)
        pred_emb = self.embedder.encode(predicted)
        similarity = cosine_similarity([exp_emb], [pred_emb])[0][0]
        
        expected_words = set(expected.lower().split())
        predicted_words = set(predicted.lower().split())
        overlap = len(expected_words.intersection(predicted_words)) / len(expected_words) if expected_words else 0
        
        return {
            "rouge1": rouge_scores['rouge1'].fmeasure,
            "rouge2": rouge_scores['rouge2'].fmeasure,
            "rougeL": rouge_scores['rougeL'].fmeasure,
            "similarity": float(similarity),
            "faithfulness": overlap
        }

    def run_evaluation(self) -> dict:
        """Запускает полное тестирование и собирает метрики."""
        results = []
        latencies = []
        errors = 0
        
        for item in self.test_data:
            query = item["query"]
            expected = item["expected_answer"]
            
            start = time.time()
            try:
                resp = requests.post(API_URL, json={"question": query, "history": []}, timeout=30)
                latency = time.time() - start
                latencies.append(latency)
            except Exception as e:
                results.append({"query": query, "error": str(e)})
                errors += 1
                continue
            
            if resp.status_code != 200:
                results.append({"query": query, "error": f"HTTP {resp.status_code}"})
                errors += 1
                continue
            
            data = resp.json()
            answer = data.get("answer", "")
            sources = data.get("sources", [])
            gen_metrics = self.evaluate_generation(answer, expected)
            
            results.append({
                "query": query,
                "expected": expected,
                "predicted": answer,
                "sources_count": len(sources),
                "latency": latency,
                **gen_metrics
            })
        
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
            "avg_sources": np.mean([r["sources_count"] for r in results if "sources_count" in r]) if results else 0
        }

    def print_report(self, metrics: dict):
        """Выводит красочный отчёт в консоль."""
        print("\n" + "=" * 70)
        print(Fore.CYAN + Style.BRIGHT + " RAG SYSTEM EVALUATION REPORT")
        print("=" * 70)
        
        # Общая статистика
        print(Fore.YELLOW + "\n GENERAL STATISTICS")
        print(f"  Total queries:        {metrics['total']}")
        print(f"  Successful responses: {metrics['total'] - metrics['errors']}")
        print(f"  Errors:               {metrics['errors']}")
        print(f"  Success rate:         {metrics['success_rate']*100:.1f}%")
        
        # Метрики генерации
        print(Fore.YELLOW + "\n GENERATION QUALITY")
        print(f"  ROUGE-1 (F1):         {metrics['avg_rouge1']:.4f}")
        print(f"  ROUGE-2 (F1):         {metrics['avg_rouge2']:.4f}")
        print(f"  ROUGE-L (F1):         {metrics['avg_rougeL']:.4f}")
        print(f"  Semantic Similarity:   {metrics['avg_similarity']:.4f}")
        print(f"  Faithfulness:          {metrics['avg_faithfulness']:.4f}")
        
        # Скорость
        print(Fore.YELLOW + "\n PERFORMANCE")
        print(f"  Average latency:      {metrics['avg_latency']*1000:.0f} ms")
        print(f"  P95 latency:          {metrics['p95_latency']*1000:.0f} ms")
        print(f"  P99 latency:          {metrics['p99_latency']*1000:.0f} ms")
        
        # Поиск
        print(Fore.YELLOW + "\n RETRIEVAL")
        print(f"  Average sources found: {metrics['avg_sources']:.1f}")
        
        # Оценка качества (цветовая индикация)
        print(Fore.YELLOW + "\n QUALITY ASSESSMENT")
        def grade(val, thresholds=[(0.7, ' Excellent'), (0.5, ' Good'), (0.3, ' Needs improvement'), (0, ' Poor')]):
            for th, label in thresholds:
                if val >= th:
                    return label
            return ' Poor'
        
        print(f"  ROUGE-L:      {metrics['avg_rougeL']:.3f}  {grade(metrics['avg_rougeL'])}")
        print(f"  Semantic Sim: {metrics['avg_similarity']:.3f}  {grade(metrics['avg_similarity'])}")
        print(f"  Faithfulness: {metrics['avg_faithfulness']:.3f}  {grade(metrics['avg_faithfulness'])}")
        print(f"  Success rate: {metrics['success_rate']*100:.1f}%  {grade(metrics['success_rate'], thresholds=[(0.95, '✅ Excellent'), (0.9, '⚠️ Good'), (0.7, '🔶 Needs improvement'), (0, '❌ Poor')])}")
        
        # Топ-5 лучших и худших запросов
        self.print_top_bottom(metric='rougeL', top_n=3)

    def print_top_bottom(self, metric='rougeL', top_n=3):
        """Печатает лучшие и худшие запросы по указанной метрике."""
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
        """Сохраняет результаты в JSON."""
        with open("tests/detailed_results.json", "w", encoding="utf-8") as f:
            json.dump({
                "summary": metrics,
                "details": self.results
            }, f, ensure_ascii=False, indent=2)
        print(Fore.GREEN + "\n Detailed results saved to tests/detailed_results.json")

if __name__ == "__main__":
    evaluator = RAGEvaluator("tests/test_questions_faq.json")
    metrics = evaluator.run_evaluation()
    evaluator.print_report(metrics)
    evaluator.save_results(metrics)