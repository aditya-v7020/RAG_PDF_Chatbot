import { Bot, Check, ChevronDown, Copy, FileText, Paperclip, UserRound } from "lucide-react";
import { useState } from "react";
import ReactMarkdown from "react-markdown";
import { imageSrc } from "../api/client.js";

export default function ChatMessage({ message }) {
  const isUser = message.role === "user";
  const hasSources = !isUser && message.sources?.length > 0;
  const [sourcesOpen, setSourcesOpen] = useState(false);
  const [copied, setCopied] = useState(false);
  const copyAnswer = async () => { try { await navigator.clipboard.writeText(message.content); setCopied(true); window.setTimeout(() => setCopied(false), 1800); } catch {} };
  return <article className={`flex items-start gap-3 ${isUser ? "justify-end" : "justify-start"}`}>
    {!isUser && <div className="mt-1 flex h-8 w-8 shrink-0 items-center justify-center rounded-xl bg-brand-600 text-white shadow-sm"><Bot size={16} /></div>}
    <div className="min-w-0 max-w-[88%] sm:max-w-[78%]"><div className={`mb-1 flex items-center gap-2 text-[11px] font-semibold ${isUser ? "justify-end text-slate-400" : "text-slate-500"}`}><span>{isUser ? "You" : "DocumentIQ"}</span>{!isUser && <><span className="h-1 w-1 rounded-full bg-slate-300" /><span className="font-normal">Grounded answer</span></>}</div><div className={`rounded-2xl px-4 py-3 text-sm leading-6 shadow-sm ${isUser ? "rounded-tr-md bg-brand-600 text-white" : "rounded-tl-md border border-slate-200 bg-white text-slate-700"}`}><div className={isUser ? "whitespace-pre-wrap" : "markdown-body"}>{isUser ? message.content : <ReactMarkdown>{message.content}</ReactMarkdown>}</div>{!isUser && <div className="mt-3 flex items-center gap-2 border-t border-slate-100 pt-2.5"><button onClick={copyAnswer} className="inline-flex items-center gap-1.5 rounded-lg px-1.5 py-1 text-xs font-medium text-slate-500 hover:bg-slate-100">{copied ? <Check size={13} className="text-emerald-600" /> : <Copy size={13} />}{copied ? "Copied" : "Copy"}</button>{hasSources && <button onClick={() => setSourcesOpen((open) => !open)} className="inline-flex items-center gap-1.5 rounded-lg px-1.5 py-1 text-xs font-medium text-brand-600 hover:bg-brand-50"><Paperclip size={13} /> {message.sources.length} source{message.sources.length !== 1 ? "s" : ""}<ChevronDown size={13} className={sourcesOpen ? "rotate-180" : ""} /></button>}</div>}{hasSources && sourcesOpen && <div className="mt-2 rounded-xl border border-brand-100 bg-brand-50/50 p-3 text-xs text-slate-600"><div className="flex items-start gap-2"><FileText size={14} className="mt-0.5 shrink-0 text-brand-600" /><div><p className="font-semibold text-slate-700">Source references</p><p className="mt-0.5 leading-5">Pages: {message.sources.join(", ")}{message.documents?.length ? ` · ${message.documents.join(", ")}` : ""}</p></div></div>{message.images?.length > 0 && <div className="mt-3 grid grid-cols-2 gap-2">{message.images.map((image, index) => <a key={image} href={imageSrc(image)} target="_blank" rel="noreferrer" className="block overflow-hidden rounded-lg border border-slate-200 bg-white"><img src={imageSrc(image)} alt={`Source visual ${index + 1}`} className="aspect-[4/3] w-full object-cover" /></a>)}</div>}</div>}</div></div>
    {isUser && <div className="mt-1 flex h-8 w-8 shrink-0 items-center justify-center rounded-xl bg-slate-200 text-slate-600"><UserRound size={16} /></div>}
  </article>;
}
