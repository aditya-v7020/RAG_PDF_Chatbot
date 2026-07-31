import { CheckCircle2, Settings2 } from "lucide-react";
import { useApp } from "../context/AppContext.jsx";
import DocumentManager from "./DocumentManager.jsx";
import MaintenancePanel from "./MaintenancePanel.jsx";
import ModelInfo from "./ModelInfo.jsx";
import StatusPill from "./StatusPill.jsx";

export default function Sidebar() {
  const { setup } = useApp();
  return <aside className="thin-scrollbar h-full w-full overflow-y-auto border-r border-slate-200 bg-white px-4 py-5"><div className="rounded-2xl bg-slate-900 p-4 text-white shadow-lg shadow-slate-200"><div className="flex items-center gap-2 text-sm font-bold"><Settings2 size={16} className="text-cyan-300" /> Workspace status</div>{setup.loading ? <p className="mt-3 text-xs text-slate-400">Checking connection…</p> : <><div className="mt-3"><StatusPill ok={setup.ready} /></div><p className="mt-3 text-xs leading-5 text-slate-300">{setup.ready ? "Your AI workspace is connected and ready for questions." : "Finish the setup steps below to activate document chat."}</p></>}</div>{!setup.loading && !setup.ready && setup.issues.length > 0 && <div className="mt-3 space-y-2">{setup.issues.map((issue) => <p key={issue} className="rounded-xl border border-amber-200 bg-amber-50 px-3 py-2 text-xs leading-5 text-amber-800">{issue}</p>)}</div>}{setup.ready && <div className="mt-4 flex items-center gap-2 rounded-xl border border-emerald-100 bg-emerald-50 px-3 py-2 text-xs font-medium text-emerald-700"><CheckCircle2 size={15} /> Documents stay private in this local workspace</div>}<DocumentManager /><MaintenancePanel /><ModelInfo /></aside>;
}
