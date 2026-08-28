import type { DoctorReport } from "../types";
import { ArrowBendDownRight, CheckCircle, WarningCircle } from "@phosphor-icons/react";

export function DoctorPanel({ doctor }: { doctor: DoctorReport }) {
  const { issues, blocking_issues } = doctor;
  return (
    <div className="panel">
      <div className={`doctor-banner ${blocking_issues.length ? "bad" : "good"}`}>
        {blocking_issues.length
          ? <WarningCircle size={17} weight="light" />
          : <CheckCircle size={17} weight="light" />}
        {blocking_issues.length
          ? `${blocking_issues.length} blocking issue(s) — pipeline halts.`
          : "Doctor clean — no blocking issues."}
      </div>
      {issues.length === 0 ? (
        <div className="muted">No findings.</div>
      ) : (
        <ul className="issues">
          {issues.map((i, idx) => (
            <li key={idx} className={`sev-${i.severity}`}>
              <span className={`badge sev-${i.severity}`}>{i.severity}</span>
              <code>{i.code}</code>
              <div>{i.message}</div>
              {i.suggestion && <div className="hint"><ArrowBendDownRight size={14} weight="light" /> {i.suggestion}</div>}
            </li>
          ))}
        </ul>
      )}
    </div>
  );
}
