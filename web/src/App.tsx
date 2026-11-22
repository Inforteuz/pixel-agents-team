import { useCallback, useEffect, useRef, useState } from "react";
import type { ReactNode, FormEvent } from "react";
import ReactMarkdown from "react-markdown";
import remarkGfm from "remark-gfm";
import {
  Armchair,
  ArrowUp,
  Check,
  ChevronRight,
  ChevronsUpDown,
  CircleHelp,
  Code2,
  Coffee,
  Expand,
  Eye,
  EyeOff,
  Folder,
  Grid2X2,
  ListTodo,
  Loader2,
  MessageSquare,
  Minus,
  Minimize2,
  Moon,
  MoreHorizontal,
  Pause,
  Play,
  Plus,
  Search,
  Settings2,
  ShieldCheck,
  Sparkles,
  Sun,
  Terminal,
  Users,
  X,
} from "lucide-react";
import Office, { Avatar } from "./Office";
import { api, setCsrf } from "./api";
import type { Agent, Provider, Studio } from "./types";
import "./style.css";
const now = (value: number) =>
  new Date(value * 1000).toLocaleTimeString("uz-UZ", {
    hour: "2-digit",
    minute: "2-digit",
    timeZone: "Asia/Tashkent",
  });
const icons: Record<string, typeof Code2> = {
  supervisor: Sparkles,
  developer: Code2,
  qa: Search,
  devops: Terminal,
  security: ShieldCheck,
};
const agentStatus = (a: Agent) =>
  !a.enabled
    ? "Pauzada"
    : a.status === "working"
      ? "Javob tayyorlamoqda"
      : "Kutmoqda";
const taskStatus: Record<string, string> = {
  new: "Navbatda",
  running: "Bajarilmoqda",
  review: "Ko‘rib chiqish",
  done: "Yakunlandi",
  paused: "Pauzada",
  error: "Xatolik",
  cancelled: "Bekor qilingan",
};
const jobStatus: Record<string, string> = {
  queued: "Navbatda",
  running: "Ishlayapti",
  done: "Javob tayyor",
  paused: "Pauzada",
  failed: "Xatolik",
  cancelled: "Bekor qilingan",
};
const stepLabels: Record<string, string> = {
  queued: "Navbatga olindi",
  context: "Loyiha konteksti tayyorlanyapti",
  request: "So‘rov provayderga yuborildi",
  response: "Javob olindi",
  saved: "Javob chatga saqlandi",
  failed: "So‘rov yakunlanmadi",
};
type View = "office" | "team" | "tasks" | "settings";
function PixelMark() {
  return (
    <svg
      width="28"
      height="28"
      viewBox="0 0 28 28"
      fill="currentColor"
      aria-hidden="true"
    >
      <path d="M5 5h18v15h-4v-4h-3v7h-4v-7H9v4H5z" />
      <path d="M8 9h4v4H8zm8 0h4v4h-4z" fill="#17241b" />
    </svg>
  );
}
function MessageText({ text, markdown }: { text: string; markdown: boolean }) {
  if (!markdown) return <p className="message-plain">{text}</p>;
  return (
    <div className="message-markdown">
      <ReactMarkdown remarkPlugins={[remarkGfm]} skipHtml>
        {text}
      </ReactMarkdown>
    </div>
  );
}
function IconButton({
  label,
  children,
  onClick,
  active = false,
}: {
  label: string;
  children: ReactNode;
  onClick: () => void;
  active?: boolean;
}) {
  return (
    <button
      className={`icon-button ${active ? "active" : ""}`}
      onClick={onClick}
      aria-label={label}
      title={label}
    >
      {children}
    </button>
  );
}
function Modal({
  title,
  children,
  onClose,
}: {
  title: string;
  children: ReactNode;
  onClose: () => void;
}) {
  const ref = useRef<HTMLDialogElement>(null);
  useEffect(() => {
    const d = ref.current;
    d?.showModal();
    return () => d?.close();
  }, []);
  return (
    <dialog
      ref={ref}
      className="modal"
      onCancel={onClose}
      onClick={(e) => {
        if (e.target === e.currentTarget) onClose();
      }}
    >
      <header>
        <h2>{title}</h2>
        <IconButton label="Yopish" onClick={onClose}>
          <X size={18} />
        </IconButton>
      </header>
      {children}
    </dialog>
  );
}
function Login({ onLogin }: { onLogin: () => void }) {
  const [password, setPassword] = useState(""),
    [showPassword, setShowPassword] = useState(false),
    [error, setError] = useState(""),
    [busy, setBusy] = useState(false);
  const login = async (e: FormEvent) => {
    e.preventDefault();
    setBusy(true);
    setError("");
    try {
      const s = await api<{ csrf_token: string }>("/api/auth/login", {
        method: "POST",
        body: JSON.stringify({ password }),
      });
      setCsrf(s.csrf_token);
      onLogin();
    } catch (e) {
      setError((e as Error).message);
    } finally {
      setBusy(false);
    }
  };
  return (
    <div className="login-page">
      <div className="login-scene">
        <div className="login-wordmark">
          <PixelMark /> pixel team<span>YOUR LITTLE BIG TEAM</span>
        </div>
        <Office
          agents={[]}
          selected={null}
          onSelect={() => {}}
          paused={false}
          grid={false}
          zoom={1}
        />
        <div className="login-scene-caption">
          <span>01 / TEAM HEADQUARTERS</span>
          <h1>
            Katta g‘oyalar.
            <br />
            Kichik piksel olam.
          </h1>
          <p>
            O‘z AI jamoangiz bilan bir joyda o‘ylang, yarating va ishni oxiriga
            yetkazing.
          </p>
        </div>
      </div>
      <main className="login-form-area">
        <div className="login-form">
          <span className="eyebrow">SHAXSIY ISH MAYDONI</span>
          <h2>Ofisga xush kelibsiz.</h2>
          <p>
            Jamoangiz sizni kutmoqda. Davom etish uchun administrator parolini
            kiriting.
          </p>
          <form onSubmit={login}>
            <label htmlFor="password">Parol</label>
            <div className="password-field">
              <input
                id="password"
                type={showPassword ? "text" : "password"}
                autoComplete="current-password"
                required
                value={password}
                onChange={(e) => setPassword(e.target.value)}
                autoFocus
              />
              <button
                type="button"
                aria-label={
                  showPassword ? "Parolni yashirish" : "Parolni ko‘rsatish"
                }
                aria-pressed={showPassword}
                onClick={() => setShowPassword(!showPassword)}
              >
                {showPassword ? <EyeOff size={19} /> : <Eye size={19} />}
              </button>
            </div>
            <button className="primary full" disabled={busy}>
              {busy ? <Loader2 className="spin" size={18} /> : <PixelMark />}
              Ofisga kirish
            </button>
          </form>
          {error && (
            <div className="form-error" role="alert">
              {error}
            </div>
          )}
          <div className="login-privacy">
            <ShieldCheck size={15} /> Faqat siz va sizning jamoangiz.
          </div>
        </div>
      </main>
    </div>
  );
}
export default function App() {
  const [theme, setTheme] = useState(
    () =>
      localStorage.getItem("pixel-theme") ||
      (window.matchMedia("(prefers-color-scheme: light)").matches
        ? "light"
        : "dark"),
  );
  const [chatFocus, setChatFocus] = useState(false);
  const themeAction = theme === "dark" ? "Yorug‘ rejim" : "Qorong‘i rejim";
  const themeToggle = (
    <IconButton
      label={themeAction}
      onClick={() => setTheme(theme === "dark" ? "light" : "dark")}
    >
      {theme === "dark" ? <Sun size={18} /> : <Moon size={18} />}
    </IconButton>
  );
  const [auth, setAuth] = useState<boolean | null>(null),
    [data, setData] = useState<Studio | null>(null);
  const [project, setProject] = useState(
    () => localStorage.getItem("pixel-project") || "default",
  );
  const [view, setView] = useState<View>("office"),
    [selected, setSelected] = useState<string | null>(null);
  const [paused, setPaused] = useState(
    () =>
      localStorage.getItem("pixel-motion") === "paused" ||
      (!localStorage.getItem("pixel-motion") &&
        window.matchMedia("(prefers-reduced-motion: reduce)").matches),
  );
  const [grid, setGrid] = useState(false),
    [zoom, setZoom] = useState(1),
    [clock, setClock] = useState(new Date());
  const [modal, setModal] = useState<"task" | "project" | "help" | null>(null),
    [toast, setToast] = useState(""),
    [error, setError] = useState("");
  const [chatTab, setChatTab] = useState<"chat" | "activity">("chat"),
    [draft, setDraft] = useState(""),
    [sending, setSending] = useState(false);
  const [taskFilter, setTaskFilter] = useState("all"),
    [chatOpen, setChatOpen] = useState(() => window.innerWidth > 900);
  const officeRef = useRef<HTMLDivElement>(null);
  const chatStream = useRef<HTMLDivElement>(null);
  const followChat = useRef(true);
  useEffect(() => {
    document.documentElement.dataset.theme = theme;
    localStorage.setItem("pixel-theme", theme);
  }, [theme]);
  useEffect(() => {
    if (!chatFocus) return;
    const exit = (e: KeyboardEvent) => {
      if (e.key === "Escape" && !document.querySelector("dialog[open]"))
        setChatFocus(false);
    };
    window.addEventListener("keydown", exit);
    return () => window.removeEventListener("keydown", exit);
  }, [chatFocus]);
  useEffect(() => {
    api<{ authenticated: boolean; csrf_token: string }>("/api/auth/status")
      .then((s) => {
        setCsrf(s.csrf_token || "");
        setAuth(s.authenticated);
      })
      .catch(() => {
        setAuth(false);
      });
    const expired = () => setAuth(false);
    window.addEventListener("session-expired", expired);
    return () => window.removeEventListener("session-expired", expired);
  }, []);
  const refresh = useCallback(async () => {
    try {
      const s = await api<Studio>(
        `/api/studio?project_id=${encodeURIComponent(project)}`,
      );
      setData(s);
      setError("");
    } catch (e) {
      setError((e as Error).message);
    }
  }, [project]);
  useEffect(() => {
    if (!auth) return;
    void refresh();
    const timer = setInterval(() => {
      if (!document.hidden) void refresh();
    }, 3000);
    return () => clearInterval(timer);
  }, [auth, refresh]);
  useEffect(() => {
    const timer = setInterval(() => setClock(new Date()), 1000);
    return () => clearInterval(timer);
  }, []);
  useEffect(() => {
    localStorage.setItem("pixel-project", project);
    followChat.current = true;
  }, [project]);
  useEffect(() => {
    localStorage.setItem("pixel-motion", paused ? "paused" : "playing");
  }, [paused]);
  useEffect(() => {
    if (
      chatOpen &&
      followChat.current &&
      chatTab === "chat" &&
      chatStream.current
    ) {
      chatStream.current.scrollTop = chatStream.current.scrollHeight;
    }
  }, [data?.messages.at(-1)?.id, chatTab, chatOpen, chatFocus, project]);
  useEffect(() => {
    if (!toast) return;
    const timer = setTimeout(() => setToast(""), 5000);
    return () => clearTimeout(timer);
  }, [toast]);
  if (auth === null)
    return (
      <div className="boot">
        <PixelMark />
        <span>Ofis ochilmoqda…</span>
      </div>
    );
  if (!auth)
    return (
      <>
        <div className="login-theme">{themeToggle}</div>
        <Login onLogin={() => setAuth(true)} />
      </>
    );
  const chosen = data?.agents.find((a) => a.id === selected),
    activeTasks = data?.tasks.filter((t) => t.status !== "cancelled") || [];
  const select = (id: string) => {
    setSelected(id === selected ? null : id);
    if (id !== selected) setChatOpen(true);
  };
  const send = async (e: FormEvent) => {
    e.preventDefault();
    if (!draft.trim() || sending) return;
    setSending(true);
    followChat.current = true;
    try {
      await api("/api/messages", {
        method: "POST",
        body: JSON.stringify({ project_id: project, text: draft }),
      });
      setDraft("");
      await refresh();
    } catch (e) {
      setToast((e as Error).message);
    } finally {
      setSending(false);
    }
  };
  const cancel = async (id: string) => {
    try {
      await api(`/api/tasks/${id}/cancel`, { method: "POST" });
      await refresh();
      setToast("Vazifa bekor qilindi.");
    } catch (e) {
      setToast((e as Error).message);
    }
  };
  const complete = async (id: string) => {
    try {
      await api(`/api/tasks/${id}/complete`, { method: "POST" });
      await refresh();
      setToast("Vazifa yakunlandi.");
    } catch (e) {
      setToast((e as Error).message);
    }
  };
  const changeTask = async (id: string, action: "pause" | "run") => {
    try {
      await api(`/api/tasks/${id}/${action}`, { method: "POST" });
      await refresh();
      setToast(
        action === "pause" ? "Vazifa pauzada." : "Vazifa navbatga qo‘yildi.",
      );
    } catch (e) {
      setToast((e as Error).message);
    }
  };
  const logout = async () => {
    try {
      await api("/api/auth/logout", { method: "POST" });
      setAuth(false);
      setData(null);
    } catch (e) {
      setToast((e as Error).message);
    }
  };
  return (
    <div
      className={`app-shell ${chatOpen ? "mobile-chat-open" : "chat-collapsed"} ${chatFocus ? "chat-focus" : ""}`}
    >
      <aside className="rail">
        <button
          className="brand-button"
          onClick={() => setView("office")}
          aria-label="Pixel Team bosh sahifa"
        >
          <PixelMark />
        </button>
        <div className="rail-divider" />
        {(
          [
            ["office", Armchair, "Ofis"],
            ["team", Users, "Jamoa"],
            ["tasks", ListTodo, "Vazifalar"],
          ] as const
        ).map(([id, Icon, label]) => (
          <button
            key={id}
            className={`rail-item ${view === id ? "selected" : ""}`}
            onClick={() => setView(id)}
            title={label}
            aria-label={label}
          >
            <Icon size={21} />
            <span>{label}</span>
            {id === "tasks" && activeTasks.length > 0 && (
              <b className="rail-count">{activeTasks.length}</b>
            )}
          </button>
        ))}
        <div className="rail-bottom">
          <button
            className={`rail-item ${view === "settings" ? "selected" : ""}`}
            onClick={() => setView("settings")}
            aria-label="Sozlamalar"
          >
            <Settings2 size={21} />
            <span>Sozlama</span>
          </button>
          <button
            className="rail-item"
            onClick={() => setModal("help")}
            aria-label="Yordam"
          >
            <CircleHelp size={21} />
          </button>
          <button
            className="owner"
            onClick={logout}
            title="Chiqish"
            aria-label="Chiqish"
          >
            S
          </button>
        </div>
      </aside>
      <div className="workspace">
        <header className="topbar">
          <div className="workspace-name">
            <span className="app-name">pixel team</span>
            <span className="slash">/</span>
            <div className="project-select">
              <Folder size={15} />
              <select
                aria-label="Loyiha"
                value={project}
                onChange={(e) => {
                  setProject(e.target.value);
                  setSelected(null);
                }}
              >
                {data?.projects.map((p) => (
                  <option key={p.id} value={p.id}>
                    {p.name}
                  </option>
                )) || <option value="default">Mening jamoam</option>}
              </select>
              <ChevronsUpDown size={13} />
            </div>
            <button
              className="small-plus"
              onClick={() => setModal("project")}
              aria-label="Loyiha yaratish"
            >
              <Plus size={16} />
            </button>
          </div>
          <div className="topbar-right">
            {themeToggle}
            <span className="local-badge">
              <span />
              {window.location.hostname === "127.0.0.1" ||
              window.location.hostname === "localhost"
                ? "LOCAL"
                : "PRIVATE"}
            </span>
            <span className="clock">
              {clock.toLocaleTimeString("en-GB", {
                hour: "2-digit",
                minute: "2-digit",
                timeZone: "Asia/Tashkent",
              })}
              <span>UZT</span>
            </span>
            <button
              className="mobile-chat-toggle"
              onClick={() => {
                if (chatOpen) setChatFocus(false);
                setChatOpen(!chatOpen);
              }}
              aria-label={chatOpen ? "Chatni yopish" : "Chatni ochish"}
            >
              {chatOpen ? <X size={20} /> : <MessageSquare size={20} />}
            </button>
          </div>
        </header>
        {!data ? (
          <main className="loading-state">
            <Loader2 className="spin" />
            <p>{error || "Jamoa yuklanmoqda…"}</p>
            {error && (
              <button
                onClick={() => {
                  setProject("default");
                  void refresh();
                }}
              >
                Qayta urinish
              </button>
            )}
          </main>
        ) : (
          <div className="workspace-content">
            <main className="main-content">
              {view === "office" && (
                <>
                  <section className="page-heading">
                    <div>
                      <h1>
                        Jamoa ofisi<span>.</span>
                      </h1>
                      <p>
                        {
                          data.agents.filter(
                            (agent) => agent.status === "working",
                          ).length
                        }{" "}
                        agent ishlayapti ·{" "}
                        {
                          data.jobs.filter((job) => job.status === "queued")
                            .length
                        }{" "}
                        ish navbatda
                      </p>
                    </div>
                    <button
                      className="primary"
                      onClick={() => setModal("task")}
                    >
                      <Plus size={17} />
                      Yangi vazifa
                    </button>
                  </section>
                  <section className="office-panel" ref={officeRef}>
                    <header className="panel-toolbar">
                      <div className="office-title">
                        <span className="room-pixel">▧</span>
                        <strong>Jamoa ofisi</strong>
                        <span className="divider-v" />
                        <span className="secondary">5 agent</span>
                      </div>
                      <div className="toolbar-actions">
                        <IconButton
                          label={
                            paused
                              ? "Animatsiyani davom ettirish"
                              : "Animatsiyani to‘xtatish"
                          }
                          onClick={() => setPaused(!paused)}
                          active={paused}
                        >
                          {paused ? <Play size={15} /> : <Pause size={15} />}
                        </IconButton>
                        <IconButton
                          label="Kataklar"
                          onClick={() => setGrid(!grid)}
                          active={grid}
                        >
                          <Grid2X2 size={15} />
                        </IconButton>
                        <span className="divider-v" />
                        <IconButton
                          label="Kichraytirish"
                          onClick={() => setZoom(Math.max(0.4, zoom - 0.2))}
                        >
                          <Minus size={15} />
                        </IconButton>
                        <span className="zoom-value">
                          {Math.round(zoom * 100)}%
                        </span>
                        <IconButton
                          label="Kattalashtirish"
                          onClick={() => setZoom(Math.min(2.8, zoom + 0.2))}
                        >
                          <Plus size={15} />
                        </IconButton>
                        <IconButton
                          label="Ofisni kengaytirish"
                          onClick={() => {
                            if (document.fullscreenElement)
                              void document.exitFullscreen();
                            else
                              void officeRef.current
                                ?.requestFullscreen()
                                .catch(() =>
                                  setToast(
                                    "Bu oynada to‘liq ekran mavjud emas.",
                                  ),
                                );
                          }}
                        >
                          <Expand size={15} />
                        </IconButton>
                      </div>
                    </header>
                    <div className="office-stage">
                      <div className="scene-corner">
                        <span className="scene-dot" /> TEAM HQ <span>/</span> 01
                      </div>
                      <Office
                        agents={data.agents}
                        selected={selected}
                        onSelect={select}
                        paused={paused}
                        grid={grid}
                        zoom={zoom}
                      />
                      <div className="scene-foot">
                        <span>
                          <Coffee size={12} /> Ofisni surib ko‘ring. Zoom bilan
                          yaqinlashtiring.
                        </span>
                        <span>AGENTNI TANLASH UCHUN BOSING</span>
                      </div>
                    </div>
                    <footer className="office-footer">
                      <span>
                        <span className="idle-dot" />{" "}
                        {paused
                          ? "Animatsiya pauzada"
                          : data.agents.some((a) => a.status === "working")
                            ? "Agent javob tayyorlamoqda"
                            : "Jamoa kutmoqda"}
                      </span>
                      <span>
                        Har bir piksel ortida bir g‘oya bor<small>✦</small>
                      </span>
                    </footer>
                  </section>
                  <section className="team-section">
                    <div className="section-heading">
                      <h2>
                        Jamoangiz <span>05</span>
                      </h2>
                      <button
                        className="text-button"
                        onClick={() => setView("team")}
                      >
                        Barchasini ko‘rish <ChevronRight size={14} />
                      </button>
                    </div>
                    <div className="agent-strip">
                      {data.agents.map((a) => (
                        <AgentCard
                          key={a.id}
                          agent={a}
                          selected={selected === a.id}
                          onClick={() => select(a.id)}
                        />
                      ))}
                    </div>
                  </section>
                  <section className="tasks-preview">
                    <div className="section-heading">
                      <h2>
                        Vazifalar{" "}
                        <span>
                          {activeTasks.length.toString().padStart(2, "0")}
                        </span>
                      </h2>
                      <button
                        className="text-button"
                        onClick={() => setView("tasks")}
                      >
                        Vazifalar doskasi <ChevronRight size={14} />
                      </button>
                    </div>
                    {activeTasks.length ? (
                      <div className="task-mini-list">
                        {activeTasks.slice(0, 3).map((t) => (
                          <div className="task-mini" key={t.id}>
                            <span className="task-outline" />
                            <span>{t.title}</span>
                            <span className="tag">
                              {taskStatus[t.status] || t.status}
                            </span>
                            <span className="secondary">
                              {
                                data.agents.find((a) => a.id === t.agent_id)
                                  ?.name
                              }
                            </span>
                          </div>
                        ))}
                      </div>
                    ) : (
                      <button
                        className="empty-task"
                        onClick={() => setModal("task")}
                      >
                        <span className="empty-task-icon">
                          <ListTodo size={22} />
                        </span>
                        <span>
                          <strong>
                            Katta g‘oya kichik vazifadan boshlanadi.
                          </strong>
                          <small>
                            Birinchi vazifani yarating va jamoaga topshiring.
                          </small>
                        </span>
                        <span className="empty-task-plus">
                          <Plus size={18} />
                        </span>
                      </button>
                    )}
                  </section>
                </>
              )}
              {view === "team" && (
                <>
                  <section className="page-heading">
                    <div>
                      <span className="eyebrow">THE PEOPLE, BUT PIXELS</span>
                      <h1>
                        Bir-birini to‘ldiradigan beshlik<span>.</span>
                      </h1>
                      <p>
                        Har bir agentning o‘z roli, xarakteri va ish joyi bor.
                      </p>
                    </div>
                  </section>
                  <div className="team-grid">
                    {data.agents.map((a) => (
                      <button
                        className={`team-profile ${selected === a.id ? "chosen" : ""}`}
                        onClick={() => select(a.id)}
                        key={a.id}
                      >
                        <div
                          className="profile-art"
                          style={{ background: a.color + "15" }}
                        >
                          <Avatar agent={a} size={70} />
                          <span className="ai-label">AI AGENT</span>
                        </div>
                        <div className="profile-content">
                          <h2>{a.name}</h2>
                          <span style={{ color: a.color }}>{a.role}</span>
                          <p>{a.description}</p>
                          <div className="profile-meta">
                            <span className="idle-dot" /> {agentStatus(a)}
                            <span>{a.model || "Model tanlanmagan"}</span>
                          </div>
                        </div>
                      </button>
                    ))}
                  </div>
                </>
              )}
              {view === "tasks" && (
                <>
                  <section className="page-heading">
                    <div>
                      <span className="eyebrow">ONE THING AT A TIME</span>
                      <h1>
                        Rejadan natijagacha<span>.</span>
                      </h1>
                      <p>
                        Vazifalar, mas’ullar va har bir ishning hozirgi holati.
                      </p>
                    </div>
                    <button
                      className="primary"
                      onClick={() => setModal("task")}
                    >
                      <Plus size={17} />
                      Yangi vazifa
                    </button>
                  </section>
                  <div className="task-filters">
                    {[
                      ["all", "Barchasi"],
                      ["new", "Navbatda"],
                      ["running", "Bajarilmoqda"],
                      ["review", "Ko‘rib chiqish"],
                      ["paused", "Pauzada"],
                      ["error", "Xatolik"],
                      ["cancelled", "Bekor qilingan"],
                    ].map(([id, label]) => (
                      <button
                        key={id}
                        className={taskFilter === id ? "active" : ""}
                        onClick={() => setTaskFilter(id)}
                      >
                        {label}
                        <span>
                          {
                            data.tasks.filter(
                              (t) => id === "all" || t.status === id,
                            ).length
                          }
                        </span>
                      </button>
                    ))}
                  </div>
                  <div className="task-table">
                    <div className="task-table-head">
                      <span>VAZIFA</span>
                      <span>MAS’UL</span>
                      <span>HOLAT</span>
                      <span />
                    </div>
                    {data.tasks
                      .filter(
                        (t) => taskFilter === "all" || t.status === taskFilter,
                      )
                      .map((t) => (
                        <div className="task-row" key={t.id}>
                          <div>
                            <span className="task-outline" />
                            <strong>{t.title}</strong>
                            <small>
                              {t.description || "Tavsif qo‘shilmagan"}
                            </small>
                          </div>
                          <span>
                            {data.agents.find((a) => a.id === t.agent_id)?.name}
                          </span>
                          <span
                            className={`tag ${t.status === "cancelled" ? "muted" : ""}`}
                          >
                            {taskStatus[t.status] || t.status}
                          </span>
                          {t.status === "review" ? (
                            <IconButton
                              label={`${t.title}ni yakunlash`}
                              onClick={() => void complete(t.id)}
                            >
                              <Check size={16} />
                            </IconButton>
                          ) : !["cancelled", "done"].includes(t.status) ? (
                            <div className="task-actions">
                              {["paused", "error"].includes(t.status) && (
                                <IconButton
                                  label={`${t.title}ni davom ettirish`}
                                  onClick={() => void changeTask(t.id, "run")}
                                >
                                  <Play size={15} />
                                </IconButton>
                              )}
                              {["new", "running"].includes(t.status) && (
                                <IconButton
                                  label={`${t.title}ni pauza qilish`}
                                  onClick={() => void changeTask(t.id, "pause")}
                                >
                                  <Pause size={15} />
                                </IconButton>
                              )}
                              <IconButton
                                label={`${t.title}ni bekor qilish`}
                                onClick={() => void cancel(t.id)}
                              >
                                <X size={15} />
                              </IconButton>
                            </div>
                          ) : (
                            <span />
                          )}
                        </div>
                      ))}
                    {!data.tasks.filter(
                      (t) => taskFilter === "all" || t.status === taskFilter,
                    ).length && (
                      <div className="empty-board">
                        <ListTodo size={36} />
                        <h3>Hozircha vazifa yo‘q</h3>
                        <p>Jamoaga birinchi vazifani bering.</p>
                        <button
                          className="primary"
                          onClick={() => setModal("task")}
                        >
                          <Plus size={16} />
                          Vazifa yaratish
                        </button>
                      </div>
                    )}
                  </div>
                  <div className="inline-note">
                    <CircleHelp size={16} />
                    {data.integrations.executor
                      ? "Agentlar taklif va kod namunalarini tayyorlaydi. Kodni bajarish, test va deploy avtomatik yoqilmagan."
                      : "AI chaqiruvlari to‘xtatilgan yoki provayder ulanmagan. Vazifalar saqlanadi."}
                  </div>
                </>
              )}
              {view === "settings" && (
                <Settings
                  key={project}
                  project={project}
                  data={data}
                  onSaved={async (text) => {
                    setToast(text);
                    await refresh();
                  }}
                />
              )}
              <footer className="workspace-footer">
                <span>
                  <PixelMark /> Aniq maqsad. Yaxshi jamoa.
                </span>
                <span>
                  PIXEL TEAM <span className="version">v{data.version}</span>
                </span>
              </footer>
            </main>
            <aside className="chat-panel">
              <header className="chat-panel-head">
                <div>
                  <MessageSquare size={17} />
                  <h2>Jamoa chati</h2>
                  <span>5</span>
                </div>
                <div className="chat-header-actions">
                  <IconButton
                    label={
                      chatFocus
                        ? "Ofisga qaytish"
                        : "Chatni to‘liq ekranga ochish"
                    }
                    onClick={() => setChatFocus(!chatFocus)}
                  >
                    {chatFocus ? <Minimize2 size={18} /> : <Expand size={18} />}
                  </IconButton>
                  <IconButton
                    label="Chat haqida"
                    onClick={() => setModal("help")}
                  >
                    <MoreHorizontal size={19} />
                  </IconButton>
                </div>
              </header>
              <div className="chat-tabs">
                <button
                  className={chatTab === "chat" ? "active" : ""}
                  onClick={() => setChatTab("chat")}
                >
                  Suhbat
                </button>
                <button
                  className={chatTab === "activity" ? "active" : ""}
                  onClick={() => setChatTab("activity")}
                >
                  Faollik <span>{data.events.length}</span>
                </button>
              </div>
              <div
                className="chat-stream"
                ref={chatStream}
                onScroll={() => {
                  const stream = chatStream.current;
                  if (stream && chatTab === "chat")
                    followChat.current =
                      stream.scrollHeight -
                        stream.scrollTop -
                        stream.clientHeight <
                      120;
                }}
              >
                {chatTab === "chat" ? (
                  <>
                    {!data.messages.length && (
                      <div className="welcome-message">
                        <div className="welcome-icon">
                          <PixelMark />
                        </div>
                        <h3>Jamoaga yozing</h3>
                        <p>
                          Agentga to‘g‘ridan to‘g‘ri yozish uchun @developer
                          yoki @qa deb boshlang.
                        </p>
                        <div className="tiny-team">
                          {data.agents.map((a) => (
                            <div
                              key={a.id}
                              style={{ background: a.color + "20" }}
                            >
                              <Avatar agent={a} size={22} />
                            </div>
                          ))}
                        </div>
                      </div>
                    )}
                    {data.messages.length > 0 && (
                      <div className="chat-date">SUHBAT</div>
                    )}
                    {data.messages.map((m) => {
                      const speaker = data.agents.find(
                        (a) => a.id === m.sender,
                      );
                      return (
                        <div
                          className={`message ${speaker ? "agent-message" : ""}`}
                          key={m.id}
                        >
                          <div
                            className="message-avatar"
                            style={
                              speaker
                                ? {
                                    background: speaker.color + "20",
                                    borderColor: speaker.color + "60",
                                  }
                                : undefined
                            }
                          >
                            {speaker ? (
                              <Avatar agent={speaker} size={24} />
                            ) : (
                              "S"
                            )}
                          </div>
                          <div>
                            <header>
                              <strong>{speaker?.name || "Siz"}</strong>
                              {speaker && <span className="ai-chip">AI</span>}
                              <time>{now(m.created_at)}</time>
                            </header>
                            <MessageText
                              text={m.text}
                              markdown={Boolean(speaker)}
                            />
                          </div>
                        </div>
                      );
                    })}
                    {!data.integrations.executor && (
                      <div className="chat-system-note">
                        <span className="idle-dot" />
                        <span>
                          AI chaqiruvlari o‘chirilgan yoki provayder ulanmagan.
                          Xabarlaringiz saqlanadi.
                        </span>
                      </div>
                    )}
                    {data.jobs.some(
                      (j) => j.status === "queued" || j.status === "running",
                    ) && (
                      <div className="typing-indicator">
                        <Loader2 className="spin" size={13} />
                        Agent javob tayyorlamoqda…
                      </div>
                    )}
                  </>
                ) : (
                  <div className="activity-list">
                    {data.events.map((event) => (
                      <div className="activity-item" key={event.id}>
                        <div className="activity-line">
                          <span />
                        </div>
                        <div>
                          <p>{event.text}</p>
                          <time>{now(event.created_at)}</time>
                        </div>
                      </div>
                    ))}
                  </div>
                )}
              </div>
              {chosen ? (
                <AgentDetails
                  agent={chosen}
                  providers={data.providers}
                  jobs={data.jobs.filter((job) => job.agent_id === chosen.id)}
                  steps={data.job_steps}
                  onClose={() => setSelected(null)}
                  onSaved={async () => {
                    setToast("Agent sozlamalari saqlandi.");
                    await refresh();
                  }}
                />
              ) : (
                <div className="integration-note">
                  <div className="integration-icon">
                    <ShieldCheck size={18} />
                  </div>
                  <div>
                    <strong>Sizning shaxsiy jamoangiz</strong>
                    <p>Chat va vazifalar faqat siz uchun.</p>
                    {data.runtime?.public_url && (
                      <p>
                        {data.runtime.environment.toUpperCase()} ·{" "}
                        {data.runtime.public_url.replace(/^https?:\/\//, "")}
                        {data.runtime.server_ip
                          ? ` · ${data.runtime.server_ip}`
                          : ""}
                      </p>
                    )}
                  </div>
                </div>
              )}
              <form className="chat-compose" onSubmit={send}>
                <div className="chat-roles" aria-label="Agentga murojaat">
                  {data.agents
                    .filter((a) => a.enabled)
                    .map((a) => (
                      <button
                        key={a.id}
                        type="button"
                        onClick={() => {
                          setDraft(
                            (value) =>
                              `@${a.id} ${value.replace(/^@\w+\s*/, "")}`,
                          );
                          document.getElementById("chat-input")?.focus();
                        }}
                      >
                        @{a.id}
                      </button>
                    ))}
                </div>
                <label className="sr-only" htmlFor="chat-input">
                  Jamoaga xabar
                </label>
                <textarea
                  id="chat-input"
                  placeholder="Jamoaga biror narsa yozing…"
                  value={draft}
                  onChange={(e) => setDraft(e.target.value)}
                  maxLength={6000}
                  onKeyDown={(e) => {
                    if (e.key === "Enter" && !e.shiftKey) {
                      e.preventDefault();
                      void send(e);
                    }
                  }}
                />
                <div>
                  <span>
                    Shift + Enter <span>yangi qator</span>
                  </span>
                  <button
                    className="send-button"
                    disabled={!draft.trim() || sending}
                    aria-label="Xabar yuborish"
                  >
                    {sending ? (
                      <Loader2 className="spin" size={16} />
                    ) : (
                      <ArrowUp size={18} />
                    )}
                  </button>
                </div>
              </form>
              <div className="chat-bottom">
                <span className="saved-dot" />
                Tarix saqlanadi · {data.usage.tokens.toLocaleString()} token
                <ShieldCheck size={12} />
              </div>
            </aside>
          </div>
        )}
      </div>
      {modal === "task" && data && (
        <TaskModal
          agents={data.agents}
          project={project}
          onClose={() => setModal(null)}
          onSaved={async () => {
            setModal(null);
            setToast("Vazifa navbatga qo‘shildi.");
            await refresh();
          }}
        />
      )}
      {modal === "project" && (
        <ProjectModal
          onClose={() => setModal(null)}
          onSaved={async (id) => {
            setModal(null);
            setProject(id);
            setToast("Yangi loyiha yaratildi.");
          }}
        />
      )}
      {modal === "help" && (
        <Modal title="Pixel Team haqida" onClose={() => setModal(null)}>
          <div className="help-content">
            <div className="help-pixel">
              <PixelMark />
            </div>
            <h3>O‘z jamoangizning kichik olami.</h3>
            <p>
              Pixel Agents’dan ilhomlangan, mustaqil yaratilgan shaxsiy AI ofis.
              Personajni yoki agent kartasini bosing — uning sozlamalari
              ochiladi.
            </p>
            <p>
              Chat, loyihalar va vazifalar saqlanadi. AI provayder matnli
              javoblar va vazifa takliflarini tayyorlaydi. GitHub va kodni
              bajarish alohida bosqichda ulanadi.
            </p>
            <p>
              Personajlarning yurishi ofis animatsiyasi; bajarilgan ish degani
              emas.
            </p>
            <button className="primary full" onClick={() => setModal(null)}>
              Tushunarli
            </button>
          </div>
        </Modal>
      )}
      {toast && (
        <div className="toast" role="status">
          <Check size={16} />
          {toast}
          <button
            onClick={() => setToast("")}
            aria-label="Bildirishnomani yopish"
          >
            <X size={14} />
          </button>
        </div>
      )}
    </div>
  );
}
function AgentCard({
  agent,
  selected,
  onClick,
}: {
  agent: Agent;
  selected: boolean;
  onClick: () => void;
}) {
  const Icon = icons[agent.id] || Code2;
  return (
    <button
      className={`agent-card ${selected ? "chosen" : ""} ${agent.status === "working" ? "is-working" : ""}`}
      style={{ "--agent-color": agent.color } as React.CSSProperties}
      onClick={onClick}
    >
      <div className="agent-card-top">
        <div className="avatar-tile">
          <Avatar agent={agent} size={31} />
        </div>
        <span className="role-icon">
          <Icon size={14} />
        </span>
      </div>
      <strong>{agent.name}</strong>
      <small>{agent.role}</small>
      <span className="agent-status">
        <span />
        {agentStatus(agent)}
      </span>
    </button>
  );
}
function AgentDetails({
  agent,
  providers,
  jobs,
  steps,
  onClose,
  onSaved,
}: {
  agent: Agent;
  providers: Provider[];
  jobs: Studio["jobs"];
  steps: Studio["job_steps"];
  onClose: () => void;
  onSaved: () => Promise<void>;
}) {
  const [model, setModel] = useState(agent.model),
    [persona, setPersona] = useState(agent.persona),
    [provider, setProvider] = useState(agent.provider_id),
    [callLimit, setCallLimit] = useState(
      agent.monthly_call_limit?.toString() ?? "",
    ),
    [enabled, setEnabled] = useState(!!agent.enabled),
    [busy, setBusy] = useState(false),
    [error, setError] = useState("");
  useEffect(() => {
    setModel(agent.model);
    setPersona(agent.persona);
    setProvider(agent.provider_id);
    setCallLimit(agent.monthly_call_limit?.toString() ?? "");
    setEnabled(!!agent.enabled);
  }, [
    agent.id,
    agent.model,
    agent.persona,
    agent.enabled,
    agent.monthly_call_limit,
    agent.provider_id,
  ]);
  const save = async (e: FormEvent) => {
    e.preventDefault();
    setBusy(true);
    try {
      await api(`/api/agents/${agent.id}`, {
        method: "PATCH",
        body: JSON.stringify({
          model,
          persona,
          enabled,
          ...(provider !== agent.provider_id ? { provider_id: provider } : {}),
          monthly_call_limit: callLimit ? Number(callLimit) : null,
        }),
      });
      await onSaved();
      setError("");
    } catch (e) {
      setError((e as Error).message);
    } finally {
      setBusy(false);
    }
  };
  const latest = jobs.find((job) => job.status === "running") || jobs[0];
  const timeline = steps.filter((step) => step.job_id === latest?.id).reverse();
  return (
    <section className="agent-details">
      <header>
        <div>
          <span style={{ color: agent.color }}>
            <Avatar agent={agent} size={24} />
          </span>
          <div>
            <strong>{agent.name}</strong>
            <small>AI AGENT / {agent.role}</small>
          </div>
        </div>
        <IconButton label="Agent tafsilotlarini yopish" onClick={onClose}>
          <X size={15} />
        </IconButton>
      </header>
      <div className="agent-timeline" aria-label="Agent ish bosqichlari">
        <strong>Ish bosqichlari</strong>
        {latest ? (
          <>
            <span className={`job-status ${latest.status}`}>
              {jobStatus[latest.status] || latest.status}
            </span>
            <ol>
              {timeline.map((step, i) => (
                <li key={i}>
                  <span>{stepLabels[step.step] || step.step}</span>
                  <time>{now(step.created_at)}</time>
                </li>
              ))}
            </ol>
            {latest.error_code && (
              <small>
                {latest.error_code === "output_limit"
                  ? "Javob limitga sig‘madi."
                  : `Sabab: ${latest.error_code}`}
              </small>
            )}
          </>
        ) : (
          <p className="secondary">Bu loyihada ish hali boshlanmagan.</p>
        )}
      </div>
      <form onSubmit={save}>
        <label>
          Provayder
          <select
            value={provider}
            onChange={(e) => {
              setProvider(e.target.value);
              setModel("");
            }}
          >
            {providers
              .filter((p) => p.configured || p.id === agent.provider_id)
              .map((p) => (
                <option key={p.id} value={p.id}>
                  {p.name}
                </option>
              ))}
          </select>
        </label>
        <label>
          Model
          <input
            value={model}
            onChange={(e) => setModel(e.target.value)}
            placeholder={
              providers.find((p) => p.id === provider)?.model ||
              "Provayderning standart modeli"
            }
            maxLength={160}
          />
        </label>
        <label>
          Fe’l-atvor
          <textarea
            value={persona}
            onChange={(e) => setPersona(e.target.value)}
            placeholder="Masalan: o‘zbekcha, qisqa va aniq javob ber."
            maxLength={2000}
          />
        </label>
        <label>
          Oylik so‘rov limiti
          <input
            type="number"
            min={1}
            max={10000}
            placeholder="Umumiy limit"
            value={callLimit}
            onChange={(e) => setCallLimit(e.target.value)}
          />
        </label>
        <div className="agent-save">
          <label className="toggle-label">
            <input
              type="checkbox"
              checked={enabled}
              onChange={(e) => setEnabled(e.target.checked)}
            />
            Agent faol
          </label>
          <button className="secondary-button" disabled={busy}>
            {busy ? "Saqlanmoqda…" : "Saqlash"}
          </button>
        </div>
        {error && <p className="form-error">{error}</p>}
      </form>
    </section>
  );
}
function TaskModal({
  agents,
  project,
  onClose,
  onSaved,
}: {
  agents: Agent[];
  project: string;
  onClose: () => void;
  onSaved: () => Promise<void>;
}) {
  const [title, setTitle] = useState(""),
    [description, setDescription] = useState(""),
    [agent, setAgent] = useState("developer"),
    [busy, setBusy] = useState(false),
    [error, setError] = useState("");
  const save = async (e: FormEvent) => {
    e.preventDefault();
    setBusy(true);
    try {
      await api("/api/tasks", {
        method: "POST",
        body: JSON.stringify({
          title,
          description,
          agent_id: agent,
          project_id: project,
        }),
      });
      await onSaved();
    } catch (e) {
      setError((e as Error).message);
    } finally {
      setBusy(false);
    }
  };
  return (
    <Modal title="Jamoaga yangi vazifa" onClose={onClose}>
      <form className="modal-form" onSubmit={save}>
        <label>
          Vazifa nomi
          <input
            autoFocus
            required
            placeholder="Nimani amalga oshiramiz?"
            value={title}
            onChange={(e) => setTitle(e.target.value)}
            maxLength={180}
          />
        </label>
        <label>
          Tafsilotlar
          <textarea
            placeholder="Kutilgan natija va muhim talablarni yozing…"
            value={description}
            onChange={(e) => setDescription(e.target.value)}
            maxLength={6000}
            rows={4}
          />
        </label>
        <label>
          Mas’ul agent
          <select value={agent} onChange={(e) => setAgent(e.target.value)}>
            {agents.map((a) => (
              <option value={a.id} key={a.id}>
                {a.name} — {a.role}
              </option>
            ))}
          </select>
        </label>
        <div className="inline-note">
          <CircleHelp size={16} />
          Vazifa navbatga saqlanadi. AI yoqilgan bo‘lsa, mas’ul agent taklif
          tayyorlaydi. Kod avtomatik bajarilmaydi.
        </div>
        {error && <p className="form-error">{error}</p>}
        <div className="modal-actions">
          <button type="button" className="secondary-button" onClick={onClose}>
            Bekor qilish
          </button>
          <button className="primary" disabled={busy || !title.trim()}>
            <Plus size={16} />
            {busy ? "Saqlanmoqda…" : "Vazifa yaratish"}
          </button>
        </div>
      </form>
    </Modal>
  );
}
function ProjectModal({
  onClose,
  onSaved,
}: {
  onClose: () => void;
  onSaved: (id: string) => Promise<void>;
}) {
  const [name, setName] = useState(""),
    [error, setError] = useState(""),
    [busy, setBusy] = useState(false);
  const save = async (e: FormEvent) => {
    e.preventDefault();
    setBusy(true);
    try {
      const project = await api<{ id: string }>("/api/projects", {
        method: "POST",
        body: JSON.stringify({ name }),
      });
      await onSaved(project.id);
    } catch (e) {
      setError((e as Error).message);
    } finally {
      setBusy(false);
    }
  };
  return (
    <Modal title="Yangi loyiha" onClose={onClose}>
      <form className="modal-form" onSubmit={save}>
        <p className="secondary">
          Har bir loyihaning alohida suhbati va vazifalari bor.
        </p>
        <label>
          Loyiha nomi
          <input
            required
            autoFocus
            value={name}
            onChange={(e) => setName(e.target.value)}
            placeholder="Keyingi katta g‘oya"
            maxLength={80}
          />
        </label>
        {error && <p className="form-error">{error}</p>}
        <button className="primary full" disabled={busy || !name.trim()}>
          <Folder size={16} />
          {busy ? "Yaratilmoqda…" : "Loyiha yaratish"}
        </button>
      </form>
    </Modal>
  );
}
function Settings({
  project,
  data,
  onSaved,
}: {
  project: string;
  data: Studio;
  onSaved: (message: string) => Promise<void>;
}) {
  const [providerId, setProviderId] = useState("deepseek");
  const provider = data.providers.find((p) => p.id === providerId);
  const [customId, setCustomId] = useState("");
  const [providerName, setProviderName] = useState("");
  const [baseUrl, setBaseUrl] = useState("");
  const [key, setKey] = useState(""),
    [model, setModel] = useState(provider?.model ?? ""),
    [busy, setBusy] = useState(false),
    [error, setError] = useState("");
  const [testMessage, setTestMessage] = useState("");
  const [testing, setTesting] = useState(false);
  const pickProvider = (id: string) => {
    const picked = data.providers.find((p) => p.id === id);
    setProviderId(id);
    setProviderName(picked?.name ?? "");
    setBaseUrl(picked?.base_url ?? "");
    setModel(picked?.model ?? "");
    setKey("");
    setError("");
    setTestMessage("");
  };
  const testConnection = async () => {
    setTesting(true);
    setTestMessage("");
    try {
      const result = await api<{
        model: string;
        latency_ms: number;
        model_available: boolean;
      }>("/api/providers/" + providerId + "/test", { method: "POST" });
      setTestMessage(
        result.model_available
          ? `${result.model} mavjud · ${result.latency_ms} ms`
          : `${result.model} katalogda topilmadi.`,
      );
    } catch (e) {
      setTestMessage((e as Error).message);
    } finally {
      setTesting(false);
    }
  };
  const [memory, setMemory] = useState(data.project_memory);
  const [memoryBusy, setMemoryBusy] = useState(false);
  const [memoryError, setMemoryError] = useState("");
  const saveMemory = async (e: FormEvent) => {
    e.preventDefault();
    setMemoryBusy(true);
    setMemoryError("");
    try {
      await api(`/api/projects/${encodeURIComponent(project)}/memory`, {
        method: "PUT",
        body: JSON.stringify({ text: memory }),
      });
      await onSaved("Loyiha xotirasi saqlandi.");
    } catch (e) {
      setMemoryError((e as Error).message);
    } finally {
      setMemoryBusy(false);
    }
  };
  const save = async (e: FormEvent) => {
    e.preventDefault();
    setBusy(true);
    try {
      const id = providerId === "new" ? customId.trim() : providerId;
      await api("/api/providers/" + encodeURIComponent(id), {
        method: "PUT",
        body: JSON.stringify({
          api_key: key,
          model,
          name: providerName,
          base_url: baseUrl,
        }),
      });
      setProviderId(id);
      setKey("");
      setError("");
      await onSaved("Provayder saqlandi.");
    } catch (e) {
      setError((e as Error).message);
    } finally {
      setBusy(false);
    }
  };
  return (
    <>
      <section className="page-heading">
        <div>
          <span className="eyebrow">MAKE IT YOURS</span>
          <h1>
            Jamoangiz, sizning qoidalaringiz<span>.</span>
          </h1>
          <p>AI provayder va integratsiyalarni boshqaring.</p>
        </div>
      </section>
      <div className="settings-card">
        <header>
          <div className="provider-mark">
            <Code2 size={24} />
          </div>
          <div>
            <h2>AI provayderlar</h2>
            <p>Har bir agent uchun provayderni alohida tanlash mumkin.</p>
          </div>
          <span className={`tag ${provider?.configured ? "" : "muted"}`}>
            {provider?.configured ? "Sozlangan" : "Ulanmagan"}
          </span>
        </header>
        <form onSubmit={save}>
          <label>
            Provayder
            <select
              value={providerId}
              onChange={(e) => pickProvider(e.target.value)}
            >
              {data.providers.map((p) => (
                <option key={p.id} value={p.id}>
                  {p.name}
                </option>
              ))}
              <option value="new">Yangi provayder qo‘shish</option>
            </select>
          </label>
          {providerId === "new" && (
            <label>
              Provayder ID
              <input
                required
                value={customId}
                maxLength={32}
                pattern="[a-z][a-z0-9-]{0,31}"
                onChange={(e) => setCustomId(e.target.value)}
                placeholder="Masalan, openrouter"
              />
            </label>
          )}
          {providerId !== "deepseek" && (
            <>
              <label>
                Provayder nomi
                <input
                  value={providerName}
                  maxLength={60}
                  onChange={(e) => setProviderName(e.target.value)}
                />
              </label>
              <label>
                OpenAI-compatible Base URL
                <input
                  type="url"
                  required
                  value={baseUrl}
                  maxLength={250}
                  onChange={(e) => setBaseUrl(e.target.value)}
                  placeholder="https://openrouter.ai/api/v1"
                />
              </label>
            </>
          )}
          <label>
            API kaliti
            <input
              type="password"
              autoComplete="off"
              placeholder={
                provider?.configured
                  ? "•••••••• (o‘zgartirish uchun yangi kalit)"
                  : "Provayder API kaliti"
              }
              value={key}
              onChange={(e) => setKey(e.target.value)}
              required={!provider?.configured}
            />
          </label>
          <label>
            Model ID
            <input
              value={model}
              onChange={(e) => setModel(e.target.value)}
              placeholder="Provayderdagi aniq model ID"
              required
              maxLength={160}
            />
          </label>
          <div className="inline-note">
            <ShieldCheck size={16} />
            Kalit shifrlanadi va brauzerga qaytarilmaydi. Saqlash pulli so‘rov
            yubormaydi.
          </div>
          {error && <p className="form-error">{error}</p>}
          <button className="primary" disabled={busy}>
            <Check size={16} />
            {busy ? "Saqlanmoqda…" : "Sozlamalarni saqlash"}
          </button>
          <button
            type="button"
            className="secondary-button provider-check"
            disabled={testing || !provider?.configured}
            onClick={() => void testConnection()}
          >
            {testing ? "Tekshirilmoqda…" : "Ulanishni tekshirish"}
          </button>
          {testMessage && (
            <p className="secondary" role="status">
              {testMessage}
            </p>
          )}
        </form>
      </div>
      <LimitsForm data={data} onSaved={onSaved} />
      <section className="settings-card limits-card">
        <h2>Loyiha xotirasi</h2>
        <p className="secondary">
          Serverdagi loyiha tavsifi{" "}
          {data.project_brief_connected ? "ulangan" : "ulanmagan"}.
        </p>
        <form onSubmit={saveMemory}>
          <label>
            Agent bilishi kerak bo‘lgan faktlar va kelishuvlar
            <textarea
              rows={4}
              maxLength={800}
              value={memory}
              onChange={(e) => setMemory(e.target.value)}
            />
          </label>
          {memoryError && <p className="form-error">{memoryError}</p>}
          <button className="primary" disabled={memoryBusy}>
            Xotirani saqlash
          </button>
        </form>
      </section>
      <section className="settings-card limits-card telegram-card">
        <h2>Telegram</h2>
        <p className="secondary">
          {data.integrations.telegram_status.connected
            ? "Guruh ulangan"
            : data.integrations.telegram_status.configured
              ? "Ulanish kutilmoqda"
              : "Sozlanmagan"}{" "}
          · {data.integrations.telegram_status.bots}/5 bot tokeni · Ovoz{" "}
          {data.integrations.telegram_status.voice
            ? "sozlangan"
            : "sozlanmagan"}
        </p>
        {data.attachments.length > 0 && (
          <ul className="attachment-list">
            {data.attachments.map((file) => (
              <li key={file.id}>
                <a
                  href={`/api/projects/${encodeURIComponent(project)}/attachments/${file.id}`}
                >
                  {file.name}
                </a>
                <span>{Math.ceil(file.size / 1024)} KB</span>
              </li>
            ))}
          </ul>
        )}
      </section>
      <div className="integration-grid">
        {[
          ["GitHub", "Branch, PR va CI natijalari"],
          ["Kod ijrosi", "Cheklangan ish maydoni va bajariladigan testlar"],
        ].map(([title, description]) => (
          <div className="integration-card" key={title}>
            <h3>
              {title}
              <span className="tag muted">Keyingi bosqich</span>
            </h3>
            <p>{description}</p>
          </div>
        ))}
      </div>
    </>
  );
}

function LimitsForm({
  data,
  onSaved,
}: {
  data: Studio;
  onSaved: (message: string) => Promise<void>;
}) {
  const [limits, setLimits] = useState(data.limits),
    [busy, setBusy] = useState(false),
    [error, setError] = useState("");
  const save = async (e: FormEvent) => {
    e.preventDefault();
    setBusy(true);
    try {
      await api("/api/limits", {
        method: "POST",
        body: JSON.stringify(limits),
      });
      await onSaved("AI limitlari yangilandi.");
      setError("");
    } catch (e) {
      setError((e as Error).message);
    } finally {
      setBusy(false);
    }
  };
  return (
    <section className="settings-card limits-card">
      <header>
        <div>
          <h2>AI chaqiruvlari va limitlar</h2>
          <p>
            Bu oy: {data.usage.calls} ta so‘rov ·{" "}
            {data.usage.tokens.toLocaleString()} ta o‘lchangan token
          </p>
        </div>
      </header>
      <form onSubmit={save}>
        <label className="toggle-label">
          <input
            type="checkbox"
            checked={limits.paid_calls_enabled}
            onChange={(e) =>
              setLimits({ ...limits, paid_calls_enabled: e.target.checked })
            }
          />
          Yangi pulli AI chaqiruvlariga ruxsat
        </label>
        <p className="secondary">
          Prompt cache: {data.usage.cached_tokens.toLocaleString()} /{" "}
          {data.usage.input_tokens.toLocaleString()} kirish tokeni
        </p>
        {data.usage.by_agent.length > 0 && (
          <ul className="attachment-list">
            {data.usage.by_agent.map((agent) => (
              <li key={agent.agent_id + ":" + agent.provider_id}>
                <strong>
                  {data.agents.find((a) => a.id === agent.agent_id)?.name ||
                    agent.agent_id}
                </strong>
                <span>
                  {data.providers.find((p) => p.id === agent.provider_id)
                    ?.name || agent.provider_id}{" "}
                  · {agent.calls} so‘rov ·{" "}
                  {(agent.input_tokens + agent.output_tokens).toLocaleString()}{" "}
                  token · {agent.cached_tokens.toLocaleString()} cache
                </span>
              </li>
            ))}
          </ul>
        )}
        <div className="limits-grid">
          <label>
            Oylik so‘rov limiti
            <input
              type="number"
              required
              min={1}
              max={10000}
              value={limits.monthly_call_limit}
              onChange={(e) =>
                setLimits({
                  ...limits,
                  monthly_call_limit: Number(e.target.value),
                })
              }
            />
          </label>
          <label>
            Oylik token limiti
            <input
              type="number"
              required
              min={1000}
              max={10000000}
              value={limits.monthly_token_limit}
              onChange={(e) =>
                setLimits({
                  ...limits,
                  monthly_token_limit: Number(e.target.value),
                })
              }
            />
          </label>
          <label>
            Bitta javob uchun token
            <input
              type="number"
              required
              min={64}
              max={4096}
              value={limits.max_output_tokens}
              onChange={(e) =>
                setLimits({
                  ...limits,
                  max_output_tokens: Number(e.target.value),
                })
              }
            />
          </label>
        </div>
        <div className="inline-note">
          <ShieldCheck size={16} />
          Limitga yetganda yangi so‘rov yuborilmaydi. Boshlangan so‘rov
          yakunlanishi mumkin. Pul narxi taxmin qilinmaydi; haqiqiy hisob
          provayder kabinetida.
        </div>
        {error && <p className="form-error">{error}</p>}
        <button className="primary" disabled={busy}>
          {busy ? "Saqlanmoqda…" : "Limitlarni saqlash"}
        </button>
      </form>
    </section>
  );
}
