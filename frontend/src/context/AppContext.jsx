import { createContext, useCallback, useContext, useEffect, useState } from "react";

import * as api from "../api/client.js";

const AppContext = createContext(null);

export function AppProvider({ children }) {
  const [setup, setSetup] = useState({
    loading: true,
    ready: false,
    issues: [],
    llm_model: "",
    embedding_model: "",
    version: "",
  });

  const [documents, setDocuments] = useState([]);
  const [documentsLoading, setDocumentsLoading] = useState(true);
  const [uploadBusy, setUploadBusy] = useState(false);
  const [uploadNotices, setUploadNotices] = useState([]); // per-file success/error toasts

  const [dashboard, setDashboard] = useState({
    documents: [],
    document_count: 0,
    total_chunks: 0,
    total_images: 0,
  });

  const [messages, setMessages] = useState([]); // {role, content, sources, images, documents}
  const [chatBusy, setChatBusy] = useState(false);

  const refreshSetup = useCallback(async () => {
    try {
      const data = await api.getSetup();
      setSetup({ loading: false, ...data });
    } catch (err) {
      setSetup((prev) => ({
        ...prev,
        loading: false,
        ready: false,
        issues: [err.message || "Could not reach the backend API."],
      }));
    }
  }, []);

  const refreshDocuments = useCallback(async () => {
    setDocumentsLoading(true);
    try {
      const data = await api.getDocuments();
      setDocuments(data);
    } catch {
      // Backend not reachable yet; leave list as-is.
    } finally {
      setDocumentsLoading(false);
    }
  }, []);

  const refreshDashboard = useCallback(async () => {
    try {
      const data = await api.getDashboard();
      setDashboard(data);
    } catch {
      // Backend not reachable yet; leave stats as-is.
    }
  }, []);

  useEffect(() => {
    refreshSetup();
    refreshDocuments();
    refreshDashboard();
  }, [refreshSetup, refreshDocuments, refreshDashboard]);

  const uploadFiles = useCallback(
    async (fileList) => {
      setUploadBusy(true);
      setUploadNotices([]);
      try {
        const { manifest, results } = await api.uploadDocuments(fileList);
        setDocuments(manifest);
        setUploadNotices(results);
        await refreshDashboard();
      } catch (err) {
        setUploadNotices([{ name: "", ok: false, message: err.message }]);
      } finally {
        setUploadBusy(false);
      }
    },
    [refreshDashboard]
  );

  const removeDocument = useCallback(
    async (name) => {
      const { manifest } = await api.deleteDocument(name);
      setDocuments(manifest);
      await refreshDashboard();
    },
    [refreshDashboard]
  );

  const resetAll = useCallback(async () => {
    await api.resetDocuments();
    setDocuments([]);
    setMessages([]);
    await refreshDashboard();
  }, [refreshDashboard]);

  const clearChat = useCallback(() => {
    setMessages([]);
  }, []);

  const askQuestion = useCallback(async (question) => {
    setMessages((prev) => [...prev, { role: "user", content: question }]);
    setChatBusy(true);
    try {
      const response = await api.sendChat(question);
      setMessages((prev) => [
        ...prev,
        {
          role: "assistant",
          content: response.answer,
          sources: response.sources,
          images: response.images,
          documents: response.documents,
        },
      ]);
    } catch (err) {
      setMessages((prev) => [
        ...prev,
        {
          role: "assistant",
          content: `Something went wrong: ${err.message}`,
          sources: [],
          images: [],
          documents: [],
        },
      ]);
    } finally {
      setChatBusy(false);
    }
  }, []);

  const exportChatMarkdown = useCallback(() => {
    const lines = [
      "# RAG PDF Chatbot — Chat Export",
      `_${new Date().toLocaleString()}_`,
      "",
    ];
    for (const m of messages) {
      lines.push(`**${m.role === "user" ? "You" : "Assistant"}**: ${m.content}`);
      lines.push("");
    }
    const blob = new Blob([lines.join("\n")], { type: "text/markdown" });
    const url = URL.createObjectURL(blob);
    const a = document.createElement("a");
    const stamp = new Date().toISOString().slice(0, 16).replace(/[-:T]/g, "").slice(0, 12);
    a.href = url;
    a.download = `chat_export_${stamp}.md`;
    document.body.appendChild(a);
    a.click();
    a.remove();
    URL.revokeObjectURL(url);
  }, [messages]);

  const hasDocuments = documents.length > 0;

  const value = {
    setup,
    refreshSetup,
    documents,
    hasDocuments,
    documentsLoading,
    uploadBusy,
    uploadNotices,
    uploadFiles,
    removeDocument,
    resetAll,
    dashboard,
    refreshDashboard,
    messages,
    chatBusy,
    askQuestion,
    clearChat,
    exportChatMarkdown,
  };

  return <AppContext.Provider value={value}>{children}</AppContext.Provider>;
}

export function useApp() {
  const ctx = useContext(AppContext);
  if (!ctx) throw new Error("useApp must be used within an AppProvider");
  return ctx;
}
