from pydantic import BaseModel, Field


class LatencyMetrics(BaseModel):
    mean: float
    p50: float
    p95: float
    retrieval_mean: float
    generation_mean: float


class TokenMetrics(BaseModel):
    total_input: int
    total_output: int
    avg_input_per_query: float
    avg_output_per_query: float


class CostMetrics(BaseModel):
    total: float
    avg_per_query: float


class CategoryMetrics(BaseModel):
    count: int
    avg_token_f1: float
    avg_rouge_l: float
    avg_citation_recall: float


class ModeSummary(BaseModel):
    total_queries: int
    avg_token_f1: float
    avg_rouge_l: float
    refusal_accuracy: float
    avg_citation_page_recall: float
    avg_grounding_rate: float
    latency_ms: LatencyMetrics
    tokens: TokenMetrics
    cost_usd: CostMetrics
    by_category: dict[str, CategoryMetrics] = Field(default_factory=dict)


class StrategyComparisonItem(BaseModel):
    label: str
    summary: ModeSummary


class BenchmarkPaperItem(BaseModel):
    filename: str
    title: str
    authors: list[str]
    arxiv_id: str
    domain: str
    character: str
    page_count: int


class EvalDashboardResponse(BaseModel):
    timestamp: str
    active_strategy: str = "hybrid_rerank"
    comparison: dict[str, StrategyComparisonItem]
    papers: list[BenchmarkPaperItem]
    markdown_table: str
    extra_notes: list[str] = Field(default_factory=list)
