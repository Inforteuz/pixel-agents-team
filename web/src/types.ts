export type Agent = {
  id: string;
  name: string;
  role: string;
  color: string;
  description: string;
  model: string;
  persona: string;
  enabled: number;
  monthly_call_limit: number | null;
  provider_id: string;
  status: "idle" | "working" | "paused";
};
export type Task = {
  id: string;
  project_id: string;
  title: string;
  description: string;
  agent_id: string;
  status: string;
  question: string | null;
  created_at: number;
};
export type Message = {
  id: string;
  sender: string;
  text: string;
  created_at: number;
};
export type Project = { id: string; name: string };
export type Provider = {
  id: string;
  name: string;
  adapter: string;
  base_url: string;
  model: string;
  configured: boolean;
};
export type Activity = {
  id: number;
  kind: string;
  text: string;
  created_at: number;
};
export type Studio = {
  agents: Agent[];
  projects: Project[];
  tasks: Task[];
  messages: Message[];
  events: Activity[];
  attachments: { id: number; name: string; kind: string; size: number }[];
  project_memory: string;
  project_brief_connected: boolean;
  providers: Provider[];
  integrations: {
    provider: boolean;
    model: string;
    telegram: boolean;
    telegram_status: {
      configured: boolean;
      connected: boolean;
      voice: boolean;
      bots: number;
    };
    github: boolean;
    executor: boolean;
  };
  usage: {
    calls: number;
    tokens: number;
    input_tokens: number;
    cached_tokens: number;
    cost: number | null;
    by_agent: {
      agent_id: string;
      provider_id: string;
      calls: number;
      input_tokens: number;
      output_tokens: number;
      cached_tokens: number;
    }[];
  };
  limits: {
    paid_calls_enabled: boolean;
    monthly_call_limit: number;
    monthly_token_limit: number;
    max_output_tokens: number;
  };
  runtime: {
    environment: string;
    public_url: string;
    server_host: string;
    server_ip: string;
  };
  jobs: {
    id: string;
    agent_id: string;
    status: string;
    error_code: string | null;
    created_at: number;
  }[];
  job_steps: { job_id: string; step: string; created_at: number }[];
  version: string;
};
