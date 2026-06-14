import { corsHeaders, jsonResponse } from './cors.js';

export async function handleTrigger(request, env) {
  if (request.method !== 'POST') {
    return new Response('Method Not Allowed', {
      status: 405,
      headers: corsHeaders(),
    });
  }

  const pat = env.GITHUB_PAT;
  if (!pat) {
    return jsonResponse({ error: 'GITHUB_PAT secret is not configured in Cloudflare Worker.' }, 500);
  }

  const owner = 'mamibj112-spec';
  const repo = 'dashboard';
  const workflowId = 'daily.yml';

  try {
    // 1. Check if the workflow is already running or queued
    const runsUrl = `https://api.github.com/repos/${owner}/${repo}/actions/workflows/${workflowId}/runs?per_page=5`;
    const runsResponse = await fetch(runsUrl, {
      headers: {
        'Authorization': `token ${pat}`,
        'Accept': 'application/vnd.github.v3+json',
        'User-Agent': 'cloudflare-worker-dashboard-trigger',
      },
    });

    if (!runsResponse.ok) {
      const errorText = await runsResponse.text();
      return jsonResponse({ error: `Failed to fetch workflow runs: ${errorText}` }, runsResponse.status);
    }

    const runsData = await runsResponse.json();
    const runs = runsData.workflow_runs || [];

    // Look for any run that is currently active (queued, in_progress, requested, waiting)
    const activeRun = runs.find(
      (run) =>
        run.status === 'queued' ||
        run.status === 'in_progress' ||
        run.status === 'requested' ||
        run.status === 'waiting'
    );

    if (activeRun) {
      return jsonResponse({
        status: 'running',
        message: '이미 업데이트 워크플로가 대기 중이거나 실행 중입니다. 잠시만 기다려주세요.',
        run_url: activeRun.html_url,
      }, 409);
    }

    // 2. Trigger the workflow_dispatch
    const dispatchUrl = `https://api.github.com/repos/${owner}/${repo}/actions/workflows/${workflowId}/dispatches`;
    const dispatchResponse = await fetch(dispatchUrl, {
      method: 'POST',
      headers: {
        'Authorization': `token ${pat}`,
        'Accept': 'application/vnd.github.v3+json',
        'Content-Type': 'application/json',
        'User-Agent': 'cloudflare-worker-dashboard-trigger',
      },
      body: JSON.stringify({ ref: 'main' }),
    });

    if (dispatchResponse.status === 204) {
      return jsonResponse({
        status: 'success',
        message: '업데이트가 성공적으로 시작되었습니다. 완료까지 1~2분이 소요됩니다.',
      });
    } else {
      const errorText = await dispatchResponse.text();
      return jsonResponse({ error: `Failed to trigger workflow: ${errorText}` }, dispatchResponse.status);
    }
  } catch (e) {
    return jsonResponse({ error: e.message || 'Unknown error occurred.' }, 500);
  }
}
