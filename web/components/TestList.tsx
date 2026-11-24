import React from 'react';
import { Download } from 'lucide-react';
import { PlannerResult } from '@/lib/types';

interface TestListProps {
  result: PlannerResult | null;
  loading: boolean;
}

export default function TestList({ result, loading }: TestListProps) {
  const getRiskBadgeColor = (risk: string) => {
    switch (risk) {
      case 'HIGH':
        return 'badge-high';
      case 'MEDIUM':
        return 'badge-medium';
      case 'GAP':
        return 'badge-gap';
      default:
        return 'badge-high';
    }
  };

  const exportJSON = () => {
    if (!result) return;
    const dataStr = JSON.stringify(result, null, 2);
    const dataBlob = new Blob([dataStr], { type: 'application/json' });
    const url = URL.createObjectURL(dataBlob);
    const link = document.createElement('a');
    link.href = url;
    link.download = `analysis-${new Date().toISOString().split('T')[0]}.json`;
    link.click();
  };

  if (loading) {
    return (
      <div className="card">
        <div className="animate-pulse space-y-4">
          {[1, 2, 3, 4, 5].map((i) => (
            <div key={i} className="h-16 bg-slate-200 dark:bg-slate-700 rounded" />
          ))}
        </div>
      </div>
    );
  }

  if (!result || result.ranked_tests.length === 0) {
    return (
      <div className="card text-center py-12">
        <p className="text-slate-600 dark:text-slate-400">
          {result ? 'No test cases matched the selected thresholds.' : 'No test cases ranked yet. Upload a Git diff to analyze.'}
        </p>
      </div>
    );
  }

  return (
    <div className="card">
      <div className="flex justify-between items-center mb-6">
        <h2 className="text-2xl font-bold text-slate-900 dark:text-white">Ranked Tests</h2>
        <button
          onClick={exportJSON}
          className="btn-secondary flex items-center gap-2"
        >
          <Download className="w-4 h-4" />
          Export JSON
        </button>
      </div>

      <div className="overflow-x-auto">
        <table className="w-full">
          <thead>
            <tr className="border-b border-slate-200 dark:border-slate-700">
              <th className="text-left py-3 px-4 font-semibold text-slate-700 dark:text-slate-300">Test ID</th>
              <th className="text-left py-3 px-4 font-semibold text-slate-700 dark:text-slate-300">Title</th>
              <th className="text-left py-3 px-4 font-semibold text-slate-700 dark:text-slate-300">Domain</th>
              <th className="text-left py-3 px-4 font-semibold text-slate-700 dark:text-slate-300">Similarity</th>
              <th className="text-left py-3 px-4 font-semibold text-slate-700 dark:text-slate-300">Risk</th>
              <th className="text-left py-3 px-4 font-semibold text-slate-700 dark:text-slate-300">Duration</th>
            </tr>
          </thead>
          <tbody>
            {result.ranked_tests.map((test, idx) => (
              <tr
                key={test.test_id}
                className={`border-b border-slate-100 dark:border-slate-700 hover:bg-slate-50 dark:hover:bg-slate-700/50 transition ${
                  idx % 2 === 0 ? 'bg-white dark:bg-slate-800' : 'bg-slate-50 dark:bg-slate-700/30'
                }`}
              >
                <td className="py-3 px-4 font-mono text-sm text-blue-600 dark:text-blue-400">{test.test_id}</td>
                <td className="py-3 px-4 text-slate-900 dark:text-white">{test.title}</td>
                <td className="py-3 px-4 text-slate-600 dark:text-slate-300">{test.domain}</td>
                <td className="py-3 px-4">
                  <div className="flex items-center gap-2">
                    <div className="w-16 bg-slate-200 dark:bg-slate-600 rounded-full h-2">
                      <div
                        className="bg-gradient-to-r from-green-500 to-blue-500 h-2 rounded-full"
                        style={{ width: `${test.similarity_score * 100}%` }}
                      />
                    </div>
                    <span className="font-mono text-sm text-slate-700 dark:text-slate-300">
                      {(test.similarity_score * 100).toFixed(0)}%
                    </span>
                  </div>
                </td>
                <td className="py-3 px-4">
                  <span className={`badge ${getRiskBadgeColor(result.high_risk_tests.some(t => t.test_id === test.test_id) ? 'HIGH' : 'MEDIUM')}`}>
                    {result.high_risk_tests.some(t => t.test_id === test.test_id) ? 'HIGH' : 'MEDIUM'}
                  </span>
                </td>
                <td className="py-3 px-4 text-slate-600 dark:text-slate-400">
                  {test.estimated_duration_seconds}s
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  );
}
