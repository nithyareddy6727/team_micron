import { createElement } from 'react'
import { BookOpen, CircleHelp, LifeBuoy, ShieldCheck } from 'lucide-react'
import { Card } from '@/components/ui/Card'

const guides = [
  ['Run a prediction', 'Select an existing customer or enter a new profile to receive a churn assessment and recommended next step.', BookOpen],
  ['Understand risk', 'High-risk customers should be prioritised for retention outreach. AI explanations show the leading factors behind each assessment.', CircleHelp],
  ['Use reports', 'Reports collect the latest prediction activity, risk trends, and operational signals for stakeholder review.', LifeBuoy],
  ['Keep data secure', 'This workspace connects to your configured service. Use an approved HTTPS endpoint in production.', ShieldCheck],
]

export default function HelpPage() {
  return <div className="space-y-5"><div><p className="text-xs font-semibold uppercase tracking-[0.18em] text-blue-600 dark:text-blue-300">Help centre</p><h1 className="mt-1 text-3xl font-semibold tracking-tight text-slate-950 dark:text-white">Get more from ChurnX AI</h1><p className="mt-2 text-sm text-slate-600 dark:text-slate-300">Guidance for turning customer signals into thoughtful retention decisions.</p></div><div className="grid gap-4 md:grid-cols-2">{guides.map(([title, description, Icon]) => <Card key={title} className="min-h-44">{createElement(Icon, { size: 22, className: 'text-blue-600 dark:text-blue-300' })}<h2 className="mt-4 text-lg font-semibold text-slate-950 dark:text-white">{title}</h2><p className="mt-2 text-sm leading-6 text-slate-600 dark:text-slate-300">{description}</p></Card>)}</div><Card title="Need assistance?" subtitle="If a screen cannot load, first check the API URL in Settings and then try again. Contact your platform administrator for access or data questions." /></div>
}
