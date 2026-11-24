'use client';

import React, { useState } from 'react';
import { Moon, Sun, Upload } from 'lucide-react';
import { analyzeDiff } from '@/lib/api-client';
import { PlannerResult, AnalysisRequest } from '@/lib/types';
import Metrics from '@/components/Metrics';
import TestList from '@/components/TestList';
import CoverageGaps from '@/components/CoverageGaps';
import { demoScenarios } from '@/lib/demo-scenarios';

export default function Home() {
  const [darkMode, setDarkMode] = useState(true);
  const [diffContent, setDiffContent] = useState('');
  const [defectDescription, setDefectDescription] = useState('');
  const [loading, setLoading] = useState(false);
  const [result, setResult] = useState<PlannerResult | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [highThreshold, setHighThreshold] = useState(0.78);
  const [mediumThreshold, setMediumThreshold] = useState(0.65);
  const [backendUrl, setBackendUrl] = useState(process.env.NEXT_PUBLIC_API_URL || '');
  const [demoId, setDemoId] = useState(demoScenarios[0].id);
  const demo = demoScenarios.find((scenario) => scenario.id === demoId) ?? demoScenarios[0];

  const handleAnalyze = async () => {
    setResult(null);
    if (!diffContent.trim()) {
      setError('Please paste a Git diff');
      return;
    }
    try {
      const url = new URL(backendUrl);
      if (url.protocol !== 'https:' && !(url.protocol === 'http:' && ['localhost', '127.0.0.1'].includes(url.hostname))) {
        throw new Error('Use an HTTPS backend URL, or localhost for local development.');
      }
    } catch (error) {
      setError(error instanceof TypeError ? 'Enter a valid backend URL.' : (error as Error).message);
      return;
    }

    setLoading(true);
    setError(null);

    try {
      const request: AnalysisRequest = {
        diff_content: diffContent,
        defect_description: defectDescription || undefined,
        high_threshold: highThreshold,
        medium_threshold: mediumThreshold,
      };

      const analysisResult = await analyzeDiff(request, backendUrl);
      setResult(analysisResult);
    } catch (err: unknown) {
      setError(err instanceof Error ? err.message : 'Failed to analyze diff. Make sure the backend is running.');
    } finally {
      setLoading(false);
    }
  };

  const handleFileUpload = (e: React.ChangeEvent<HTMLInputElement>, setContent: (val: string) => void) => {
    const file = e.target.files?.[0];
    if (!file) return;

    const reader = new FileReader();
    reader.onload = (event) => {
      setContent(event.target?.result as string);
    };
    reader.readAsText(file);
  };

  const handlePasteSample = async () => {
    setDiffContent(`diff --git a/src/cluster/speedometer.cpp b/src/cluster/speedometer.cpp
--- a/src/cluster/speedometer.cpp
+++ b/src/cluster/speedometer.cpp
@@ -24,7 +24,7 @@
     // CAN signal 0x1A4: Vehicle Speed
     uint16_t speed_kmh = (can_msg.data[0] << 8) | can_msg.data[1];
-    float speed_mph = speed_kmh * 0.621371;  // Legacy conversion
+    float speed_mph = speed_kmh * 0.621371007;  // Precision fix for mph scaling

     // Update cluster display
     display.speedometer_needle = speed_mph;
`);
  };

  return (
    <div className={darkMode ? 'dark' : ''}>
      <div className="min-h-screen bg-white dark:bg-slate-950 text-slate-900 dark:text-white transition-colors">
        {/* Header */}
        <header className="border-b border-slate-200 dark:border-slate-800 sticky top-0 z-50 bg-white/95 dark:bg-slate-950/95 backdrop-blur">
          <div className="max-w-7xl mx-auto px-4 py-4 flex justify-between items-center">
            <div>
              <h1 className="text-3xl font-bold bg-gradient-to-r from-blue-600 to-purple-600 bg-clip-text text-transparent">
                E5 Diff-to-Test Planner
              </h1>
              <p className="text-sm text-slate-600 dark:text-slate-400 mt-1">
                Risk-based test selection for automotive HMI
              </p>
            </div>
            <button
              onClick={() => setDarkMode(!darkMode)}
              className="p-2 hover:bg-slate-100 dark:hover:bg-slate-800 rounded-lg transition-colors"
            >
              {darkMode ? <Sun className="w-6 h-6" /> : <Moon className="w-6 h-6" />}
            </button>
          </div>
        </header>

        {/* Main Content */}
        <main className="max-w-7xl mx-auto px-4 py-8">
          <section aria-labelledby="demo-heading" className="mb-12">
            <div className="card mb-6">
              <h2 id="demo-heading" className="text-2xl font-bold mb-2">Explore an example</h2>
              <p className="text-sm text-slate-600 dark:text-slate-400 mb-4">
                Choose a scenario to preview what a test-selection report can look like. No server or model is needed.
                Results, scores and timings below are illustrative fixtures, not real analysis or measured savings.
                Changing the live-analysis thresholds does not affect these examples.
              </p>
              <label htmlFor="demo-scenario" className="block text-sm font-semibold mb-2">Example scenario</label>
              <select id="demo-scenario" value={demoId} onChange={(e) => setDemoId(e.target.value)} className="input-field mb-4">
                {demoScenarios.map((scenario) => <option key={scenario.id} value={scenario.id}>{scenario.name}</option>)}
              </select>
              <div aria-live="polite" className="space-y-2 text-sm text-slate-700 dark:text-slate-300">
                <p><strong>Example change:</strong> {demo.change}</p>
                <p><strong>Example defect:</strong> {demo.defect}</p>
                <p><strong>Example output:</strong> Suggested tests and possible gap for review, compared with a hypothetical 10-minute full suite.</p>
              </div>
            </div>
            <div aria-label="Illustrative example results">
              <Metrics result={demo.result} loading={false} showTimeSavings={demo.result.ranked_tests.length > 0} />
              {demo.result.ranked_tests.length === 0 && (
                <p className="mb-4 text-sm text-amber-700 dark:text-amber-300">
                  No tests selected is not evidence that regression testing can be skipped.
                </p>
              )}
              <TestList result={demo.result} loading={false} allowExport={false} />
              <div className="mt-6"><CoverageGaps result={demo.result} loading={false} /></div>
            </div>
          </section>

          <h2 className="text-2xl font-bold mb-4">Analyze your own change</h2>
          <p className="text-sm text-slate-600 dark:text-slate-400 mb-6">
            This separate live analysis requires an analysis server. The examples above work without one.
          </p>
          {/* Input Section */}
          <div className="grid grid-cols-1 lg:grid-cols-3 gap-6 mb-8">
            {/* Diff Input */}
            <div className="lg:col-span-2 card">
              <h2 className="text-xl font-bold mb-4">Git Diff Input</h2>
              <textarea
                value={diffContent}
                onChange={(e) => setDiffContent(e.target.value)}
                placeholder="Paste your unified Git diff here (or click Load Sample)..."
                className="input-field mb-4 h-40 font-mono text-sm"
              />
              <div className="flex gap-2 flex-wrap">
                <button onClick={handlePasteSample} className="btn-secondary">
                  Load Sample
                </button>
                <label className="btn-secondary cursor-pointer">
                  <Upload className="w-4 h-4 inline mr-2" />
                  Upload File
                  <input
                    type="file"
                    className="hidden"
                    onChange={(e) => handleFileUpload(e, setDiffContent)}
                    accept=".patch,.diff"
                  />
                </label>
              </div>
            </div>

            {/* Controls */}
            <div className="card">
              <h2 className="text-xl font-bold mb-4">Configuration</h2>
              <label className="block text-sm font-semibold mb-2" htmlFor="backend-url">Analysis server URL</label>
              <input
                id="backend-url"
                type="url"
                value={backendUrl}
                onChange={(e) => setBackendUrl(e.target.value)}
                placeholder="https://your-backend.example"
                className="input-field mb-2"
              />
              <p className="text-xs text-slate-600 dark:text-slate-400 mb-4">
                Analysis requires your own server. Submitted text is sent to that server; use only data you are permitted to share.
              </p>

              <div className="mb-4">
                <label className="block text-sm font-semibold mb-2">HIGH Risk Threshold</label>
                <input
                  type="range"
                  min="0.5"
                  max="1.0"
                  step="0.01"
                  value={highThreshold}
                  onChange={(e) => {
                    const value = parseFloat(e.target.value);
                    setHighThreshold(value);
                    setMediumThreshold(Math.min(mediumThreshold, value));
                  }}
                  className="w-full"
                />
                <p className="text-xs text-slate-600 dark:text-slate-400 mt-1">
                  {(highThreshold * 100).toFixed(0)}%
                </p>
              </div>

              <div className="mb-6">
                <label className="block text-sm font-semibold mb-2">MEDIUM Risk Threshold</label>
                <input
                  type="range"
                  min="0.5"
                  max={highThreshold}
                  step="0.01"
                  value={mediumThreshold}
                  onChange={(e) => setMediumThreshold(parseFloat(e.target.value))}
                  className="w-full"
                />
                <p className="text-xs text-slate-600 dark:text-slate-400 mt-1">
                  {(mediumThreshold * 100).toFixed(0)}%
                </p>
              </div>

              <button
                onClick={handleAnalyze}
                disabled={loading}
                className="btn-primary w-full disabled:opacity-50 disabled:cursor-not-allowed"
              >
                {loading ? 'Analyzing...' : 'Analyze Diff'}
              </button>

              {error && (
                <div className="mt-4 p-3 bg-red-100 dark:bg-red-900 text-red-800 dark:text-red-100 rounded text-sm">
                  ⚠️ {error}
                </div>
              )}
            </div>
          </div>

          {/* Optional Defect Input */}
          <div className="card mb-8">
            <h2 className="text-xl font-bold mb-4">Optional: Jira Defect Description</h2>
            <textarea
              value={defectDescription}
              onChange={(e) => setDefectDescription(e.target.value)}
              placeholder="Paste Jira defect description to combine with diff analysis..."
              className="input-field h-20 font-mono text-sm"
            />
          </div>
          <p className="mb-6 text-sm text-slate-600 dark:text-slate-400">
            Prototype only: similarities and time savings are estimates. Review the results and retain required regression tests.
            Image and video evidence is available in the local CLI, not this dashboard.
          </p>

          {/* Results */}
          <Metrics result={result} loading={loading} />
          <TestList result={result} loading={loading} />
          <div className="mt-8">
            <CoverageGaps result={result} loading={loading} />
          </div>
        </main>

        {/* Footer */}
        <footer className="border-t border-slate-200 dark:border-slate-800 mt-16 py-8 text-center text-slate-600 dark:text-slate-400 text-sm">
          <p>Built for automotive HMI test optimization • E5 runs on the configured server</p>
          <p className="mt-2">
            <a href="https://github.com/ankita-sathya/e5-diff-to-test-planner" className="text-blue-600 dark:text-blue-400 hover:underline">
              View on GitHub
            </a>
          </p>
        </footer>
      </div>
    </div>
  );
}
