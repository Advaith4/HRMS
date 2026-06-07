# TalentForge — Employee Intelligence Report

This report outlines the enhancements and features implemented to transform the TalentForge Employee Portal into a comprehensive **Employee Intelligence Hub** using live database metrics, policy RAG, and hybrid intelligence routing.

---

## 1. Features Added

### A. Employee Overview Dashboard Metrics Grid
A responsive 5-card dashboard has been added to the top of the Overview tab, providing immediate live stats:
1. **Employee ID:** Displays the unique employee code and their corporate join date.
2. **Department & Designation:** Displays the active department and role of the logged-in employee.
3. **Reporting Line:** Displays the direct reporting manager's username (or falls back to "Not Assigned" if not set in the DB).
4. **Time & Tickets:** Summarizes the current workday attendance check-in status alongside the total open support ticket count.
5. **Growth & Profile:** Tracks active assigned upskilling courses and the percentage of profile completeness.

### B. Leave Balance Widget
A visual widget presented alongside the leave request form details leave statistics:
- Columns for **Annual**, **Sick**, and **Casual** leaves showing remaining balances, used days, and company allocations.
- Handles empty leave histories gracefully, presenting standard policy allocations (15 Annual, 12 Sick, 7 Casual).

### C. Career Growth & Promotion Readiness Hub
The career mapping section is restructured into a side-by-side dashboard layout:
- **Skills Analytics:** Compares current profile skills against Core Expectations for their current role, grouping matched competencies (success green) and highlighting identified gaps (warning amber). Displays deterministic recommended learning directions.
- **Promotion Readiness Insights:** Displays a large colorful status card representing their current qualification tier (`Ready`, `Developing`, or `Needs Growth`), accompanied by a detailed description of requirements, and progress bars tracking core skill matches, training completions, and profile updates.

### D. Improved Training Tab
- Added stats headers (Total, Completed, Pending) and filter tabs ("All", "Pending", "Completed") to manage courses.
- **Knowledge-Base Recommendations:** If no training assignments exist, the system renders **Recommended Company Learning Paths** (Backend Engineering, System Design, Leadership, and Communication) extracted from company knowledge.
- Interactive "Ask AI Assistant" buttons are included to immediately query specific topics inside the chatbot drawer.

---

## 2. Employee AI Improvements

The floating **Employee Assistant** has been upgraded from a policy-only search bot to a **Hybrid AI Intelligence Co-Pilot**:
- **Automatic Query Routing:** The router detects queries asking about personal info (e.g. "How many leave days do I have?", "Who is my manager?", "What is my check-in status?") and routes them into `hybrid` database-retrieval mode.
- **Personalized Database Context:** Gathers all relevant profile parameters, leave requests, attendance logs, and tickets in a single optimized query path, allowing the LLM to write highly personalized answers.
- **Deduped Source Attribution:** Displays explicit, checkmarked badges under every AI bubble indicating where the info was sourced (e.g., `✓ Live Employee Data`, `✓ Company Policy`, or `✓ Employee Knowledge`).
- **Interactive Suggestions:** Offers suggested prompt buttons when the drawer is empty, letting employees quickly trigger intelligence queries.

---

## 3. Leave Intelligence Logic

Leave balances are calculated deterministically on-the-fly using the employee's active leave requests:
- **Base allocations:** `{"Annual": 15, "Sick": 12, "Casual": 7}`.
- **Used leaves calculation:** Iterates over the employee's `LeaveRequest` records, identifies those with `status == "Approved"`, extracts the day count via `max(0, (end_date - start_date).days + 1)`, and accumulates it into the corresponding category.
- **Remaining leaves calculation:** `max(0, Allocation - Used)`.
- If no leave history exists, it falls back to the baseline allocations and prints an explanatory note.

---

## 4. Career Growth & Promotion Readiness Logic

Upskilling paths and readiness levels are computed deterministically without artificial metrics:
- **Progression Mapping:** Mapped directly to designation keywords:
  - `Backend` -> Senior Backend Engineer (expected core backend stack)
  - `Frontend` / `React` -> Senior Frontend Engineer (expected frontend/state systems)
  - `QA` / `Test` -> QA Lead (expected automated pipelines)
  - `Data` -> Senior Data Scientist (expected MLOps/PyTorch)
  - `Other` -> Lead [Designation] (expected leadership/agile concepts)
- **Promotion Readiness Rules:**
  - **Ready:** Core skill match ratio >= 70%, training completion ratio >= 75%, profile completion >= 80%.
  - **Developing:** Core skill match ratio >= 40%, training completion ratio >= 50%, profile completion >= 50%.
  - **Needs Growth:** Otherwise.

---

## 5. Security Validation

Role isolation is fully enforced on both server-side and database-retrieval layers:
- **Database Context Boundaries:** `_build_employee_context` queries only records matching `user.id == current_user.id` or `employee.user_id == current_user.id`. There is no possible leakage to other employees' files.
- **RAG Collection Isolation:** `RAGAccessControl` limits the RAG collections accessible to employees to `company_policies` and `employee_knowledge`. Any request to query `candidate_profiles` or `interview_reports` raises a `403 Forbidden` error.
- **Endpoint Protection:** The employee directory, employee listing, candidate profiles, and official interview reports remain locked behind `Depends(require_roles("hr", "manager"))`.

---

## 6. Test Results

Targeted validation suites run and pass cleanly:
- **`test_rag_access_control.py`**: 6 passed.
- **`test_rag_query_router.py`**: 8 passed.
- **`test_api.py`**: 13 passed.
- **Production Build (`npm run build`)**: Vite build completed successfully in `1.39s` without compile errors.

---

## 7. Remaining Limitations

- **Historical Attendance Heatmap:** The weekly heatmap displays baseline attendance patterns and does not reflect a full calendar year.
- **Custom Target Roles:** Custom target role analysis entered in the form is computed via the AI analyzer service (CrewAI/fallback), while the dashboard card progression matches default deterministic mapping.
