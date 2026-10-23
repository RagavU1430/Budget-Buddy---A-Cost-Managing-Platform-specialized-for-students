import { useAuth } from '../context/AuthContext.jsx'

const plannedModules = [
  { title: 'Expenses', description: 'Add and categorise daily spending.' },
  { title: 'Income', description: 'Track pocket money, scholarships and freelance.' },
  { title: 'Budgets', description: 'Monthly and category-wise allocation.' },
  { title: 'Savings Goals', description: 'Targets such as a new laptop or a trip.' },
  { title: 'Analytics', description: 'Category-wise spending and monthly trends.' },
  { title: 'Reports', description: 'Monthly PDF and Excel exports.' },
]

export default function Dashboard() {
  const { user } = useAuth()
  const profile = user?.profile ?? {}

  return (
    <div className="flex flex-col gap-8">
      <section className="rounded-2xl bg-gradient-to-r from-emerald-600 to-teal-500 p-8 text-white">
        <h1 className="text-2xl font-bold">
          Welcome{user?.first_name ? `, ${user.first_name}` : ''}!
        </h1>
        <p className="mt-1 text-sm text-emerald-50">
          Your BudgetBuddy workspace is ready. Authentication is live — budget, expense and
          analytics features arrive in Milestone 2.
        </p>
      </section>

      <section className="grid gap-4 sm:grid-cols-3">
        <div className="rounded-xl border border-slate-200 bg-white p-5">
          <p className="text-xs uppercase tracking-wide text-slate-500">Role</p>
          <p className="mt-1 text-xl font-semibold capitalize text-slate-900">{user?.role}</p>
        </div>
        <div className="rounded-xl border border-slate-200 bg-white p-5">
          <p className="text-xs uppercase tracking-wide text-slate-500">Monthly income</p>
          <p className="mt-1 text-xl font-semibold text-slate-900">
            {profile.currency ?? 'INR'} {Number(profile.monthly_income ?? 0).toLocaleString()}
          </p>
        </div>
        <div className="rounded-xl border border-slate-200 bg-white p-5">
          <p className="text-xs uppercase tracking-wide text-slate-500">Currency</p>
          <p className="mt-1 text-xl font-semibold text-slate-900">{profile.currency ?? 'INR'}</p>
        </div>
      </section>

      <section>
        <h2 className="text-lg font-semibold text-slate-900">Planned modules</h2>
        <div className="mt-4 grid gap-4 sm:grid-cols-2 lg:grid-cols-3">
          {plannedModules.map((module) => (
            <article
              key={module.title}
              className="rounded-xl border border-dashed border-slate-300 bg-white p-5"
            >
              <h3 className="font-semibold text-slate-900">{module.title}</h3>
              <p className="mt-1 text-sm text-slate-500">{module.description}</p>
              <span className="mt-3 inline-block rounded-full bg-slate-100 px-2.5 py-0.5 text-xs font-medium text-slate-600">
                Milestone 2+
              </span>
            </article>
          ))}
        </div>
      </section>
    </div>
  )
}
