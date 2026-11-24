import React from 'react';
import { AlertTriangle, TrendingUp, Clock } from 'lucide-react';
import { PlannerResult } from '@/lib/types';

interface MetricsProps {
  result: PlannerResult | null;
  loading: boolean;
}

export default function Metrics({ result, loading }: MetricsProps) {
  if (loading) {
    return (
      <div className="grid grid-cols-1 md:grid-cols-4 gap-4 mb-6">
        {[1, 2, 3, 4].map((i) => (
          <div key={i} className="card animate-pulse h-24" />
        ))}
      </div>
    );
  }

  if (!result) {
    return null;
  }

  return (
    <div className="grid grid-cols-1 md:grid-cols-4 gap-4 mb-6">
      <div className="card">
        <div className="flex items-center justify-between">
          <div>
            <p className="text-slate-600 dark:text-slate-400 text-sm font-medium">Tests Ranked</p>
            <p className="text-3xl font-bold text-slate-900 dark:text-white mt-2">
              {result.ranked_tests.length}
            </p>
          </div>
          <TrendingUp className="w-8 h-8 text-blue-500" />
        </div>
      </div>

      <div className="card">
        <div className="flex items-center justify-between">
          <div>
            <p className="text-slate-600 dark:text-slate-400 text-sm font-medium">Estimated Time Saved</p>
            <p className="text-3xl font-bold text-slate-900 dark:text-white mt-2">
              {Math.round(result.hil_time_saved_seconds / 60)}m
            </p>
            <p className="text-xs text-green-600 dark:text-green-400 mt-1">
              {result.full_suite_time_seconds > 0
                ? (100 * result.hil_time_saved_seconds / result.full_suite_time_seconds).toFixed(1)
                : '0.0'}% estimated reduction
            </p>
          </div>
          <Clock className="w-8 h-8 text-green-500" />
        </div>
      </div>

      <div className="card">
        <div className="flex items-center justify-between">
          <div>
            <p className="text-slate-600 dark:text-slate-400 text-sm font-medium">HIGH Risk</p>
            <p className="text-3xl font-bold text-slate-900 dark:text-white mt-2">
              {result.high_risk_tests.length}
            </p>
          </div>
          <AlertTriangle className="w-8 h-8 text-red-500" />
        </div>
      </div>

      <div className="card">
        <div className="flex items-center justify-between">
          <div>
            <p className="text-slate-600 dark:text-slate-400 text-sm font-medium">Coverage Gaps</p>
            <p className="text-3xl font-bold text-slate-900 dark:text-white mt-2">
              {result.gap_tickets.length}
            </p>
          </div>
          <AlertTriangle className="w-8 h-8 text-purple-500" />
        </div>
      </div>
    </div>
  );
}
