import React, { useState } from 'react';
import { Star, ShieldCheck, ThumbsUp, CheckCircle, AlertCircle, X } from 'lucide-react';
import api from '../api/axios';

const CRITERIA = [
  {
    key: 'correctness',
    label: 'Factual Correctness',
    description: 'Alignment with candidate resume evidence and job requirements',
  },
  {
    key: 'helpfulness',
    label: 'Recruiter Utility / Helpfulness',
    description: 'Practical value for hiring team decision-making',
  },
  {
    key: 'completeness',
    label: 'Evaluation Completeness',
    description: 'Coverage of strengths, skill gaps, and interview questions',
  },
  {
    key: 'safety_groundedness',
    label: 'Safety & Groundedness',
    description: 'Absence of hallucinations, bias, or ungrounded claims',
  },
];

export default function HumanEvaluationModal({ application, onClose, onSubmitted }) {
  const [ratings, setRatings] = useState({
    correctness: 5,
    helpfulness: 5,
    completeness: 5,
    safety_groundedness: 5,
  });
  const [decisionOverride, setDecisionOverride] = useState('agreed');
  const [feedbackNotes, setFeedbackNotes] = useState('');
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);
  const [success, setSuccess] = useState(false);

  const handleRatingChange = (key, val) => {
    setRatings((prev) => ({ ...prev, [key]: val }));
  };

  const compositeScore = (
    (ratings.correctness + ratings.helpfulness + ratings.completeness + ratings.safety_groundedness) /
    4.0
  ).toFixed(2);

  const handleSubmit = async (e) => {
    e.preventDefault();
    setLoading(true);
    setError(null);
    try {
      await api.post(`/applications/${application.id}/human-evaluation`, {
        correctness: ratings.correctness,
        helpfulness: ratings.helpfulness,
        completeness: ratings.completeness,
        safety_groundedness: ratings.safety_groundedness,
        feedback_notes: feedbackNotes,
        decision_override: decisionOverride,
      });
      setSuccess(true);
      if (onSubmitted) onSubmitted();
      setTimeout(() => {
        onClose();
      }, 1500);
    } catch (err) {
      setError(err?.response?.data?.detail || 'Failed to submit human evaluation.');
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-slate-900/60 backdrop-blur-sm p-4">
      <div className="bg-white dark:bg-slate-900 rounded-2xl shadow-2xl max-w-xl w-full border border-slate-200 dark:border-slate-800 overflow-hidden">
        {/* Header */}
        <div className="px-6 py-4 bg-gradient-to-r from-blue-600 to-indigo-600 text-white flex items-center justify-between">
          <div className="flex items-center space-x-2">
            <ShieldCheck className="w-6 h-6" />
            <h3 className="font-bold text-lg">Human-in-the-Loop AI Evaluation</h3>
          </div>
          <button
            onClick={onClose}
            className="p-1 rounded-lg hover:bg-white/20 transition-colors"
          >
            <X className="w-5 h-5" />
          </button>
        </div>

        {/* Form Body */}
        <form onSubmit={handleSubmit} className="p-6 space-y-5">
          {error && (
            <div className="p-3 bg-red-50 dark:bg-red-950/40 text-red-700 dark:text-red-400 rounded-xl flex items-center space-x-2 text-sm">
              <AlertCircle className="w-4 h-4 flex-shrink-0" />
              <span>{error}</span>
            </div>
          )}

          {success && (
            <div className="p-3 bg-emerald-50 dark:bg-emerald-950/40 text-emerald-700 dark:text-emerald-400 rounded-xl flex items-center space-x-2 text-sm">
              <CheckCircle className="w-4 h-4 flex-shrink-0" />
              <span>Human verification recorded successfully!</span>
            </div>
          )}

          <div className="bg-slate-50 dark:bg-slate-800/50 p-3 rounded-xl flex items-center justify-between text-sm">
            <div>
              <span className="text-slate-500">Applicant: </span>
              <span className="font-semibold text-slate-800 dark:text-slate-200">
                {application?.candidate_name || `Candidate #${application?.id}`}
              </span>
            </div>
            <div className="flex items-center space-x-1">
              <span className="text-slate-500">Composite: </span>
              <span className="font-bold text-blue-600 dark:text-blue-400 text-base">
                {compositeScore} / 5.0
              </span>
            </div>
          </div>

          {/* 4 Likert Dimensions */}
          <div className="space-y-3">
            {CRITERIA.map(({ key, label, description }) => (
              <div
                key={key}
                className="flex items-center justify-between p-3 rounded-xl border border-slate-100 dark:border-slate-800/80 hover:bg-slate-50/50 dark:hover:bg-slate-800/30 transition-colors"
              >
                <div>
                  <p className="text-sm font-semibold text-slate-800 dark:text-slate-200">
                    {label}
                  </p>
                  <p className="text-xs text-slate-500 dark:text-slate-400">{description}</p>
                </div>
                <div className="flex items-center space-x-1">
                  {[1, 2, 3, 4, 5].map((star) => (
                    <button
                      key={star}
                      type="button"
                      onClick={() => handleRatingChange(key, star)}
                      className="p-1 focus:outline-none transition-transform hover:scale-110"
                    >
                      <Star
                        className={`w-5 h-5 ${
                          star <= ratings[key]
                            ? 'text-amber-400 fill-amber-400'
                            : 'text-slate-300 dark:text-slate-600'
                        }`}
                      />
                    </button>
                  ))}
                </div>
              </div>
            ))}
          </div>

          {/* Decision Alignment / Override */}
          <div className="space-y-1.5">
            <label className="text-xs font-semibold uppercase text-slate-500 tracking-wider">
              Recruiter Decision Alignment
            </label>
            <select
              value={decisionOverride}
              onChange={(e) => setDecisionOverride(e.target.value)}
              className="w-full px-3 py-2 text-sm rounded-xl border border-slate-200 dark:border-slate-700 bg-white dark:bg-slate-800 text-slate-900 dark:text-slate-100 focus:ring-2 focus:ring-blue-500"
            >
              <option value="agreed">Agreed with AI Recommendation</option>
              <option value="overridden_pass">Override: Manually Advance to Next Round</option>
              <option value="overridden_reject">Override: Manually Reject Applicant</option>
            </select>
          </div>

          {/* Notes */}
          <div className="space-y-1.5">
            <label className="text-xs font-semibold uppercase text-slate-500 tracking-wider">
              Auditor Feedback Notes (Optional)
            </label>
            <textarea
              rows={2}
              value={feedbackNotes}
              onChange={(e) => setFeedbackNotes(e.target.value)}
              placeholder="e.g., Confirmed candidate's FastAPI depth and Redis caching claims."
              className="w-full px-3 py-2 text-sm rounded-xl border border-slate-200 dark:border-slate-700 bg-white dark:bg-slate-800 text-slate-900 dark:text-slate-100 focus:ring-2 focus:ring-blue-500"
            />
          </div>

          {/* Action Buttons */}
          <div className="pt-2 flex items-center justify-end space-x-3">
            <button
              type="button"
              onClick={onClose}
              className="px-4 py-2 text-sm font-medium text-slate-600 dark:text-slate-300 hover:bg-slate-100 dark:hover:bg-slate-800 rounded-xl transition-colors"
            >
              Cancel
            </button>
            <button
              type="submit"
              disabled={loading}
              className="px-5 py-2 text-sm font-semibold text-white bg-blue-600 hover:bg-blue-700 rounded-xl shadow-md hover:shadow-lg transition-all flex items-center space-x-1.5 disabled:opacity-50"
            >
              <ThumbsUp className="w-4 h-4" />
              <span>{loading ? 'Submitting...' : 'Submit Evaluation'}</span>
            </button>
          </div>
        </form>
      </div>
    </div>
  );
}

