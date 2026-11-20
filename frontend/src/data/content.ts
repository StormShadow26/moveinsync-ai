import { Code2, Database, ShieldCheck, Sparkles } from 'lucide-react'

export const features = [
  { icon: Sparkles, color: 'bg-blue-50 text-brand-blue', label: 'Ask naturally', title: 'Questions in, useful context out.', text: 'Ask about no-shows, vehicle occupancy, night-shift exceptions, or vendor costs using language your team already uses.' },
  { icon: ShieldCheck, color: 'bg-green-50 text-brand-green', label: 'Guardrails first', title: 'Access stays where it belongs.', text: 'Identity and company scope are enforced below the model, so a prompt cannot grant itself more data.' },
  { icon: Code2, color: 'bg-yellow-50 text-yellow-700', label: 'Trace the result', title: 'Review the exact query.', text: 'See the returned data, final SQL, and a short statement of what the calculation includes.' },
]

export const plans = [
  { name: 'Explorer', title: 'For focused teams', price: '$0', copy: 'Explore a guided product workspace.', items: ['Sample transport questions', 'Product walkthrough', 'Community support'] },
  { name: 'Operations', title: 'For daily decisions', price: 'Custom', copy: 'For teams connecting governed operational data.', items: ['Scoped team access', 'Query history and review', 'Priority implementation'], featured: true },
  { name: 'Enterprise', title: 'For multi-company control', price: 'Tailored', copy: 'For larger organisations with advanced controls.', items: ['Organisation controls', 'Dedicated environment', 'Technical partnership'] },
]

export const assurance = [
  ['Clear outputs', 'Rows, SQL, and a plain-English explanation.'],
  ['Scoped by design', "Every request respects the caller's company access."],
  ['Built for operations', 'Designed around routes, trips, vendors, and shifts.'],
]

export const processSteps = [
  ['Understand the question', 'Relevant transport schema and business context are selected for the request.'],
  ['Validate the query', 'Only safe, read-only SQL within the user scope is allowed to execute.'],
  ['Explain the result', 'The response includes the data, the SQL, and what was computed.'],
]

export const testimonials = [
  ['The best outcome is fewer handoffs between the transport desk and the people who need an answer.', 'Transport desk workflow'],
  ['A manager should understand how a number was calculated before acting on it.', 'Operations oversight'],
  ['The right access model lets teams move faster without making tenant boundaries fuzzy.', 'Security and data'],
]

export const footerGroups = [
  ['Platform', 'How it works', 'Use cases', 'Pricing'],
  ['Resources', 'Developer docs', 'Security', 'Status'],
  ['Company', 'About', 'Contact', 'Careers'],
]
