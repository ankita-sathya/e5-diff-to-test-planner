export interface TestCase {
  test_id: string;
  title: string;
  domain: string;
  similarity_score: number;
  estimated_duration_seconds: number;
}

export interface PlannerResult {
  ranked_tests: TestCase[];
  high_risk_tests: TestCase[];
  total_hil_time_seconds: number;
  full_suite_time_seconds: number;
  hil_time_saved_seconds: number;
  gap_tickets: CoverageGap[];
}

export interface CoverageGap {
  domain: string;
  similarity_max: number;
  title: string;
  gap_reason: string;
  hil_bench_tags: string[];
}

export interface AnalysisRequest {
  diff_content: string;
  catalog_path?: string;
  defect_description?: string;
  high_threshold?: number;
  medium_threshold?: number;
  gap_threshold?: number;
}
