import client from './client';

export interface Template {
  template_id: string;
  name: string;
  description: string;
  configurable_params: Array<{
    name: string;
    type: string;
    default: any;
  }>;
}

export interface TemplateDetail extends Template {
  version: string;
  steps: Array<{
    step_type: string;
    depends_on: string[];
    output_key: string;
    parameters: Record<string, any>;
  }>;
}

export interface WorkflowCreateRequest {
  template_id: string;
  session_id: string;
  parameters: Record<string, any>;
}

export interface WorkflowCreateResponse {
  workflow_id: string;
  template_id: string;
  job_id: string;
  step_count: number;
  status: string;
}

export interface JobResponse {
  job: Record<string, any>;
  tasks: Array<{
    task_id: string;
    job_id: string;
    step_type: string;
    order_num: number;
    status: string;
    started_at: string | null;
    completed_at: string | null;
    error_message: string | null;
    result_keys: string[];
  }>;
}

export async function listTemplates(): Promise<Template[]> {
  const resp = await client.get('/flow-builder/templates');
  return resp.data;
}

export async function getTemplate(templateId: string): Promise<TemplateDetail> {
  const resp = await client.get(`/flow-builder/templates/${templateId}`);
  return resp.data;
}

export async function createWorkflow(
  templateId: string,
  sessionId: string,
  parameters: Record<string, any>,
): Promise<WorkflowCreateResponse> {
  const resp = await client.post('/flow-builder/workflows', {
    template_id: templateId,
    session_id: sessionId,
    parameters,
  });
  return resp.data;
}

export async function getJob(jobId: string): Promise<JobResponse> {
  const resp = await client.get(`/perfact/jobs/${jobId}`);
  return resp.data;
}

export async function getJobTasks(jobId: string) {
  const resp = await client.get(`/perfact/jobs/${jobId}/tasks`);
  return resp.data;
}

export async function listJobs(sessionId?: string) {
  const params = sessionId ? { session_id: sessionId } : {};
  const resp = await client.get('/perfact/jobs', { params });
  return resp.data;
}
