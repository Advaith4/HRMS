import React, { useEffect, useState } from 'react'
import toast from 'react-hot-toast'
import { EmptyState } from '../../components/ui/EmptyState'
import { MetricCard } from '../../components/ui/MetricCard'
import { StatusPill } from '../../components/ui/StatusPill'
import { getTeamTrainingAssignments, getTrainingSummary } from '../../api'

export const ManagerTrainingView = () => {
  const [summary, setSummary] = useState({})
  const [assignments, setAssignments] = useState([])
  const [loading, setLoading] = useState(true)

  useEffect(() => {
    const fetchData = async () => {
      setLoading(true)
      try {
        const [summaryData, assignmentData] = await Promise.all([
          getTrainingSummary(),
          getTeamTrainingAssignments(),
        ])
        setSummary(summaryData || {})
        setAssignments(assignmentData || [])
      } catch (err) {
        console.error(err)
        toast.error('Failed to load team training')
      } finally {
        setLoading(false)
      }
    }
    fetchData()
  }, [])

  return (
    <div className="space-y-6">
      <div className="grid grid-cols-1 sm:grid-cols-3 gap-6">
        <MetricCard iconName="ClipboardList" label="Team Assignments" value={summary.assignments || 0} delta="Visible team scope" />
        <MetricCard iconName="Award" label="Completion" value={`${summary.completion_percent || 0}%`} delta={`${summary.completed || 0} complete`} hoverColor="teal" />
        <MetricCard iconName="CalendarCheck" label="Overdue Training" value={summary.overdue || 0} delta="Follow up" />
      </div>
      <div className="rounded-xl border border-border-custom bg-white p-6 shadow-xs space-y-4">
        <div className="border-b border-border-custom pb-3">
          <h4 className="text-sm font-semibold">Team Training Progress</h4>
          <p className="text-[11px] text-txt-secondary">Managers can view completion status and overdue assignments.</p>
        </div>
        {loading ? (
          <div className="text-xs text-txt-tertiary py-8">Loading team training...</div>
        ) : assignments.length === 0 ? (
          <EmptyState title="No team training assigned" description="Assigned training programs will appear here." />
        ) : (
          <div className="overflow-x-auto">
            <table className="w-full text-left text-xs">
              <thead>
                <tr className="bg-bg-page text-txt-tertiary uppercase text-[10px]">
                  <th className="py-2.5 px-3">Employee</th>
                  <th className="py-2.5 px-3">Program</th>
                  <th className="py-2.5 px-3">Progress</th>
                  <th className="py-2.5 px-3">Due Date</th>
                  <th className="py-2.5 px-3">Status</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-border-custom/50">
                {assignments.map((item) => (
                  <tr key={item.id}>
                    <td className="py-3 px-3">
                      <span className="font-semibold block">{item.employee_name}</span>
                      <span className="text-[10px] text-txt-secondary">{item.employee_code}</span>
                    </td>
                    <td className="py-3 px-3">{item.program_title}</td>
                    <td className="py-3 px-3">
                      <div className="w-32 h-2 bg-bg-page rounded-full overflow-hidden border border-border-custom">
                        <div className="h-full bg-brand-indigo" style={{ width: `${item.progress_percent || 0}%` }} />
                      </div>
                      <span className="text-[10px] text-txt-secondary">{item.progress_percent || 0}%</span>
                    </td>
                    <td className="py-3 px-3 text-txt-secondary">{item.due_date ? new Date(item.due_date).toLocaleDateString() : 'None'}</td>
                    <td className="py-3 px-3"><StatusPill status={item.status} /></td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </div>
    </div>
  )
}

export default ManagerTrainingView
