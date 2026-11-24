import axios from 'axios';
import { AnalysisRequest, PlannerResult } from './types';

export async function analyzeDiff(request: AnalysisRequest, backendUrl: string): Promise<PlannerResult> {
  const response = await axios.post<PlannerResult>(`${backendUrl.replace(/\/+$/, '')}/api/analyze`, request, {
    timeout: 180000,
  });
  return response.data;
}
