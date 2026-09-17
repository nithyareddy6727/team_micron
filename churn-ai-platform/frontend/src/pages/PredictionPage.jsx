import { useEffect, useMemo, useState } from 'react'
import { useMutation, useQuery } from '@tanstack/react-query'
import { motion } from 'framer-motion'
import { ArrowLeft, ArrowRight, BrainCircuit, CheckCircle2, CreditCard, Landmark, Mail, ReceiptText, Search, ShieldCheck, Sparkles, UserPlus, Users, Zap } from 'lucide-react'
import { Card } from '@/components/ui/Card'
import { Button } from '@/components/ui/Button'
import { Input } from '@/components/ui/Input'
import { PredictionOutputCard } from '@/components/Prediction/PredictionOutputCard'
import { BatchPredictionCard } from '@/components/Prediction/BatchPredictionCard'
import { getCustomers } from '@/services/analyticsService'
import { getBatchJobStatus, predict, uploadBatchCsv } from '@/services/predictionService'
import { useAppStore } from '@/hooks/useAppStore'
import { normalizePredictionPayload } from '@/utils/formatters'

const blank = { customer_id: '', age: '', tenure: '', monthly_charges: '', contract_type: '', internet_service: '', payment_method: '' }

function getSectorQuestions(sector) {
  if (sector === 'saas') {
    return [
      { key: 'age', title: 'Organization Maturity', detail: 'How many years has the client organization been operating?', placeholder: '4', type: 'number', hint: 'Years in operation (e.g. 1 to 50)', valid: (v) => Number(v) >= 0 && Number(v) <= 100, error: 'Please enter a valid number of years.' },
      { key: 'tenure', title: 'Subscription Tenure', detail: 'How many months has this account subscribed to the software?', placeholder: '6', type: 'number', hint: 'Months subscribed (under 6 months is high onboarding risk)', valid: (v) => Number(v) >= 0, error: 'Please enter the number of months.' },
      { key: 'monthly_charges', title: 'Monthly Recurring Revenue (MRR)', detail: 'Enter the monthly subscription fee ($) paid by this account.', placeholder: '149', type: 'number', hint: 'Enter subscription amount ($10 – $5,000)', valid: (v) => Number(v) >= 0, error: 'Please enter a valid monthly subscription amount.' },
      { key: 'contract_type', title: 'Subscription Commitment Tier', detail: 'Long-term contracts significantly lower churn risk.', options: [['Month-to-month', 'Monthly Flexible', 'Highest cancellation risk'], ['One year', 'Annual Plan', 'Standard commitment'], ['Two year', 'Multi-Year Enterprise', 'Highest retention']] },
      { key: 'internet_service', title: 'Cloud & Platform Add-on Level', detail: 'Select the platform integration and service tier.', options: [['Fiber optic', 'Enterprise Cloud Tier', 'Full API & dedicated compute'], ['DSL', 'Standard Cloud Suite', 'Core productivity tools'], ['No', 'Basic Seat Only', 'Limited integration']] },
      { key: 'payment_method', title: 'B2B Payment Method', detail: 'Automated card/ACH billing reduces involuntary churn.', options: [['Credit card', 'Corporate Card', 'Automated card billing', CreditCard], ['Bank transfer', 'ACH Direct Debit', 'Automated bank clearing', Landmark], ['Electronic check', 'Automated e-Invoice', 'Online invoice portal', ReceiptText], ['Mailed check', 'Manual Purchase Order', 'Manual payment follow-up', Mail]] },
    ]
  }

  if (sector === 'consumer') {
    return [
      { key: 'age', title: 'Member / Consumer Age', detail: 'Helps personalize engagement recommendations.', placeholder: '28', type: 'number', hint: 'Age between 18 and 100', valid: (v) => Number(v) >= 18 && Number(v) <= 100, error: 'Please enter a valid age.' },
      { key: 'tenure', title: 'Active Membership Duration', detail: 'How many months has this consumer been a member?', placeholder: '4', type: 'number', hint: 'Months subscribed (under 3 months is high drop-off window)', valid: (v) => Number(v) >= 0, error: 'Please enter active membership months.' },
      { key: 'monthly_charges', title: 'Monthly Spend / Membership Fee', detail: 'Average monthly billing or recurring orders in $.', placeholder: '39', type: 'number', hint: 'Monthly spend amount in $', valid: (v) => Number(v) >= 0, error: 'Please enter a valid monthly amount.' },
      { key: 'contract_type', title: 'Membership Plan Tier', detail: 'Annual pass members form stronger habits.', options: [['Month-to-month', 'Monthly Pass', 'Flexible monthly renewal'], ['One year', 'Annual VIP Pass', '1-year commitment'], ['Two year', 'Multi-Year Pass', 'Longest commitment']] },
      { key: 'internet_service', title: 'Digital Content & Streaming Tier', detail: 'Access tier for streaming or member perks.', options: [['Fiber optic', 'Premium Multi-Device / Ultra', 'Full access & family tier'], ['DSL', 'Standard Digital Tier', 'Regular streaming/shopping'], ['No', 'Basic Single-User Tier', 'Standard features only']] },
      { key: 'payment_method', title: 'Payment Method on Record', detail: 'Digital auto-renew reduces payment friction.', options: [['Credit card', 'Credit / Debit Card', 'Auto-renew enabled', CreditCard], ['Bank transfer', 'Direct Bank / Wallet', 'Linked bank account', Landmark], ['Electronic check', 'Digital Wallet', 'Instant digital checkout', ReceiptText], ['Mailed check', 'Prepaid Voucher', 'Requires manual reload', Mail]] },
    ]
  }

  // Telecom default
  return [
    { key: 'age', title: 'Subscriber Age', detail: 'Age profile helps categorize communication preferences.', placeholder: '35', type: 'number', hint: 'Enter a value from 18 to 100.', valid: (v) => Number(v) >= 18 && Number(v) <= 100, error: 'Please enter an age between 18 and 100.' },
    { key: 'tenure', title: 'Tenure with Provider', detail: 'Customers with short tenure generally exhibit higher churn propensity.', placeholder: '24', type: 'number', hint: 'Months with provider (12 = 1 year, 24 = 2 years)', valid: (v) => Number(v) >= 0, error: 'Please enter the number of months.' },
    { key: 'monthly_charges', title: 'Average Monthly Bill', detail: 'Enter the average monthly bill paid by the subscriber ($).', placeholder: '75', type: 'number', hint: 'Enter monthly bill in $', valid: (v) => Number(v) >= 0, error: 'Please enter a valid monthly bill.' },
    { key: 'contract_type', title: 'Contract Agreement Term', detail: 'Longer contract terms significantly improve retention.', options: [['Month-to-month', 'Month-to-month', 'Flexible plan, higher churn'], ['One year', 'One Year Agreement', 'Medium commitment'], ['Two year', 'Two Year Agreement', 'Highest commitment']] },
    { key: 'internet_service', title: 'Broadband / Internet Technology', detail: 'Choose the internet service plan actively used.', options: [['Fiber optic', 'Fiber Optic High-Speed', 'Gigabit fiber connection'], ['DSL', 'DSL Broadband', 'Traditional broadband connection'], ['No', 'No Internet Service', 'Voice-only plan']] },
    { key: 'payment_method', title: 'Billing & Payment Setup', detail: 'Electronic auto-pay reduces payment friction.', options: [['Credit card', 'Credit Card (Auto-pay)', 'Automatic card payment', CreditCard], ['Bank transfer', 'Bank Transfer (Auto-pay)', 'Direct automated transfer', Landmark], ['Electronic check', 'Electronic Check', 'Online check payment', ReceiptText], ['Mailed check', 'Mailed Paper Check', 'Manual paper check', Mail]] },
  ]
}

function Progress({ step, total }) {
  const pct = Math.round((step / total) * 100)
  return (
    <div className="mb-6">
      <div className="flex justify-between text-sm font-medium text-[#4e5875] dark:text-slate-300">
        <span>Step {step} of {total}</span>
        <span>{pct}% complete</span>
      </div>
      <div className="mt-2 h-2 overflow-hidden rounded-full bg-slate-200 dark:bg-slate-700">
        <motion.div className="h-full rounded-full bg-gradient-to-r from-[#0A84FF] to-[#5E5CE6]" animate={{ width: `${pct}%` }} />
      </div>
    </div>
  )
}

function Insight({ form, sector }) {
  const notes = []
  const cur = '$'
  if (form.age) notes.push(`Age/Maturity = ${form.age}. Profile signals align with baseline risk benchmarks.`)
  if (Number(form.tenure) > 0 && Number(form.tenure) <= 6) notes.push(`Tenure = ${form.tenure} months. This customer is in the early lifecycle window, which historically has higher churn risk.`)
  if (Number(form.monthly_charges) >= 80) notes.push(`Monthly fee = ${cur}${form.monthly_charges}. Higher recurring cost increases churn sensitivity unless clear value is recognized.`)
  if (form.contract_type === 'Month-to-month') notes.push('Month-to-month is flexible, but it carries higher churn than annual commitments.')

  return (
    <aside className="rounded-3xl border border-blue-100 bg-gradient-to-br from-blue-50 to-indigo-50 p-5 dark:border-blue-900/60 dark:from-blue-950/40 dark:to-indigo-950/30">
      <p className="flex items-center gap-2 font-semibold text-[#1D1D1F] dark:text-white">
        <BrainCircuit size={18} className="text-[#0A84FF]" />AI Retention Copilot
      </p>
      <p className="mt-2 text-sm text-[#4e5875] dark:text-slate-300">
        Sector: <strong className="capitalize">{sector}</strong>. Real-time feedback updates as fields are entered:
      </p>
      {notes.length ? (
        <div className="mt-4 space-y-3">
          {notes.map((note) => (
            <p key={note} className="rounded-xl bg-white/85 p-3 text-sm text-[#39405a] shadow-sm dark:bg-slate-900/70 dark:text-slate-200">
              {note}
            </p>
          ))}
        </div>
      ) : (
        <p className="mt-4 rounded-xl bg-white/85 p-3 text-sm text-[#39405a] dark:bg-slate-900/70 dark:text-slate-200">
          Select existing record or start a guided prediction to evaluate churn probability and retention actions.
        </p>
      )}
    </aside>
  )
}

export default function PredictionPage() {
  const [screen, setScreen] = useState('welcome')
  const [mode, setMode] = useState('')
  const [step, setStep] = useState(0)
  const [form, setForm] = useState(blank)
  const [existingId, setExistingId] = useState('')
  const [error, setError] = useState('')
  const [copied, setCopied] = useState(false)
  const [batchFile, setBatchFile] = useState(null)
  const [batchJobId, setBatchJobId] = useState('')
  const [batchStatus, setBatchStatus] = useState(null)
  const [batchError, setBatchError] = useState('')

  const sector = useAppStore((state) => state.sector) || 'telecom'
  const setSector = useAppStore((state) => state.setSector)
  const setLatestPrediction = useAppStore((state) => state.setLatestPrediction)
  const latestPrediction = useAppStore((state) => state.latestPrediction)

  const customersQuery = useQuery({ queryKey: ['prediction-customers'], queryFn: () => getCustomers(''), staleTime: 60_000 })
  const customers = useMemo(() => customersQuery.data?.customers || [], [customersQuery.data])
  const selectedId = existingId || customers[0]?.customer_id || ''
  const customer = customers.find((item) => item.customer_id === selectedId)

  const prediction = useMutation({
    mutationFn: predict,
    onSuccess: (data) => {
      setLatestPrediction({ ...normalizePredictionPayload(data), timestamp: new Date().toISOString(), sector })
      setScreen('result')
      setError('')
    },
    onError: (err) => {
      setError(err.message)
      setScreen(mode === 'new' ? 'wizard' : 'existing')
    },
  })

  const batchUpload = useMutation({
    mutationFn: (file) => uploadBatchCsv(file, { returnProba: true, explain: true, sector }),
    onSuccess: (data) => {
      setBatchJobId(data.job_id)
      setBatchError('')
    },
    onError: () => setBatchError("We couldn't upload this file right now. Please check that it is a CSV and try again."),
  })

  useEffect(() => {
    if (!batchJobId) return undefined
    let active = true
    const check = async () => {
      try {
        const status = await getBatchJobStatus(batchJobId)
        if (active) setBatchStatus(status)
      } catch {
        if (active) setBatchError("We couldn't retrieve the batch status. Please try again in a few moments.")
      }
    }
    check()
    const timer = setInterval(check, 1500)
    return () => {
      active = false
      clearInterval(timer)
    }
  }, [batchJobId])

  const setValue = (key, value) => {
    setForm((current) => ({ ...current, [key]: value }))
    setError('')
  }

  const analyze = (payload) => {
    setScreen('analyzing')
    prediction.mutate({ ...payload, sector })
  }

  const quickAnalyze = () => {
    if (!selectedId) return setError('Please wait for a customer to load, then try again.')
    analyze({ customer_id: selectedId })
  }

  // Pre-configured hackathon demo presets
  const triggerDemoPreset = (type) => {
    if (type === 'high-risk-saas') {
      setSector('saas')
      analyze({
        customer_id: 'DEMO-SAAS-01',
        age: 2,
        tenure: 3,
        monthly_charges: 189,
        contract_type: 'Month-to-month',
        internet_service: 'Fiber optic',
        payment_method: 'Credit card',
        sector: 'saas',
      })
    } else if (type === 'high-risk-telecom') {
      setSector('telecom')
      analyze({
        customer_id: 'DEMO-TELCO-01',
        age: 45,
        tenure: 2,
        monthly_charges: 95,
        contract_type: 'Month-to-month',
        internet_service: 'Fiber optic',
        payment_method: 'Electronic check',
        sector: 'telecom',
      })
    } else {
      setSector('consumer')
      analyze({
        customer_id: 'DEMO-LOYAL-01',
        age: 38,
        tenure: 48,
        monthly_charges: 29,
        contract_type: 'Two year',
        internet_service: 'DSL',
        payment_method: 'Credit card',
        sector: 'consumer',
      })
    }
  }

  const currentQuestions = getSectorQuestions(sector)
  const current = currentQuestions[step] || currentQuestions[0]

  const next = () => {
    if (current.options ? !form[current.key] : !current.valid(form[current.key])) {
      return setError(current.error || 'Please complete this question before continuing.')
    }
    setError('')
    setStep((value) => value + 1)
  }

  const copyOutput = () => {
    const text = `Customer Churn Analysis
Prediction: ${latestPrediction?.predictionLabel || (latestPrediction?.prediction === 1 ? 'Likely to Churn' : 'Likely to Stay')}
Churn Probability: ${(Number(latestPrediction?.probability || 0) * 100).toFixed(1)}%
Risk Level: ${latestPrediction?.risk || 'Low'}
Primary Driver: ${latestPrediction?.primaryDriver || 'General Usage'}
Recommended Action: ${latestPrediction?.recommendations?.[0] || 'Schedule proactive follow-up'}`
    navigator.clipboard.writeText(text)
    setCopied(true)
    setTimeout(() => setCopied(false), 1500)
  }

  const risk = (p) =>
    Number(p) >= 0.7
      ? { bg: 'bg-rose-500/20', text: 'text-rose-700', label: 'High Risk' }
      : Number(p) >= 0.3
      ? { bg: 'bg-amber-500/20', text: 'text-amber-700', label: 'Medium Risk' }
      : { bg: 'bg-emerald-500/20', text: 'text-emerald-700', label: 'Low Risk' }

  if (screen === 'analyzing') {
    return (
      <div className="mx-auto flex min-h-[65vh] max-w-2xl items-center">
        <Card className="w-full">
          <motion.div initial={{ opacity: 0 }} animate={{ opacity: 1 }} className="p-6 text-center">
            <div className="mx-auto flex h-16 w-16 items-center justify-center rounded-full bg-blue-100 text-[#0A84FF] dark:bg-blue-950">
              <BrainCircuit size={32} />
            </div>
            <h2 className="mt-5 text-2xl font-bold text-[#1D1D1F] dark:text-white">Analyzing customer profile...</h2>
            <p className="mt-2 text-sm text-[#69708b] dark:text-slate-300">
              Mapping attributes to {sector.toUpperCase()} retention intelligence engine.
            </p>
            <div className="mx-auto mt-7 max-w-md space-y-2.5 text-left">
              {[
                'Standardizing customer features',
                'Executing ML inference & calibration',
                'Extracting SHAP feature impact drivers',
                'Segmenting customer risk tier (Low / Medium / High)',
                'Generating evidence-driven retention plays',
              ].map((text, index) => (
                <motion.p
                  key={text}
                  animate={{ opacity: [0.35, 1, 0.55] }}
                  transition={{ duration: 1.2, repeat: Infinity, delay: index * 0.14 }}
                  className="flex items-center gap-3 rounded-xl bg-slate-50 px-4 py-2.5 text-sm text-[#39405a] dark:bg-slate-800 dark:text-slate-200"
                >
                  <CheckCircle2 size={17} className="text-emerald-500" />
                  {text}
                </motion.p>
              ))}
            </div>
          </motion.div>
        </Card>
      </div>
    )
  }

  if (screen === 'result') {
    return (
      <div className="mx-auto max-w-4xl space-y-4">
        <button
          onClick={() => {
            setScreen('welcome')
            setMode('')
            setStep(0)
            setForm(blank)
          }}
          className="flex items-center gap-2 text-sm font-semibold text-[#4e5875] hover:text-[#0A84FF]"
        >
          <ArrowLeft size={16} /> Start another prediction
        </button>
        <PredictionOutputCard
          latestPrediction={latestPrediction}
          getRiskColor={risk}
          copyOutput={copyOutput}
          copiedOutput={copied}
        />
      </div>
    )
  }

  if (screen === 'welcome') {
    return (
      <div className="mx-auto max-w-4xl space-y-5">
        <Card>
          <div className="grid gap-8 p-4 md:grid-cols-[1.25fr_.75fr]">
            <div>
              <span className="inline-flex rounded-full bg-blue-50 px-3 py-1 text-xs font-bold uppercase tracking-wider text-[#0A84FF] dark:bg-blue-950/40">
                Customer Churn Prediction Agent
              </span>
              <h1 className="mt-4 text-3xl font-extrabold tracking-tight text-[#1D1D1F] dark:text-white">
                Predict &amp; Retain Customers <span role="img" aria-label="wave">👋</span>
              </h1>
              <p className="mt-3 max-w-xl text-base leading-relaxed text-[#4e5875] dark:text-slate-300">
                A domain-aware AI copilot that predicts churn risk, identifies SHAP drivers, and recommends tailored retention actions.
              </p>

              {/* Sector Switcher on Welcome */}
              <div className="mt-5 rounded-2xl border border-slate-200/80 bg-slate-50/80 p-3.5 dark:border-slate-800 dark:bg-slate-900/60">
                <p className="text-xs font-bold uppercase tracking-wider text-[#5f6475] dark:text-slate-400">
                  Select Business Sector Profile:
                </p>
                <div className="mt-2 flex flex-wrap gap-2">
                  {[
                    { id: 'saas', label: 'SaaS / Cloud', icon: '💻' },
                    { id: 'telecom', label: 'Telecom', icon: '📡' },
                    { id: 'consumer', label: 'Consumer / Digital', icon: '🛍️' },
                  ].map((s) => (
                    <button
                      key={s.id}
                      onClick={() => setSector(s.id)}
                      className={`flex items-center gap-1.5 rounded-xl px-3 py-1.5 text-xs font-semibold transition ${
                        sector === s.id
                          ? 'bg-gradient-to-r from-[#0A84FF] to-[#5E5CE6] text-white shadow-sm'
                          : 'bg-white text-slate-700 hover:bg-slate-200 dark:bg-slate-800 dark:text-slate-300'
                      }`}
                    >
                      <span>{s.icon}</span>
                      <span>{s.label}</span>
                    </button>
                  ))}
                </div>
              </div>

              {/* Demo Quick-Run Presets for Fast Hackathon Evaluation */}
              <div className="mt-4 space-y-2">
                <p className="text-xs font-semibold text-slate-500 dark:text-slate-400">
                  Quick Hackathon Demo Presets:
                </p>
                <div className="flex flex-wrap gap-2">
                  <button
                    onClick={() => triggerDemoPreset('high-risk-saas')}
                    className="inline-flex items-center gap-1.5 rounded-xl border border-rose-200 bg-rose-50 px-3 py-1.5 text-xs font-semibold text-rose-700 transition hover:bg-rose-100 dark:border-rose-900/60 dark:bg-rose-950/40 dark:text-rose-300"
                  >
                    <Zap size={13} /> High-Risk SaaS Account
                  </button>
                  <button
                    onClick={() => triggerDemoPreset('high-risk-telecom')}
                    className="inline-flex items-center gap-1.5 rounded-xl border border-amber-200 bg-amber-50 px-3 py-1.5 text-xs font-semibold text-amber-700 transition hover:bg-amber-100 dark:border-amber-900/60 dark:bg-amber-950/40 dark:text-amber-300"
                  >
                    <Zap size={13} /> High-Risk Telecom Subscriber
                  </button>
                  <button
                    onClick={() => triggerDemoPreset('loyal')}
                    className="inline-flex items-center gap-1.5 rounded-xl border border-emerald-200 bg-emerald-50 px-3 py-1.5 text-xs font-semibold text-emerald-700 transition hover:bg-emerald-100 dark:border-emerald-900/60 dark:bg-emerald-950/40 dark:text-emerald-300"
                  >
                    <ShieldCheck size={13} /> Loyal Customer Profile
                  </button>
                </div>
              </div>

              <div className="mt-6 flex flex-wrap items-center gap-3">
                <Button className="px-6 py-3 text-base" onClick={() => setScreen('choose')}>
                  Start Custom Prediction
                </Button>
                <button
                  onClick={quickAnalyze}
                  className="text-sm font-semibold text-[#0A84FF] underline underline-offset-4 hover:text-[#5E5CE6]"
                >
                  Predict Existing Dataset Customer
                </button>
              </div>
              {error ? <p className="mt-3 text-sm text-rose-600">Prediction error: {error}</p> : null}
            </div>
            <Insight form={form} sector={sector} />
          </div>
        </Card>

        {/* Batch Prediction / CSV Upload */}
        <BatchPredictionCard
          batchFile={batchFile}
          setBatchFile={setBatchFile}
          submitBatch={() => batchUpload.mutate(batchFile)}
          isSubmitting={batchUpload.isPending}
          batchJobId={batchJobId}
          batchStatus={batchStatus}
          batchError={batchError}
        />
      </div>
    )
  }

  if (screen === 'choose') {
    return (
      <div className="mx-auto max-w-4xl">
        <Card title="Customer Profile Source" subtitle={`Predicting under ${sector.toUpperCase()} sector profile`}>
          <div className="grid gap-4 md:grid-cols-2">
            <button
              onClick={() => {
                setMode('existing')
                setScreen('existing')
              }}
              className="rounded-3xl border-2 border-[#dce6fa] bg-white p-6 text-left transition hover:border-[#0A84FF] hover:shadow-lg dark:bg-slate-900"
            >
              <Users className="text-[#0A84FF]" size={28} />
              <h2 className="mt-4 text-xl font-bold text-[#1D1D1F] dark:text-white">Existing Database Record</h2>
              <p className="mt-2 text-sm text-[#4e5875] dark:text-slate-300">
                Select an existing customer from the connected repository.
              </p>
              <span className="mt-5 inline-flex text-sm font-semibold text-[#0A84FF]">
                Select Customer <ArrowRight className="ml-1" size={16} />
              </span>
            </button>

            <button
              onClick={() => {
                setMode('new')
                setScreen('wizard')
                setStep(0)
              }}
              className="rounded-3xl border-2 border-[#dce6fa] bg-white p-6 text-left transition hover:border-[#5E5CE6] hover:shadow-lg dark:bg-slate-900"
            >
              <UserPlus className="text-[#5E5CE6]" size={28} />
              <h2 className="mt-4 text-xl font-bold text-[#1D1D1F] dark:text-white">New Customer Entry</h2>
              <p className="mt-2 text-sm text-[#4e5875] dark:text-slate-300">
                Input fresh metrics to evaluate churn risk on a new account.
              </p>
              <span className="mt-5 inline-flex text-sm font-semibold text-[#5E5CE6]">
                Launch Guided Wizard <ArrowRight className="ml-1" size={16} />
              </span>
            </button>
          </div>
        </Card>
      </div>
    )
  }

  if (screen === 'existing') {
    return (
      <div className="mx-auto grid max-w-5xl gap-4 lg:grid-cols-[1.2fr_.8fr]">
        <Card title="Search Existing Customer" subtitle="Search database records by ID or Name">
          <label className="sr-only" htmlFor="customer-search">
            Search by Customer ID or Customer Name
          </label>
          <div className="relative">
            <Search className="absolute left-4 top-3 text-[#6f7691]" size={18} />
            <Input
              id="customer-search"
              list="customer-list"
              value={selectedId}
              onChange={(event) => setExistingId(event.target.value)}
              placeholder="Search by Customer ID or Name..."
              className="py-3 pl-11 text-base"
            />
            <datalist id="customer-list">
              {customers.slice(0, 100).map((item) => (
                <option key={item.customer_id} value={item.customer_id}>
                  {item.name || item.customer_id}
                </option>
              ))}
            </datalist>
          </div>
          {customer ? (
            <motion.div
              initial={{ opacity: 0, y: 6 }}
              animate={{ opacity: 1, y: 0 }}
              className="mt-5 rounded-3xl border border-emerald-200 bg-emerald-50 p-5 dark:border-emerald-900 dark:bg-emerald-950/30"
            >
              <p className="font-semibold text-emerald-950 dark:text-emerald-100">Customer Profile Found</p>
              <div className="mt-4 flex gap-4">
                <div className="flex h-14 w-14 shrink-0 items-center justify-center rounded-full bg-emerald-200 text-xl font-bold text-emerald-800">
                  {(customer.name || 'C').slice(0, 1)}
                </div>
                <div className="grid flex-1 gap-2 text-sm sm:grid-cols-2">
                  <span>Name: {customer.name || 'Customer profile'}</span>
                  <span>ID: {customer.customer_id}</span>
                  <span>Age: {customer.age ?? '--'}</span>
                  <span>Tenure: {customer.tenure_in_months ?? customer.tenure ?? '--'} mos</span>
                  <span>Monthly Fee: ${customer.monthly_charge ?? customer.monthly_charges ?? '--'}</span>
                  <span>Contract: {customer.contract || customer.contract_type || 'Month-to-month'}</span>
                </div>
              </div>
              <Button className="mt-5" onClick={() => analyze({ customer_id: selectedId })}>
                Run AI Churn Prediction
              </Button>
            </motion.div>
          ) : (
            <div className="mt-5 rounded-2xl bg-amber-50 p-4 text-sm text-amber-900 dark:bg-amber-950/30 dark:text-amber-100">
              Customer not found in database. You can{' '}
              <button
                className="font-semibold underline"
                onClick={() => {
                  setMode('new')
                  setScreen('wizard')
                }}
              >
                enter details manually
              </button>
              .
            </div>
          )}
        </Card>
        <Insight form={form} sector={sector} />
      </div>
    )
  }

  const isReview = step === currentQuestions.length
  return (
    <div className="mx-auto grid max-w-5xl gap-4 lg:grid-cols-[1.2fr_.8fr]">
      <Card>
        <Progress step={Math.min(step + 1, currentQuestions.length + 1)} total={currentQuestions.length + 1} />
        {isReview ? (
          <div>
            <span className="text-xs font-bold uppercase tracking-wider text-[#0A84FF]">
              Step {currentQuestions.length + 1}: Review &amp; Analyze
            </span>
            <h1 className="mt-2 text-2xl font-bold text-[#1D1D1F] dark:text-white">Profile Summary</h1>
            <p className="mt-1 text-sm text-[#4e5875] dark:text-slate-300">
              Review details mapped under {sector.toUpperCase()} profile, then execute prediction:
            </p>
            <div className="mt-5 grid gap-3 sm:grid-cols-2">
              {[
                ['Age / Maturity', form.age || '--'],
                ['Tenure', `${form.tenure || 0} months`],
                ['Monthly Charges / Spend', `$${form.monthly_charges || 0}`],
                ['Contract Tier', form.contract_type || 'Month-to-month'],
                ['Service / Cloud Add-on', form.internet_service || 'Standard'],
                ['Payment Method', form.payment_method || 'Electronic'],
              ].map(([label, value]) => (
                <div key={label} className="rounded-xl bg-slate-50 p-3 text-sm dark:bg-slate-800">
                  <p className="text-xs text-[#69708b]">{label}</p>
                  <p className="mt-1 font-semibold text-[#1D1D1F] dark:text-white">{value}</p>
                </div>
              ))}
            </div>
            <div className="mt-6 flex gap-3">
              <Button variant="ghost" onClick={() => setStep(0)}>
                Edit answers
              </Button>
              <Button
                onClick={() =>
                  analyze({
                    ...form,
                    age: Number(form.age),
                    tenure: Number(form.tenure),
                    monthly_charges: Number(form.monthly_charges),
                  })
                }
              >
                Analyze Customer <ShieldCheck className="ml-1" size={17} />
              </Button>
            </div>
          </div>
        ) : (
          <div>
            <span className="text-xs font-bold uppercase tracking-wider text-[#0A84FF]">
              Question {step + 1} of {currentQuestions.length} ({sector.toUpperCase()})
            </span>
            <h1 className="mt-2 text-2xl font-bold text-[#1D1D1F] dark:text-white">{current.title}</h1>
            <p className="mt-2 text-sm text-[#4e5875] dark:text-slate-300">{current.detail}</p>
            {current.options ? (
              <div className="mt-6 grid gap-3">
                {current.options.map(([value, title, description, Icon]) => (
                  <button
                    key={value}
                    onClick={() => {
                      setValue(current.key, value)
                      setTimeout(() => setStep((s) => s + 1), 180)
                    }}
                    className={`flex items-center gap-4 rounded-2xl border-2 p-4 text-left transition ${
                      form[current.key] === value
                        ? 'border-[#0A84FF] bg-blue-50 dark:bg-blue-950/30'
                        : 'border-[#dce6fa] hover:border-[#0A84FF]'
                    }`}
                  >
                    {Icon ? <Icon className="text-[#0A84FF]" size={22} /> : <Sparkles className="text-[#0A84FF]" size={22} />}
                    <span>
                      <strong className="block text-[#1D1D1F] dark:text-white">{title}</strong>
                      <span className="text-xs text-[#69708b] dark:text-slate-300">{description}</span>
                    </span>
                  </button>
                ))}
              </div>
            ) : (
              <div className="mt-6">
                <Input
                  autoFocus
                  type={current.type}
                  min="0"
                  value={form[current.key]}
                  onChange={(event) => setValue(current.key, event.target.value)}
                  onKeyDown={(event) => event.key === 'Enter' && next()}
                  placeholder={current.placeholder}
                  className="max-w-md py-4 text-xl"
                />
                <p className="mt-2 text-xs text-[#69708b]">{current.hint}</p>
                <div className="mt-5 flex gap-3">
                  {step > 0 ? (
                    <Button variant="ghost" onClick={() => setStep((s) => s - 1)}>
                      Back
                    </Button>
                  ) : null}
                  <Button onClick={next}>
                    Continue <ArrowRight className="ml-1" size={17} />
                  </Button>
                </div>
              </div>
            )}
            {error ? (
              <p className="mt-4 rounded-xl bg-amber-50 p-3 text-xs text-amber-900 dark:bg-amber-950/30 dark:text-amber-100">
                {error}
              </p>
            ) : null}
          </div>
        )}
      </Card>
      <Insight form={form} sector={sector} />
    </div>
  )
}
