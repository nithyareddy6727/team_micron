import { motion } from 'framer-motion'
import { AlertCircle, ArrowRight, Check, CheckCircle2, Copy, HelpCircle, ShieldAlert, ShieldCheck, Sparkles, TrendingUp, Zap } from 'lucide-react'
import { Card } from '@/components/ui/Card'
import { formatPercent } from '@/utils/formatters'
import { useAppStore } from '@/hooks/useAppStore'

const sectorFeatureLabels = {
  saas: {
    monthly_charges: 'Subscription Cost (MRR)',
    monthly_charge: 'Subscription Cost (MRR)',
    tenure: 'Account Maturity / Tenure',
    tenure_in_months: 'Account Maturity / Tenure',
    contract_type: 'Commitment Plan',
    contract: 'Commitment Plan',
    internet_service: 'Cloud Add-on Services',
    payment_method: 'Billing Method',
    satisfaction_score: 'NPS / Satisfaction Score',
    age: 'Account Age',
  },
  consumer: {
    monthly_charges: 'Monthly Spend / Membership Fee',
    monthly_charge: 'Monthly Spend / Membership Fee',
    tenure: 'Membership Duration',
    tenure_in_months: 'Membership Duration',
    contract_type: 'Membership Plan',
    contract: 'Membership Plan',
    internet_service: 'Service Add-on Tier',
    payment_method: 'Payment Setup',
    satisfaction_score: 'Engagement & Rating',
    age: 'Member Age',
  },
  telecom: {
    monthly_charges: 'Monthly Bill',
    monthly_charge: 'Monthly Bill',
    tenure: 'Customer Tenure',
    tenure_in_months: 'Customer Tenure',
    contract_type: 'Contract Term',
    contract: 'Contract Term',
    internet_service: 'Internet Service Type',
    payment_method: 'Payment Method',
    satisfaction_score: 'Customer Satisfaction Score',
    age: 'Subscriber Age',
  },
}

function getFeatureLabel(feature, sector = 'telecom') {
  const raw = typeof feature === 'string' ? feature : feature?.feature || feature?.name || ''
  if (!raw || /^(feature_?\d+|longitude|latitude|zip_code)$/i.test(raw)) return null
  const labels = sectorFeatureLabels[sector] || sectorFeatureLabels.telecom
  return labels[raw] || raw.replace(/_/g, ' ').replace(/\b\w/g, (c) => c.toUpperCase())
}

export function PredictionOutputCard({ latestPrediction, getRiskColor, copyOutput, copiedOutput }) {
  const activeSector = useAppStore((state) => state.sector) || 'telecom'

  if (!latestPrediction) {
    return (
      <Card title="Prediction Output" subtitle="A clear, business-friendly report will appear here.">
        <div className="rounded-2xl bg-slate-50 p-8 text-center dark:bg-slate-800/50">
          <Sparkles className="mx-auto mb-3 text-[#0A84FF]" size={28} />
          <p className="text-base font-semibold text-[#1D1D1F] dark:text-white">Awaiting Customer Input</p>
          <p className="mt-1 text-sm text-[#69708b] dark:text-slate-400">
            Complete the guided prediction flow to view risk segmentation, SHAP feature drivers, and retention recommendations.
          </p>
        </div>
      </Card>
    )
  }

  const prob = Number(latestPrediction.probability || 0)
  const isChurn = Number(latestPrediction.prediction) === 1 || prob >= 0.5
  const riskTier = prob >= 0.7 ? 'High' : prob >= 0.3 ? 'Medium' : 'Low'
  const sector = latestPrediction.sector || activeSector

  const riskStyles = {
    High: {
      cardBg: 'from-rose-500/15 via-rose-500/5 to-transparent border-rose-200 dark:border-rose-900/50',
      badgeBg: 'bg-rose-500 text-white',
      badgeLight: 'bg-rose-100 text-rose-700 dark:bg-rose-950/60 dark:text-rose-300',
      barColor: 'bg-rose-500',
      icon: ShieldAlert,
      tag: 'CRITICAL ATTENTION REQUIRED',
    },
    Medium: {
      cardBg: 'from-amber-500/15 via-amber-500/5 to-transparent border-amber-200 dark:border-amber-900/50',
      badgeBg: 'bg-amber-500 text-white',
      badgeLight: 'bg-amber-100 text-amber-800 dark:bg-amber-950/60 dark:text-amber-300',
      barColor: 'bg-amber-500',
      icon: AlertCircle,
      tag: 'MODERATE RETENTION RISK',
    },
    Low: {
      cardBg: 'from-emerald-500/15 via-emerald-500/5 to-transparent border-emerald-200 dark:border-emerald-900/50',
      badgeBg: 'bg-emerald-500 text-white',
      badgeLight: 'bg-emerald-100 text-emerald-800 dark:bg-emerald-950/60 dark:text-emerald-300',
      barColor: 'bg-emerald-500',
      icon: ShieldCheck,
      tag: 'HEALTHY / LOYAL PROFILE',
    },
  }[riskTier]

  const RiskIcon = riskStyles.icon
  const namedFeatures = (latestPrediction.topFeatures || [])
    .map((f) => getFeatureLabel(f, sector))
    .filter(Boolean)
    .slice(0, 4)

  const recommendations = (latestPrediction.recommendations && latestPrediction.recommendations.length > 0)
    ? latestPrediction.recommendations
    : [
        'Engage customer before the upcoming billing cycle.',
        'Review recent account activity and confirm service satisfaction.',
        'Offer targeted loyalty or renewal incentive.',
      ]

  const sectorName = sector === 'saas' ? 'SaaS / Cloud' : sector === 'consumer' ? 'Consumer / Digital' : 'Telecom'

  return (
    <Card title="Prediction & Retention Intelligence" subtitle={`Analyzed under ${sectorName} sector profile`}>
      <motion.div
        className="space-y-5"
        initial={{ opacity: 0, y: 12 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ duration: 0.3 }}
      >
        {/* Core Decision Header Card */}
        <div className={`rounded-3xl border bg-gradient-to-br p-6 shadow-sm ${riskStyles.cardBg}`}>
          <div className="flex flex-wrap items-center justify-between gap-3">
            <span className="inline-flex items-center gap-1.5 rounded-full bg-slate-900/10 px-3 py-1 text-xs font-bold tracking-wider text-slate-800 dark:bg-white/10 dark:text-slate-200">
              <RiskIcon size={14} /> {riskStyles.tag}
            </span>
            <span className="text-xs font-medium text-slate-500 dark:text-slate-400">
              Sector: <strong className="text-slate-800 dark:text-slate-200">{sectorName}</strong>
            </span>
          </div>

          <div className="mt-4 grid gap-4 sm:grid-cols-2">
            {/* Churn Classification */}
            <div>
              <p className="text-xs font-semibold uppercase tracking-wider text-slate-500 dark:text-slate-400">
                Churn Classification
              </p>
              <div className="mt-1 flex items-center gap-2">
                <span className={`rounded-xl px-4 py-2 text-xl font-bold tracking-tight shadow-sm ${
                  isChurn ? 'bg-rose-600 text-white' : 'bg-emerald-600 text-white'
                }`}>
                  {isChurn ? 'LIKELY TO CHURN' : 'LIKELY TO STAY'}
                </span>
              </div>
              <p className="mt-2 text-sm text-slate-600 dark:text-slate-300">
                {isChurn
                  ? 'High probability of subscription abandonment without retention action.'
                  : 'Customer demonstrates solid loyalty markers; risk of departure is minimal.'}
              </p>
            </div>

            {/* Probability & Risk Segment */}
            <div className="rounded-2xl bg-white/70 p-4 dark:bg-slate-900/60">
              <div className="flex items-center justify-between">
                <p className="text-xs font-semibold uppercase tracking-wider text-slate-500 dark:text-slate-400">
                  Churn Probability
                </p>
                <span className={`rounded-full px-2.5 py-0.5 text-xs font-bold ${riskStyles.badgeLight}`}>
                  {riskTier.toUpperCase()} RISK
                </span>
              </div>
              <p className="mt-1 text-3xl font-extrabold text-[#1D1D1F] dark:text-white">
                {(prob * 100).toFixed(1)}%
              </p>
              {/* Visual Progress Bar */}
              <div className="mt-2 h-2.5 w-full overflow-hidden rounded-full bg-slate-200 dark:bg-slate-700">
                <div
                  className={`h-full rounded-full transition-all duration-700 ${riskStyles.barColor}`}
                  style={{ width: `${Math.min(100, Math.max(5, prob * 100))}%` }}
                />
              </div>
              <p className="mt-2 text-xs text-slate-500 dark:text-slate-400">
                Risk segmented into: Low (&lt;30%), Medium (30–70%), High (≥70%)
              </p>
            </div>
          </div>

          {/* Primary Driver Banner */}
          {latestPrediction.primaryDriver ? (
            <div className="mt-4 flex items-center gap-2 rounded-xl bg-white/90 px-4 py-2.5 text-sm font-medium text-slate-800 shadow-sm dark:bg-slate-900/90 dark:text-slate-200">
              <Zap size={16} className="text-amber-500" />
              <span>Primary Risk Driver:</span>
              <strong className="text-[#0A84FF]">{latestPrediction.primaryDriver}</strong>
            </div>
          ) : null}
        </div>

        {/* Explainability Section: WHY is this customer at risk? */}
        <div className="rounded-2xl border border-[#dce6fa] bg-white/85 p-5 dark:border-slate-700 dark:bg-slate-900/85">
          <div className="flex items-center gap-2 text-base font-bold text-[#1D1D1F] dark:text-white">
            <HelpCircle size={18} className="text-[#0A84FF]" />
            <h3>Why is this customer at risk? (SHAP Key Factors)</h3>
          </div>
          <p className="mt-1 text-sm text-[#4e5875] dark:text-slate-300">
            {latestPrediction.explanationText || 'The model evaluated key behavioral indicators relative to historical retention benchmarks:'}
          </p>

          {namedFeatures.length > 0 ? (
            <div className="mt-3 grid gap-2 sm:grid-cols-2">
              {namedFeatures.map((name, i) => (
                <div key={name} className="flex items-center gap-2.5 rounded-xl bg-slate-50 px-3.5 py-2.5 text-sm font-medium text-slate-800 dark:bg-slate-800/70 dark:text-slate-200">
                  <span className="flex h-6 w-6 shrink-0 items-center justify-center rounded-full bg-blue-100 text-xs font-bold text-[#0A84FF] dark:bg-blue-950">
                    {i + 1}
                  </span>
                  <span>{name}</span>
                </div>
              ))}
            </div>
          ) : (
            <p className="mt-2 text-xs text-slate-500">
              Evaluated across tenure, contract commitment, billing levels, and service add-on adoption.
            </p>
          )}
        </div>

        {/* Retention Recommendations Agent Section: WHAT SHOULD WE DO? */}
        <div className="rounded-2xl border border-emerald-200 bg-gradient-to-br from-emerald-50 to-teal-50/40 p-5 dark:border-emerald-900 dark:from-emerald-950/40 dark:to-slate-900">
          <div className="flex items-center justify-between">
            <div className="flex items-center gap-2">
              <Sparkles size={18} className="text-emerald-600 dark:text-emerald-400" />
              <h3 className="text-base font-bold text-emerald-950 dark:text-emerald-100">
                Retention Recommendations Agent
              </h3>
            </div>
            <span className="rounded-full bg-emerald-200/60 px-2.5 py-0.5 text-xs font-semibold text-emerald-800 dark:bg-emerald-900 dark:text-emerald-200">
              Evidence-Driven Plays
            </span>
          </div>
          <p className="mt-1 text-xs text-emerald-800/80 dark:text-emerald-300/80">
            Tailored retention strategies generated from risk drivers under the {sectorName} profile:
          </p>

          <ul className="mt-3 space-y-2">
            {recommendations.map((rec, i) => (
              <motion.li
                key={rec}
                initial={{ opacity: 0, x: -6 }}
                animate={{ opacity: 1, x: 0 }}
                transition={{ delay: i * 0.08 }}
                className="flex items-start gap-3 rounded-xl bg-white/90 p-3 text-sm text-slate-800 shadow-sm dark:bg-slate-900/90 dark:text-slate-200"
              >
                <CheckCircle2 size={18} className="mt-0.5 shrink-0 text-emerald-600 dark:text-emerald-400" />
                <span className="font-medium">{rec}</span>
              </motion.li>
            ))}
          </ul>
        </div>

        {/* Latency & Confidence Footer */}
        <div className="grid grid-cols-2 gap-3 text-sm">
          <div className="rounded-2xl bg-white/85 p-3 dark:bg-slate-900/85">
            <p className="text-xs text-[#69708b] dark:text-slate-400">AI Confidence Score</p>
            <p className="mt-0.5 text-lg font-bold text-[#1D1D1F] dark:text-white">
              {formatPercent(latestPrediction.confidence)}
            </p>
          </div>
          <div className="rounded-2xl bg-white/85 p-3 dark:bg-slate-900/85">
            <p className="text-xs text-[#69708b] dark:text-slate-400">Inference Response Time</p>
            <p className="mt-0.5 text-lg font-bold text-[#1D1D1F] dark:text-white">
              {Number(latestPrediction.latencyMs || 0).toFixed(1)} ms
            </p>
          </div>
        </div>

        {/* Copy Action Button */}
        <button
          onClick={copyOutput}
          className="flex w-full items-center justify-center gap-2 rounded-xl bg-slate-100 py-3 text-sm font-semibold text-slate-700 transition hover:bg-slate-200 dark:bg-slate-800 dark:text-slate-300 dark:hover:bg-slate-700"
        >
          {copiedOutput ? (
            <>
              <Check size={16} className="text-emerald-600" /> Copied Prediction &amp; Actions
            </>
          ) : (
            <>
              <Copy size={16} /> Copy Prediction &amp; Recommended Actions
            </>
          )}
        </button>
      </motion.div>
    </Card>
  )
}
