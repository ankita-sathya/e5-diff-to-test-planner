import React from 'react';
import { AlertCircle } from 'lucide-react';
import { PlannerResult } from '@/lib/types';

interface CoverageGapsProps {
  result: PlannerResult | null;
  loading: boolean;
}

export default function CoverageGaps({ result, loading }: CoverageGapsProps) {
  if (loading) {
    return (
      <div className="card">
        <div className="animate-pulse space-y-4">
          {[1, 2, 3].map((i) => (
            <div key={i} className="h-24 bg-slate-200 dark:bg-slate-700 rounded" />
          ))}
        </div>
      </div>
    );
  }

  if (!result) {
    return null;
  }
  if (result.gap_tickets.length === 0) {
    return (
      <div className="card">
        <div className="text-center py-8">
          <p className="text-slate-600 dark:text-slate-400">No coverage gap flagged by this analysis. This does not prove complete coverage.</p>
        </div>
      </div>
    );
  }

  return (
    <div className="card">
      <h2 className="text-2xl font-bold text-slate-900 dark:text-white mb-6 flex items-center gap-2">
        <AlertCircle className="w-6 h-6 text-purple-500" />
        Coverage Gaps (Suggested Xray Tickets)
      </h2>

      <div className="space-y-4">
        {result.gap_tickets.map((gap, idx) => (
          <div
            key={idx}
            className="border-l-4 border-purple-500 bg-purple-50 dark:bg-purple-900/20 p-4 rounded"
          >
            <div className="flex justify-between items-start mb-2">
              <h3 className="font-bold text-slate-900 dark:text-white">{gap.domain}</h3>
            </div>

            <p className="text-sm text-slate-700 dark:text-slate-300 mb-3">
              <strong>Similarity:</strong> {(gap.similarity_max * 100).toFixed(1)}%
            </p>

            <div className="bg-white dark:bg-slate-800 p-3 rounded mb-3">
              <p className="text-sm font-semibold text-slate-900 dark:text-white mb-1">
                Suggested Test Title:
              </p>
              <p className="text-sm text-slate-700 dark:text-slate-300">{gap.title}</p>
            </div>

            <div className="bg-white dark:bg-slate-800 p-3 rounded mb-3">
              <p className="text-sm font-semibold text-slate-900 dark:text-white mb-1">
                Description:
              </p>
              <p className="text-sm text-slate-700 dark:text-slate-300">{gap.gap_reason}</p>
            </div>

            <div className="flex gap-2 flex-wrap">
              {gap.hil_bench_tags.map((tag, tagIdx) => (
                <span
                  key={tagIdx}
                  className="inline-block px-2 py-1 bg-slate-200 dark:bg-slate-700 text-slate-800 dark:text-slate-200 text-xs rounded font-mono"
                >
                  {tag}
                </span>
              ))}
            </div>
          </div>
        ))}
      </div>

      <div className="mt-6 p-4 bg-blue-50 dark:bg-blue-900/20 border border-blue-200 dark:border-blue-800 rounded">
        <p className="text-sm text-slate-700 dark:text-slate-300">
          💡 <strong>Tip:</strong> Copy these suggested test cases and create new Xray tickets in Jira to close your test coverage gaps.
        </p>
      </div>
    </div>
  );
}
